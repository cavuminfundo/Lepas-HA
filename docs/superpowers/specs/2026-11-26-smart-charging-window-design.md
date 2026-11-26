# Specifica di Design — Fase 2: Finestra di Ricarica Dinamica Smart (`Lepas`)

- **Data:** 2026-11-26
- **Stato:** Approvata nel brainstorming (in attesa di User Review Gate finale)
- **Target:** `custom_components/lepas` (Lepas L8 PHEV — Chery EU `com.chery.eu.lepas`)
- **Prerequisito:** Fase 1 (`v1.33.2`, commit `e4970ec`: `startTime` e `cycleData` UTC + floor 15m, `CMD_PROBE` su comandi carica, avviso `2132` differito al fallimento, isolamento `appointmentChargeState`)

---

## 0. Contesto, Obiettivi e Perimetro

### 0.1 Obiettivo
Evitare che la batteria da `18.4 kWh` (`DEFAULT_BATTERY_CAPACITY_KWH`) della Lepas L8 resti inutilmente ore al 100% di SoC prima della partenza programmata, spostando automaticamente in avanti `startTime` in modalità **Just-in-Time al 100%** in base al SoC residuo, alla potenza reale di ricarica domestica (auto-appresa separatamente per AC e DC o impostata manualmente) e al margine di bilanciamento CV, con **bypass automatico fuori casa** e **override immediato da Partenza rapida**.

### 0.2 Perimetro Fase 2 vs Fase 3
- **In scope (Fase 2):**
  1. Selettore unico modalità finestra domestica (`off`, `fixed`, `smart_departure`) con retrocompatibilità bidirezionale verso `switch.lepas_sync_charge_to_departure`.
  2. Bypass automatico fuori casa (`at_home is False`) per consentire ricariche immediate alle colonnine pubbliche senza blocchi da programmazione domestica.
  3. Calcolo energetico puro Just-in-Time al 100% basato su SoC filtrato, capacità batteria, potenza effettiva (AC vs DC), efficienza e margine CV, con cap di sicurezza `number.lepas_charge_duration`.
  4. Auto-apprendimento separato della potenza reale a casa (profilo AC vs profilo DC) in fase CC, persistito nello `Store` esistente di `charging_stats.py`, più controllo manuale/auto in HA.
  5. Override temporaneo da Partenza rapida (`switch.lepas_quick_departure`) sia sopra `fixed` sia sopra `smart_departure`.
  6. Gestione esplicita dei giorni liberi senza partenze entro 24h (`ricarica_prog_off` per ricarica immediata al collegamento) e del collegamento in ritardo.
  7. Trigger su collegamento cavo a casa (con debounce per SoC fresco), guardie batteria 12V, diagnostica e controlli in `lepas-card.js`.
- **Out of scope (rimandato a Fase 3):**
  - Modalità **Solar Power** (pianificazione su fascia/previsione FV o surplus wallbox): il selettore di modalità è strutturato per accogliere `solar` in futuro, ma in Fase 2 non vengono aggiunte opzioni non attive né codice morto.
  - Taglio automatico `< 100%` SoC (non supportato dal protocollo `chargeAppointControl`; in Just-in-Time il distacco al 100% è gestito in sicurezza dal BMS).
  - Controllo di wallbox/prese smart esterne o modulazione in ampere.

### 0.3 Vincoli Hardware / Protocollo & Anticorpi
- **Schema wire `/asc/vehicleControl/chargeAppointControl` (`chargeAppointPlans[0]`):**
  - `startTime`: `int` minuti dalla mezzanotte **UTC** (`0..1439`), allineato per difetto a multipli di `CHARGE_START_STEP_MINUTES = 15` (`AB-LEP-009`).
  - `timeConsuming`: `int` durata in minuti sul wire.
  - `cycleData`: `list[int]` giorni ISO `1..7` in **UTC**; su Lepas L8 con permesso `2131 = 0`, `effective_charge_days()` normalizza a `[1, 2, 3, 4, 5, 6, 7]` (la centralina esegue comunque la finestra entro le 24 ore successive).
  - `switchStatus`: `1` (attivo) / `0` (disattivo), con `mainSwitch: 1` o `0` nel payload comando.
  - `targetSoc`: **assente** nel firmware/API Lepas L8.
  - Ricarica immediata via `ricarica_start` / `ricarica_stop`: **disabilitata** su Lepas L8 quando permesso `220 = 0`; l'unico modo affidabile per far partire subito la carica al collegamento del cavo è disattivare la programmazione (`ricarica_prog_off`).
- **Anticorpi da rispettare integralmente:**
  - `AB-LEP-001`: nessun polling/wake aggressivo a veicolo dormiente; refresh token sotto lock.
  - `AB-LEP-002`: tutti i nuovi entity ID con `ID_PREFIX = "lepas"` in `naming.py`; nessun dato PII (VIN, coordinate, token) nei log o in `diagnostics.py`.
  - `AB-LEP-005`: test dal vivo su moduli `core/*.py` richiedono `ha_restart`.
  - `AB-LEP-007` / `AB-LEP-014`: `_state_lock` e `_hv_lock` non rientranti e mai annidati; mai chiamare `_auto_e_sveglia()` dentro `_state_lock`.
  - `AB-LEP-008` / `AB-LEP-016`: `window.customCards` senza prefisso `custom:` e controlli card coerenti con `car_in_use`.
  - `AB-LEP-009`: conversione locale ↔ UTC con `resolve_tzinfo(hass)` e floor 15m su `startTime`.
  - `AB-LEP-015`: reset latch `_hv_session_in_use` al plug-in fermo senza rifiuti.
  - `AB-LEP-019`: mai dedurre lo stato schedule da `appointmentChargeState`; `CMD_PROBE` attivo su `CHARGE_PROBE_COMMANDS`.

---

## 1. Sezione 1 — Modello a Modalità, Entità HA & Override Partenza Rapida

### 1.1 Selettore unico delle modalità domestiche
Viene introdotta l'entità `select.lepas_charge_window_mode` (suffisso `unique_id`: `charge_window_mode`, registrata in `naming.CANON_ENTITY_ID` e `naming.ENGLISH_KEYS`, `RestoreEntity`) con 3 opzioni ordinate:
1. **`off`** — Automazione finestra disattivata: il coordinator non invia `ricarica_prog_on`/`ricarica_prog_off` automatici; l'utente controlla manualmente via `switch.lepas_scheduled_charging`, `button.lepas_apply_charging_schedule` o app Lepas.
2. **`fixed`** (*Orario fisso*) — A casa mantiene sincronizzata la finestra fissa configurata in `time.lepas_charge_start_time` + `number.lepas_charge_duration` (salvo override da Partenza rapida).
3. **`smart_departure`** (*Segui partenza Smart*) — A casa calcola dinamicamente `startTime` e `timeConsuming` in modalità **Just-in-Time al 100%** rispetto alla prossima partenza utile, usando `number.lepas_charge_duration` come tetto massimo di sicurezza e fallback su SoC assente/degradato.

#### Retrocompatibilità e sincronizzazione con `switch.lepas_sync_charge_to_departure`
`switch.lepas_sync_charge_to_departure` viene mantenuto per non rompere automazioni o dashboard esistenti, mantenendo la sincronia bidirezionale col selettore su `coordinator.charge_window_mode`:
- Se l'utente accende `switch.lepas_sync_charge_to_departure` → `charge_window_mode = "smart_departure"` (`sync_charge_to_departure = True`).
- Se l'utente spegne `switch.lepas_sync_charge_to_departure` mentre `charge_window_mode == "smart_departure"` → `charge_window_mode = "fixed"` (`sync_charge_to_departure = False`).
- Se l'utente imposta `select.lepas_charge_window_mode`:
  - `"smart_departure"` → `sync_charge_to_departure = True`.
  - `"fixed"` oppure `"off"` → `sync_charge_to_departure = False`.
- **Migrazione al boot (primo avvio senza stato restaurato su `select.lepas_charge_window_mode`):**
  - Se `switch.lepas_sync_charge_to_departure` era restaurato `ON` → `charge_window_mode = "smart_departure"`.
  - Altrimenti → `charge_window_mode = "off"` (nessun cambio di comportamento automatico per chi non usava il sync alla partenza).
- Lo stato effettivo viene persistito via `RestoreEntity` su `select.lepas_charge_window_mode` (che in caso di conflitto al boot riconcilia `coord.sync_charge_to_departure` secondo la regola sopra).

### 1.2 Controlli Potenza Domestica (Auto vs Manuale)
Vengono aggiunte 2 sole entità dedicate (nessuna modifica arbitraria del valore impostato manualmente dall'utente):
1. **`switch.lepas_home_charge_power_auto`** (suffisso `home_charge_power_auto`, default `True`, `RestoreEntity`, categoria `EntityCategory.CONFIG`):
   - `ON`: il motore usa la potenza media auto-appresa a casa per il tipo di ricarica corrente (`home_learned_dc_kw` se DC, altrimenti `home_learned_ac_kw`), con fallback a `number.lepas_home_charge_power` finché non esiste ancora una sessione appresa per quel profilo.
   - `OFF`: il motore usa sempre e solo il valore manuale `number.lepas_home_charge_power`.
2. **`number.lepas_home_charge_power`** (suffisso `home_charge_power`, `EntityCategory.CONFIG`, `RestoreEntity`):
   - Unità `kW`, range `1.4 .. 40.0`, step `0.1`, default conservativo **`2.3`** (presa Schuko / carichino domestico standard).
   - Non viene mai sovrascritto dal sistema di auto-apprendimento: i valori appresi vengono esposti negli attributi diagnostici di `sensor.lepas_scheduled_charging_window` (e in `diagnostics.py`).

### 1.3 Ruolo di `number.lepas_charge_duration` (`1..12` ore)
- In modalità **`fixed`**: rappresenta la durata esatta della finestra fissa (`duration_hours * 60`).
- In modalità **`smart_departure`** (e in override Partenza rapida): rappresenta il **tetto massimo di sicurezza** (`max_duration_min = charge_duration_hours * 60`) e il **fallback automatico** quando il SoC è assente o scartato da `is_degraded_battery_frame(rt)`.

### 1.4 Override da Partenza Rapida (`switch.lepas_quick_departure`)
In `scheduler.py` attuale (`compute_next_occurrence`), la partenza rapida prevale sulla settimanale solo se è cronologicamente anteriore (`quick_occ.departure_at <= weekly_occ.departure_at`). Per la ricarica smart viene introdotta la selezione esplicita di **override di target**:
- **`select_charge_departure_occurrence(...)`:**
  - Se `quick_departure_enabled` è `True` e `quick_occ` è valida → **la partenza rapida vince sempre come target della ricarica** (anche se programmata più tardi della prossima partenza settimanale, es. domani alle `10:00` anziché `08:00`), con flag `quick_override_active = True`.
  - Se `quick_departure_enabled` è `False` (o appena l'ancora `_quick_target_at` scade al superamento dell'orario) → si rientra automaticamente alla prossima partenza settimanale (`weekly_occ`), con `quick_override_active = False`.
- **Comportamento nelle 3 modalità domestiche quando `quick_departure` è attiva (a casa):**
  - **`off`:** nessuna azione sulla ricarica (la partenza rapida gestisce solo pre-clima e preriscaldamento batteria).
  - **`fixed`:** la partenza rapida **scavalca temporaneamente** la finestra fissa calcolando una finestra Just-in-Time Smart verso `quick_occ.departure_at` (`reason = "quick_override"`), senza modificare la modalità salvata `fixed`. Quando la partenza rapida viene disattivata o scade, il coordinator ripristina automaticamente la finestra `fixed`.
  - **`smart_departure`:** usa `quick_occ.departure_at` al posto della settimanale (`reason = "quick_override"`).

### 1.5 Giorno Libero / Nessuna Partenza entro 24 ore (`no_departure_24h`)
A causa del vincolo firmware `2131 = 0` (`cycleData = [1,2,3,4,5,6,7]`), la centralina Lepas L8 non può escludere un singolo giorno della settimana e avvia qualunque finestra programmata entro 24 ore.
Pertanto, in modalità **`smart_departure`** (senza `quick_departure` attiva):
- Se non esiste alcuna partenza attiva (`occ is None`), oppure
- se l'inizio calcolato della ricarica dista più della finestra operativa di 24 ore (`smart_start_at - now > 23h 45m`, es. collegamento venerdì sera con prossima partenza lunedì mattina),
il motore sceglie **`action = "disable"`** (`reason = "no_departure_24h"`) inviando `ricarica_prog_off` (se la programmazione risulta attiva o sconosciuta da sincronizzare), così l'auto carica immediatamente al collegamento del cavo senza false attese del giorno successivo.
- Se l'auto resta collegata fino al giorno precedente alla partenza successiva ed entra nella finestra utile (`<= 23h 45m` prima di `smart_start_at`, oppure nella rete di sicurezza pre-carica `[start_at - 60m, departure_at)`), la finestra smart ritorna applicabile.

---

## 2. Sezione 2 — Algoritmo Energetico Puro & Auto-Apprendimento AC/DC

### 2.1 Funzione pura di stima (`estimate_smart_charge_plan` in `scheduler.py`)
Input:
- `soc_pct: float | None` (validato: finito, `0.0 <= soc_pct <= 100.0`, con `degraded_battery: bool` calcolato via `is_degraded_battery_frame(rt)`).
- `capacity_kwh: float` (da `coord.battery_capacity_kwh`, default `18.4`).
- `power_kw: float` (potenza effettiva selezionata, validata `> 0.0`, default fallback `2.3`).
- `charge_kind: Literal["ac", "dc"]`.
- `max_duration_hours: int` (`1..12`, da `coord.charge_duration_hours`).
- `step_minutes: int` (`CHARGE_DURATION_STEP_MINUTES`).

Costanti calibrate:
- **AC** (`charge_kind == "ac"`): `SMART_AC_EFFICIENCY = 0.90`, `SMART_AC_CV_MARGIN_MIN = 25`.
- **DC** (`charge_kind == "dc"`): `SMART_DC_EFFICIENCY = 0.92`, `SMART_DC_CV_MARGIN_MIN = 30`.
- **Limiti durata:** `SMART_MIN_DURATION_MIN = 30`.

Calcolo:
1. **Caso fallback SoC:** se `degraded_battery` è `True` o `soc_pct is None` o non valido (`< 0` o `> 100` o `bool`):
   - `estimated_duration_min = clamp(int(max_duration_hours) * 60, 30, 720)`
   - `fallback_used = True`
2. **Caso batteria già piena (`soc_pct >= 99.0`):**
   - `estimated_duration_min = SMART_MIN_DURATION_MIN` (`30` min, arrotondato a `step_minutes`), `fallback_used = False`.
3. **Caso calcolo energetico normale (`0.0 <= soc_pct < 99.0`):**
   - `missing_kwh = capacity_kwh * ((100.0 - soc_pct) / 100.0)`
   - `raw_min = (missing_kwh / (power_kw * eta)) * 60.0 + cv_margin_min`
   - Arrotondamento **per eccesso** a multipli di `step_minutes`: `rounded_min = int(math.ceil(raw_min / step_minutes)) * step_minutes`
   - Clamp `[SMART_MIN_DURATION_MIN, max_duration_hours * 60]`: se `max_duration_hours * 60 < SMART_MIN_DURATION_MIN` non può accadere (`max_duration_hours >= 1`), quindi risultato sempre compreso in `[30, max_duration_hours * 60]`.
   - `fallback_used = False`.

Calcolo dell'istante di inizio (`start_at`):
- `raw_start = (departure_at.hour * 60 + departure_at.minute - estimated_duration_min) % 1440`
- `floor_delta = raw_start - align_charge_start_minutes(raw_start, step=15)`
- `start_at = shift_minutes(departure_at, -(estimated_duration_min + floor_delta))`
- In questo modo `start_at` cade sempre su un multiplo locale di `15` minuti (`AB-LEP-009`) e `start_at + estimated_duration_min` termina **entro** `departure_at` (anticipo di `0..14` minuti).

#### Verifica pre-implementazione obbligatoria su `timeConsuming`
Prima di scrivere codice di implementazione (durante il piano esecutivo), va verificato su payload reali / codice `commands.py` + risposta TSP `chargeAppointControl` se l'auto accetta `timeConsuming` a step di **`15` minuti** (es. `135`) oppure richiede multipli di **`60` minuti** (`60, 120, 180, ...`).
- Per design, la formula separa `CHARGE_START_STEP_MINUTES = 15` (sempre `15` per `startTime`, verificato in `v1.33.2`) da `CHARGE_DURATION_STEP_MINUTES` (`15` se accettato dal backend, altrimenti `60` con `math.ceil` all'ora intera): in entrambi i casi `startTime` resta preciso al quarto d'ora e la carica finisce al 100% entro `departure_at`.

### 2.2 Casi limite gestiti in `resolve_desired_charge_schedule`
`resolve_desired_charge_schedule(...)` restituisce una dataclass immutabile `DesiredChargePlan`:
- `action`: `"enable" | "disable" | "noop"`
- `reason`: `"mode_off" | "unknown_location" | "away_bypass" | "fixed_home" | "smart_home" | "quick_override" | "no_departure_24h" | "late_plug_in" | "already_charged"`
- `start_minutes`: `int | None` (locale `0..1439`, multiplo di 15)
- `duration_minutes`: `int | None` (`30..720`)
- `days`: `tuple[int, ...] | None` (giorni locali prima della conversione `effective_charge_days` / UTC)
- `ref_date`: `date | None` (data di `start_at` locale per corretta gestione DST in `build_charge_appoint_plan`)
- `target_key`: `str` (`"manual"`, `"fixed"`, `"quick:<iso>"`, `"weekly:<iso>"`, `"bypass"`, `"immediate"`)
- `estimated_duration_min`: `int | None`, `soc_used`: `float | None`, `charge_kind`: `"ac" | "dc"`, `effective_power_kw`: `float`, `power_source`: `"learned_ac" | "learned_dc" | "manual"`, `fallback_used`: `bool`, `away_bypass_active`: `bool`, `quick_override_active`: `bool`.

Regole sui casi limite (in ordine di priorità):
1. **`mode == "off"`:** `action = "noop"`, `reason = "mode_off"`.
2. **`at_home is None`:** `action = "noop"`, `reason = "unknown_location"` (fail-safe all'avvio finché HA non determina la zona).
3. **`at_home is False`:** `action = "disable"`, `reason = "away_bypass"`, `away_bypass_active = True` (l'effettivo invio è poi filtrato dal coordinator su stato veicolo fermo + programmazione non già spenta).
4. **Target di partenza (`quick_override` su `fixed`, oppure `smart_departure`):**
   - Calcola `occ = select_charge_departure_occurrence(...)`.
   - Se `occ is None`: `action = "disable"`, `reason = "no_departure_24h"`.
   - Se `charge_state == 2` (`Ricarica completata`) o (`soc_pct is not None and soc_pct >= 99.0 and is_plugged`): `action = "noop"`, `reason = "already_charged"` (evita ri-programmazioni inutili a batteria già al 100%).
   - Calcola `smart_start_at` e `duration_minutes` tramite `estimate_smart_charge_plan(...)`.
   - Se `now >= smart_start_at` e `now < occ.departure_at`: **`action = "disable"`**, `reason = "late_plug_in"` (collegata in ritardo rispetto all'inizio stimato → spegne la programmazione per avviare subito la carica ed evitare che `startTime` slitti alle 24h successive).
   - Se `(smart_start_at - now) > timedelta(hours=23, minutes=45)`: **`action = "disable"`**, `reason = "no_departure_24h"`.
   - Altrimenti: **`action = "enable"`**, `reason = "quick_override"` (se `occ.source == "quick"`) oppure `"smart_home"`.
5. **Modalità `fixed` senza override `quick_departure`:**
   - `action = "enable"`, `reason = "fixed_home"`, `start_minutes = align_charge_start_minutes(charge_start_minutes)`, `duration_minutes = int(charge_duration_hours) * 60`, `days = tuple(charge_days)`.

### 2.3 Auto-apprendimento Potenza Domestica (AC vs DC) in `charging_stats.py`
Estensione retrocompatibile di `ChargingStatsTracker` (`Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.charging_stats")`, mantenendo `version: 1` e leggendo i nuovi campi come opzionali in `from_dict`):

1. **Classificazione tipo connettore (`classify_charge_kind`):**
   - `dc` se `field_on(rt.get("fastChargingGunStatus"))` è `True` (valore `1` o `2`) **oppure** `charging_power_kw > 11.0`.
   - `ac` altrimenti (incluso quando `fastChargingGunStatus` è `0` o assente e `chargeGunState != 0`).
2. **Condizioni di campionamento (fase CC a casa):**
   Tutti i seguenti requisiti devono essere veri sul frame corrente (non degradato):
   - `in_home_zone is True` (`at_home == True`)
   - `charging is True` (`chargeState == 1`)
   - `degraded_battery is False`
   - `power_kw is not None` e `0.5 <= power_kw <= 120.0` (valido `<= 15.0` per AC, `<= 120.0` per DC; esclude rumore standby `< 0.5 kW`)
   - **Fase CC pura** (esclude la coda CV dove la potenza cala artificialmente):
     - AC: `soc_pct is not None and soc_pct < 85.0`
     - DC: `soc_pct is not None and soc_pct < 75.0`
3. **Aggregazione di sessione & EMA storica:**
   - Durante una sessione attiva a casa, i campioni validi di fase CC vengono accumulati separatamente per `ac` e `dc` nel buffer di sessione (massimo `120` campioni per sessione per evitare crescita illimitata in memoria).
   - Alla chiusura sessione (`not plugged and not charging`, `reset_cont`, oppure cambio `charge_kind`), se il buffer ha almeno **`3` campioni validi**:
     - `session_kw = statistics.median(samples)` (robusta a picchi/cali temporanei).
     - Se il profilo storico (`home_learned_ac_kw` o `home_learned_dc_kw`) è `None` → `new_kw = round(session_kw, 2)`.
     - Altrimenti → `new_kw = round(0.7 * old_kw + 0.3 * session_kw, 2)`.
     - Incrementa `home_ac_sessions` o `home_dc_sessions` e marca il tracker dirty per il salvataggio su `Store` (riutilizzando `_charging_store` già persistito dal coordinator).
4. **Selezione potenza effettiva (`select_effective_home_power`):**
   - Se `home_charge_power_auto` è `False`: ritorna `(manual_kw, "manual")`.
   - Se `home_charge_power_auto` è `True`:
     - Se `charge_kind == "dc"` e `home_learned_dc_kw is not None` → `(home_learned_dc_kw, "learned_dc")`.
     - Se `charge_kind == "ac"` e `home_learned_ac_kw is not None` → `(home_learned_ac_kw, "learned_ac")`.
     - Altrimenti (prima sessione non ancora appresa) → `(manual_kw, "manual")`.

---

## 3. Sezione 3 — Trigger, Bypass Fuori Casa & Guardie Batteria 12V

### 3.1 Determinazione di `at_home` & Fail-Safe
- Legge lo stato corrente di zona casa già usato dal coordinator (`_in_home_zone()` / `binary_sensor.lepas_at_home`): `True` (dentro raggio casa), `False` (fuori casa), `None` (posizione non ancora disponibile al boot o `poll_enabled` disattivato con posizione assente).
- Con `at_home is None`, `resolve_desired_charge_schedule` ritorna sempre `action = "noop"` (`unknown_location`), impedendo disattivazioni o programmazioni errate prima del primo fix GPS/stato ripristinato.

### 3.2 Bypass Fuori Casa (`away_bypass`)
Per evitare i rigetti ECU `0:95` mentre il veicolo è in movimento (`AB-LEP-016`) e risparmiare la batteria 12V (`AB-LEP-001`):
- Finché `car_in_use is True`: **nessun comando** `ricarica_prog_on` / `ricarica_prog_off` automatico viene inviato.
- Quando `at_home is False` e `not car_in_use` (transizione `car_in_use: True -> False` al parcheggio fuori casa, oppure plug-in fuori casa `chargeGunState` / `fastChargingGunStatus: 0 -> 1` con `at_home is False`):
  - Verifica se la programmazione sull'auto non è già nota come spenta (`_car_charge_schedule_is_on()` basato su `fields["chargeAppointPlans"][0]["switchStatus"] == 1`, oppure su `_last_synced_charge_sig` con `action == "enable"` se `chargeAppointPlans` non è ancora stato letto).
  - Se risulta attiva (o potenzialmente attiva), invia **`ricarica_prog_off`** una sola volta con payload completo compatibile con `AB-LEP-009`/`AB-LEP-019` (`mainSwitch: 0`, `chargeAppointPlans[0].switchStatus = 0`) e registra la firma `("disable", "away_bypass")` per evitare ri-invii.
- Al rientro e successivo collegamento cavo a casa (`at_home is True` + plug-in), la modalità domestica (`fixed` o `smart_departure`) riattiva automaticamente la finestra desiderata.

### 3.3 Tabella dei Trigger & Debounce Plug-in
| Evento | Condizioni | Azione verso il veicolo | Impatto 12V |
|---|---|---|---|
| **Plug-in a casa** (`plugged: False -> True`, `at_home is True`) | `mode != "off"`, `not car_in_use` | Arma debounce **`20s`** in `TimerRegistry` (`CHARGE_PLUGIN_DEBOUNCE`); allo scadere ricalcola `resolve_desired_charge_schedule` con SoC aggiornato e invia se firma diversa | **Zero wake extra** (auto già sveglia al collegamento) |
| **Parcheggio / plug-in fuori casa** (`at_home is False`) | `mode != "off"`, `not car_in_use` | Cancella eventuale debounce plug-in a casa; invia `ricarica_prog_off` una volta se schedule risulta attivo | **Zero wake extra** (appena parcheggiata/collegata) |
| **Cambio configurazione utente** (cambio modalità, toggle `power_auto`, modifica `home_charge_power`, modifica partenze, `quick_departure` ON/OFF) | `mode != "off"`, `at_home is True`, `not car_in_use` | Ricalcola e sincronizza subito (se `action == "enable"` o passaggio necessario a `"disable"` per `quick_override`/`no_departure_24h`/`late_plug_in`) | Solo su azione esplicita utente |
| **Rete di sicurezza pre-carica** (tick 60s `_departure_tick_cb`) | `mode != "off"`, `at_home is True`, **`is_plugged is True`**, `not car_in_use`, ingresso in `[start_at - 60m, departure_at)` | Invia solo se la firma corrente non coincide con `_last_synced_charge_sig` e non è in `_last_attempted_charge_sig` | Minimo (recupera solo errori cloud/riavvii HA al plug-in) |
| **Auto a casa NON collegata** (`is_plugged is False`) | Nessun comando utente recente | **Nessun invio periodico nel tick** (aggiorna solo lo stato locale/preview in HA) | **Zero wake** |

### 3.4 Guardie Anti-Spam, Concorrenza e Integrità Sessione
- **Stabilità durante la carica (`chargeState == 1`):** mentre l'auto sta caricando, le variazioni di SoC (`80% -> 81% -> ...`) e gli aggiornamenti delle medie di potenza appresa **non** scatenano ricalcoli/invii automatici su `chargeAppointControl`; la finestra non viene spostata sotto i piedi di una carica già in corso.
- **Dedup & Anti Retry-Storm:**
  - Firma deterministica: `(plan.action, plan.start_minutes, plan.duration_minutes, eff_days, plan.target_key)`.
  - Se `sig == self._last_synced_charge_sig` → skip.
  - Se `sig == self._last_attempted_charge_sig` (precedente tentativo fallito) → skip automatico fino a cambio firma, nuovo evento di plug-in (`plugged: False -> True`) o azione manuale esplicita dell'utente.
- **Lock safety (`AB-LEP-007`, `AB-LEP-014`):**
  - Tutti gli invii automatici passano sotto `self._departure_lock` (async), senza mai acquisire né trattenere `self._state_lock` o `self._hv_lock` durante I/O di rete.
  - Il timer debounce `CHARGE_PLUGIN_DEBOUNCE` è registrato nel `TimerRegistry` e cancellato su `unload` / `closing`.
- **Override manuale preservato:** `button.lepas_apply_charging_schedule` e il servizio `lepas.set_charging_schedule` continuano a eseguire l'invio immediato ignorando `_last_attempted_charge_sig` e aggiornando `_last_synced_charge_sig`.

---

## 4. Sezione 4 — Diagnostica, Card Lovelace & Strategia di Test

### 4.1 Sensori Esistenti & Diagnostica
- **`LepasScheduledChargingWindowSensor` (`sensor.lepas_scheduled_charging_window`):**
  - Mantiene il formato di stato esistente (`"HH:MM → HH:MM · giorni"`) quando è pianificata una finestra attiva (`enable`), e riflette il piano calcolato dal motore (oppure stato immediato / bypassato quando applicabile) negli attributi:
    - `window_mode`: `"off" | "fixed" | "smart_departure"`
    - `effective_action`: `"enable" | "disable" | "noop"`
    - `plan_reason`: codice motivo del `DesiredChargePlan`
    - `estimated_duration_min`: `int | None`
    - `soc_used`: `float | None`
    - `charge_kind`: `"ac" | "dc"`
    - `effective_power_kw`: `float`
    - `power_source`: `"learned_ac" | "learned_dc" | "manual"`
    - `learned_ac_kw`: `float | None`
    - `learned_dc_kw`: `float | None`
    - `home_ac_sessions`: `int`
    - `home_dc_sessions`: `int`
    - `fallback_used`: `bool`
    - `away_bypass_active`: `bool`
    - `quick_override_active`: `bool`
- **`LepasNextDepartureSensor` (`sensor.lepas_next_departure`):**
  - Calcola l'attributo `planned_charge_start` tramite il nuovo motore `resolve_desired_charge_schedule` (usando `select_charge_departure_occurrence` + stima smart se attiva), garantendo coerenza 1:1 tra preview UI e comando inviato.
- **`diagnostics.py`:**
  - Esporta una sezione `smart_charging` priva di PII (`window_mode`, `home_charge_power_auto`, `home_charge_power_kw`, `learned_ac_kw`, `learned_dc_kw`, `home_ac_sessions`, `home_dc_sessions`, `last_plan_reason`).

### 4.2 Aggiornamento Card Lovelace (`custom_components/lepas/lovelace/lepas-card.js`)
Nella sezione Ricarica di `lepas-card.js` (rispettando `AB-LEP-008` su `window.customCards` e `AB-LEP-016` su `carInUse` / controlli ricarica):
- **Selettore modalità finestra:** controllo compatto collegato a `select.lepas_charge_window_mode` con etichette bilingue IT/EN (`Spenta` / `Orario fisso` / `Partenza Smart`; `Off` / `Fixed schedule` / `Smart departure`).
- **Badge di stato contestuali** (letti dagli attributi di `sensor.lepas_scheduled_charging_window`):
  - *Bypass fuori casa* (`away_bypass_active == true`)
  - *Override Partenza rapida* (`quick_override_active == true`)
  - *Ricarica immediata* (`effective_action == "disable"` con `plan_reason` in `no_departure_24h` / `late_plug_in`)
- **Riga potenza domestica:**
  - Toggle *Auto / Manuale* legato a `switch.lepas_home_charge_power_auto`
  - Controllo numerico `number.lepas_home_charge_power` (abilitato e modificabile anche quando Auto è attivo come fallback/override rapido)
  - Riepilogo compatto della sorgente effettiva (es. `Auto AC · 2.2 kW`, `Auto DC · 24.0 kW`, `Manuale · 3.7 kW`).
- Cache-busting `?v=<version>` in sincronia con `manifest.json` e `pyproject.toml` al rilascio successivo.

### 4.3 Strategia di Test (TDD)
1. **`tests/test_smart_charging.py` (Unit test puri `scheduler.py`):**
   - Formula AC (`0.90`, `+25m`) e DC (`0.92`, `+30m`) su SoC `10%`, `50%`, `80%`, `99%`, verificando arrotondamento `ceil` a multipli di `step_minutes`, minimo `30m` e cap `charge_duration_hours * 60`.
   - Fallback sicuro a `charge_duration_hours` su `soc_pct=None`, `soc_pct=-1`, `degraded_battery=True`.
   - Allineamento `start_at` a multipli di `15` min con scavalco mezzanotte locale/UTC e cambio ora legale DST (`AB-LEP-009`).
   - Tutti i rami di `resolve_desired_charge_schedule`: `off -> noop`, `at_home is None -> noop`, `at_home is False -> disable (away_bypass)`, `fixed` normale, `fixed + quick_override`, `smart + quick_override` anche quando rapida > settimanale, `no_departure_24h (>23h45m) -> disable`, `occ is None -> disable`, `late_plug_in -> disable`, `already_charged -> noop`.
2. **`tests/test_charging_stats.py` (Estensione auto-apprendimento `charging_stats.py`):**
   - Separazione AC vs DC (`chargeGunState` vs `fastChargingGunStatus` e soglia `>11 kW`).
   - Scarto campioni fuori casa (`in_home_zone=False/None`), non in carica (`chargeState != 1`), frame degradati, potenza `< 0.5 kW` e fase CV (`soc >= 85%` AC, `soc >= 75%` DC).
   - Mediana su sessione con spike singolo, minimo 3 campioni, EMA `0.7/0.3`, persistenza `to_dict`/`from_dict` retrocompatibile con file `v1` esistenti.
3. **`tests/test_smart_charge_coordinator.py` (Integrazione Coordinator & Entità):**
   - Migrazione/sincronia bidirezionale `switch.lepas_sync_charge_to_departure` ↔ `select.lepas_charge_window_mode`.
   - Debounce `20s` su plug-in a casa, nessun re-invio con `chargeState == 1`, bypass `ricarica_prog_off` su `car_in_use: True -> False` fuori casa e su plug-in fuori casa (mai con `car_in_use == True`), ripristino al rientro a casa.
   - Attivazione/disattivazione `quick_departure` in `fixed` (override temporaneo + ripristino `fixed`) e in `smart_departure`.
   - Anti retry-storm (`_last_attempted_charge_sig`) e cancellazione timer debounce su unload.
   - Attributi di `LepasScheduledChargingWindowSensor`, `LepasNextDepartureSensor.planned_charge_start` e `diagnostics.py` (redacted).
4. **`tests/lepas_card.test.mjs` & `tests/test_lovelace_card.py`:**
   - Rendering selettore `lepas_charge_window_mode`, badge contestuali, riga potenza Auto/Manuale + riepilogo `kW`, assenza di prefisso `custom:` (`AB-LEP-008`) e compatibilità `carInUse` (`AB-LEP-016`).
