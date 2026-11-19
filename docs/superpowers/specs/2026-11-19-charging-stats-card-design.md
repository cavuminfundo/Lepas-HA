# Specifica: Card Dedicata "Statistiche Lepas" (Ricarica + Consumi Medi) e Tracker Persistente

**Data:** 2026-11-19
**Stato:** Design approvato dall'utente (in attesa di User Review Gate sulla spec e successivo piano implementativo)
**Ambito:** `custom_components/lepas/*`, `custom_components/lepas/lovelace/lepas-card.js`, `tests/*`

---

## 1. Contesto e Obiettivo

In `v1.29.1` sono stati rimossi i riquadri `Casa` / `Fuori` dal blocco *Ricarica live* della card principale (`lepas-card`), mantenendo attivi `sensor.lepas_home_charging_energy` e `sensor.lepas_away_charging_energy` (`LepasChargedEnergy`) per la Dashboard Energia di Home Assistant. Tuttavia:
- `LepasChargedEnergy` usa unicamente l'integrazione trapezoidale su `chargingPower` con finestra massima `CHARGE_ENERGY_MAX_GAP = 300s`: nei buchi di polling a veicolo fermo (> 5 minuti) o durante un riavvio di Home Assistant, l'energia ricaricata tra due letture non viene recuperata.
- Mancano statistiche aggregate e persistenti per **Oggi**, **Mese**, **Anno** e **Da inizio** con dettaglio `Tutte` / `Casa` / `Fuori` e un **grafico storico compatto** consultabile direttamente in dashboard.
- La sezione **Consumi medi** (EV + Ibrido) appesantisce attualmente la tab *Panoramica* di `lepas-card` e appartiene concettualmente alla vista statistiche.

L'obiettivo è introdurre:
1. Un motore puro Python (`custom_components/lepas/charging_stats.py`) con **integratore ibrido** (trapezoidale su `chargingPower` per `dt <= 300s` + riconciliazione tramite **delta SoC** sui buchi `> 300s` e riavvii) e persistenza autonoma via `Store`.
2. Il miglioramento contestuale di `LepasChargedEnergy` tramite lo stesso helper ibrido condiviso, mantenendo la compatibilità `TOTAL_INCREASING` per la Dashboard Energia.
3. **4 nuovi sensori periodici** (`today`, `month`, `year`, `from_start`) + **1 pulsante di reset** (`reset_charging_from_start`).
4. Una **seconda card Lovelace dedicata** (`lepas-stats-card`, *Statistiche Lepas*) nello stesso bundle `lepas-card.js`, che unifica **Ricarica** (KPI + filtro `Tutte | Casa | Fuori` + mini-grafico a barre `7g / 30g / 12m` + pulsante reset con conferma) e **Consumi medi** (EV + Ibrido + pulsante reset con conferma), rimuovendo la sezione *Consumi medi* dalla card principale `lepas-card`.

---

## 2. Architettura e Decisioni Chiave (Approvate)

1. **Approccio 1 — 4 Sensori Periodici + Breakdown negli Attributi + Serie Compatta in `Store`**:
   - Superficie entità snella: `+4` sensori + `+1` pulsante (`142 → 147` entità complessive).
   - `native_value` espone sempre il totale `kWh` del periodo (`total_kwh`), garantendo che nessuna energia vada persa anche in caso di assenza temporanea del fix GPS (`in_zona_casa() is None`).
   - `extra_state_attributes` espone `home_kwh`, `away_kwh`, `sessions_count`, `period_key` e le serie compatte (`daily_series` su `today`, `monthly_series` su `year`) per alimentare il grafico della card in modo sincrono da `hass.states` senza chiamate WebSocket al `recorder`.
2. **Classificazione geografica standard `zone.home`**:
   - Nessuna euristica opaca o riassegnazione retroattiva: `Casa` e `Fuori` usano esclusivamente `in_zona_casa(hass, position)` in `entity.py`, mantenendo coerenza 1:1 tra i sensori Energy Dashboard e `charging_stats`.
   - Nella card il selettore parte su **`Tutte`** così eventuali ritardi di aggancio GPS al rientro in garage non nascondono energia reale.
3. **Unificazione Statistiche nella Nuova Card + Rimozione da `lepas-card`**:
   - La nuova card `lepas-stats-card` contiene sia **Ricarica** sia **Consumi medi**.
   - La sezione `consSection` (*Consumi medi*) viene rimossa dalla tab *Panoramica* della card principale `lepas-card` per evitare duplicazioni e alleggerire la vista operativa.
4. **Reset `Da inizio` direttamente da Card (con conferma)**:
   - Entrambe le sezioni (*Ricarica* e *Consumi medi*) offrono un pulsante discreto di reset nell'header di sezione (attivabile/disattivabile via editor `show_reset_buttons`, default `true`) protetto da finestra di conferma prima di invocare `button.press`.

---

## 3. Motore di Calcolo (`custom_components/lepas/charging_stats.py`)

Modulo puro Python (nessuna dipendenza runtime da Home Assistant, 100% testabile in isolamento sul modello di `consumption.py`):

### 3.1 Costanti e Helper Condiviso Integratore Ibrido
- `CHARGE_ENERGY_MAX_GAP = 300.0` (importato da `const.py`, 5 minuti).
- `DAILY_HISTORY_LIMIT = 30` (giorni conservati per il grafico `7g / 30g`).
- `MONTHLY_HISTORY_LIMIT = 12` (mesi conservati per il grafico `12m`).
- `MIN_VALID_SOC_STEP_PCT = 0.5` (soglia minima anti-rumore per il recupero delta SoC sui buchi `> 300s`).
- `MAX_SOC_JUMP_PCT = 100.0`.
- **Helper puro condiviso (`compute_charge_delta_kwh`)**:
  - Input: stato precedente (`prev_ts`, `prev_power_kw`, `prev_soc_pct`, `prev_odo_km`, `prev_charging`), stato corrente (`now_ts`, `power_kw`, `soc_pct`, `odo_km`, `charging`, `plugged`, `degraded_battery`, `battery_capacity_kwh`).
  - **Guardie Fail-Closed**:
    1. Se `degraded_battery` è `True` (`is_degraded_battery_frame(rt)`): ignora il frame (`delta_kwh = 0.0`, non aggiorna i baseline SoC).
    2. Se `odo_km` e `prev_odo_km` sono validi e `odo_km > prev_odo_km + 0.1` (veicolo guidato tra i due campioni): resetta lo stato continuo della ricarica (`reset_continuity = True`, `delta_kwh = 0.0`) ed evita recuperi SoC spuri.
  - **Ramo A — Integrazione trapezoidale (`0 < dt_s <= CHARGE_ENERGY_MAX_GAP`)**:
    - Attivo quando `charging` e `prev_charging` sono `True` e `power_kw > 0` e `prev_power_kw > 0`:
      `delta_kwh = 0.5 * (prev_power_kw + power_kw) * (dt_s / 3600.0)`.
    - Non somma mai anche il delta SoC nello stesso step (nessun doppio conteggio).
  - **Ramo B — Riconciliazione Delta SoC (`dt_s > CHARGE_ENERGY_MAX_GAP`)**:
    - Attivo quando l'auto era in carica o collegata (`prev_charging` oppure `charging` o `plugged`) **e** l'odometro non è aumentato **e** `soc_pct` e `prev_soc_pct` sono validi con `(soc_pct - prev_soc_pct) >= MIN_VALID_SOC_STEP_PCT`:
      `delta_kwh = ((soc_pct - prev_soc_pct) / 100.0) * battery_capacity_kwh`.
    - Se `charging` è attivo sul frame corrente ma `dt_s > CHARGE_ENERGY_MAX_GAP` senza incremento di `soc_pct`, `delta_kwh = 0.0` (nessuna stima inventata) e si aggiornano i baseline per il ciclo successivo.

### 3.2 `ChargingStatsTracker`: Bucket, Rollover, Sessioni e Serie Storiche
- **Chiavi temporali locali**: `ingest(...)` riceve `local_date: str` (`YYYY-MM-DD`, derivato sul loop HA con `dt_util.as_local(now_dt).date().isoformat()`). Da `local_date` si ricavano `local_month = local_date[:7]` (`YYYY-MM`) e `local_year = local_date[:4]` (`YYYY`).
- **Struttura bucket (`_Bucket`)**: `{ total_kwh: float, home_kwh: float, away_kwh: float, sessions_count: int }`.
- **Rollover deterministico**:
  - Se `local_date != self._today_key`: azzera `self._today` e aggiorna `self._today_key = local_date`.
  - Se `local_month != self._month_key`: azzera `self._month` e aggiorna `self._month_key = local_month`.
  - Se `local_year != self._year_key`: azzera `self._year` e aggiorna `self._year_key = local_year`.
  - **Rollover in lettura (`period_stats(period, current_local_date)`)**: se il calendario locale è avanzato ma non è ancora arrivato un frame di ricarica dopo la mezzanotte (o cambio mese/anno), i getter restituiscono `0.0` per il periodo scaduto (`today`/`month`/`year`) senza attendere la prossima ricarica.
- **Attribuzione `Casa / Fuori / Totale`**:
  - Per ogni `delta_kwh > 0`: `bucket.total_kwh += delta_kwh`.
  - Se `in_home_zone is True`: `bucket.home_kwh += delta_kwh`.
  - Se `in_home_zone is False`: `bucket.away_kwh += delta_kwh`.
  - Se `in_home_zone is None`: incrementa solo `total_kwh` (nessuna attribuzione arbitraria a `home` o `away`).
- **Conteggio sessioni (`sessions_count`)**:
  - Mantiene `self._session_active: bool` (e `self._session_counted: bool`).
  - Quando l'auto entra in carica attiva (`charging and power_kw > 0`) partendo da `not _session_active`, avvia una nuova sessione; incrementa `sessions_count += 1` sui 4 bucket (e sulla voce giornaliera/mensile corrente) non appena la sessione diventa attiva/produce energia (`not _session_counted`), evitando falsi multipli su micro-oscillazioni mentre resta collegata. Chiude `_session_active = False` quando `!plugged and not charging` (o l'odometro aumenta).
- **Serie storiche compatte**:
  - `daily_history`: mappa ordinata fino a `DAILY_HISTORY_LIMIT` (30) giorni (`YYYY-MM-DD -> { total_kwh, home_kwh, away_kwh, sessions_count }`), potata alle date più recenti.
  - `monthly_history`: mappa ordinata fino a `MONTHLY_HISTORY_LIMIT` (12) mesi (`YYYY-MM -> { total_kwh, home_kwh, away_kwh, sessions_count }`), potata ai mesi più recenti.
- **Reset (`reset_from_start()`)**:
  - Azzera esclusivamente `self._from_start` (`total_kwh = 0.0`, `home_kwh = 0.0`, `away_kwh = 0.0`, `sessions_count = 0`), lasciando intatti `today`, `month`, `year`, `daily_history`, `monthly_history` e i baseline correnti.
- **Serializzazione resiliente (`to_dict()` / `from_dict()`)**:
  - `version: 1`, zero PII (nessun VIN, lat/lon o token). `from_dict` scarta valori non finiti/negativi o chiavi malformate senza mai sollevare eccezioni.

---

## 4. Integrazione Coordinator, `LepasChargedEnergy`, Entità & Traduzioni

### 4.1 `custom_components/lepas/coordinator.py` & `__init__.py`
- In `LepasCoordinator.__init__`:
  - `self._charging_lock: threading.Lock = threading.Lock()` (lock dedicato, **mai annidato** con `_state_lock`, `_hv_lock` o `_consumption_lock` per rispetto di `AB-LEP-007` / `AB-LEP-014`).
  - `self._charging_tracker: ChargingStatsTracker = ChargingStatsTracker()`
  - `self._charging_store: Store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.charging_stats")`
- **Ciclo di vita `Store`**:
  - `async_start()`: chiama `await self.async_load_charging_stats()` insieme a `async_load_consumption()` prima di connettere MQTT.
  - `_apply_update(patch)` (eseguito **sempre sul loop eventi HA** via `call_soon_threadsafe`, unificando sia `_on_probe_data` sia `_on_car_message` senza accessi cross-thread a `hass.states`): chiama `self._ingest_charging_stats_on_loop()`, che legge `rt` / `fields` / `position`, calcola `in_zona_casa(self.hass, pos)` e `dt_util.as_local(dt_util.utcnow()).date().isoformat()`, esegue `self._charging_tracker.ingest(...)` sotto `self._charging_lock`, e se `changed` schedula `self._charging_store.async_delay_save(self._charging_snapshot, 30)`.
  - `async_unload_entry()` in `__init__.py`: chiama `await coordinator.async_flush_charging_stats()` subito dopo `async_flush_consumption()`.
- **Metodi pubblici coordinator**:
  - `charging_stats(period: str) -> dict[str, object]` (calcola `local_date` corrente con `dt_util.as_local` e legge sotto `_charging_lock`).
  - `async_reset_charging_from_start() -> None` (resetta `from_start`, salva subito su `_charging_store`, notifica i listener se non in chiusura).

### 4.2 Miglioramento Contestuale di `LepasChargedEnergy` (`custom_components/lepas/sensor.py`)
- Mantiene intatti `unique_id`, `entity_id` (`sensor.lepas_home_charging_energy`, `sensor.lepas_away_charging_energy`), `SensorDeviceClass.ENERGY`, `SensorStateClass.TOTAL_INCREASING`, `RestoreSensor` e `available = bool(self.coordinator.poll_enabled)`.
- In `_campiona()` sostituisce l'integrazione puramente limitata a `<= 300s` con l'helper puro condiviso `compute_charge_delta_kwh(...)`:
  - Per `dt <= 300s`: integrazione trapezoidale su `chargingPower` (comportamento identico al precedente).
  - Per `dt > 300s` (buco di polling a runtime mentre è collegata nella stessa zona): riconciliazione tramite delta SoC (`(soc_now - soc_prev) / 100 * coordinator.battery_capacity_kwh`) purché `delta_kwh > 0`, frame non degradato, odometro non aumentato e `in_zona_casa == self._home`. La continuità cross-riavvio HA (con baseline SoC persistiti su `Store`) è invece garantita dai nuovi sensori `ChargingStatsTracker` (§3–§4.1), mantenendo `LepasChargedEnergy` privo di attributi extra non necessari per la Dashboard Energia.
  - Monotonicità garantita: `self._energia_wh` può solo aumentare (`delta_kwh > 0`).

### 4.3 Nuove Entità HA & Conteggi
- **`sensor.py` (`LepasChargingStatsSensor(LepasEntity, SensorEntity)`)**:
  - `_attr_device_class = SensorDeviceClass.ENERGY`
  - `_attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR`
  - `_attr_state_class = SensorStateClass.TOTAL`
  - `_attr_suggested_display_precision = 2`
  - 4 istanze:
    1. `sensor.lepas_charging_energy_today` (`unique_suffix="charging_energy_today"`, `icon="mdi:calendar-today"`, include `daily_series` negli attributi — ultimi 30 giorni in ordine cronologico).
    2. `sensor.lepas_charging_energy_month` (`unique_suffix="charging_energy_month"`, `icon="mdi:calendar-month"`).
    3. `sensor.lepas_charging_energy_year` (`unique_suffix="charging_energy_year"`, `icon="mdi:calendar"`, include `monthly_series` negli attributi — ultimi 12 mesi in ordine cronologico).
    4. `sensor.lepas_charging_energy_from_start` (`unique_suffix="charging_energy_from_start"`, `icon="mdi:ev-plug-type2"`).
  - `extra_state_attributes` su tutti e 4: `home_kwh`, `away_kwh`, `sessions_count`, `period_key` (e `daily_series` su `today`, `monthly_series` su `year`).
  - `available`: segue `LepasEntity` (non richiede `poll_enabled` per mostrare i dati storici già accumulati in `Store`).
- **`button.py` (`LepasActionButton`)**:
  - `button.lepas_reset_charging_from_start` (`suffix="reset_charging_from_start"`, `EntityCategory.CONFIG`, `icon="mdi:restart"`, `translation_key="reset_charging_from_start"`).
- **Traduzioni & Test Strutturali**:
  - `strings.json`, `translations/en.json`, `translations/it.json`, `translations/nl.json` aggiornati per i 4 sensori + 1 pulsante.
  - `tests/test_entity_count.py` aggiornato (`sensor: 50 → 54`, `button: 16 → 17`, `TOTALE_ATTESO: 142 → 147`).

---

## 5. Seconda Card Lovelace `lepas-stats-card` & Pulizia `lepas-card` (`lepas-card.js`)

Tutto il frontend rimane in un unico bundle `custom_components/lepas/lovelace/lepas-card.js` (nessuna modifica richiesta al backend statico in `__init__.py`, cache-busting `?v=X.Y.Z` condiviso).

### 5.1 Pulizia della Card Principale (`LepasCard`)
- Rimozione di `consSection` (`buildConsRowHtml` / `consHtml`) dalla tab *Panoramica* di `LepasCard` e dei relativi binding (`consEv*`, `consHyb*`), rendendo la card principale puramente operativa.

### 5.2 Nuova Card `LepasStatsCard` & `LepasStatsCardEditor`
- **Registrazione**:
  - `customElements.define("lepas-stats-card-editor", LepasStatsCardEditor)`
  - `customElements.define("lepas-stats-card", LepasStatsCard)`
  - `window.customCards.push({ type: "lepas-stats-card", name: "Lepas Stats Card", preview: true, description: "..." })` (senza prefisso `custom:` in `type`, regola `AB-LEP-008`).
- **Stile e Vincoli Tecnici**:
  - Design system *Matte Titanium* condiviso con `LepasCard` (`--lp-canvas: #111317`, `--lp-surface: #181B20`, `--lp-elevated: #21252C`, `--lp-emerald: #34D399`, `--lp-glacier: #60A5FA`, `.num` tabular-nums).
  - Zero `?.` (optional chaining), zero `??` (nullish coalescing), zero `import`/`export` top-level (IIFE CJS-safe), zero `#00D2FF` o `:host-context`.
  - Traduzioni complete `it`, `en`, `nl` in `I18N`.
- **Struttura Card (`LepasStatsCard`)**:
  - **Header**: icona + titolo configurabile (default localizzato *"Statistiche Lepas"*).
  - **Sezione 1 — Ricarica** (visibile se `config.show_charging !== false`):
    - Header sezione con:
      - Titolo *"Ricarica"* + icona `bolt`.
      - Toggle segmentato **`Tutte | Casa | Fuori`** (default configurabile via `config.default_scope`, default `"all"`).
      - Pulsante discreto **Reset (`Da inizio`)** (visibile se `config.show_reset_buttons !== false` e `button.*reset_charging_from_start` presente): al click apre la finestra di conferma e, se confermato, chiama `hass.callService("button", "press", { entity_id })`.
    - **Griglia 4 KPI (`.cons-grid`)**: `Oggi`, `Mese`, `Anno`, `Da inizio`.
      - Mostra il valore in `kWh` coerente con lo scope selezionato (`total`, `home_kwh`, `away_kwh`).
      - Quando lo scope è `Tutte`, mostra una sotto-riga compatta con `Casa X · Fuori Y` (e numero sessioni se `> 0`); cliccando su qualsiasi riquadro si apre `hass-more-info` dell'entità corrispondente.
    - **Mini-grafico a barre SVG puro** (visibile se `config.show_chart !== false`):
      - Toggle **`7g | 30g | 12m`** (default `config.default_chart || "7d"`).
      - Barre verticali SVG alimentate da `daily_series` (ultimi 7 o 30 giorni) o `monthly_series` (ultimi 12 mesi):
        - In modalità `Tutte`: barre impilate **Casa** (`#34D399` emerald) + **Fuori** (`#60A5FA` glacier), con eventuale residuo non localizzato (`#9CA3AF`).
        - In modalità `Casa` / `Fuori`: barra singola con il colore corrispondente.
        - Stato vuoto elegante se non ci sono ancora sessioni nel periodo, e tooltip/etichetta valore sintetico al focus/tap/hover su ciascuna barra.
  - **Sezione 2 — Consumi medi** (visibile se `config.show_consumption !== false` e presenti sensori consumo):
    - Header sezione con titolo *"Consumi medi"*, e pulsante discreto **Reset (`Da inizio`)** con finestra di conferma che invoca `button.press` su `reset_consumption_from_start`.
    - Righe **EV** (`50 km` / `100 km` / `1000 km` / `Da inizio`, toggle `kWh/100` ↔ `kWh/km`) e **Ibrida** (`50 km` / `100 km` / `1000 km` / `Da inizio`, toggle `L/100` ↔ `km/L`, nascosta su BEV), identiche nello stile a quanto rimosso da `LepasCard`, con `hass-more-info` su ogni cella.
- **Editor Visuale (`LepasStatsCardEditor`)**:
  - `title` (testo), `default_scope` (`all` / `home` / `away`), `default_chart` (`7d` / `30d` / `12m`), checkbox `show_charging` (default `true`), `show_consumption` (default `true`), `show_chart` (default `true`), `show_reset_buttons` (default `true`).
  - `getStubConfig()` ritorna `{ type: "custom:lepas-stats-card" }`.
  - `getGridOptions()` ritorna `{ columns: 12, min_columns: 4, rows: "auto" }`.

---

## 6. Verifica e Criteri di Successo

1. **Test unitari puri (`tests/test_charging_stats.py`)**:
   - Integrazione trapezoidale `<= 300s`, riconciliazione delta SoC sui buchi `> 300s` (nessun doppio conteggio sullo stesso intervallo), scarto frame degradati (`is_degraded_battery_frame`), reset continuità su avanzamento odometro, rollover giornaliero/mensile/annuale sia su `ingest` sia in lettura, attribuzione `home`/`away`/`None` (`total` garantito), conteggio `sessions_count`, potatura `30` giorni / `12` mesi, `reset_from_start()`, deserializzazione resiliente a payload corrotti.
2. **Test integrazione HA (`tests/test_energia_ricarica.py`, `tests/test_sensors.py`, `tests/test_entity_count.py`, `tests/test_traduzioni_complete.py`, `tests/test_translation_key_declared.py`)**:
   - Verifica `LepasChargedEnergy` con recupero delta SoC su buchi `> 300s` + monotonicità `TOTAL_INCREASING`.
   - Verifica ciclo `Store` in `LepasCoordinator` (`load`, `delay_save`, `flush` su unload, `async_reset_charging_from_start`, nessun annidamento lock).
   - Verifica 4 nuovi sensori + 1 nuovo pulsante + conteggio totale `147` entità + traduzioni `en`/`it`/`nl`.
3. **Test Frontend & Lint (`tests/test_lovelace_card.py`, `tests/lepas_card.test.mjs`, `ruff`)**:
   - `LepasCard` non renderizza più `consSection`.
   - `LepasStatsCard` registrata in `window.customCards` senza prefisso `custom:`, renderizza KPI Ricarica + toggle `Tutte/Casa/Fuori` + grafico SVG `7g/30g/12m` + Consumi medi + entrambi i reset con dialog di conferma + `LepasStatsCardEditor` + traduzioni `it`/`en`/`nl`.
   - `node --check`, `node --test tests/lepas_card.test.mjs`, `uv run --with pytest pytest -q --tb=short --maxfail=2`, `uv run ruff check custom_components/ tests/`, `uv run ruff format --check custom_components/ tests/`.
