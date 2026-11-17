# Design Spec — Configurazione UX Friendly, Programmatore Partenze Settimanale/Rapido & Ricarica Intelligente

**Data:** 2026-11-17
**Stato:** Bozza completa da brainstorming — in attesa di revisione utente prima del piano implementativo (`writing-plans`)
**Obiettivo:** Rendere la sezione Configurazione e la pianificazione partenze/ricarica di Home Assistant intuitive, auto-esplicative e più flessibili dell'app ufficiale Lepas, mantenendo intatti gli `entity_id` esistenti e rispettando i vincoli reali del protocollo `com.chery.eu.lepas`.

---

## 1. Contesto & Vincoli Reali del Protocollo

1. **Clima automatico (`airControl`)**: `climate.lepas_climate` (`LepasClimate` in `custom_components/lepas/climate.py`) opera già in modo `HVACMode.HEAT_COOL`: inviando `temperature` e `times` (`A/C acceso per`), l'auto riscalda o raffredda automaticamente l'abitacolo fino al setpoint.
2. **Ricarica programmata (`chargeAppointControl`)**: l'auto accetta un solo piano attivo per volta (`startTime` in minuti locali da mezzanotte, `timeConsuming` in minuti, `cycleData` giorni `1..7`, `mainSwitch`/`switchStatus`). Inoltre la validazione permessi (`permessi.CICLO` / voce `2131`) può rifiutare cicli parziali (`!= [1..7]`) su alcuni VIN.
3. **Partenza programmata (`appointmentTravelSetVOS`)**: oggi nel package esiste solo la lettura dal payload `/asr/manager/realtime` (`sensor.lepas_scheduled_departure`), non l'endpoint di scrittura verso il server. Gestendo il **Programmatore Partenze direttamente in Home Assistant**, l'utente può impostare orari diversi per ciascun giorno della settimana e partenze rapide una tantum usando i comandi reali già collaudati (`airControl` + `chargeAppointControl`).

---

## 2. Pulizia & Miglioramento Configurazione Esistente

Tutti gli `entity_id` esistenti restano invariati per preservare automazioni e storico.

### 2.1 Revisione Nomenclatura (`strings.json`, `it.json`, `en.json`, `nl.json`)
- `number.lepas_climate_duration` (`clima_durata`): `"A/C acceso per (pre-clima)"` / `"A/C duration (pre-climate)"` / `"Airco-duur (voorklimatisering)"`.
- `time.lepas_charge_start_time` (`ricarica_orario_inizio`): `"Ricarica prog. · inizio"` / `"Scheduled charge · start"` / `"Gepland laden · start"`.
- `number.lepas_charge_duration` (`ricarica_durata_ore`): `"Ricarica prog. · durata"` / `"Scheduled charge · duration"` / `"Gepland laden · duur"`.

### 2.2 Fallback Stato `switch.lepas_scheduled_charging`
- In `LepasScheduledChargeSwitch._live_on()` (`custom_components/lepas/switch.py`):
  - Continua a preferire `fields["chargeAppointPlans"][0]["switchStatus"]` (telemetria live/5A02).
  - Quando `chargeAppointPlans` è assente, legge `realtime["appointmentChargeState"]`: `"1"` → `True`, `"0"` → `False` (valori mancanti/non riconosciuti lasciano invariato il fallback `RestoreEntity`), eliminando lo stato `unknown` all'avvio.

### 2.3 Finestra Ricarica, Giorni & Pulsante Applica
- **Nuova piattaforma `select`** (`"select"` aggiunta a `PLATFORMS` in `custom_components/lepas/const.py`):
  - **`select.lepas_charge_days`** (`EntityCategory.CONFIG`, `RestoreEntity`, gated su `scheduled_charging`):
    - Opzioni preset: `all_days` (`[1..7]`, *"Tutti i giorni (Lun–Dom)"*), `weekdays` (`[1..5]`, *"Feriali (Lun–Ven)"*), `weekend` (`[6,7]`, *"Weekend (Sab–Dom)"*), `mon_wed_fri` (`[1,3,5]`, *"Lun · Mer · Ven"*), `tue_thu_sat` (`[2,4,6]`, *"Mar · Gio · Sab"*), più opzione `custom` usabile quando un servizio passa una lista arbitraria (es. `[1,4]`).
    - Aggiorna `coordinator.charge_days`. In `LepasScheduledChargeSwitch._plan()`, `cycleData` legge `coordinator.charge_days` al posto del precedente `[1..7]` fisso.
- **Nuovo sensore `sensor.lepas_scheduled_charging_window`** (`EntityCategory.DIAGNOSTIC`, gated su `scheduled_charging`):
  - Stato calcolato in tempo reale da `charge_start_minutes`, `charge_duration_hours` e `charge_days`:
    es. **`23:00 → Giorno dopo 05:00 · Lun–Dom`** (in IT/EN/NL in base alla lingua configurata) o **`08:00 → 14:00 · Lun–Ven`**.
  - Attributi: `start_time`, `end_time`, `next_day` (`bool`), `duration_hours`, `days` (`list[int]`), `synced_with_car` (`bool | None` rispetto a `chargeAppointPlans`, se disponibile).
- **Nuovo pulsante `button.lepas_apply_charging_schedule`** (`EntityCategory.CONFIG`, gated su `scheduled_charging`):
  - Invia `ricarica_prog_on` (`chargeAppointControl` con `mainSwitch=1`, `switchStatus=1`, inizio/durata/giorni correnti) per applicare subito le modifiche senza spegnere e riaccendere lo switch.

---

## 3. Programmatore Partenze Intelligente (Settimanale + Rapida)

**Convenzione UX:** ogni orario configurato indica l'**ora in cui l'utente vuole trovare l'auto pronta** (`T_dep`).

### 3.1 Entità di Configurazione & Diagnostica
1. **Programmazione Settimanale (7 giorni, `EntityCategory.CONFIG`, `RestoreEntity`)**:
   - Per ciascun giorno (`mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun`, indici ISO `1..7`):
     - `switch.lepas_departure_<day>_enabled`: `"Partenza Lun · attiva"` … (default `False`).
     - `time.lepas_departure_<day>_time`: `"Partenza Lun · orario"` … (default `07:00`).
2. **Prenotazione Partenza Rapida (una tantum, `EntityCategory.CONFIG`, `RestoreEntity`)**:
   - `time.lepas_quick_departure_time`: `"Partenza rapida · orario"` (default `18:00`).
   - `switch.lepas_quick_departure`: `"Prenota partenza rapida"` (default `False`).
     - Quando attiva, punta alla **prossima occorrenza** locale di `quick_departure_time` (oggi se `> now`, altrimenti domani) e ha priorità sulla programmazione settimanale nella finestra corrispondente.
     - Si disattiva automaticamente (auto-reset a `False`) una volta completata/scattata la preparazione per quella occorrenza.
3. **Comportamento & Sicurezza (`EntityCategory.CONFIG`, `RestoreEntity`)**:
   - `select.lepas_departure_climate_mode` (`"Partenza · clima automatico"`, gated su `climate`):
     - `at_home` *(default)*: `"Solo a casa"` — esegue il pre-clima solo se l'auto risulta a casa (`at_home` / raggio zona `home`; se `home` non ha coordinate, nessuna restrizione).
     - `anywhere`: `"Ovunque"` — esegue sempre quando scatta l'orario.
     - `off`: `"Disattivato"` — non invia comandi clima automatici.
   - `switch.lepas_sync_charge_to_departure` (`"Adatta ricarica alla partenza"`, gated su `scheduled_charging`, default `False`):
     - Quando attiva, adatta automaticamente inizio/finestra di ricarica affinché la ricarica termini all'ora della prossima partenza prevista.
4. **Sensore Riepilogativo `sensor.lepas_next_departure`** (`EntityCategory.DIAGNOSTIC`):
   - Stato testuale chiaro (entro 255 caratteri, bilingue IT/EN/NL):
     - es. `"Oggi 18:00 (rapida · clima 17:45)"`
     - es. `"Domani mar 13:30 (clima 13:15)"`
     - es. `"Disattivata"` se nessuna partenza rapida né settimanale è attiva.
   - Attributi: `departure_at` (ISO), `climate_start_at` (ISO), `source` (`"quick"` | `"weekly"` | `None`), `weekday` (`int | None`), `climate_mode`, `sync_charging` (`bool`), `planned_charge_start` (`"HH:MM" | None`).

### 3.2 Logica di Esecuzione sul Coordinator (`scheduler`)
Per evitare timer dispersi e mantenere tutto deterministico/testabile:
- Un modulo dedicato `custom_components/lepas/scheduler.py` contiene funzioni pure per calcolo prossima partenza, finestra pre-clima e finestra ricarica adattata.
- `LepasCoordinator` mantiene stato in-memory delle preferenze (aggiornate al boot/restore e ad ogni cambio da `time`/`number`/`select`/`switch`) più `climate_target_temp` sincronizzata da `LepasClimate` (default `DEFAULT_TEMP = 21.0`).
- **Tick schedulatore al minuto (`async_track_time_interval(..., timedelta(minutes=1))`)** registrato nel `TimerRegistry` (cancellato pulitamente in `async_unload_entry`):
  1. **Calcolo prossima occorrenza**: confronta l'eventuale partenza rapida (`quick`) e la prossima occorrenza settimanale attiva (`weekly` nei prossimi 7 giorni); seleziona la più imminente.
  2. **Pre-condizionamento Clima (`T_clima = T_dep - timedelta(minutes=clima_duration)`)**:
     - Se `climate_mode != "off"` e `now` cade nella finestra `[T_clima, T_dep)` (e l'occorrenza non è ancora stata eseguita in `_fired_climate_key`):
       - **Guardie:**
         - Se `climate_mode == "at_home"` e l'auto non risulta in zona casa → segna occorrenza come saltata (log info/esito diagnostico senza inviare comandi).
         - Se motore acceso (`engineState != 0`) o velocità `> 0` → salta senza inviare comandi.
       - **Esecuzione:** segna `_fired_climate_key` (anti-duplicato), poi chiama `async_send_command("clima_on", {"temperature": f"{target_temp:.1f}", "times": str(clima_duration)})` (che gestisce il risveglio automatico se l'auto dorme).
       - Se `source == "quick"`, disattiva `switch.lepas_quick_departure` notificando la UI.
  3. **Adattamento Ricarica (`sync_charge_to_departure == True`)**:
     - Calcola `start_min = (T_dep_min - charge_duration_hours * 60) % 1440`.
     - Aggiorna localmente `coordinator.charge_start_minutes = start_min` e notifica la UI (`time.lepas_charge_start_time` + `sensor.lepas_scheduled_charging_window`).
     - Determina i giorni da inviare: `[1..7]` se il permesso `2131` (ciclo personalizzato) è esplicitamente `0` nei permessi probed (evitando `A00084` su VIN come la Lepas L8), altrimenti il giorno/lista giorni correnti.
     - Invia `chargeAppointControl` (`mainSwitch=1`) automaticamente in due casi:
       - subito (asincrono) quando l'utente attiva `switch.lepas_quick_departure` o invoca `lepas.set_quick_departure` con sync attivo;
       - entro una finestra di anticipo (`60` minuti prima di `T_charge_start`, o subito se mancano `< 60` minuti e `now < T_dep`) per una partenza settimanale, con deduplica per chiave `(target_start_iso, start_min, duration_h, tuple(days))` in modo da non risvegliare l'auto se il piano è già stato inviato identico.

---

## 4. Servizi Asincroni Home Assistant (`services.yaml` + `__init__.py`)

1. **`lepas.set_quick_departure`**:
   - Parametri: `entry_id` *(opzionale se singola auto)*, `time` (`HH:MM`), `enabled` (`bool`, default `True`), `sync_charging` (`bool`, opzionale).
   - Imposta orario rapido, attiva/disattiva la partenza rapida, aggiorna eventualmente la sincronizzazione ricarica e notifica lo schedulatore.
2. **`lepas.set_charging_schedule`**:
   - Parametri: `entry_id` *(opzionale)*, `start_time` (`HH:MM`, opzionale), `duration_hours` (`int 1..12`, opzionale), `days` (`list[int] | str`, opzionale), `apply` (`bool`, default `True`).
   - Aggiorna le preferenze locali e, se `apply=True`, invia `chargeAppointControl` (`mainSwitch=1`).

---

## 5. Impatto su Test, Documentazione & Versioning

- **Naming & Traduzioni (`naming.py`, `strings.json`, `translations/{it,en,nl}.json`)**:
  - Tutte le nuove entità (`select`, `sensor`, `button`, `switch`, `time`) registrate in `naming.ENTITY_ID_MAP` e tradotte nei 3 idiomi (`it`, `en`, `nl`) mantenendo parità con `test_le_traduzioni_coprono_le_stesse_entita`.
- **Nuovi test unitari e integrazione HA (nessun mock sulla logica sotto test)**:
  - `tests/test_scheduler.py`: calcolo prossima partenza (`quick` vs `weekly`, rollover giorno successivo), calcolo finestra ricarica notturna/diurna, guardia `at_home` / `engineState`, reset partenza rapida post-esecuzione, deduplica invii `clima_on` e `chargeAppointControl`, fallback `2131=0` → `[1..7]`.
  - `tests/test_config_ux.py`: `select.lepas_charge_days`, `sensor.lepas_scheduled_charging_window`, `button.lepas_apply_charging_schedule`, fallback `appointmentChargeState` su `switch.lepas_scheduled_charging`, servizi `lepas.set_quick_departure` e `lepas.set_charging_schedule`.
- **Target Release:** `v1.18.0` (`minor` SemVer per nuove feature ed entità) + `CHANGELOG.md`.
