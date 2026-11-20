# What is new in Lepas Connect for Home Assistant

What changes with each update, in plain words. The most recent entries are at
the top. Versions are the "episode" number of the integration: update from
**HACS → Lepas Connect → Update**.

Every release is written in both languages, English first.

---

# Novità di Lepas Connect per Home Assistant

Cosa cambia a ogni aggiornamento, spiegato in parole semplici.
Le voci più recenti sono in alto. Le versioni indicano la "puntata"
dell'integrazione: aggiorna da **HACS → Lepas Connect → Aggiorna**.

## [Non rilasciato]

## v1.32.1 — 2026-11-20

### 🇬🇧 English

- **Statistics Modal Chart Y-Axis & `kWh` Scale (`lepas-card.js`, `docs/images/lepas-card-stats.png`)**: Added a vertical Y-axis (`chart-yaxis`), subtle mid/top horizontal dashed gridlines (`chart-gridline`), proportional `niceChartStep` scaling (`0`, mid, and top ticks), and a `kWh` unit legend (`chart-yaxis-unit`) to the **Charged energy history** SVG bar chart inside the Statistics modal so bar heights are immediately readable without hovering. Updated `docs/images/lepas-card-stats.png` and bumped card assets to `?v=1.32.1`.

### 🇮🇹 Italiano

- **Asse Verticale `kWh` e Griglie nel Grafico Statistiche (`lepas-card.js`, `docs/images/lepas-card-stats.png`)**: Aggiunti asse verticale (`chart-yaxis`), griglie orizzontali tratteggiate intermedia e superiore (`chart-gridline`), scala proporzionale dinamica tramite `niceChartStep` (`0`, valore intermedio e massimo) e legenda unità **`kWh`** (`chart-yaxis-unit`) nel grafico SVG **Storico energia ricaricata** della modale Statistiche, così da rendere leggibili a colpo d'occhio i valori delle barre. Aggiornato `docs/images/lepas-card-stats.png` e aggiornati gli asset della card a `?v=1.32.1`.

## v1.32.0 — 2026-11-20

### 🇬🇧 English

- **Horizontal 2-Column Desktop Cockpit, Compact Inline Statistics & Zero-Flicker Updates (`lepas-card.js`, `README.md`, `docs/images/`)**: Redesigned `custom:lepas-card` for desktop (`cockpit` and `auto >= 680px` via shared `desktopLayoutRules` ES5 CSS parity across `@container` and `@supports not`) into a balanced 2-column horizontal Cockpit: the left column pairs the `16:9` hero render (with a multi-stop SoC SVG ring gradient), 2×2 KPI grid, Overview `Updated / Sync` surface (with desktop `Wake car` button), and a compact 3-KPI inline **Statistics** card (`Charging · Today`, `EV · 50 km`, `Fuel/Hybrid · 50 km`, capped at `max-height: 152px` with 1-click access to the full `<dialog>` modal); the right column places the 3-tab operational switcher (`Climate | Charging | Security`) on top with `.is-desktop-fallback` to Security when `default_tab` is `overview`, hides duplicate quick actions, adds a `Scheduled charging | Departure scheduler` switcher inside Charging, renders all 12 `Departure climate extras` in a compact 3-column desktop grid without removing any Mobile/Compact control, and gives `Climate` and `Security` (expanded top-down SUV + TPMS stage) balanced desktop ergonomics. Also removed `warnSig` from `structKey` to eliminate DOM-rebuild flicker on warning updates, aligned `LepasCardEditor` image placeholder to `CARD_VERSION`, updated `docs/images/lepas-card-cockpit.png` & `docs/images/lepas-card-security.png`, and bumped card assets to `?v=1.32.0`.

### 🇮🇹 Italiano

- **Plancia Cockpit Orizzontale a 2 Colonne, Statistiche Compatte Inline e Zero Flicker (`lepas-card.js`, `README.md`, `docs/images/`)**: Ridisegnata la `custom:lepas-card` su desktop (`cockpit` e `auto >= 680px` con parità ES5 condivisa tramite `desktopLayoutRules` su `@container` e `@supports not`) in un layout Cockpit orizzontale bilanciato a 2 colonne: la colonna sinistra abbina l'immagine hero `16:9` (con gradiente SVG dinamico sull'anello SoC), la griglia KPI 2×2, la sezione `Aggiornato / Sync` (con tasto desktop `Sveglia auto`) e il riquadro compatto **Statistiche** a 3 KPI inline (`Ricarica · Oggi`, `EV · 50 km`, `Carburante/Ibrido · 50 km`, limitato a `max-height: 152px` con apertura rapida del `<dialog>` completo); la colonna destra sposta in alto lo switcher operativo a 3 tab (`Clima | Ricarica | Sicurezza`) con fallback desktop automatico su `Sicurezza` quando `default_tab` è `overview`, nasconde i comandi rapidi duplicati, aggiunge il selettore `Ricarica programmata | Partenze programmate` in Ricarica, dispone tutti i 12 extra clima alla partenza su 3 colonne compatte su desktop senza rimuovere nessun controllo rispetto a Mobile/Compact e bilancia spaziature ed ergonomia di `Clima` e `Sicurezza` (schema auto dall'alto e TPMS ingranditi). Rimosso inoltre `warnSig` da `structKey` per eliminare il flicker di ricostruzione DOM sugli avvisi, allineato il placeholder di `LepasCardEditor` a `CARD_VERSION`, aggiornati gli screenshot `docs/images/lepas-card-cockpit.png` e `docs/images/lepas-card-security.png` e aggiornati gli asset della card a `?v=1.32.0`.

## v1.31.2 — 2026-11-20

### 🇬🇧 English

- **Documentation & Dashboard Preview Update (`README.md`, `docs/images/`)**: Aligned `README.md` with `v1.31.2` capabilities (`147` active entities across `11` platforms, Matte Titanium `custom:lepas-card`, persistent charging statistics & EV/Hybrid consumption engine, scheduled departures & battery preheating, climate/closure sync, `5` services, active `.agents/memory/antibodies/lepas.md` index, and verified local test commands), added the adaptive light/dark brand logo (`logo@2x.png` / `dark_logo@2x.png`) and three synthetic PII-free dashboard previews (`lepas-card-cockpit.png`, `lepas-card-security.png`, `lepas-card-stats.png`), clarified in the `[!CAUTION]` disclaimer that the integration is currently tested only on the Lepas L8 version distributed in Italy, and added a `[!TIP]` recommending a dedicated/delegated secondary account so Home Assistant polling does not sign out the official mobile app. Also bumped card assets in `lepas-card.js` to `?v=1.31.2`.

### 🇮🇹 Italiano

- **Aggiornamento Documentazione & Anteprima Plancia (`README.md`, `docs/images/`)**: Allineato `README.md` alle funzionalità di `v1.31.2` (`147` entità attive su `11` piattaforme, card Matte Titanium `custom:lepas-card`, statistiche di ricarica persistenti e motore consumi EV/Ibrido, partenze programmate e preriscaldamento batteria, sincronizzazione clima/chiusure, `5` servizi, collegamento aggiornato a `.agents/memory/antibodies/lepas.md` e comandi di test verificati), aggiunti il nuovo logo adattivo chiaro/scuro (`logo@2x.png` / `dark_logo@2x.png`) e tre screenshot sintetici senza PII della plancia (`lepas-card-cockpit.png`, `lepas-card-security.png`, `lepas-card-stats.png`), precisato nel disclaimer `[!CAUTION]` che l'integrazione è attualmente testata solo sulla versione Lepas L8 distribuita in Italia, e aggiunto il riquadro `[!TIP]` che consiglia un account dedicato/delegato per evitare la disconnessione dell'app ufficiale sullo smartphone. Aggiornati anche gli asset della card in `lepas-card.js` a `?v=1.31.2`.

## v1.31.1 — 2026-11-20

### 🇬🇧 English

- **Automatic Closure Sync on Vehicle Lock (`const.py`, `coordinator.py`, `entity.py`)**: Added shared `_apply_lock_auto_close` logic across `_on_car_message` and `_on_probe_data` so that a confirmed `blocca` command or an external `doorLock` transition (`unlocked → locked`, e.g. physical key fob or official app) automatically sets `sunroofState`, `sunshadeState`, and all four window states (`frontLeftWindowState`, `frontRightWindowState`, `backLeftWindowState`, `backRightWindowState`) to closed (`"0"`) when omitted from the payload, clearing pending optimistic cover states while explicitly excluding `trunkDoor` and `hood` and preserving any explicitly open fields or rejected lock commands.
- **Fast Realtime Closure Settlement & Post-Command Verification (`const.py`, `timers.py`, `coordinator.py`, `entity.py`)**: Replaced the 300 s `awake_window` block on `CLOSURE_META_KEYS` in `_on_probe_data` with a 15 s `PROBE_MQTT_GRACE_S` window (preserving `awake_window` protection for non-closure telemetry and keeping `msg_fields` untouched), updated `LepasOptimisticMixin._verita_arrivata` to settle immediately on semantic `probe_changed_fields` or within `PROBE_OPT_SETTLE_S` (60 s) instead of waiting 15 minutes (`OPT_MAX_S`), and added a read-only `TimerRegistry`-managed two-step `CMD_PROBE` (`+25 s`, `+90 s`) after closure commands when `poll_enabled` is active (no `vehicleLocation` wakes, clean cancellation on `set_poll_enabled(False)` and `async_stop()`). Also bumped card assets in `lepas-card.js` to `?v=1.31.1`.

### 🇮🇹 Italiano

- **Sincronizzazione Automatica Chiusure al Blocco Veicolo (`const.py`, `coordinator.py`, `entity.py`)**: Introdotta la logica condivisa `_apply_lock_auto_close` tra `_on_car_message` e `_on_probe_data` in modo che la conferma positiva di `blocca` o una transizione esterna di `doorLock` (`sbloccata → bloccata`, es. telecomando/chiave fisica o app ufficiale) porti subito a chiuso (`"0"`) `sunroofState`, `sunshadeState` e tutti e quattro i finestrini (`frontLeftWindowState`, `frontRightWindowState`, `backLeftWindowState`, `backRightWindowState`) quando omessi dal payload, chiudendo l'eventuale ottimismo pendente delle cover ed escludendo esplicitamente `trunkDoor` (baule) e `hood` (cofano), senza mai agire su comandi rifiutati o campi esplicitamente aperti.
- **Riallineamento Rapido Chiusure Manuali & Verifica Post-Comando (`const.py`, `timers.py`, `coordinator.py`, `entity.py`)**: Sostituito il blocco di 300 s (`awake_window`) sui campi `CLOSURE_META_KEYS` in `_on_probe_data` con una finestra breve `PROBE_MQTT_GRACE_S` di 15 s (mantenendo invariata la protezione `awake_window` sulle altre telemetrie e senza popolare `msg_fields`), aggiornato `LepasOptimisticMixin._verita_arrivata` per chiudere l'ottimismo subito su `probe_changed_fields` o entro `PROBE_OPT_SETTLE_S` (60 s) anziché attendere 15 minuti (`OPT_MAX_S`), e aggiunta la doppia lettura passiva `CMD_PROBE` (`+25 s`, `+90 s`) gestita da `TimerRegistry` dopo i comandi sulle chiusure con aggiornamento automatico attivo (zero sveglie `vehicleLocation`, cancellazione pulita su `set_poll_enabled(False)` e `async_stop()`). Aggiornati anche gli asset della card in `lepas-card.js` a `?v=1.31.1`.

## v1.31.0 — 2026-11-20

### 🇬🇧 English

- **Automatic Vehicle Color Detection (`const.py`, `coordinator.py`, `sensor.py`, `diagnostics.py`)**: Extracted the vehicle paint code and localized/English color name (`colorCode`, `colorNameEn`, `colorName`) from `vmc/queryList` via `normalize_vehicle_color()` and `capabilities_from_item()`, persisted them in `entry.data` with a one-time `DATA_CAPS_PROBED_V6` backfill for existing installs, exposed non-PII `vehicle_color` / `vehicle_color_code` / `vehicle_color_name` attributes on `LepasSessionStatus` (`sensor.lepas_session_status`), and added them under `diag["vehicle"]` in diagnostics.
- **Automatic Card Color & `"Auto"` Editor Swatch (`lepas-card.js`)**: Added `resolveCardColor` / `resolveHeroImage` automatic vehicle color resolution (used whenever `config.color` is unset or `"auto"` while keeping explicit manual `config.color` overrides and `vehicle_image` precedence intact), updated both the hero image and Blueprint SVG (`.bp-stage[data-car-color]`) reactively, added the `"Auto"` swatch in `LepasCardEditor`, and bumped card assets to `?v=1.31.0`.

### 🇮🇹 Italiano

- **Auto-rilevamento Colore Veicolo (`const.py`, `coordinator.py`, `sensor.py`, `diagnostics.py`)**: Estratti codice vernice e nome colore (`colorCode`, `colorNameEn`, `colorName`) da `vmc/queryList` tramite `normalize_vehicle_color()` e `capabilities_from_item()`, salvati in `entry.data` con backfill una-tantum `DATA_CAPS_PROBED_V6` per le installazioni esistenti, esposti come attributi non-PII `vehicle_color` / `vehicle_color_code` / `vehicle_color_name` su `LepasSessionStatus` (`sensor.lepas_session_status`), e aggiunti nella sezione `vehicle` della diagnostica.
- **Colore Automatico nella Card e Opzione `"Auto"` nell'Editor (`lepas-card.js`)**: Aggiunta la risoluzione automatica del colore tramite `resolveCardColor` / `resolveHeroImage` (attiva quando `config.color` è vuoto o `"auto"`, preservando la precedenza di eventuali override manuali `config.color` e `vehicle_image`), aggiornati reattivamente sia l'immagine hero sia il Blueprint SVG (`.bp-stage[data-car-color]`), aggiunto il selettore `"Auto"` in `LepasCardEditor`, e aggiornati gli asset della card a `?v=1.31.0`.

## v1.30.3 — 2026-11-20

### 🇬🇧 English

- **Hero Layout & Status Pill Deduplication (`lepas-card.js`)**: Removed the redundant `"Offline"` warning chip from `.warns-row` while making the top-left `.status-pill` clickable and keyboard-accessible (`more-info` on `binary_sensor.lepas_connection`), moved the Statistics modal button (`statsBtn`) from the top-right hero image overlay into the bottom-right `.hero-meta` bar (isolated from `data-device` navigation) so the SoC ring stands cleanly on the vehicle render, shortened `statsCardDefaultTitle` to `Statistics` / `Statistiche` / `Statistieken`, and bumped card assets to `?v=1.30.3`.

### 🇮🇹 Italiano

- **Pulizia Layout Hero e Rimozione Stato `Offline` Duplicato (`lepas-card.js`)**: Rimosso il chip rosso ridondante `Offline` da `.warns-row` rendendo cliccabile e accessibile da tastiera la pillola `.status-pill` in alto a sinistra (`more-info` su `binary_sensor.lepas_connection`), spostato il pulsante delle Statistiche (`statsBtn`) dall'angolo superiore destro della foto alla fascia inferiore `.hero-meta` in basso a destra (isolato dalla navigazione `data-device`) per lasciare pulito l'anello SoC sull'auto, abbreviato il titolo del modale `statsCardDefaultTitle` in `Statistiche` (`Statistics` / `Statistieken`), e aggiornati gli asset della card a `?v=1.30.3`.

## v1.30.2 — 2026-11-20

### 🇬🇧 English

- **Context-Aware ECU `0:95` Rejection & Optimistic Rollback (`coordinator.py`)**: Tracked the active command key and timestamp (`_last_cmd_key`, `_last_cmd_at` under `_state_lock`) so MQTT `110x` confirmations carrying `[0:95]` are treated as benign only for `Clima` commands with non-failure results (`result != "0"`). For access/closure commands (`blocca`, `sblocca`, `finestrini_*`, `tetto_*`, `baule_*`) or explicit `result == "0"` failures, `cmd_rejected_other` is set to `True` (immediately rolling back optimistic `LepasCover` / `LepasLock` states instead of leaving e.g. `cover.lepas_windows` stuck on `open` for 900s), `car_in_use` latches when HV is active, and `sensor.lepas_command_result` reports a clear rejection warning. Preserved `"result": "3"` as non-failure on `airControl` / `cmd_confirm` acknowledgements.
- **`HomeAssistantError` Propagation on Command Buttons (`button.py`)**: Updated `LepasCommandButton.async_press` to re-raise `HomeAssistantError` and wrap unexpected errors into `HomeAssistantError` instead of silently swallowing command send failures.
- **Unified `car_in_use` Gating on Security & Overview Quick Actions (`lepas-card.js`)**: Hoisted `carInUse` / `applyCarInUseState` above Overview & Security bindings, added `secCarInUseBanner` to the *Security* tab, disabled *Security* controls (`Lock`, `Trunk`, `Windows`, `Vent windows`, `Sunroof`, `Vent sunroof`, `Alarm`, `Remote start`, `Locate GPS`, `Flash lights`) and *Overview* quick-action mirrors (`Quick lock`, `Quick climate`, `Quick trunk`, `Flash lights`) while `car_in_use` is `true` (keeping `Wake`, `Refresh location`, `Refresh full status`, `Statistics`, and charging controls active), cleared `_lastCmdFeedback` when an MQTT error arrives in flight during `_callService`, and bumped card assets to `?v=1.30.2`.

### 🇮🇹 Italiano

- **Gestione Contestuale Rifiuti ECU `0:95` e Rollback Ottimistico (`coordinator.py`)**: Tracciati chiave e timestamp dell'ultimo comando (`_last_cmd_key`, `_last_cmd_at` sotto `_state_lock`) in modo che le conferme MQTT `110x` con `[0:95]` siano considerate innocue solo per comandi del gruppo `Clima` con esito non di fallimento (`result != "0"`). Sui comandi di accesso/chiusure (`blocca`, `sblocca`, `finestrini_*`, `tetto_*`, `baule_*`) o su esito esplicito `result == "0"`, `cmd_rejected_other` viene impostato a `True` (annullando subito lo stato ottimistico di `LepasCover` / `LepasLock` invece di lasciare `cover.lepas_windows` bloccata su `open` per 900s), il latch `car_in_use` si aggancia con HV attiva e `sensor.lepas_command_result` mostra un avviso chiaro di rifiuto. Preservato `"result": "3"` come non-errore per le conferme `airControl` / `cmd_confirm`.
- **Propagazione `HomeAssistantError` sui Pulsanti Comando (`button.py`)**: Aggiornato `LepasCommandButton.async_press` per rilanciare `HomeAssistantError` e incapsulare eventuali altre eccezioni invece di ingoiare silenziosamente gli errori di invio.
- **Blocco `car_in_use` Uniforme su Sicurezza e Azioni Rapide Plancia (`lepas-card.js`)**: Eseguito hoisting di `carInUse` / `applyCarInUseState` sopra i binding di Plancia e Sicurezza, aggiunto `secCarInUseBanner` nel pannello *Sicurezza*, disabilitati i comandi *Sicurezza* (`Blocca/Sblocca`, `Baule`, `Finestrini`, `Ventila finestrini`, `Tetto`, `Ventila tetto`, `Allarme`, `Avvio remoto`, `Localizza GPS`, `Lampeggia`) e i rispettivi specchi rapidi in *Plancia* quando `car_in_use` è attivo (mantenendo sempre attivi `Sveglia`, `Aggiorna posizione`, `Aggiorna stato`, `Statistiche` e ricarica), azzerato `_lastCmdFeedback` se un errore MQTT arriva mentre `_callService` è in volo, e aggiornati gli asset della card a `?v=1.30.2`.

## v1.30.1 — 2026-11-19

### 🇬🇧 English

- **Integrated Statistics Modal inside `LepasCard` & Removal of `LepasStatsCard` (`lepas-card.js`)**: Consolidated all charging statistics (`All | Home | Away` scope toggle, 4 KPI tiles, `7d | 30d | 12m` SVG bar chart with tooltips, confirmed reset) and average consumption grids (EV + Hybrid with persistent unit toggles, `50 km`/`100 km`/`1000 km`/`From start` metrics, and confirmed reset) into an on-demand modal `<dialog>` opened from a compact Statistics icon button in the hero overlay (keeping the 4-tab layout and desktop Cockpit grid unchanged, with an internal modal error banner and in-flight reset lock). Removed `LepasStatsCard`, `LepasStatsCardEditor`, and the `lepas-stats-card` registration from `window.customCards` and `customElements`.
- **Overview-Only Command Badge with 5-Minute Success TTL (`lepas-card.js`)**: Removed the duplicate `climateCmdBar` from the *Climate* tab so `cmdResultBadge` appears only in the *Overview* footer, suppressed idle `"In attesa"` / `"Waiting"` / `"Wachten"` placeholders, kept error outcomes persistently visible, and added a 5-minute TTL (plus auto-hide timer cleanup) for successful command outcomes.
- **Climate Duration Capability Alignment (`number.py`, `lepas-card.js`)**: Aligned `number.lepas_climate_duration` (`min`, `max`, `step`, `allowed_durations` attribute, and restore/input snapping via `durata_ammessa`) and `LepasCard` duration chips with the vehicle's declared `maxAirDuration` capabilities (`5, 10, 15` min on Lepas L8) while preserving immediate `notify_schedule_changed()` updates on `sensor.lepas_next_departure`, and bumped card assets to `?v=1.30.1`.

### 🇮🇹 Italiano

- **Modale Statistiche Integrata in `LepasCard` e Rimozione `LepasStatsCard` (`lepas-card.js`)**: Integrate le statistiche di ricarica (selettore `Tutte | Casa | Fuori`, 4 KPI, grafico a barre SVG `7g | 30g | 12m` con tooltip, reset con conferma) e i consumi medi (EV + Ibrido con selettori unità persistenti, metriche `50 km`/`100 km`/`1000 km`/`Da inizio` e reset con conferma) in un popup `<dialog>` dedicato accessibile dal pulsante compatto Statistiche in alto nell'hero (mantenendo invariati i 4 tab e la griglia Cockpit desktop, con banner errori interno al modale e lock anti-doppio invio sul reset). Rimosse `LepasStatsCard`, `LepasStatsCardEditor` e la registrazione `lepas-stats-card` da `window.customCards` e `customElements`.
- **Badge `Ultimo comando` Solo in Plancia con Scadenza 5 Minuti (`lepas-card.js`)**: Rimossa la barra duplicata `climateCmdBar` dal pannello *Clima* lasciando `cmdResultBadge` solo nel footer di *Plancia*, nascosti gli stati di attesa (`"In attesa"` / `"Waiting"` / `"Wachten"`), mantenuti sempre visibili eventuali errori, e introdotto un TTL di 5 minuti sui successi con timer automatico di pulizia.
- **Allineamento Durata Clima alle Capability del Veicolo (`number.py`, `lepas-card.js`)**: Allineati `number.lepas_climate_duration` (`min`, `max`, `step`, attributo `allowed_durations` e snap in ripristino/impostazione tramite `durata_ammessa`) e i chip di durata nella scheda alle durate ammesse da `maxAirDuration` (`5, 10, 15` min su Lepas L8) preservando l'aggiornamento immediato di `sensor.lepas_next_departure`, con aggiornamento asset a `?v=1.30.1`.

## v1.30.0 — 2026-11-19

### 🇬🇧 English

- **Persistent Charging Energy Statistics Engine (`charging_stats.py`, `coordinator.py`, `sensor.py`, `button.py`)**: Added autonomous Home Assistant `Store`-backed charging statistics with hybrid energy integration (trapezoidal `chargingPower` for gaps `<= 300s` plus SoC-delta reconciliation for polling gaps `> 300s` and restarts, guarding against degraded battery frames and odometer advances), local-timezone rollover across **Today**, **Month**, **Year**, and **From start**, session counting, compact 30-day / 12-month history series, 4 new periodic energy sensors (`sensor.lepas_charging_energy_{today,month,year,from_start}`) with `home_kwh` / `away_kwh` attributes, and `button.lepas_reset_charging_from_start` (`142 → 147` entities).
- **Hybrid Upgrade for Energy Dashboard Counters (`sensor.py`)**: Updated `LepasChargedEnergy` (`home_charging_energy`, `away_charging_energy`) to share `compute_charge_delta_kwh()` so slow AC polling gaps `> 300s` reconcile from SoC deltas while preserving `TOTAL_INCREASING` monotonicity and `zone.home` isolation.
- **Dedicated `LepasStatsCard` & Main Card Cleanup (`lepas-card.js`)**: Registered a new `lepas-stats-card` (`LepasStatsCard` + `LepasStatsCardEditor`) in the Lovelace bundle unifying **Charging** (`All | Home | Away` scope toggle, 4 KPI tiles, stacked SVG bar chart `7d | 30d | 12m`, confirmed reset button) and **Average consumption** (EV + Hybrid grids with unit toggles and confirmed reset button); removed `consSection`, the redundant `fastPortBadge` tile (keeping AC/DC detection), and scheduled-charging preset buttons/badge (`preset-row` / `chgDaysPresetLbl`) from `LepasCard`; redesigned the hero SoC badge with two concentric rings (outer SoC % arc + inner charging pulse ring) and bumped card assets to `?v=1.30.0`.

### 🇮🇹 Italiano

- **Motore Statistiche di Ricarica Persistenti (`charging_stats.py`, `coordinator.py`, `sensor.py`, `button.py`)**: Introdotte statistiche di ricarica persistenti su `Store` di Home Assistant con integratore ibrido (`chargingPower` trapezoidale per intervalli `<= 300s` + riconciliazione delta SoC per buchi `> 300s` e riavvii, scartando frame batteria degradati e spostamenti odometro), rollover nel fuso locale su **Oggi**, **Mese**, **Anno** e **Da inizio**, conteggio sessioni, serie storiche compatte 30 giorni / 12 mesi, 4 nuovi sensori periodici (`sensor.lepas_charging_energy_{today,month,year,from_start}`) con attributi `home_kwh` / `away_kwh`, e `button.lepas_reset_charging_from_start` (`142 → 147` entità).
- **Upgrade Ibrido per Contatori Dashboard Energia (`sensor.py`)**: Aggiornato `LepasChargedEnergy` (`home_charging_energy`, `away_charging_energy`) con l'helper condiviso `compute_charge_delta_kwh()` per recuperare i buchi `> 300s` su cariche AC lente mantenendo monotonicità `TOTAL_INCREASING` e isolamento `zone.home`.
- **Nuova Card Dedicata `LepasStatsCard` e Pulizia Card Principale (`lepas-card.js`)**: Registrata nel bundle Lovelace la nuova card `lepas-stats-card` (`LepasStatsCard` + `LepasStatsCardEditor`) che unifica **Ricarica** (selettore `Tutte | Casa | Fuori`, 4 KPI, grafico a barre SVG `7g | 30g | 12m`, pulsante reset con conferma) e **Consumi medi** (EV + Ibrido con cambio unità e reset con conferma); rimossi dalla card principale `LepasCard` la sezione *Consumi medi*, il riquadro ridondante `Presa rapida` (mantenendo il rilevamento AC/DC) e i pulsanti/badge preset nella *Ricarica programmata*; ridisegnato il badge SoC in alto con due cerchi concentrici (anello esterno SoC % fisso + anello interno con effetto pulse in ricarica) e aggiornati gli asset a `?v=1.30.0`.

## v1.29.1 — 2026-11-19

### 🇬🇧 English

- **Clear `car_in_use` Latch When Plugged-In Charging (`coordinator.py`)**: Updated `_evaluate_car_in_use()` to reset `_hv_session_in_use` and align `_hv_session_start_odo` when the vehicle is plugged in (`chargeGunState != 0`) with engine off, zero speed, closed doors, and no ECU comfort rejection, preventing climate controls from staying locked after driving straight into a charging session while `hVoltageState` remains `1`.
- **Enable Live Charging Power (`kW`) on All Models & Clean Live Charging Grid (`sensor.py`, `lepas-card.js`)**: Promoted `sensor.lepas_charging_power` (`chargingPower`, `kW`, `volatile=True`) from BEV-only `_RT_SENSORI_BEV` to `_RT_SENSORS` after confirming live `chargingPower` telemetry on Lepas L8 PHEV while charging, renamed the live-charging power tile label to localized `Power` / `Potenza` / `Vermogen`, removed the cumulative `Home` and `Away` energy tiles from the `Live charging` panel (keeping both HA entities active for the Energy Dashboard and future Statistics card), and bumped card assets to `?v=1.29.1`.

### 🇮🇹 Italiano

- **Sblocco `car_in_use` Durante la Ricarica da Collegata (`coordinator.py`)**: Aggiornato `_evaluate_car_in_use()` per azzerare `_hv_session_in_use` e riallineare `_hv_session_start_odo` quando l'auto è collegata al cavo (`chargeGunState != 0`) con motore spento, velocità zero, porte chiuse e nessun rifiuto ECU nel frame, evitando che i comandi clima restino disabilitati dopo un viaggio seguito da ricarica con `hVoltageState` ancora a `1`.
- **Potenza di Ricarica Istantanea (`kW`) per Tutti i Modelli e Pulizia Ricarica Live (`sensor.py`, `lepas-card.js`)**: Spostato `sensor.lepas_charging_power` (`chargingPower`, `kW`, `volatile=True`) da `_RT_SENSORI_BEV` a `_RT_SENSORS` dopo aver confermato la telemetria live su Lepas L8 PHEV sotto carica, rinominata in `Potenza` (`Power` / `Vermogen`) l'etichetta del riquadro in *Ricarica live*, rimossi i contatori cumulativi `Casa` e `Fuori` dal pannello *Ricarica live* (mantenendo entrambe le entità HA attive per la Dashboard Energia e la futura card Statistiche), con bump degli asset a `?v=1.29.1`.

## v1.29.0 — 2026-11-19

### 🇬🇧 English

- **Long-Term EV & Fuel Consumption Engine (`consumption.py`, `coordinator.py`, `sensor.py`, `button.py`)**: Added persistent rolling (`100 km`, `1000 km`) and cumulative (`From start`) consumption tracking separated by `engineState` (`ev_consumption_*` in `kWh/100 km` when thermal engine is off; `hybrid_consumption_*` in `L/100 km` with `electric_consumption_kwh_100km` attribute when engine is on), automatic suppression of `hybrid_*` sensors on pure BEV vehicles, configurable `battery_capacity_kwh` in options/config flow, and `button.lepas_reset_consumption_from_start` to reset cumulative counters without clearing rolling queues.
- **Overview Consumption Grid, Unit Switches & Auto-Updates Toggle (`lepas-card.js`)**: Added the compact `Average consumption` section (`50 km`, `100 km`, `1000 km`, `From start`) below the Overview KPI grid with independent per-row segmented unit switches (`kWh/100 | kWh/km` on EV; `L/100 | km/L` with zero-division guard on Fuel/Carburante) persisted in `localStorage`, added a 1-tap `switch.lepas_automatic_updates` toggle button in the Overview footer, fixed `.btn-row > .ctrl-btn` flexing and `.badge` width bounds, and bumped card assets to `?v=1.29.0`.

### 🇮🇹 Italiano

- **Motore Consumi a Lunga Durata EV e Carburante (`consumption.py`, `coordinator.py`, `sensor.py`, `button.py`)**: Aggiunto il tracciamento persistente dei consumi su finestre mobili (`100 km`, `1000 km`) e cumulativo (`Da inizio`) separato tramite `engineState` (`ev_consumption_*` in `kWh/100 km` a motore termico spento; `hybrid_consumption_*` in `L/100 km` con attributo `electric_consumption_kwh_100km` a motore acceso), soppressione automatica dei sensori `hybrid_*` sui veicoli BEV puri, `battery_capacity_kwh` configurabile da config/options flow e pulsante `button.lepas_reset_consumption_from_start` per azzerare i totalizzatori cumulativi preservando le code mobili.
- **Griglia Consumi Overview, Selettori Unità e Toggle Aggiornamenti Auto (`lepas-card.js`)**: Aggiunto il blocco compatto `Consumi medi` (`50 km`, `100 km`, `1000 km`, `Da inizio`) in Plancia con selettori segmentati indipendenti per riga (`kWh/100 | kWh/km` su EV; `L/100 | km/L` con guardia zero-divisione su Carburante) salvati in `localStorage`, aggiunto il pulsante 1-tap per `switch.lepas_automatic_updates` nel footer Overview, sistemato il layout `.btn-row > .ctrl-btn` / `.badge`, e aggiornato il cache-busting della card a `?v=1.29.0`.

## v1.28.0 — 2026-11-19

### 🇬🇧 English

- **OEM Top-Down Vehicle SVG Redesign (`lepas-card.js`)**: Replaced the legacy rectangular schematic in the Security/TPMS panel with `renderCarTopViewSvg(t)` (`viewBox="0 0 200 340"`), featuring Lepas L8 SUV proportions (sculpted hood creases, side mirrors, roof rails, full-width rear LED bar, flush-handle doors hinged at front pillars with outward `±22deg` rotation, and centered lock badge), synchronized 5-color paint gradients via `.bp-stage[data-car-color]` (`grey`, `teal`, `violet`, `black`, `white`) with >= 3:1 WCAG contrast overrides on light/dark finishes, 4 corner wheel elements (`[data-bp-wheel]`) tied to TPMS alert states, distinct slide-open (`.is-open`) vs tilt-ventilation (`.is-tilted`) panoramic sunroof states, balanced `.bp-stage` responsiveness for both mobile and 3-column cockpit layouts, and bumped card assets to `?v=1.28.0`.

### 🇮🇹 Italiano

- **Redesign Vista Auto dall'Alto OEM (`lepas-card.js`)**: Sostituito lo schema rettangolare precedente nel pannello Sicurezza/TPMS con `renderCarTopViewSvg(t)` (`viewBox="0 0 200 340"`), dotato di proporzioni reali da SUV Lepas L8 (nervature sul cofano, specchietti laterali, mancorrenti sul tetto, barra LED posteriore continua, portiere sagomate incernierate sul montante anteriore con rotazione esterna `±22deg` e badge lucchetto centrale), verniciatura dinamica sincronizzata sulle 5 tinte via `.bp-stage[data-car-color]` (`grey`, `teal`, `violet`, `black`, `white`) con regole di contrasto WCAG >= 3:1 dedicate su bianco e nero, 4 pneumatici ai passaruota (`[data-bp-wheel]`) collegati agli alert TPMS, distinzione visiva tra tetto panoramico aperto a scorrimento (`.is-open`) e ventilazione/basculamento (`.is-tilted`), griglia `.bp-stage` bilanciata per mobile e cockpit a 3 colonne, con aggiornamento cache-busting della card a `?v=1.28.0`.

## v1.27.0 — 2026-11-19

### 🇬🇧 English

- **Brand Logo & Icon Redesign (`custom_components/lepas/brand/`, `lepas-card.js`)**: Replaced all 8 Home Assistant brand PNG assets (`icon`, `icon@2x`, `dark_icon`, `dark_icon@2x`, `logo`, `logo@2x`, `dark_logo`, `dark_logo@2x`) with the Matte Dark Titanium geometric roaring leopard emblem embedded with smooth alpha transparency from the left corner, paired with the crisp warm-gold (`#FACC15` → `#F59E0B`) italic `Lepas` wordmark (with subtle `#181B20` contrast outline on light-mode variants), removed legacy cyan glow, added pixel-level alpha/gold/cyan verification in `tests/test_brand_assets.py`, and bumped Lovelace card asset cache-busting to `?v=1.27.0`.

### 🇮🇹 Italiano

- **Redesign Brand Logo & Icona (`custom_components/lepas/brand/`, `lepas-card.js`)**: Sostituiti tutti gli 8 asset PNG del brand Home Assistant (`icon`, `icon@2x`, `dark_icon`, `dark_icon@2x`, `logo`, `logo@2x`, `dark_logo`, `dark_logo@2x`) con il nuovo emblema del leopardo geometrico a fauci aperte in finitura Matte Dark Titanium incastonato con dissolvenza alfa morbida dall'angolo sinistro, abbinato al wordmark corsivo `Lepas` giallo-oro (`#FACC15` → `#F59E0B`) con contorno di contrasto `#181B20` sulle varianti chiare, rimosso il bagliore ciano precedente, aggiunte le verifiche sui pixel (trasparenza alfa, oro e assenza ciano) in `tests/test_brand_assets.py` e aggiornato il cache-busting degli asset della card Lovelace a `?v=1.27.0`.

## v1.26.0 — 2026-11-19

### 🇬🇧 English

- **SoC Ring Orbital Charging Animation & AC/DC Mode Slide (`lepas-card.js`)**: Extracted `resolveSocChargingState(vm, helpers)` to distinguish active charging (`"In ricarica"`, `"Charging"`, `"Opladen"`, `"1"`, or live switch/power) from plugged-in waiting or completed states (`"Non in ricarica"`, `"Ricarica completata"`) and classify normal AC vs fast DC charging (`fast_charging_port`, `>= 15 kW` power, or `hvVolt × |hvCurr|`), added a sibling `<svg class="soc-svg-orbit">` rotation ring (`--lp-emerald` at `2.4s` for AC, `--lp-amber` at `1.35s` for DC) and GPU-composited vertical `@keyframes lp-soc-slide` (`% ↔ AC/DC`) with `data-mode`-guarded `bolt`/`fast_charge` SVG updates, added `@media (prefers-reduced-motion: reduce)` static fallback showing percentage and AC/DC icon without motion, updated localized `aria-label` attributes (`it`, `en`, `nl`) and `heroStateBadge` Italian active-charging parity, and bumped cache-busting assets to `?v=1.26.0`.

### 🇮🇹 Italiano

- **Animazione Orbitale Anello SoC & Slide AC/DC (`lepas-card.js`)**: Estratta `resolveSocChargingState(vm, helpers)` per distinguere la ricarica attiva (`"In ricarica"`, `"Charging"`, `"Opladen"`, `"1"`, oppure interruttore/potenza attivi) dallo stato collegato in attesa o completato (`"Non in ricarica"`, `"Ricarica completata"`) e classificare ricarica normale AC vs rapida DC (`fast_charging_port`, potenza `>= 15 kW` o `hvVolt × |hvCurr|`), aggiunto l'arco orbitale `<svg class="soc-svg-orbit">` (`--lp-emerald` a `2.4s` per AC, `--lp-amber` a `1.35s` per DC) e lo slide verticale GPU `@keyframes lp-soc-slide` (`% ↔ AC/DC`) con aggiornamento icone `bolt`/`fast_charge` protetto da `data-mode`, introdotto il fallback statico `@media (prefers-reduced-motion: reduce)` con percentuale e icona AC/DC senza animazioni, aggiornati gli `aria-label` localizzati (`it`, `en`, `nl`) e la parità italiana di `heroStateBadge`, con bump degli asset a `?v=1.26.0`.

## v1.25.0 — 2026-11-19

### 🇬🇧 English

- **Immediate Optimism Cancellation on ECU `reason` & Car-in-Use Detection (`coordinator.py`, `entity.py`, `switch.py`, `climate.py`, `binary_sensor.py`)**: Mapped ECU `reason` `modelId` rejections via `REASON_FIELD_MAP` and `_extract_rejected_fields()` in `LepasCoordinator` while preserving `_solo_clima` (`0:95`) tolerance, cleared stuck optimistic switches/climate states immediately via `LepasOptimisticMixin._rifiuto_arrivato()` (including mutually exclusive `LepasComfortSwitch` twins and `LepasClimate`), introduced an HV session latch (`_hv_lock`, `_evaluate_car_in_use()`, `is_car_in_use()`) that separates parked pre-climate/charging from driving/engine-on/red-light stops and exposes `car_in_use` on `binary_sensor.lepas_high_voltage_active` and `climate.lepas_climate` without adding entities, and serialized `_hv_followup_cb` / `_schedule_probe_on_loop` against `_poll_busy`.
- **Climate Tab `car_in_use` Lockout, Command Outcome Sync & Departure UX Option 1 (`lepas-card.js`)**: Added the `carInUseBanner` (`role="status"`), non-sticky disabling with translucent `⊘` / `Car in use` overlay and disabled-click guard on Climate tab comfort controls when `car_in_use === true`, synced `[data-bind="cmdResultBadge"]` across both Overview and Climate tabs (`climateCmdBar`), implemented Departure UX Option 1 (`Next departure` + `On car` with `Synced` / `To apply (car: ...)` / `Disabled` states) while removing the `nextDepText` override, and bumped assets to `?v=1.25.0`.

### 🇮🇹 Italiano

- **Annullamento Immediato Ottimismo su `reason` & Rilevamento "Auto in uso" (`coordinator.py`, `entity.py`, `switch.py`, `climate.py`, `binary_sensor.py`)**: Mappati i `modelId` di rifiuto centralina tramite `REASON_FIELD_MAP` e `_extract_rejected_fields()` in `LepasCoordinator` preservando la tolleranza `_solo_clima` (`0:95`), azzerato subito lo stato ottimistico bloccato via `LepasOptimisticMixin._rifiuto_arrivato()` (inclusa la mutua esclusione su `LepasComfortSwitch` e `LepasClimate`), introdotto il latch di sessione HV (`_hv_lock`, `_evaluate_car_in_use()`, `is_car_in_use()`) che distingue pre-clima/ricarica da marcia/motore/semaforo esponendo l'attributo `car_in_use` su `binary_sensor.lepas_high_voltage_active` e `climate.lepas_climate` senza nuove entità, e protetto `_hv_followup_cb` / `_schedule_probe_on_loop` con `_poll_busy`.
- **Blocco Controlli Tab Clima su `car_in_use`, Badge Esito Comandi & UX Partenze Opzione 1 (`lepas-card.js`)**: Aggiunto il banner `carInUseBanner` (`role="status"`), la disabilitazione non sticky con velo traslucido `⊘` / `Auto in uso` e guardia click su tutti i comandi comfort della tab Clima con `car_in_use === true`, sincronizzato `[data-bind="cmdResultBadge"]` tra Plancia e tab Clima (`climateCmdBar`), applicata l'Opzione 1 UX Partenze (`Prossima partenza` + `Su auto` con stati `Sincronizzata` / `Da applicare (auto: ...)` / `Disattivata`) rimuovendo l'override su `nextDepText`, con bump degli asset a `?v=1.25.0`.

## v1.24.0 — 2026-11-19

### 🇬🇧 English

- **Full-Plan Departure Dirty Tracking, Auto-Advance & `lepas.disable_departure_schedule` (`coordinator.py`, `sensor.py`, `switch.py`, `time.py`, `__init__.py`, `services.yaml`)**: Serialized departure mutations under `self._departure_lock` (`asyncio.Lock`), added canonical full-plan signature tracking (`departure_schedule_signature()` / `_applied_schedule_sig`) exposed and restored across restarts on `sensor.lepas_scheduled_departure` (`has_pending_changes`, `applied_schedule_sig`), kept weekly/quick UI edits local (`sync_native=False`) until applied, automatically enabled `native_departure_sync` on explicit **Apply to car** for cross-day auto-advance without leaking unapplied weekly drafts, and added the fail-closed `lepas.disable_departure_schedule` service to turn off the vehicle schedule, HA weekly/quick switches, and `native_departure_sync`.
- **Lovelace Card 3-State Departure Button & Accessibility (`lepas-card.js`)**: Replaced the ambiguous scheduled-departure label with `departureStatus` (`"Status"` / `"Stato"`), registered `disable_departure_schedule` in `CONFIRM_ACTIONS` and card actions, implemented the null-safe ES5 3-state button machine (**Apply to car** / **Disable schedule** / hidden via both `.hidden` and `hidden`) driven by `has_pending_changes` and `synced_with_ha`, and bumped cache-busting assets to `?v=1.24.0`.

### 🇮🇹 Italiano

- **Tracciamento Modifiche sull'Intero Piano Partenza, Avanzamento Automatico & `lepas.disable_departure_schedule` (`coordinator.py`, `sensor.py`, `switch.py`, `time.py`, `__init__.py`, `services.yaml`)**: Serializzate le mutazioni partenza sotto `self._departure_lock` (`asyncio.Lock`), introdotta la firma canonica dell'intero piano (`departure_schedule_signature()` / `_applied_schedule_sig`) esposta e ripristinata al riavvio su `sensor.lepas_scheduled_departure` (`has_pending_changes`, `applied_schedule_sig`), mantenute locali le modifiche UI su giorni/orari/rapida (`sync_native=False`) finché non vengono applicate, attivato automaticamente `native_departure_sync` alla pressione di **Applica su auto** per il passaggio automatico tra giorni senza inviare bozze settimanali non applicate, e aggiunto il servizio fail-closed `lepas.disable_departure_schedule` per spegnere auto, giorni/rapida HA e auto-sync.
- **Pulsante Partenza a 3 Stati & Accessibilità nella Card Lovelace (`lepas-card.js`)**: Sostituita la dicitura nella prima riga di *Partenze programmate* con `departureStatus` (`"Stato"` / `"Status"`), registrata l'azione confermata `disable_departure_schedule` in `CONFIRM_ACTIONS`, implementata la macchina a 3 stati ES5 null-safe (**Applica su auto** / **Disattiva piano** / nascosto con `.hidden` e attributo `hidden`) guidata da `has_pending_changes` e `synced_with_ha`, con bump degli asset a `?v=1.24.0`.

## v1.23.0 — 2026-11-19

### 🇬🇧 English

- **Guarded `A07900` Wake-and-Retry via Reactive MQTT Sync (`const.py`, `coordinator.py`)**: Added protected single wake-and-retry in `LepasCoordinator.async_send_command()` when `tspconsole-eu` rejects a command with `CommandError(code="A07900")` (*vehicle asleep*). Releases `_cmd_gate` in the attempt-1 `finally` block before calling `async_assicura_sveglia()` (`localizza`, preventing any deadlock), waits up to `POLL_WAKE_WAIT` (25 s) on `_wait_for_car_wake()` using a race-free double-check around `asyncio.Event` signalled via `call_soon_threadsafe` from `_on_car_message` (and unblocked on `async_stop`), and retries once with `_allow_wake_retry=False` (reusing cached `taskId` without consuming PIN attempts). Enforces `A07900_WAKE_COOLDOWN_S = 60`, skips when `auto_sveglia` is already `True`, `key == "localizza"`, or `closing`, and restores the original `A07900` `cmd_status` / notes before `_instrada_rimedio()` and re-raising on wake timeout.
- **Native Departure `appointmentTravelAOS` Write Schema & Post-Settle Sync (`commands.py`, `coordinator.py`)**: Updated `/asc/vehicleControl/appointmentTravel` write payloads (`partenza_prog_on` / `partenza_prog_off` and `LepasCoordinator._build_native_departure_payload()`) to send `"appointmentTravelAOS"` with `"travelWeekday"` as `list[str]` (keeping `"appointmentTravelSetVOS"` for read queries), added `_post_settle_travel_refresh()` after `async_apply_departure_schedule()`, and preserved `mainSwitcher` / `appointmentTravelSetVOS` in `_on_probe_data()` when omitted by `probe_once()`, bumping `?v=1.23.0`.

### 🇮🇹 Italiano

- **Retry Automatico Protetto con Sveglia MQTT su `A07900` (`const.py`, `coordinator.py`)**: Aggiunto in `LepasCoordinator.async_send_command()` un retry singolo protetto su `CommandError(code="A07900")` (*auto a riposo*). Lo slot `_cmd_gate` viene rilasciato nel `finally` del tentativo 1 prima di chiamare `async_assicura_sveglia()` (`localizza`, zero deadlock); `_wait_for_car_wake()` attende fino a `POLL_WAKE_WAIT` (25 s) il risveglio MQTT tramite `asyncio.Event` segnalato da `_on_car_message` con `call_soon_threadsafe` (e sbloccato in `async_stop()`) con double-check anti-race sotto `_state_lock`, rieseguendo il comando una sola volta con `_allow_wake_retry=False` (riuso del `taskId` in cache senza consumo PIN). Protetto da `A07900_WAKE_COOLDOWN_S = 60`, escluso se `auto_sveglia` è attiva, `key == "localizza"` o in chiusura, con ripristino di `cmd_status` / note originali e chiamata a `_instrada_rimedio()` su timeout.
- **Schema Scrittura Partenza Programmata `appointmentTravelAOS` & Sync Post-Settle (`commands.py`, `coordinator.py`)**: Aggiornati i payload di scrittura verso `/asc/vehicleControl/appointmentTravel` (`partenza_prog_on` / `partenza_prog_off` e `LepasCoordinator._build_native_departure_payload()`) a `"appointmentTravelAOS"` con `"travelWeekday"` come `list[str]` (mantenendo `"appointmentTravelSetVOS"` in lettura), aggiunto `_post_settle_travel_refresh()` dopo `async_apply_departure_schedule()` e preservati `mainSwitcher` / `appointmentTravelSetVOS` in `_on_probe_data()` quando omessi da `probe_once()`, con bump `?v=1.23.0`.

## v1.22.3 — 2026-11-18

### 🇬🇧 English

- **Scheduled Departure OFF (`appointmentTravel`) & Instant `mainSwitcher=0` Sensor Refresh (`commands.py`, `permessi.py`, `coordinator.py`, `sensor.py`)**: Fixed `partenza_prog_off` sending `travelWeekday: ""` (which `tspconsole-eu` rejected with `A07900` even while the car was awake) by preserving the existing `travelTime` and using non-empty `effective_departure_days([1])` (and `"1,2,3,4,5"` in `CMD_MAP` while skipping cycle warnings when `mainSwitcher == "0"`). Fixed `LepasDeparturePlan` to report `Disattivata` (`attiva: false`) when `/asd/travelManage/travelQuery` returns `mainSwitcher: 0` without `appointmentTravelSetVOS`, and refreshed `realtime` from `travelQuery` right after `async_apply_departure_schedule()`, bumping `?v=1.22.3`.

### 🇮🇹 Italiano

- **Disattivazione Partenza Programmata (`appointmentTravel`) & Aggiornamento Immediato `mainSwitcher=0` (`commands.py`, `permessi.py`, `coordinator.py`, `sensor.py`)**: Risolto il rifiuto `A07900` di `partenza_prog_off` dovuto a `travelWeekday: ""` (rifiutato dal backend anche ad auto sveglia) preservando l'eventuale `travelTime` esistente e inviando `effective_departure_days([1])` non vuoto (con `"1,2,3,4,5"` nel catalogo e senza falsi avvisi ciclo su `mainSwitcher == "0"`). Aggiornato inoltre `LepasDeparturePlan` per mostrare `Disattivata` (`attiva: false`) anche quando `/asd/travelManage/travelQuery` risponde `{mainSwitcher: 0}` senza `appointmentTravelSetVOS`, e riallineato subito `realtime` dopo `async_apply_departure_schedule()`, con bump `?v=1.22.3`.

## v1.22.2 — 2026-11-18

### 🇬🇧 English

- **Native Departure & Battery Preheat TSP Endpoints Fix (`commands.py`, `permessi.py`)**: Replaced the unverified Flutter method-channel names (`travelAppointControl`, `travelAppointQuery`, `/asc/vehicleControl/queryBatteryPackHeat`, which returned `HTTP 404 Not Found` on `tspconsole-eu`) with the real live-verified TSP endpoints: `/asc/vehicleControl/appointmentTravel` for scheduled departure control (`partenza_prog_on` / `partenza_prog_off` and permission tables `CATEGORIA`/`CICLO` cat. `212`/`2121`/`2122`), `/asd/travelManage/travelQuery` for `query_travel_appoint`, and `/asd/travelManage/queryBatteryPackHeat` for `query_battery_pack_heat`. Also hardened `commands.send()` to raise `CommandError` on any `HTTP >= 400` response even when no Chery JSON `code` is present (preventing Spring Boot `404` responses from reporting silent success), bumping `?v=1.22.2`.

### 🇮🇹 Italiano

- **Fix Endpoint Reali Partenza Programmata & Preriscaldamento Batteria (`commands.py`, `permessi.py`)**: Sostituiti i nomi interni del bridge Flutter (`travelAppointControl`, `travelAppointQuery`, `/asc/vehicleControl/queryBatteryPackHeat`, che rispondevano `HTTP 404 Not Found` su `tspconsole-eu`) con gli endpoint reali verificati dal vivo: `/asc/vehicleControl/appointmentTravel` per il controllo partenza programmata (`partenza_prog_on` / `partenza_prog_off` e tabelle permessi `CATEGORIA`/`CICLO` cat. `212`/`2121`/`2122`), `/asd/travelManage/travelQuery` per `query_travel_appoint` e `/asd/travelManage/queryBatteryPackHeat` per `query_battery_pack_heat`. Inoltre `commands.send()` solleva sempre `CommandError` su qualsiasi risposta `HTTP >= 400` anche in assenza del campo JSON `code` (evitando falsi successi su risposte `404` Spring Boot), con bump `?v=1.22.2`.

## v1.22.1 — 2026-11-18

### 🇬🇧 English

- **Scroll Preservation & Incremental Day Editor (`custom:lepas-card`)**: Added `ev.stopPropagation()` on internal controls (`tab`, `day-chip`, `charge-day`, `charge-preset`, `charge-mode`, `climate-extra`), removed `_expandedDay` from `structKey` so toggling weekday chips updates `.day-editor` incrementally without rebuilding `shadowRoot.innerHTML`, preserved `scrollTop` of the nearest scrollable ancestor across Shadow DOM boundaries (`getRootNode().host`) around `_render` and `_applyBindings` (with `focus({ preventScroll: true })`), and added `overflow-anchor: none` on `:host` and `ha-card`, bumping `?v=1.22.1`.

### 🇮🇹 Italiano

- **Preservazione Scroll & Editor Giorni Incrementale (`custom:lepas-card`)**: Aggiunto `ev.stopPropagation()` sui controlli interni (`tab`, `day-chip`, `charge-day`, `charge-preset`, `charge-mode`, `climate-extra`), rimosso `_expandedDay` da `structKey` per gestire i pannelli `.day-editor` incrementalmente senza ricostruire `shadowRoot.innerHTML` al click sui chip `L–D`, preservato `scrollTop` del primo antenato scrollabile anche attraverso Shadow DOM (`getRootNode().host`) attorno a `_render` e `_applyBindings` (con `focus({ preventScroll: true })`), e aggiunto `overflow-anchor: none` su `:host` e `ha-card`, con bump `?v=1.22.1`.

## v1.22.0 — 2026-11-18

### 🇬🇧 English

- **Native `<dialog>` Confirmation Modal for Commands & Sensitive Actions (`custom:lepas-card`)**: Replaced the 4-second inline button double-tap confirmation with an explicit native Shadow DOM `<dialog>` modal (`Confermare comando?` / `Confirm command?` / `Opdracht bevestigen?`) across all 10 stateless one-shot commands (`wake_car`, `refresh_location`, `refresh_full`, `locate_gps`, `flash_lights`, `vent_windows`, `vent_sunroof`, `remote_start`, `apply_charging_schedule`, `apply_departure_schedule`) and all 5 sensitive stateful actions (`unlock`, `trunk_open`, `windows_open`, `sunroof_open`, `alarm_toggle`), keeping non-destructive stateful switches 1-tap immediate and maintaining older WebView compatibility (`showModal` fallback + drag-safe backdrop dismiss).
- **Concise Command Outcome Badge (`custom:lepas-card`)**: Replaced raw `sensor.lepas_command_result` debug strings in the Overview footer with a clean two-state localized badge (`Last command · HH:MM ✓` / `Command failed · HH:MM ✕` across IT/EN/NL) via `formatCommandOutcome`, including immediate local feedback on command resolution/failure before backend state updates.
- **Concise Next Car Departure & Active Status Consistency (`custom:lepas-card`)**: Replaced the full 7-day weekday list on *Next scheduled departure* with the exact next car occurrence (`Today 06:35`, `Tomorrow 06:35`, `Fri 06:35`, across IT/EN/NL) via `formatCarNextDeparture`, and updated *Next departure* to show `Active` (`Attiva` / `Active` / `Actief`) rather than `Disabled` when HA has no active schedule yet while the car/app schedule is active, bumping `?v=1.22.0`.

### 🇮🇹 Italiano

- **Modale `<dialog>` Nativo di Conferma per Comandi & Azioni Sensibili (`custom:lepas-card`)**: Sostituita la vecchia doppia pressione inline da 4 secondi con un modale nativo `<dialog>` nello Shadow DOM (`Confermare comando?` / `Annulla` / `Invia`) per tutti i 10 comandi one-shot stateless (`wake_car`, `refresh_location`, `refresh_full`, `locate_gps`, `flash_lights`, `vent_windows`, `vent_sunroof`, `remote_start`, `apply_charging_schedule`, `apply_departure_schedule`) e le 5 azioni sensibili stateful (`unlock`, `trunk_open`, `windows_open`, `sunroof_open`, `alarm_toggle`), lasciando immediati a 1 tap gli switch stateful non distruttivi e garantendo piena compatibilità con WebView datate (fallback `showModal` + light-dismiss anti-drag).
- **Badge Sintetico Esito Comando (`custom:lepas-card`)**: Sostituiti i testi di debug grezzi di `sensor.lepas_command_result` nel footer della Plancia con un badge compatto a due stati localizzato (`Ultimo comando · HH:MM ✓` / `Errore invio comando · HH:MM ✕` in IT/EN/NL) tramite `formatCommandOutcome`, con feedback locale immediato alla risoluzione o al rifiuto di `callService` prima dell'aggiornamento dal backend.
- **Prossima Partenza Pianificata Concisa & Stato Coerente (`custom:lepas-card`)**: Sostituita la lista completa dei giorni su *Prossima partenza pianificata* con la prossima occorrenza effettiva sull'auto (es. `Oggi 06:35`, `Domani 06:35`, `Ven 06:35`, in IT/EN/NL) tramite `formatCarNextDeparture`, e aggiornata *Prossima partenza* per mostrare `Attiva` (`Attiva` / `Active` / `Actief`) invece di `Disattivata` quando su HA non è ancora pianificata alcuna partenza ma il piano in auto/app è attivo (senza mostrare dettagli di pianificazione HA), con bump `?v=1.22.0`.

## v1.21.2 — 2026-11-18

### 🇬🇧 English

- **Clearer Scheduled Departure Controls (`custom:lepas-card`, `LepasDeparturePlan`)**: Renamed *Car schedule* to *Next scheduled departure* across IT/EN/NL (`Prossima partenza pianificata` / `Next scheduled departure` / `Volgend gepland vertrek`), showing the active car departure or *No scheduled departure* (*Nessuna partenza programmata* / *Geen gepland vertrek*), aligned `LepasDeparturePlan` with `mainSwitcher == "0"`, removed the redundant *Sync to car* toggle and *Pending sync* badge from the card UI (keeping `switch.lepas_native_departure_sync` in Home Assistant), and replaced the button with an adaptive *Apply to car* / *Disable on car* control that hides automatically when both HA and the car have no active departure, bumping `?v=1.21.2`.

### 🇮🇹 Italiano

- **Controlli Partenza Programmata Più Chiari (`custom:lepas-card`, `LepasDeparturePlan`)**: Rinominato *Piano su auto* in *Prossima partenza pianificata* (IT/EN/NL), mostrando l'orario attivo o *Nessuna partenza programmata*, allineato `LepasDeparturePlan` a `mainSwitcher == "0"`, rimossi dalla card il toggle *Sync su auto* e il badge *Da sincronizzare* (mantenendo `switch.lepas_native_departure_sync` in Home Assistant), e reso adattivo il pulsante *Applica su auto* / *Disattiva su auto* (nascosto quando sia HA sia l'auto non hanno partenze attive), con bump `?v=1.21.2`.

## v1.21.1 — 2026-11-18

### 🇬🇧 English

- **Compact Scheduled Departure Panel & Clear Seat Labels (`custom:lepas-card`)**: Unified the *Scheduled departures* header with the `synced_with_ha` badge, grouped *Next departure* and *Car schedule* into a single compact `.dep-summary` box, moved the sync controls cleanly beneath the weekday chips, arranged *Departure climate extras* into a canonically ordered 2-column `.climate-extras-grid`, and clarified seat heating/ventilation chip labels across IT/EN/NL (`Sedile guida caldo`, `Driver seat heat`, `Stoel best. verw.`, etc.), bumping `?v=1.21.1`.

### 🇮🇹 Italiano

- **Pannello Partenze Programmate Compatto & Etichette Esplicite Sedili (`custom:lepas-card`)**: Unificata l'intestazione *Partenze programmate* con il badge di sincronia `synced_with_ha`, raccolti *Prossima partenza* e *Piano su auto* in un unico riquadro compatto `.dep-summary`, integrati i pulsanti *Sync su auto* e *Applica partenza* sotto i giorni `L–D`, ordinati gli *Extra clima alla partenza* in una griglia simmetrica a 2 colonne `.climate-extras-grid` con etichette esplicite per i sedili in IT/EN/NL (`Sedile guida caldo/aria`, `Sedile pass. caldo/aria`, ecc.) e query anti-cache `?v=1.21.1`.

## v1.21.0 — 2026-11-18

### 🇬🇧 English

- **Native Scheduled Departure Sync (`travelAppointControl`, Cat. `212`)**: Added bidirectional UTC↔local schedule translation (`local_schedule_to_utc` / `utc_schedule_to_local`), server `id` preservation, `DATA_CAPS_PROBED_V5` capability backfill, `switch.lepas_native_departure_sync`, `button.lepas_apply_departure_schedule`, `synced_with_ha` on `sensor.lepas_scheduled_departure`, and optional `apply_native` on `lepas.set_quick_departure`, including clean quick-departure hold and post-expiry resync across all climate modes.
- **Plug-in Battery Preheating (`batteryPackHeat`, Cat. `216`)**: Added `switch.lepas_battery_pack_heat` (optimistic + `RestoreEntity`), `time.lepas_battery_pack_heat_time`, `switch.lepas_sync_battery_heat_to_departure` (`T_dep - 30 min`), `lepas.set_battery_pack_heat`, and permission-gated hiding (`216=0`).
- **Dynamic Departure Climate Extras & Lovelace Card v2 Controls**: Added 12 VIN-filtered cabin/seat/defrost climate extras persisted on `sensor.lepas_next_departure` (`climate_extras` / `allowed_climate_extras`) and configurable via `lepas.set_departure_climate_extras`, plus XSS-safe interactive chips, native departure controls, and conditional battery preheat UI in `custom:lepas-card` (`?v=1.21.0`, full IT/EN/NL localization).

### 🇮🇹 Italiano

- **Sincronizzazione Partenza Programmata Nativa (`travelAppointControl`, Cat. `212`)**: Aggiunta la conversione bidirezionale UTC↔locale (`local_schedule_to_utc` / `utc_schedule_to_local`), preservazione dell'`id` server, backfill capacità `DATA_CAPS_PROBED_V5`, `switch.lepas_native_departure_sync`, `button.lepas_apply_departure_schedule`, attributo `synced_with_ha` su `sensor.lepas_scheduled_departure` e opzione `apply_native` su `lepas.set_quick_departure`, con gestione pulita della scadenza partenza veloce e riallineamento automatico in tutte le modalità clima.
- **Preriscaldamento Batteria Plug-in (`batteryPackHeat`, Cat. `216`)**: Aggiunti `switch.lepas_battery_pack_heat` (ottimistico + `RestoreEntity`), `time.lepas_battery_pack_heat_time`, `switch.lepas_sync_battery_heat_to_departure` (`T_dep - 30 min`), il servizio `lepas.set_battery_pack_heat` e occultamento automatico se il permesso `216` è `0`.
- **Extra Clima Dinamici alla Partenza & Controlli Lovelace Card v2**: Aggiunti 12 extra clima abitacolo/sedili/sbrinamento filtrati sulle feature del VIN e persistiti su `sensor.lepas_next_departure` (`climate_extras` / `allowed_climate_extras`), configurabili via `lepas.set_departure_climate_extras`, insieme a chip interattivi protetti da allowlist/XSS, controlli di partenza nativa e riquadro condizionale batteria in `custom:lepas-card` (`?v=1.21.0`, traduzioni complete IT/EN/NL).

## v1.20.3 — 2026-11-18

### 🇬🇧 English

- **Sync `climate.lepas_climate` Target Temperature from Vehicle Telemetry (`frontSetTempLeft`)**: `LepasClimate` now synchronizes its `target_temperature` (and `coordinator.climate_target_temp`) whenever the vehicle reports a changed setpoint via `frontSetTempLeft`/`frontSetTempRight` in `realtime` telemetry (validated within `[min_temp, max_temp]`), eliminating the mismatch between the card temperature stepper (`21 °C`) and the live left/right cabin setpoints (`23 °C`). Unchanged background polls never clobber a manual Home Assistant override or active optimistic command. Bumped card cache-busting query to `?v=1.20.3`.

### 🇮🇹 Italiano

- **Sincronizzazione Temperatura Target Clima dall'Auto (`frontSetTempLeft`)**: `LepasClimate` allinea ora `target_temperature` (e `coordinator.climate_target_temp`) ogni volta che il veicolo riporta un nuovo setpoint valido (`frontSetTempLeft`/`frontSetTempRight`, dentro `[min_temp, max_temp]`) nel canale `realtime`, eliminando lo scostamento nella card tra il selettore `21 °C` e la temperatura reale impostata in abitacolo (`SX/DX: 23 °C`). I poll successivi con dato invariato non sovrascrivono eventuali modifiche manuali appena impostate da Home Assistant o comandi ottimistici in corso. Aggiornata la query anti-cache della card a `?v=1.20.3`.

## v1.20.2 — 2026-11-17

### 🇬🇧 English

- **Fix `binary_sensor.lepas_at_home` Boot Availability Race (`set_poll_enabled`)**: `LepasCoordinator.set_poll_enabled()` now notifies coordinator listeners (`async_update_listeners()`) when polling state is restored or toggled, eliminating an intermittent race on Home Assistant startup where `binary_sensor.lepas_at_home` could remain `unavailable` if `device_tracker` restored position before `switch.lepas_automatic_updates` restored `on`. Bumped card cache-busting query to `?v=1.20.2`.

### 🇮🇹 Italiano

- **Fix Race Condition Disponibilità `binary_sensor.lepas_at_home` all'Avvio (`set_poll_enabled`)**: `LepasCoordinator.set_poll_enabled()` notifica ora i listener del coordinator (`async_update_listeners()`) al ripristino o al cambio dello switch *Aggiornamento automatico*, eliminando la race intermittente in avvio Home Assistant in cui `binary_sensor.lepas_at_home` poteva restare `unavailable` se `device_tracker` ripristinava la posizione prima di `switch.lepas_automatic_updates`. Aggiornata la query anti-cache della card a `?v=1.20.2`.

## v1.20.1 — 2026-11-17

### 🇬🇧 English

- **Fix Scheduled Departure UTC→Local Time Conversion (`sensor.lepas_scheduled_departure`)**: Converted `appointmentTravelSetVOS.travelTime` (which arrives in UTC minutes since midnight rather than local minutes) into Home Assistant's configured local time zone (handling CET/CEST and midnight weekday rollover automatically).
- **Selection-Only Time Pickers (`custom:lepas-card`)**: Disabled manual keyboard typing and mobile soft keyboards (`inputmode="none"`, blocked `keydown`/`beforeinput`/`paste`) on all `input[type="time"]` selectors while opening the scrollable `HH | MM` picker directly via `showPicker()` on tap/click, with `?v=1.20.1` cache-busting.

### 🇮🇹 Italiano

- **Fix Conversione Orario Partenza Programmata UTC→Locale (`sensor.lepas_scheduled_departure`)**: Convertito `appointmentTravelSetVOS.travelTime` (che arriva dal cloud in minuti dalla mezzanotte UTC anziché in ora locale) nel fuso orario configurato su Home Assistant, gestendo automaticamente ora solare/legale (CET/CEST) e l'eventuale salto di giorno attorno alla mezzanotte.
- **Selettori Orario Solo a Scelta (`custom:lepas-card`)**: Bloccata la digitazione manuale e la tastiera mobile (`inputmode="none"`, blocco `keydown`/`beforeinput`/`paste`) su tutti i campi `input[type="time"]` della card aprendo direttamente il selettore a scorrimento `HH | MM` (`showPicker()`) al tap/click, con query anti-cache `?v=1.20.1`.

## v1.20.0 — 2026-11-17

### 🇬🇧 English

- **Uncropped `2:1` Lepas L8 Hero Stage & Separated Meta Bar**: Updated the `custom:lepas-card` hero stage to a full `2:1` aspect ratio with `object-fit: contain` so the Lepas L8 studio render is never cropped, moving the vehicle identity, live connection/location status, SoC ring, and lock summary into a dedicated meta bar directly beneath the vehicle stage, with asset cache-busting bumped to `?v=1.20.0`.
- **Inline SVG Icons, WCAG 1.4.1 Tab Bar & Integer Metric Formatting**: Replaced generic icons with a crisp inline SVG icon system and restrained OEM micro-animations across all four tabs (`Overview`, `Climate`, `Charging`, `Security`), styled the active tab with a WCAG 1.4.1-compliant indicator underline without blinding white fills, and formatted integer distance and duration readouts cleanly (e.g., `551 km` instead of `551,00 km`).
- **Live Charging Telemetry, Interactive `Mon–Sun` Chips & Mode Selector**: Added a live Charging telemetry grid with a direct Start/Stop charging toggle and an animated energy flow bar, and redesigned Scheduled Charging with interactive `Mon–Sun` (`L–D`) weekday chips plus quick presets wired to `lepas.set_charging_schedule` (`apply: false`) alongside a prominent *Manual time* vs *Follow departure* (`switch.lepas_sync_charge_to_departure`) mode selector.
- **Localized `departure_climate_mode` / TPMS Labels, Animated SUV Blueprint & Grouped Closures**: Translated `departure_climate_mode` selector options across EN/IT/NL (`Home only` / `Anywhere` / `Off`, `Solo a casa` / `Ovunque` / `Disattivato`, `Alleen thuis` / `Overal` / `Uitgeschakeld`), added localized TPMS corner labels (`ANT SX` / `ANT DX` / `POST SX` / `POST DX` in IT, `FL` / `FR` / `RL` / `RR` in EN), refined the animated top-down SUV SVG blueprint, and organized Security & Closures controls into clean functional groups.

### 🇮🇹 Italiano

- **Hero Stage `2:1` Senza Ritagli & Barra Meta Separata**: Aggiornato il riquadro hero di `custom:lepas-card` al formato pieno `2:1` con `object-fit: contain` per mostrare il render studio della Lepas L8 senza alcun ritaglio, spostando identità del veicolo, stato connessione/posizione, anello SoC e riepilogo serrature in una barra meta dedicata sotto l'immagine, con query anti-cache degli asset aggiornata a `?v=1.20.0`.
- **Icone SVG Inline, Tab WCAG 1.4.1 & Formattazione Intera dei Metrici**: Introdotto un sistema nitido di icone SVG inline con micro-animazioni OEM sobrie in tutte e 4 le schede (`Plancia`, `Clima`, `Ricarica`, `Sicurezza`), sottolineatura attiva conforme a WCAG 1.4.1 priva di riempimenti bianchi abbaglianti e formattazione pulita dei valori interi di distanza e durata (es. `551 km` invece di `551,00 km`).
- **Telemetria Ricarica Live, Chip `L–D` Interattivi & Selettore Modalità**: Aggiunta la griglia di telemetria Ricarica live con toggle diretto Avvia/Ferma e barra animata del flusso energetico, e riprogettata la Ricarica Programmata con chip interattivi dei giorni `L–D` (`Mon–Sun`) + preset rapidi collegati a `lepas.set_charging_schedule` (`apply: false`) insieme a un selettore chiaro tra *Orario manuale* e *Segui partenza* (`switch.lepas_sync_charge_to_departure`).
- **Etichette `departure_climate_mode` / TPMS Tradotte, Blueprint SUV Animato & Controlli Raggruppati**: Tradotte le opzioni di `departure_climate_mode` in IT/EN/NL (`Solo a casa` / `Ovunque` / `Disattivato`, `Home only` / `Anywhere` / `Off`, `Alleen thuis` / `Overal` / `Uitgeschakeld`), localizzate le etichette ruote TPMS (`ANT SX` / `ANT DX` / `POST SX` / `POST DX` in IT, `FL` / `FR` / `RL` / `RR` in EN), perfezionato il blueprint SVG animato del SUV e raggruppati in modo ordinato i comandi di Sicurezza e Aperture.

## v1.19.1 — 2026-11-17

### 🇬🇧 English

- **Fix Lovelace Card Picker Visibility & Frontend Load Order**: Registered `type: "lepas-card"` (without the `custom:` prefix) in `window.customCards` inside `lepas-card.js` so Home Assistant's **Add Card** picker discovers and inserts `custom:lepas-card` reliably, added `"frontend"` to `after_dependencies` in `manifest.json` to ensure `add_extra_js_url` runs after Frontend initialization, and bumped asset cache-busting queries to `?v=1.19.1`.

### 🇮🇹 Italiano

- **Fix Visibilità nel Selettore Schede & Ordine di Caricamento Frontend**: Registrato `type: "lepas-card"` (senza prefisso `custom:`) in `window.customCards` dentro `lepas-card.js` affinché il selettore **"Aggiungi scheda"** di Home Assistant rilevi e inserisca correttamente `custom:lepas-card`, aggiunto `"frontend"` in `after_dependencies` di `manifest.json` per garantire l'inizializzazione del Frontend prima di `add_extra_js_url`, e aggiornata la query anti-cache degli asset a `?v=1.19.1`.

## v1.19.0 — 2026-11-17

### 🇬🇧 English

- **Redesigned `custom:lepas-card` (*Matte Titanium OEM*) & Visual Editor**: Rebuilt `lepas-card.js` in a zero-neon *Matte Titanium OEM* style (`#111317` / `#181B20` / `#21252C` surfaces, `tabular-nums` telemetry, `#34D399` / `#60A5FA` / `#F59E0B` / `#EF4444` semantic accents) as a single responsive Web Component via CSS `@container` (`container-type: inline-size`), switching between a 4-tab compact view (`< 680px`) and a multi-column Cockpit (`>= 680px`, 3 columns at `>= 960px`) with `layout: auto|compact|cockpit` and `default_tab` options. Added native Home Assistant visual editor (`LepasCardEditor` / `<lepas-card-editor>`) and Sections grid support (`getGridOptions`).
- **5 Faithful Lepas L8 Studio Vehicle Renders**: Added 5 consistent Lepas L8 studio renders (`grey` default, plus `teal`, `violet`, `black`, and `white`) served via `/lepas_card/lepas-hero-{color}.png?v=1.19.0` (with `lepas-hero.png` updated to the grey render for compatibility), selectable via `color:` or visual editor swatches while preserving `image:` overrides and `vehicle_image` entity attributes.
- **Full `v1.18.0` Telemetry, SVG Blueprint & Safe Controls**: Integrated `v1.18.0` weekly/quick departure schedules and the 24h scheduled charging timeline (`scheduled_charging_window`, `charge_days`, `next_departure`), climate hub (`number.lepas_climate_duration`, `cool_everything` / `heat_everything` macros, 4 defrost/steering heaters, 4+1 seat heating/ventilation matrix), animated top-down SUV SVG blueprint with 4-corner TPMS, 4-second inline confirmation on sensitive physical actions, EN/IT/NL translations, and Android System WebView ES compatibility.

### 🇮🇹 Italiano

- **Nuova `custom:lepas-card` (*Matte Titanium OEM*) & Editor Visuale**: Riprogettata `lepas-card.js` in stile *Matte Titanium OEM* (zero neon, superfici `#111317` / `#181B20` / `#21252C`, numeri `tabular-nums` e accenti semantici `#34D399` / `#60A5FA` / `#F59E0B` / `#EF4444`) come singolo Web Component reattivo tramite CSS `@container` (`container-type: inline-size`), con vista compatta a 4 tab (`< 680px`) e Cockpit multi-colonna (`>= 680px`, 3 colonne da `>= 960px`) configurabile con `layout: auto|compact|cockpit` e `default_tab`. Aggiunti l'editor visuale nativo Home Assistant (`LepasCardEditor` / `<lepas-card-editor>`) e il supporto alle dashboard a Sezioni (`getGridOptions`).
- **5 Render Studio Fedeli della Lepas L8**: Aggiunti 5 render studio coerenti della Lepas L8 (`grey` predefinito, più `teal`, `violet`, `black` e `white`) serviti da `/lepas_card/lepas-hero-{color}.png?v=1.19.0` (con `lepas-hero.png` aggiornato al render grigio per compatibilità), selezionabili tramite `color:` o i selettori dell'editor visuale preservando gli override `image:` e l'attributo `vehicle_image`.
- **Telemetria Completa `v1.18.0`, Blueprint SVG & Comandi Sicuri**: Integrati il programmatore partenze settimanale/rapido e la timeline 24h di ricarica programmata (`scheduled_charging_window`, `charge_days`, `next_departure`), hub clima completo (`number.lepas_climate_duration`, macro `cool_everything` / `heat_everything`, 4 sbrinamenti/volante, matrice sedili 4+1), blueprint SVG top-down animato della SUV con TPMS ai 4 angoli, conferma inline di 4 secondi sulle azioni fisiche sensibili, traduzioni IT/EN/NL e compatibilità Android System WebView.

## v1.18.0 — 2026-11-17

### 🇬🇧 English

- **Scheduled Charging UX, Days Selector & `appointmentChargeState` Fallback**: Clarified configuration entity labels (`A/C duration (pre-climate)`, `Scheduled charge · duration`, `Scheduled charge · start`) without changing existing `entity_id`s, added `select.lepas_charge_days` (with presets and custom weekday support), `button.lepas_apply_charging_schedule`, and diagnostic `sensor.lepas_scheduled_charging_window` (including `synced_with_car`). `switch.lepas_scheduled_charging` now also falls back to `realtime["appointmentChargeState"]` when `chargeAppointPlans` is absent, and vehicles lacking permission `2131` (`DATA_CAPS_PROBED_V4`) transparently fall back to `[1..7]` for `cycleData`.
- **Weekly & Quick Departure Scheduler (`airControl` + `chargeAppointControl` Sync)**: Added per-weekday departure schedules (`switch.lepas_departure_{mon..sun}_enabled`, `time.lepas_departure_{mon..sun}_time`), one-time quick departure (`switch.lepas_quick_departure`, `time.lepas_quick_departure_time` with automatic reset after firing), `select.lepas_departure_climate_mode` (`at_home` / `anywhere` / `off`), `switch.lepas_sync_charge_to_departure`, and diagnostic `sensor.lepas_next_departure`. Automatic pre-climatization (`airControl`) includes safety guards against starting while the engine is running or vehicle speed > 0 and respects the `at_home` geofence check; charging schedule synchronization (`chargeAppointControl`) aligns the charging end time with the next departure.
- **New Automation Services (`lepas.set_quick_departure`, `lepas.set_charging_schedule`)**: Added Home Assistant services with full EN/IT/NL translations to configure quick departures and scheduled charging parameters directly from automations and dashboards.

### 🇮🇹 Italiano

- **UX Ricarica Programmata, Selettore Giorni & Fallback `appointmentChargeState`**: Chiarite le etichette di configurazione (`A/C acceso per (pre-clima)`, `Ricarica prog. · durata`, `Ricarica prog. · inizio`) senza cambiare gli `entity_id` esistenti, e aggiunti `select.lepas_charge_days` (con preset e giorni personalizzati), `button.lepas_apply_charging_schedule` e il sensore diagnostico `sensor.lepas_scheduled_charging_window` (incluso `synced_with_car`). Lo switch `switch.lepas_scheduled_charging` ora usa `realtime["appointmentChargeState"]` come ripiego quando `chargeAppointPlans` è assente, e i veicoli senza permesso `2131` (`DATA_CAPS_PROBED_V4`) ripiegano automaticamente su `[1..7]` in `cycleData`.
- **Pianificatore Partenze Settimanale e Rapido (Sync `airControl` + `chargeAppointControl`)**: Aggiunti gli orari di partenza per giorno (`switch.lepas_departure_{mon..sun}_enabled`, `time.lepas_departure_{mon..sun}_time`), la partenza rapida singola (`switch.lepas_quick_departure`, `time.lepas_quick_departure_time` con disattivazione automatica dopo l'esecuzione), `select.lepas_departure_climate_mode` (`at_home` / `anywhere` / `off`), `switch.lepas_sync_charge_to_departure` e il sensore diagnostico `sensor.lepas_next_departure`. La pre-climatizzazione automatica (`airControl`) integra controlli di sicurezza (motore spento, velocità nulla, verifica geofence `at_home`); l'allineamento della ricarica (`chargeAppointControl`) sincronizza la fine ricarica con la prossima partenza prevista.
- **Nuovi Servizi di Automazione (`lepas.set_quick_departure`, `lepas.set_charging_schedule`)**: Aggiunti servizi Home Assistant tradotti in EN/IT/NL per configurare partenza rapida e finestra di ricarica programmata direttamente da automazioni e dashboard.

## v1.17.1 — 2026-11-17

### 🇬🇧 English

- **Populate Vehicle State Entities from `/asr/manager/realtime` (`_on_probe_data`)**: Propagated `META` status fields already returned in the 90-key `/asr/manager/realtime` payload (`frontLeftDoor`..`backRightDoor`, `trunkDoor`, `liftgateOperateState`, `doorLock`, `*WindowState`, `sunroofState`, `sunroofMoveState`, `frontHVACState`, `airPurification`, `fWinHeatingState`, seat switches, `chargeGunState`, `engineState`) into `coordinator.data["fields"]`, eliminating `unknown` states on vehicles that do not emit unsolicited `5A02` MQTT pushes during driving or door events. Fresh MQTT `5A02` updates (`_auto_e_sveglia()`) are never overwritten by cached `realtime` snapshots, and `msg_fields` / `CMD_CONFIRM_META` / `GEO_KEYS` remain strictly isolated.

### 🇮🇹 Italiano

- **Popolamento Entità di Stato da `/asr/manager/realtime` (`_on_probe_data`)**: Propagati in `coordinator.data["fields"]` i campi `META` di stato fisico già restituiti dal payload a 90 chiavi di `/asr/manager/realtime` (`frontLeftDoor`..`backRightDoor`, `trunkDoor`, `liftgateOperateState`, `doorLock`, `*WindowState`, `sunroofState`, `sunroofMoveState`, `frontHVACState`, `airPurification`, `fWinHeatingState`, switch sedili, `chargeGunState`, `engineState`), eliminando gli `unknown` sui veicoli che non inviano push MQTT `5A02` spontanei durante la guida o l'apertura delle portiere. Eventuali push `5A02` live recenti (`_auto_e_sveglia()`) non vengono mai sovrascritti e `msg_fields` / `CMD_CONFIRM_META` / `GEO_KEYS` restano rigorosamente isolati.

## v1.17.0 — 2026-11-16

### 🇬🇧 English

- **Per-VIN Auto-Learning Capabilities (`DATA_CAPS_PROBED_V3`, Fail-Open)**: Added `features_from_permissions`, `ENTITY_FEATURE_MAP`, and `entity_allowed` in `const.py` backed by `POST /tsp/v1/app/vmc/queryVehicleAuthority` (`permessi.leggi()`). During onboarding (`_probe_caps_for_vin`) and one-time backfill (`async_ensure_vehicle_identity`), only features explicitly returned as `0` by the backend are marked `False` in `entry.data["vehicle_features"]` (missing keys or network errors fail open), keeping unsupported entities (e.g. steering wheel heating, electric windshield, instant charging, alarm, rear seats on Lepas L8) out of Home Assistant while removing orphaned registry entries (`async_cleanup_disabled_entities`) and scheduling a single reload on backfill.
- **Default-Disabled `sunshadeState` & `at_home` Startup Restore**: Set `binary_sensor.lepas_sunroof_blind` (`sunshadeState`) to `entity_registry_enabled_default = False` when `sunroof` is enabled, and added `LepasCoordinator.restore_position()` called from `LepasTracker.async_added_to_hass()` so `binary_sensor.lepas_at_home` and home/away charging energy zones resolve immediately after a restart without waiting for a live GPS fix (without altering `last_pos_fix`).
- **Residual `unknown` State & Nomenclature Alignment**: `sensor.lepas_remaining_charge_time` now reports `0` min when idle (`chargeState != "1"`), `LepasTextSensor` diagnostic results (`command_result`, `wake_up_result`, `location_probe_result`) and `sensor.lepas_sunroof_movement_state` display `"In attesa"` / `"Waiting"` until the first live event, and `strings.json` plus `translations/{en,it,nl}.json` are aligned with zero entity ID changes.

### 🇮🇹 Italiano

- **Auto-apprendimento Capability per-VIN (`DATA_CAPS_PROBED_V3`, Fail-Open)**: Introdotte `features_from_permissions`, `ENTITY_FEATURE_MAP` ed `entity_allowed` in `const.py` basate su `POST /tsp/v1/app/vmc/queryVehicleAuthority` (`permessi.leggi()`). Durante l'onboarding (`_probe_caps_for_vin`) e il backfill una-tantum (`async_ensure_vehicle_identity`), solo le feature dichiarate esplicitamente `0` dal backend vengono salvate come `False` in `entry.data["vehicle_features"]` (chiavi mancanti o errori di rete restano *fail-open*), evitando di creare entità non supportate dal veicolo (es. volante riscaldato, parabrezza elettrico, ricarica immediata, antifurto, sedili posteriori su Lepas L8), ripulendo gli orfani nel registro (`async_cleanup_disabled_entities`) e schedulando un singolo reload al backfill.
- **`sunshadeState` Disabilitato di Default & Ripristino `at_home` al Riavvio**: Impostato `entity_registry_enabled_default = False` su `binary_sensor.lepas_sunroof_blind` (`sunshadeState`) e aggiunto `LepasCoordinator.restore_position()` richiamato da `LepasTracker.async_added_to_hass()`, così `binary_sensor.lepas_at_home` e la zona dei contatori ricarica funzionano subito dopo ogni riavvio senza attendere un fix GPS live (preservando `last_pos_fix`).
- **Fix Stati `unknown` Residui & Allineamento Nomenclature**: `sensor.lepas_remaining_charge_time` mostra ora `0` min a carica ferma (`chargeState != "1"`), i sensori diagnostici `LepasTextSensor` (`command_result`, `wake_up_result`, `location_probe_result`) e `sensor.lepas_sunroof_movement_state` mostrano `"In attesa"` / `"Waiting"` prima del primo evento live, e `strings.json` + `translations/{en,it,nl}.json` sono riallineati mantenendo invariati tutti gli `entity_id`.

## v1.16.5 — 2026-11-16

### 🇬🇧 English

- **Lepas EU `channelId: "6"` Alignment (`A00361` Root Fix)**: Updated `DEFAULTS[CONF_CHANNEL_ID]`, `PRESETS[PRESET_LEPAS_EU][CONF_CHANNEL_ID]`, `CoreCtx.DEFAULT_CHANNEL_ID`, and fallback `CHANNEL_ID` constants from `"1"` to `"6"` (matching `/tsp/v1/app/env/defaultEnv` used by the official Lepas Android app at startup), resolving `A00361` ("User does not exist") across `cpm/checkPassword`, `vmc/queryVehicleAuthority`, and `vac/queryAuthRemoteList`, as well as aligning the MQTT broker topic (`app/6/{tuserid}/account/msgCenter/msg`).
- **Automatic `ConfigEntry` Migration (`v1 → v2`)**: Bumped `LepasConfigFlow.VERSION` to `2` and added `async_migrate_entry` to automatically migrate existing Lepas EU `v1` entries (with `channel_id="1"`, empty, `None`, or missing) to `"6"`, while preserving `chery_eu` (`"2"`), custom region settings, and rejecting schema downgrades (`version > 2`).
- **Non-PII `checkPassword` Diagnostics**: Enriched failure logging in `core/commands.py` with non-PII routing/region metadata (`tuid_source`, `tuid_len`, `ql_code`, `auth_type`, `sv_code`, `scene`, `bff`, `ch`, `tenant`, `country`, `pin_len`, `pin_dig`, `cp_http`, `cp_key`, `ql_keys`).

### 🇮🇹 Italiano

- **Allineamento `channelId: "6"` per Lepas EU (Fix Root Cause `A00361`)**: Aggiornati `DEFAULTS[CONF_CHANNEL_ID]`, `PRESETS[PRESET_LEPAS_EU][CONF_CHANNEL_ID]`, `CoreCtx.DEFAULT_CHANNEL_ID` e le costanti di fallback `CHANNEL_ID` da `"1"` a `"6"` (valore restituito da `/tsp/v1/app/env/defaultEnv` all'avvio dell'app ufficiale Lepas), risolvendo definitivamente `A00361` ("User does not exist") su `cpm/checkPassword`, `vmc/queryVehicleAuthority` e `vac/queryAuthRemoteList` e allineando il topic MQTT (`app/6/{tuserid}/account/msgCenter/msg`).
- **Migrazione Automatica `ConfigEntry` (`v1 → v2`)**: Incrementata `LepasConfigFlow.VERSION = 2` e introdotta `async_migrate_entry` per migrare automaticamente a `"6"` le configurazioni Lepas EU `v1` esistenti (con `channel_id="1"`, vuoto, `None` o assente), preservando `chery_eu` (`"2"`), le configurazioni custom e bloccando eventuali downgrade (`version > 2`).
- **Diagnostica Non-PII su `checkPassword`**: Arricchito il log di errore in `core/commands.py` con soli metadati non-PII di regione/routing (`tuid_source`, `tuid_len`, `ql_code`, `auth_type`, `sv_code`, `scene`, `bff`, `ch`, `tenant`, `country`, `pin_len`, `pin_dig`, `cp_http`, `cp_key`, `ql_keys`).

## v1.16.4 — 2026-11-16

### 🇬🇧 English

- **Controlled `scene=2` Fallback on `A00361` (APK Parity)**: When `checkPassword` returns `A00361` ("User does not exist") with `scene=0`, Lepas now performs a single controlled retry with `scene=2` (matching the default scene parameter in the official app's `RusApiService::checkPassword`), allowing command authorization for secondary and primary accounts where `scene=0` is rejected by the backend.

### 🇮🇹 Italiano

- **Fallback Controllato `scene=2` su `A00361` (Parità APK)**: Quando `checkPassword` restituisce `A00361` ("User does not exist") con `scene=0`, Lepas esegue ora un singolo retry controllato con `scene=2` (allineato al default dell'app ufficiale in `RusApiService::checkPassword`), abilitando l'autorizzazione dei comandi sugli account dove il backend rifiuta `scene=0`.

## v1.16.3 — 2026-11-16

### 🇬🇧 English

- **APK Signature Path Parity (`_normalize_sig_url`)**: Normalized BFF signature calculation and `url` header by stripping the leading microservice prefix (`/tsp/` and `/marketing/` -> `/v1/...`, matching `http_utils.dart` in the official Lepas app) while keeping `/auth/oauth2/token` unchanged.
- **OAuth Refresh `user_id` Preservation & `getUserInfo` Recovery**: `_refresh_token_detail` now preserves `user_id` and identity metadata across token refreshes instead of overwriting `token.json` with a stripped refresh response, and `_resolve_tuserid` recovers missing `user_id` via `GET /marketing/v1/app/user` (`UserState::getUserInfo`) under `lock_token` with `0o600` atomic writes.
- **Pre-`checkPassword` Hard Gate, Controlled `A00361` Retry & Non-PII Diagnostics**: Aborts before `setVecDefault`/`checkPassword` when `tUserId` is unavailable (zero PIN lockout attempts consumed), performs a single `getTuserId` retry if `A00361` occurs with a login-supplied `tUserId` when an alternative ID is returned, normalizes `tuserid` on coordinator startup and password reauthentication, and exposes strictly non-PII health flags (`token_has_user_id`, `tuserid_present`, `tuserid_length`) in diagnostics and logs.

### 🇮🇹 Italiano

- **Parità Firma APK su Path BFF (`_normalize_sig_url`)**: Normalizzati il calcolo della firma e l'header `url` rimuovendo il prefisso del microservizio (`/tsp/` e `/marketing/` -> `/v1/...`, come in `http_utils.dart` dell'app ufficiale Lepas), lasciando invariato `/auth/oauth2/token`.
- **Preservazione `user_id` al Refresh OAuth & Fallback `getUserInfo`**: `_refresh_token_detail` conserva ora `user_id` e i metadati identitari durante il rinnovo del token senza più cancellarli da `token.json`; se assente, `_resolve_tuserid` recupera `user_id` tramite `GET /marketing/v1/app/user` (`UserState::getUserInfo`) serializzato sotto `lock_token` con scrittura atomica `0o600`.
- **Hard Gate Pre-`checkPassword`, Retry Singolo `A00361` & Telemetria Non-PII**: Blocca prima di `setVecDefault`/`checkPassword` se `tUserId` manca (zero tentativi PIN consumati), esegue un solo retry con `getTuserId` alternativo su `A00361` da login, normalizza `tuserid` all'avvio del coordinator e nella riautenticazione con password, e aggiunge flag sintetici non-PII (`token_has_user_id`, `tuserid_present`, `tuserid_length`) in diagnostica e log.

## v1.16.2 — 2026-11-16

### 🇬🇧 English

- **Secondary Account `tUserId == "0"` Resolution (`A00361`)**: Normalized placeholder `"0"` / `"None"` / `""` values for `tUserId` across BFF login, command PIN minting (`checkPassword`), permission lookup, and config flow discovery, resolving the real `tUserId` via signed `GET /tsp/v1/app/auth/getTuserId` (with `ts` before `[vals]` and the `keys` header, preserving `scene=0`).
- **Existing `ConfigEntry` Backfill & Discovery Envelope Support**: `LepasCoordinator` now automatically backfills invalid/zero `tuserid` values on startup before MQTT connection, and config flow vehicle discovery supports nested dictionary envelopes such as `authorizedControlCarList`.

### 🇮🇹 Italiano

- **Risoluzione `tUserId == "0"` su Account Secondari (`A00361`)**: Normalizzati i valori fittizi `"0"` / `"None"` / `""` di `tUserId` in login BFF, conio PIN comandi (`checkPassword`), verifica permessi e config flow, risolvendo il `tUserId` reale tramite `GET /tsp/v1/app/auth/getTuserId` firmata con `ts` prima di `[vals]` e header `keys` (preservando `scene=0`).
- **Backfill Automatico `ConfigEntry` ed Envelope Veicoli**: `LepasCoordinator` esegue ora automaticamente il backfill di `tuserid` mancanti o `"0"` all'avvio prima della connessione MQTT, e la scoperta veicoli nel config flow supporta gli envelope a dizionario come `authorizedControlCarList`.

## v1.16.1 — 2026-11-15

### 🇬🇧 English

- **Command PIN / `checkPassword` Routing (`A00361`)**: Backend error `A00361` ("User does not exist") wrapped in `code=1, message='A00361'` is now extracted and classified as a non-PIN configuration/user-ID issue (`reason="config"`) instead of falsely triggering the PIN error message and anti-lockout counter.
- **`tUserId` Alignment from `queryList`**: `checkPassword` now passes `tUserId`/`channelId` to `vmc/queryList` (matching the official Lepas app) and aligns `tUserId` from the vehicle entry if missing or mismatched.

### 🇮🇹 Italiano

- **Classificazione errore `A00361` in `checkPassword`**: Il codice applicativo `A00361` ("User does not exist") restituito dentro `code=1, message='A00361'` viene ora estratto e classificato correttamente come errore di configurazione/utente (`reason="config"`) invece di essere scambiato per PIN errato e consumare il contatore anti-lockout.
- **Allineamento `tUserId` da `queryList`**: `checkPassword` invia ora `tUserId`/`channelId` a `vmc/queryList` (come l'app ufficiale Lepas) e riallinea `tUserId` dal veicolo se mancante o disallineato.

## v1.16.0 — 2026-11-15

### 🇬🇧 English

- **Password-Only Authentication (Email or Phone + Password)**: Removed the deprecated OTP login/reauth flow (email/SMS OTP, captcha solver, WAF TLS fallback, `numpy` dependency, and the 3 OTP entities `text.lepas_otp_code`, `button.lepas_request_otp_code`, `button.lepas_confirm_otp`). Setup now goes directly to a unified `login_password` form supporting both email and international phone number with area code.
- **Automatic Cleanup & Migration**: Existing installations automatically remove orphaned OTP entities from the Home Assistant entity registry on startup, and reauthentication routes directly to password login with automatic entry migration.
- **Documentation (`README.md`)**: Added clear prerequisites and setup instructions, including the requirement to set a password in the official Lepas app, one-shot password handling, and first-start `unknown` sensor behavior when the vehicle is asleep.

### 🇮🇹 Italiano

- **Autenticazione esclusiva con Password (Email o Telefono + Password)**: Rimosso il flusso di login/riautenticazione tramite codice OTP (email/SMS, solver captcha, ripiego TLS WAF, dipendenza `numpy` e le 3 entità OTP `text.lepas_otp_code`, `button.lepas_request_otp_code`, `button.lepas_confirm_otp`). La configurazione passa ora direttamente al form unificato `login_password` che supporta sia email sia numero di telefono con prefisso internazionale.
- **Pulizia e Migrazione Automatica**: Le installazioni esistenti rimuovono automaticamente dal registro di Home Assistant le entità OTP orfane all'avvio, e la riautenticazione porta direttamente al login con password aggiornando l'entry.
- **Documentazione (`README.md`)**: Aggiunti i prerequisiti e la guida dettagliata per la registrazione, inclusa la necessità di impostare una password nell'app ufficiale Lepas, la gestione one-shot della password e il comportamento dei sensori `unknown` al primo avvio ad auto spenta.

## v1.15.4 — 2026-11-14

### 🇬🇧 English

- **Cleaner Config Flow UX (`custom_region` Step)**: Moved the 8 advanced/regional endpoint fields (`bff`, `tenant_code`, `country_id`, `channel_id`, `tsp_host`, `car_mqtt_host`, `car_mqtt_port`, `certs_src`) out of the `login_email`, `login_phone`, and `login_password` forms into a dedicated `custom_region` step shown only when the **Custom** preset is selected. Standard EU logins now show only credentials, language, and brand/region preset.

### 🇮🇹 Italiano

- **UX Config Flow più pulita (step dedicato `custom_region`)**: Spostati gli 8 campi tecnici avanzati di regione/marchio (`bff`, `tenant_code`, `country_id`, `channel_id`, `tsp_host`, `car_mqtt_host`, `car_mqtt_port`, `certs_src`) fuori dai form `login_email`, `login_phone` e `login_password`, in uno step secondario dedicato `custom_region` mostrato solo scegliendo il preset **Custom**. I login EU standard ora mostrano solo credenziali, lingua e preset.

## v1.15.3 — 2026-11-14

### 🇬🇧 English

- **Security Hardening**: Masked `tuserid` in MQTT `on_connect` `INFO` logs (`coordinator.py`), switched temporary token file creation to atomic `0o600` mode via `os.open` (`core/wake.py`, `core/prova_token.py`), and HTML-escaped error messages in the Lovelace card `catch` block (`lovelace/lepas-card.js`).
- **4- or 6-Digit Remote PIN Translations**: Updated UI descriptions in `strings.json`, `en.json`, `it.json`, and `nl.json` to clarify support for both 4-digit and 6-digit remote control PINs.

### 🇮🇹 Italiano

- **Hardening di sicurezza**: Mascherato `tuserid` nei log `INFO` di connessione MQTT (`coordinator.py`), resa atomica la creazione con permessi `0o600` dei file temporanei dei token tramite `os.open` (`core/wake.py`, `core/prova_token.py`) e applicato l'escaping HTML ai messaggi d'errore nel blocco `catch` della card Lovelace (`lovelace/lepas-card.js`).
- **Traduzioni PIN comandi (4 o 6 cifre)**: Aggiornate le descrizioni UI in `strings.json`, `en.json`, `it.json` e `nl.json` per chiarire il supporto ai PIN di controllo remoto a 4 o 6 cifre.

## v1.15.2 — 2026-10-23

### 🇬🇧 English

- **Automated GitHub Release Workflow (`.github/workflows/release.yml`)**: Added continuous release automation triggered on SemVer version tags (`vX.Y.Z`). The workflow automatically verifies manifest version alignment, extracts bilingual release notes from `CHANGELOG.md`, and creates or updates GitHub Releases with notes for HACS.

### 🇮🇹 Italiano

- **Workflow di rilascio GitHub automatico (`.github/workflows/release.yml`)**: Aggiunta automazione di rilascio attivata dai tag di versione SemVer (`vX.Y.Z`). Il workflow verifica l'allineamento della versione nel manifest, estrae le note di rilascio bilingui da `CHANGELOG.md` e pubblica o aggiorna la GitHub Release con le note per HACS.

## v1.15.1 — 2026-10-23

### 🇬🇧 English

- **Complete Native Lepas / Chery EU Alignment**: Removed all residual sibling brand references from UI translations (`strings.json`, `en.json`, `it.json`, `nl.json`), configuration presets (`config_flow.py`, `const.py`), core subprocess environment variables (`LEPAS_*`), and legacy migration shims (`legacy.py`).
- **Permanent Hygiene Regression Gate**: Added `test_zero_legacy_brand_references` in `tests/test_repo_hygiene.py` to guarantee zero legacy brand occurrences across code, translations, tools, and tests.

### 🇮🇹 Italiano

- **Allineamento nativo completo Lepas / Chery EU**: Rimossi tutti i riferimenti residuali ad altri marchi dalle traduzioni UI (`strings.json`, `en.json`, `it.json`, `nl.json`), dai preset di configurazione (`config_flow.py`, `const.py`), dalle variabili d'ambiente del motore core (`LEPAS_*`) e dai moduli di migrazione legacy (`legacy.py`).
- **Gate di regressione permanente**: Aggiunto `test_zero_legacy_brand_references` in `tests/test_repo_hygiene.py` per garantire zero occorrenze legacy in codice, traduzioni, tool e test.

## v1.15.0 — 2026-10-23

### 🇬🇧 English

- **Direct HACS Repository Support (`cavuminfundo/Lepas-HA`)**: Native direct download HACS configuration without `zip_release`, featuring official repository endpoints, comprehensive English documentation, and quick-start installation guide in `README.md`.
- **New Cursive Brand Identity (`custom_components/lepas/brand/`)**: Complete replacement of legacy brand assets with 8 original RGBA PNG icons featuring the *"Lepas"* monogram and wordmark in chrome and electric cyan cursive typography.
- **Dark Tech Automotive Lovelace Card & Real Lepas L8 Hero (`lepas-card.js` & `lepas-hero.png`)**: Full redesign of the Lovelace card with Dark Tech Automotive palette (`#0F141C` / `#00D2FF`), 4 core metrics (EV Range, Fuel/Total Range, Charging Power, Odometer), responsive CSS Container Queries, WCAG AA/AAA keyboard accessibility, and a 3/4 studio render faithful to the real proportions of the 4.69 m Lepas L8 SUV.

### 🇮🇹 Italiano

- **Supporto repository HACS diretto (`cavuminfundo/Lepas-HA`)**: Configurazione HACS diretta senza `zip_release`, con documentazione completa e guida rapida all'installazione in inglese in `README.md`.
- **Nuova identità visiva corsiva (`custom_components/lepas/brand/`)**: Sostituzione integrale delle vecchie icone legacy con 8 nuovi asset PNG RGBA originali dotati di monogramma e logotipo *"Lepas"* in calligrafia corsiva cromata/ciano elettrico.
- **Scheda Lovelace Dark Tech Automotive & Hero Lepas L8 reale (`lepas-card.js` e `lepas-hero.png`)**: Riprogettazione completa della scheda Lovelace con palette Dark Tech Automotive (`#0F141C` / `#00D2FF`), 4 metriche chiave (Autonomia EV, Carburante/Totale, Potenza di ricarica, Contachilometri), CSS Container Queries responsive, accessibilità tastiera WCAG AA/AAA e render studio 3/4 fedele alle proporzioni reali del SUV Lepas L8 da 4,69 m.

## v1.14.0 — 2026-08-24

### 🇬🇧 English

- **New "Vent sunroof" button: the sunroof can now be tilted, not only opened or closed.**
  It works like "Vent windows": one press moves the sunroof to the tilt / vent position, and
  the usual close on the sunroof card brings it back down. Full open and close are
  unchanged. This adds one entity, `button.chery_connect_vent_sunroof`. *The command was
  found and tested on a Jaecoo 7 PHEV by the person who reported it; this change has not
  yet been tried on other models.*
- **"Petrol range (miles)" now works out for itself which unit the car is speaking.** It is
  a diagnostic sensor, and until now it assumed that reading arrived in miles — true on the
  Omoda 9, but worked out from two readings of a single car. On a model sending kilometres
  instead, Home Assistant would have converted an already-metric number and shown **a range
  half again as long as the real one**. It now compares against the ordinary petrol range,
  which always arrives in kilometres, and that comparison settles which case it is. On an
  Omoda 9 nothing changes: the number is identical to before.
- **An incomplete reading no longer produces a wrong number.** When the value needed for
  that comparison is missing, the sensor keeps the last good number instead of showing one
  that might be false — and that would have stayed on screen until the next reading.
- **SMS sign-in now works, including for accounts registered with a phone number only.** Signing in with a phone number instead of an email always failed, even with the right code: the integration built the account identity **in the wrong order** (area code and number swapped) and minted a token for an empty phantom account with no vehicles. The order is now correct — confirmed both live and by reading the official app — so SMS sign-in reaches your real account and your car.
- **A clear message when the account has no car.** If the code was correct but that account has no vehicle on it, it used to say "invalid code", sending you to re-check an OTP that was actually fine. Now it tells you what is really going on: the code is right, but there is no car linked to that account.
- **Safer phone-number redaction in the diagnostics file.** The rule that hides the number in logs was hardened so it cannot slip through on an unexpected shape: when in doubt it masks more, never less.
- **You can sign in with your account password, without waiting for any code.** Until now
  the only way in was an OTP code by e-mail or SMS, and for anyone who no longer receives
  that code it was a wall: the integration simply could not be set up. The first screen now
  offers a third option, "Sign in with password": account e-mail, password and vehicle PIN,
  and the car appears without any code at all. The password is used **only** to get in and
  is never stored: from there the session lives on the token, exactly as it does with OTP.
  And if the session expires one day, you are asked for the password instead of being sent
  hunting for a code.
- **A dropdown picks your brand and region for you.** The integration always introduced
  itself to the server as Omoda, so a Chery account was not recognised and four technical
  parameters had to be guessed by hand. You now choose "Omoda / Jaecoo (Europe)" or
  "Chery (Europe)" and they fill themselves in; "Custom" remains for any other region or
  brand, with the fields on show as before. *None of us owns a Chery account: the
  Omoda/Jaecoo path is the tested one, the other is written from reading the official app
  and is waiting for the first person to actually use it.*
- **You can choose which language the car writes to you in.** The e-mails and texts carrying
  the code, and the messages the server returns when something goes wrong, follow the
  language declared at sign-in: it used to be fixed. There is now a dropdown, English or
  Italian. If you already have the integration set up, you need do nothing and will see no
  change; the choice applies to new setups.
- **The dashboard card now ships with the integration.** It used to be a separate download
  that you registered by hand among the Lovelace resources, a step which is easy to get
  wrong and which not everybody wants to take. It is now included and loads itself: add a
  card of type `custom:chery-card`. It finds your car's entities on its own, so with no
  configuration at all it already shows photo, battery, range, charging state, and the
  warnings (tyres, low battery, car unreachable) only when something is actually wrong.
- **Two separate counters for energy charged at home and away, plus a sensor saying whether
  the car is at home.** They exist to answer "what is this actually costing me": energy
  taken from your own socket and energy taken elsewhere land in two distinct totals, usable
  in the Home Assistant Energy dashboard. ⚠️ **They only work with automatic updating
  switched on**: the counters are built by sampling charging power at each reading, and with
  no periodic readings there is nothing to add up.
- **When a command is refused, we now tell you why.** If the integration has to skip or adapt something before sending a command — a function the manufacturer does not authorise on your car, a duration your car does not accept — it writes that in "Command result". Until now, though, the explanation only appeared **when the command succeeded**: in the opposite case, which is exactly the one where it is needed, all you got was the bare error, and the reason went only to the technical log, where nobody goes looking. The explanation now stays attached to the result either way. And the command's name is no longer repeated in front of the explanation, since the result already opens with it: those were the characters missing for the sentence to fit in the space Home Assistant allows. On an Omoda 9 almost none of these notices appear at all — they concern functions the manufacturer denies on other cars — but **one of them you will see too**: if you set the climate duration to a value the car does not accept (the slider goes to 30 minutes, an Omoda 9 takes 5, 10 or 15) and the command is then refused, for instance because the car is busy, you now read alongside the error which duration was actually used. Before, in that case, only the error was left.
- **A warning is either readable in full or not there at all.** When the warnings do not all fit in the line we tell you how many there are. One case remained, though, where making room for that count chopped the last warning mid-word: precisely what this rule exists to prevent, because a cut sentence looks complete. Now a warning that does not fit whole leaves the line and adds to the count instead.
- **"Cool everything" now does something even on cars that do not have that command.** On some vehicles the manufacturer does not authorise the single "cool everything" button at all: pressing it produced nothing but an error, and there was no way round it. Its **constituent parts**, however, are perfectly authorised on that same car, taken one at a time: the climate control and the front seat ventilation. Now, when the single command is denied, the integration rebuilds it itself into one request the car does accept — exactly the same thing you would get by switching on the climate and then each seat by hand in the official app. Whatever your car does not allow is left out, and **"Command result" tells you how many functions were left behind** instead of leaving you to work it out from a seat that stays lukewarm; if their names fit in the line we write those too, and in full they are always in the log. (Space really is tight: Home Assistant allows a message 255 characters, result included.)
- **Tested on a real car, not only on paper — switching on.** The owner of a Jaecoo 7 (the car this whole story started from) sent the recomposed request by hand with the vehicle parked: accepted — and he went out and put a hand on the cushions: **both front seats really were ventilating**. **Switching off** is the symmetrical twin of that request, but nobody has tried that one yet: if your car refused it, the switch would not falsely claim "off" — it stays as it was and you read the error.
- **On his car the rear seats stay out, and he told us that is no loss:** on that vehicle the rear seats are neither heated nor ventilated. Worth saying because he checked it in the car himself: **we cannot infer from this list what your car does or does not have fitted**, and we do not try.
- **Cooling yes, heating no — and that is not an oversight.** "Heat everything" is not rebuilt the same way, because among the things it switches on is the heated steering wheel, and for the steering wheel we do not know which alternative route the car would accept: guessing could make everything else fail too. On every vehicle we know of, besides, the heating command is already authorised and the pruning that was already there is enough for it.
- **On an Omoda 9 nothing changes at all.** There the manufacturer's command is authorised and works: when the official route is open we never replace it with an imitation of our own.

- **If the login fails after your code was accepted, we now tell you where it broke.** Anyone stuck at first setup got the same sentence every time, "token minted but login still KO", with no way to tell what to try next: wrong code? clock out of sync? the PIN? None of the three. That message means **the code was accepted** and what fails is the step after it, the connection to the server holding your cars. The integration already knew how to tell a network problem from an expired session from a failed renewal, and threw that away an instant before writing the message. It is in the message now, and the server's own answer goes to the technical log. This is not a repair: it is the difference between a fault you can diagnose and one you guess at. If you are one of the people stuck here, your next attempt finally produces something you can send us.

- **Internal: entity names can move to English without your installation noticing.** Nothing changes for you in this version. Until now an entity's technical id and its translated label were both derived from the same Italian word, so translating the labels would have meant renaming every entity - and renaming an entity breaks the automations and history of whoever uses it. The two are now separate: labels can move to English while the technical ids stay put, which means nobody's automations, dashboards or history are touched.

- **If the first login does not get in, the log now also says which server it was knocking on.** The previous step made explicit *which* of the three problems it was; what stayed invisible was the thing that most often explains them, the region parameters actually in use: gateway, tenant, country, channel and language. They could only be worked out by asking the person which entry they picked in the first menu, and an answer from memory is not a measurement. They now appear next to the error, together with the reason the automatic renewal was not carried out and the text of the network error rather than just its class name. These are settings, not personal data: no address, no number, no token.

- **Every entity has a new name, and your history came with it.** The entity ids of this integration were Italian (`sensor.omoda9_batteria`) because they were built from the Italian labels it grew up with. They are now English: `sensor.chery_connect_battery`. **The rename happens by itself the first time you start this version, and your graphs, history and energy dashboard follow it** - Home Assistant moves the statistics when an entity is renamed, and the integration does the renaming for you. There is nothing to click and nothing to reinstall. **What does not move on its own is anything you wrote by hand**: automations, scripts, template sensors and dashboard cards that name an entity in text. Those need one search and replace, and the full old-to-new list is in `docs/entity-id-rename.md`. It is one break, on purpose, done once: the names were the last thing in this project that only made sense if you read Italian.

- **The integration is now called Chery Connect, and the bundled card finally works.** The name in Home Assistant and in HACS was still "Omoda 9 / Jaecoo", which is one car out of the several this supports. Your car keeps its own name: the integration is the brand, the device is the vehicle. And the dashboard card that ships with the integration, which until now loaded and showed almost nothing, now finds your entities: it was matching them by English names while the entity ids were Italian, and after the rename it was matching an old prefix. Battery, range, charging, odometer, lock and the warnings all appear. If you had given up on that card, add it again.

- **Coming from the older `omoda_jaecoo` installation? Your history can come with you.** Home Assistant treats that line as a different integration, so setting this one up gives you new, empty entities while years of readings stay attached to the installation you are about to remove. There is now a way to take them over instead: disable the old integration, then call the action **Adopt entities from the omoda_jaecoo installation** (Developer tools, Actions). Run it first with *dry run* on, which changes nothing and reports what it would do. 96 of the 101 entities come across with their history; the five that cannot are named in the report, with the reason - two because the two lines built them as different kinds of entity, three because they do not exist here at all. Nothing is automatic and nothing happens unless you ask for it.

- **Already deleted the old `omoda_jaecoo` integration? Your history is still there.** Removing an integration takes its entities out of Home Assistant's registry; it does **not** delete the data. Long-term statistics and state history stay in the database, orphaned but intact, and Home Assistant still remembers every entity it removed. There is now an action for exactly this: **Recover history from a removed omoda_jaecoo installation** (Developer tools, Actions), which moves the statistics and the history onto the entities of this integration. Nothing to reinstall, and the old integration does not need to exist any more. Run it with *dry run* on first. One warning on timing: the recorder eventually purges orphaned data, so this is a matter of days, not forever.

- **Recovering from an `omoda_jaecoo` installation now brings the state history too, not only the statistics.** If you already ran the recovery on an earlier beta, run it again: it will pick up what was left behind, and it will not touch what it already moved. The first time this ran on a real migration, the long-term statistics came across and the state history did not, for every entity that already existed under its new name - which is every entity, if you set up the integration before recovering. Graphs went back to July, the history panel started that evening. Both now move.

- **The history recovery now actually moves the history.** The previous attempt tried to clear the shorter series out of the way with the recorder's purge, which does not work: purging deletes the states but leaves the row that blocks the rename, so every single entity failed with `already in use` and the report said it had succeeded. It now moves the shorter history aside under a parked name instead of deleting it, which works and destroys nothing. If you ran the recovery before, run it again.

- **Three sensors that only exist on a battery-electric car kept their old Italian names, and had no translation at all.** Charging power, WLTP range and electric efficiency are created only once the car has confirmed it is battery-only, which happens after the first setup - so they were not present when the renaming table was built, and they were never in the translation files either. They now have English ids like everything else, and a name in every language. If you have them, they are renamed automatically at the next start, and your history follows.

- **Internal: the integration no longer asks to install `requests` and `pillow`.** Home Assistant already ships both, and its validator now rejects a custom integration that lists them, which would have blocked this release. Nothing changes on your installation: the integration uses the copies Home Assistant already has.

### 🇮🇹 Italiano

- **Nuovo pulsante «Ventila tetto»: il tetto ora si può anche inclinare, non solo aprire o
  chiudere.** Funziona come «Ventila finestrini»: una pressione porta il tetto in posizione
  inclinata / ventilazione, e la normale chiusura della card del tetto lo richiude. Apertura
  e chiusura complete non cambiano. Si aggiunge un'entità, `button.chery_connect_vent_sunroof`.
  *Il comando è stato trovato e provato su una Jaecoo 7 PHEV da chi l'ha segnalato; su altri
  modelli non è ancora stato provato.*

- **«Autonomia benzina (miglia)» ora capisce da sola in che unità parla l'auto.** È un
  sensore di diagnostica, e finora dava per scontato che quel dato arrivasse in miglia —
  cosa vera sulla Omoda 9, ma dedotta da due sole letture di una sola macchina. Su un
  modello che lo mandasse in chilometri, Home Assistant avrebbe convertito un numero già
  metrico e mostrato **un'autonomia più lunga di una volta e mezza**. Adesso il confronto
  con l'autonomia benzina normale, che arriva sempre in chilometri, dice quale delle due
  cose sta succedendo. Sulla Omoda 9 non cambia niente: il numero è identico a prima.
- **Un dato incompleto non fa più comparire un numero sbagliato.** Se in una lettura manca
  il valore di confronto, quel sensore tiene l'ultimo numero buono invece di mostrarne uno
  che potrebbe essere falso — e che sarebbe rimasto lì fino alla lettura dopo.
- **Il login via SMS ora funziona, anche per gli account registrati solo col numero.** Chi accedeva col numero di telefono invece che con l'email otteneva sempre un errore, anche col codice giusto: l'integrazione componeva l'identità dell'account **nell'ordine sbagliato** (prefisso e numero invertiti) e coniava un token per un account fantasma vuoto, senza veicoli. Ora l'ordine è quello corretto — confermato sia dal vivo sia leggendo il programma dell'app ufficiale — e il login via SMS raggiunge il tuo account reale, con la tua auto.
- **Un messaggio chiaro quando l'account non ha un'auto.** Se il codice era corretto ma su quell'account non risulta nessun veicolo, prima compariva «codice non valido», mandandoti a ricontrollare un OTP che invece andava benissimo. Adesso te lo diciamo com'è davvero: il codice è giusto, ma non c'è un'auto collegata a quell'account.
- **Numero di telefono più protetto nei file di diagnostica.** La regola che nasconde il numero nei log è stata resa più robusta, così non può sfuggire per un caso di forma inattesa: nel dubbio nasconde di più, mai di meno.
- **Puoi accedere con la password dell'account, senza aspettare nessun codice.** Finora
  l'unica strada era il codice OTP via e-mail o SMS, e per chi quel codice non lo riceve
  più era un muro: l'integrazione non si poteva proprio configurare. Adesso la prima
  schermata offre una terza voce, «Accedi con password»: e-mail, password e PIN del
  veicolo, e l'auto compare senza passare da nessun codice. La password serve **solo** per
  entrare e non viene mai salvata: da lì in poi la sessione vive sul token, esattamente
  come con l'OTP. E se un giorno la sessione scade, ti viene richiesta la password invece
  di mandarti a caccia di un codice.
- **Un menù a tendina sceglie marchio e regione al posto tuo.** L'integrazione si
  presentava al server sempre come Omoda, quindi un account Chery non veniva riconosciuto e
  bisognava indovinare a mano quattro parametri tecnici. Ora si sceglie «Omoda / Jaecoo
  (Europa)» oppure «Chery (Europa)» e vengono compilati da soli; «Custom» resta per
  qualsiasi altra regione o marchio, con i campi a vista come prima. *Nessuno di noi ha un
  account Chery: la strada Omoda/Jaecoo è quella provata, l'altra è scritta seguendo il
  programma dell'app ufficiale e aspetta la prima persona che la usi davvero.*
- **Puoi scegliere in che lingua l'auto ti scrive.** Le e-mail e gli SMS col codice, e i
  messaggi che il server restituisce quando qualcosa va storto, seguono la lingua dichiarata
  al momento dell'accesso: prima era fissa. Ora c'è un menù a tendina, inglese o italiano.
  Chi ha già l'integrazione configurata non deve fare niente e non vede alcun cambiamento;
  la scelta riguarda le configurazioni nuove.
- **La scheda per la dashboard arriva insieme all'integrazione.** Prima andava scaricata a
  parte e registrata a mano fra le risorse di Lovelace, passaggio che si sbaglia facilmente
  e che non tutti hanno voglia di fare. Adesso è inclusa e si carica da sola: basta
  aggiungere una scheda di tipo `custom:chery-card`. Trova da sé le entità della tua auto,
  quindi senza configurazione mostra già foto, batteria, autonomia, stato di ricarica e gli
  avvisi (gomme, batteria bassa, auto irraggiungibile) solo quando c'è qualcosa che non va.
- **Due contatori separati per l'energia caricata a casa e fuori, più un sensore che dice se
  l'auto è a casa.** Servono a rispondere alla domanda «quanto mi costa davvero»: l'energia
  presa dalla tua presa e quella presa altrove finiscono in due totali distinti, utilizzabili
  nel pannello Energia di Home Assistant. ⚠️ **Funzionano solo con l'aggiornamento automatico
  acceso**: i contatori si costruiscono campionando la potenza di ricarica a ogni lettura, e
  senza letture periodiche non c'è niente da sommare.
- **Quando un comando viene rifiutato, adesso ti diciamo perché.** Se prima di mandare un comando l'integrazione deve saltare o adattare qualcosa — una funzione che il costruttore non autorizza sulla tua auto, una durata che la tua vettura non accetta — te lo scrive in «Esito comando». Fino a ieri però quella spiegazione compariva **solo quando il comando riusciva**: nel caso opposto, che è proprio quello in cui serve, restava scritto solo l'errore nudo e il motivo finiva unicamente nel registro tecnico, dove nessuno lo va a cercare. Adesso la spiegazione resta attaccata all'esito in entrambi i casi. E non ripetiamo più il nome del comando davanti alla spiegazione, visto che l'esito lo dice già come prima cosa: erano i caratteri che mancavano perché la frase ci stesse tutta nello spazio che Home Assistant concede. Su un'Omoda 9 quasi tutti questi avvisi non escono affatto — riguardano funzioni che il costruttore nega su altre vetture — ma **uno lo vedrai anche tu**: se imposti la durata del clima su un valore che l'auto non ammette (il cursore arriva a 30 minuti, l'Omoda 9 ne accetta 5, 10 o 15) e il comando viene rifiutato, per esempio perché l'auto è occupata, adesso accanto all'errore leggi anche quale durata è stata usata. Prima, in quel caso, restava solo l'errore.
- **Un avviso o si legge intero o non c'è.** Quando gli avvisi non entrano tutti nella riga te ne diciamo il numero. Restava però un caso in cui, per far posto a quel conteggio, l'ultimo avviso veniva accorciato a metà parola: proprio la cosa che questa regola vuole evitare, perché una frase tagliata sembra completa. Adesso l'avviso che non ci sta per intero esce dalla riga e va a ingrossare il conteggio.
- **«Raffredda tutto» ora fa qualcosa anche sulle auto che quel comando non ce l'hanno.** Su alcune vetture il costruttore non autorizza affatto il pulsante unico «raffredda tutto»: premendolo si otteneva soltanto un errore, e non c'era niente da fare. I suoi **pezzi**, però, quella stessa auto li autorizza benissimo, presi uno per uno: il climatizzatore e la ventilazione dei sedili anteriori. Adesso, quando il comando unico è negato, l'integrazione lo rifà da sé in un'unica richiesta che l'auto accetta — la stessa identica cosa che otterresti accendendo a mano il clima e poi i sedili dall'app ufficiale. Quello che la tua vettura non consente resta fuori, e **in «Esito comando» trovi quante funzioni sono rimaste indietro** invece di doverlo indovinare da un sedile che resta tiepido; se nella riga ci sta anche il loro nome te lo scriviamo, e per esteso ci sono comunque sempre nel registro. (Lo spazio è poco davvero: Home Assistant concede 255 caratteri a un messaggio, esito compreso.)
- **Provato su un'auto vera, non solo sulla carta — l'accensione.** Il proprietario di una Jaecoo 7 (l'auto da cui è nata tutta questa storia) ha spedito a mano la richiesta ricomposta a vettura ferma: accettata, ed è uscito a toccare i cuscini — **i due sedili anteriori ventilavano davvero**. Lo **spegnimento** è il gemello simmetrico di quella richiesta, ma quello nessuno l'ha ancora provato: se la tua auto lo rifiutasse, l'interruttore non ti direbbe «spento» per finta — resta com'era e leggi l'errore.
- **Sulla sua auto i sedili posteriori restano fuori, e ci ha detto che non è una rinuncia:** su quella vettura i sedili di dietro non sono né riscaldati né ventilati. Vale la pena dirlo perché lo ha verificato lui a bordo: **noi non possiamo dedurre da questo elenco cosa la tua auto abbia o non abbia montato**, e non ci proviamo.
- **Il freddo sì, il caldo no — e non è una dimenticanza.** «Riscalda tutto» non viene ricomposto allo stesso modo, perché fra le cose che accende c'è il volante riscaldato, e per il volante non sappiamo quale strada alternativa l'auto accetterebbe: tirare a indovinare rischierebbe di far fallire tutto il resto. Su tutte le vetture che conosciamo, del resto, il comando del caldo è già autorizzato e gli basta la potatura che c'era già.
- **Su un'Omoda 9 non cambia assolutamente nulla.** Lì il comando del costruttore è autorizzato e funziona: quando la via ufficiale è aperta non la sostituiamo mai con una nostra imitazione.

- **Se l'accesso fallisce dopo che il codice e' stato accettato, adesso ti diciamo dove si e' rotto.** Chi si bloccava al primo accesso leggeva sempre la stessa frase, "token coniato ma login ancora KO", e non aveva modo di capire cosa provare: il codice era sbagliato? l'ora del computer? il PIN? Nessuna delle tre. Quel messaggio vuol dire che **il codice e' stato accettato** e che a fallire e' il passo successivo, il collegamento al server che tiene le tue auto. L'integrazione sapeva gia' distinguere fra un problema di rete, una sessione scaduta e un rinnovo non riuscito, ma buttava via quella informazione un istante prima di scriverla. Adesso la trovi nel messaggio, e nel registro tecnico compare anche la risposta del server. Non e' una riparazione: e' la differenza fra un guasto che si puo' diagnosticare e uno su cui si tira a indovinare. Se sei fra le persone ferme qui, il prossimo tentativo produce finalmente qualcosa da mandarci.

- **Lavoro interno: i nomi delle entita' potranno passare all'inglese senza che la tua installazione se ne accorga.** Non cambia niente per te in questa versione. Finora il nome tecnico di ogni entita' e la sua etichetta tradotta erano ricavati dalla stessa parola italiana, quindi tradurre le etichette avrebbe voluto dire rinominare tutte le entita' - e rinominare un'entita' rompe le automazioni e i grafici di chi la usa. Ora le due cose sono separate: le etichette si possono portare all'inglese lasciando fermi i nomi tecnici, cioe' senza toccare automazioni, dashboard e storico di nessuno.

- **Se il primo accesso non entra, adesso il registro dice anche su quale server stava bussando.** Il passo precedente aveva reso esplicito *quale* dei tre problemi fosse; restava invisibile la cosa che li spiega piu' spesso, cioe' i parametri di regione realmente in uso: gateway, tenant, paese, canale e lingua. Erano deducibili solo chiedendo alla persona quale voce avesse scelto nel primo menu, e una risposta a memoria non e' una misura. Ora compaiono accanto all'errore, insieme al motivo per cui il rinnovo automatico non e' stato fatto e al testo dell'errore di rete invece del solo nome tecnico. Sono impostazioni, non dati personali: nessun indirizzo, nessun numero, nessun token.

- **Ogni entita' ha un nome nuovo, e il tuo storico e' venuto dietro.** Gli `entity_id` di questa integrazione erano italiani (`sensor.omoda9_batteria`) perche' nascevano dalle etichette italiane con cui il progetto e' cresciuto. Adesso sono inglesi: `sensor.chery_connect_battery`. **Il cambio avviene da solo al primo avvio di questa versione, e grafici, cronologia e dashboard Energia lo seguono** - Home Assistant sposta le statistiche quando un'entita' viene rinominata, e ci pensa l'integrazione a rinominarle. Non c'e' niente da premere e niente da reinstallare. **Quello che non si sposta da solo e' cio' che hai scritto a mano**: automazioni, script, sensori template e schede della dashboard che nominano un'entita' per iscritto. Serve una sostituzione, e l'elenco completo vecchio-nuovo e' in `docs/entity-id-rename.md`. E' una rottura sola, voluta, fatta una volta: i nomi erano l'ultima cosa di questo progetto che aveva senso solo sapendo l'italiano.

- **L'integrazione adesso si chiama Chery Connect, e la scheda inclusa finalmente funziona.** Il nome in Home Assistant e in HACS era ancora "Omoda 9 / Jaecoo", cioe' una delle diverse auto che questa integrazione gestisce. La tua auto tiene il suo nome: l'integrazione e' il marchio, il dispositivo e' la vettura. E la scheda per la dashboard inclusa nel pacchetto, che fino a ieri si caricava e non mostrava quasi niente, adesso trova le tue entita': cercava nomi inglesi quando gli identificativi erano italiani, e dopo il cambio di nome cercava il prefisso vecchio. Batteria, autonomia, ricarica, odometro, serratura e avvisi compaiono tutti. Se avevi rinunciato a quella scheda, riaggiungila.

- **Vieni dalla vecchia installazione `omoda_jaecoo`? Il tuo storico puo' venire con te.** Per Home Assistant quella linea e' un'altra integrazione, quindi configurando questa ti ritrovi entita' nuove e vuote mentre anni di letture restano attaccati all'installazione che stai per togliere. Adesso c'e' un modo per adottarle: disattiva la vecchia integrazione, poi chiama l'azione **Adotta le entita' dell'installazione omoda_jaecoo** (Strumenti per sviluppatori, Azioni). Lanciala prima con *dry run* acceso, che non cambia niente e ti dice cosa farebbe. 96 entita' su 101 passano col loro storico; le cinque che non possono sono elencate nel rapporto col motivo - due perche' le due linee le hanno fatte di tipo diverso, tre perche' qui non esistono affatto. Niente e' automatico e niente succede se non lo chiedi tu.

- **Hai gia' cancellato la vecchia integrazione `omoda_jaecoo`? Il tuo storico e' ancora li'.** Togliere un'integrazione elimina le sue entita' dal registro di Home Assistant; **non** elimina i dati. Statistiche a lungo termine e cronologia restano nel database, orfane ma intatte, e Home Assistant ricorda ancora tutte le entita' che ha tolto. Adesso c'e' un'azione apposta: **Recupera lo storico da un'installazione omoda_jaecoo rimossa** (Strumenti per sviluppatori, Azioni), che sposta statistiche e cronologia sulle entita' di questa integrazione. Niente da reinstallare, e la vecchia integrazione non serve che esista piu'. Lanciala prima con *dry run* acceso. Un avvertimento sui tempi: il recorder prima o poi ripulisce i dati orfani, quindi si parla di giorni, non di sempre.

- **Il recupero da un'installazione `omoda_jaecoo` adesso porta con se' pure la cronologia degli stati, non solo le statistiche.** Se avevi gia' lanciato il recupero su una beta precedente, rilancialo: riprende quello che era rimasto indietro e non tocca cio' che aveva gia' spostato. La prima volta che ha girato su una migrazione vera, le statistiche a lungo termine sono passate e la cronologia no, per ogni entita' che esisteva gia' col nome nuovo - cioe' tutte, se hai configurato l'integrazione prima di recuperare. I grafici tornavano a luglio, il pannello Cronologia partiva da quella sera. Adesso si spostano entrambe.

- **Il recupero della cronologia adesso la sposta davvero.** Il tentativo precedente cercava di togliere di mezzo la cronologia piu' corta con il purge del recorder, e non funziona: il purge cancella gli stati ma lascia la riga che blocca la rinomina, quindi tutte le entita' fallivano con `already in use` e il rapporto diceva di avercela fatta. Adesso la cronologia corta viene spostata di lato sotto un nome parcheggio invece che cancellata: funziona e non distrugge niente. Se avevi gia' lanciato il recupero, rilancialo.

- **Tre sensori che esistono solo su un'auto elettrica erano rimasti coi vecchi nomi italiani, e non avevano nessuna traduzione.** Potenza di ricarica, autonomia WLTP ed efficienza elettrica nascono solo dopo che l'auto ha confermato di essere solo elettrica, cosa che avviene a configurazione gia' fatta: non c'erano nella tabella dei nomi, e nei file di traduzione non c'erano mai stati. Adesso hanno identificativi inglesi come tutto il resto e un nome in ogni lingua. Se li hai, vengono rinominati da soli al prossimo avvio e lo storico li segue.

- **Lavoro interno: l'integrazione non chiede piu' di installare `requests` e `pillow`.** Home Assistant li include gia' entrambi, e il suo validatore adesso rifiuta un'integrazione custom che li elenca, cosa che avrebbe bloccato questo rilascio. Sulla tua installazione non cambia niente: l'integrazione usa le copie che Home Assistant ha gia'.

## v1.13.0 — 2026-08-10

### 🇬🇧 English

- **The integration now asks your car how it is built, instead of assuming.** A few values were written by hand in the program, because that is how the Omoda 9 it was born on works: how much cold and how much heat the "Cool everything" and "Heat everything" buttons ask for, and how many minutes the climate control should run. On a different car those numbers can differ, and nobody would have noticed. They are now read from the spec sheet the manufacturer sends **along with the car's name**: a response the integration already asked for, so there is no new kind of request to its servers.
- **If you set a duration your car does not accept, we tell you.** The "Climate duration" slider goes up to 30 minutes, but not every car accepts that: the Omoda 9, for one, only allows 5, 10 or 15. Previously it was sent a value it did not understand; now the allowed value **just below** the one you picked is used — never a longer one, that would not be what you asked for — and **you can read it** in the command result, instead of finding out because the car switched off early.
- **On the first start after this update the integration asks the car one extra question, once only.** If you already have the integration installed, its spec sheet was read back when these values were not being collected: without re-reading it, the change above would never have reached existing users. It happens once and never again.
- **A limitation we would rather tell you about.** If your car only allows short durations — say 5 minutes — the car switches the climate control off after 5 minutes, but the switch in Home Assistant stays on for a few more minutes before returning to "off" by itself. Only the switch lags behind: no wrong command is sent, and on an Omoda 9 it does not happen at all. We will fix it calmly, in an update that does not also touch the climate commands.
- **On an Omoda 9 nothing changes at all.** The values the manufacturer declares for this car are exactly the ones that were hard-coded. This update is for the **other** cars in the family: it is one more piece of the work to make the integration run on Jaecoo and on the battery-only models.
- **"Cool everything" and "Heat everything": the last thing you pressed now always wins.** If you switched off and straight back on (or the other way round), the two commands could reach the car **in reverse order**: the car started up and then shut itself down, while the switch stayed on — and trying again it looked as though it would not restart. The reason: before sending the command the integration has to wake the car, and the wait is far longer when the car is asleep; the first press woke it, so the second had less ground to cover and got there first. The overtaken command is now simply dropped: the car only ever receives the last thing you asked for.
- **We now tell you while the car is being woken.** For a good half minute after pressing, nothing appeared: that silence is what made people press again, which is exactly what caused the problem above. "Command result" now shows *"Waking the car: command goes out in ~35 s"*.
- **After a Home Assistant restart the switch no longer stays on for nothing.** Pre-conditioning runs for a quarter of an hour and then the switch turns itself off; but if Home Assistant was restarted in the meantime — or you updated the integration — that reminder was lost and the switch stayed on indefinitely, announcing something the car had already finished. It now picks the countdown up where it left off, and if the quarter of an hour has passed it comes back already off.
- **If switching off fails, the switch no longer claims "off".** When the command could not go out, the switch went to off anyway while the car carried on cooling. It now stays as it was, which is the truth.
- **When the car ends the pre-conditioning, the switch now notices.** "Cool everything" and "Heat everything" did not look at what the car says about itself at all: once the two drifted apart — because you had used the official app, because the car had finished early, or because you switched everything off from the dashboard — the switch stayed on until the quarter of an hour ran out, with no way to put it right other than by hand. Now, when the car reports the climate control is off, the switch follows. **In that direction only**: climate switched on for other reasons will not conjure up a "Cool everything" you never asked for.
- **Switches no longer flip back on their own moments after you press them.** You turned the ventilated seat on, the switch came on, and a few seconds later it went off again while the seat was actually running. It happened because any message from the car — even one that said nothing about that seat, such as the confirmation of the command itself — made the switch fall back to the last measured value, which was the one from before. It now waits for the car to say something **about that function**. This applies to seats, defrosters, steering wheel, door lock, boot, windows, sunroof and to the climate card.
- **A rare lock-up that left the integration mute until a restart.** If a command was interrupted half-way — which happens with automations set to "restart" — its place in the queue was never handed back: from then on every later command, even one pressed days afterwards, failed with "The car is still busy with previous commands", and the only cure was restarting Home Assistant. The place is now always returned.
- **Alarm: after every command we check what it really did.** It is the one function whose state the car never reports on its own: until now the value shown was the one read when Home Assistant started, and it could stay wrong all day. Now, right after you switch the alarm on or off, the integration asks the manufacturer for the current state. **It does not change what you see at that moment**: that stays what you asked for, because the answer comes back before the car has finished acting on it.
- **One wake-up at a time.** A sleeping car has to be woken before it will listen, and pre-conditioning and the automatic refresh could wake it at the same moment, each unaware of the other: the second wake-up arrived for nothing and the car turned it down as "I am busy", delaying the real command. Whoever arrives second now waits for the wake-up already under way.
- **No more alerts when "Cool everything" does what it can.** If you use the ready-made automation that warns you about failed commands (the "Failed command alert" *blueprint*), until yesterday an alert popped up on **every** press of "Cool everything" and "Heat everything": on a parked car the climate control starts but the ventilated seats do not, and that was reported as "carried out only in part". It is not a fault, it is how the car works — and an alert that always shows up and asks nothing of you only teaches you to ignore the real ones too. You now get the popup **only when a command genuinely fails to go out**. If you care about that detail there is a new option to bring it back, and it is written in "Command result" either way.
- **Command warnings no longer vanish in a flash.** When the integration corrects or skips something before sending a command — a duration your car does not accept, a function the manufacturer does not authorise — it writes so in "Command result". Except that the message was immediately covered by the next step: **measured on the car, it stayed readable for 12 thousandths of a second.** It was written, but nobody could read it. It now stays attached to the command's result and survives the confirmation the car sends a few seconds later. If there are many warnings and they do not all fit in the space available, we tell you **how many are left out** rather than cutting one in half: a truncated warning looks complete, which is worse than a missing one. On an Omoda 9 with normal settings nothing new appears — warnings only come out when there is genuinely something to say.

### 🇮🇹 Italiano

- **L'integrazione ora chiede alla tua auto com'è fatta, invece di darlo per scontato.** Alcuni valori erano scritti a mano nel programma perché era così che funzionava l'Omoda 9 su cui è nata: quanto freddo e quanto caldo chiedere con i pulsanti «Raffredda tutto» e «Riscalda tutto», e quanti minuti far durare il climatizzatore. Su un'altra vettura quei numeri possono essere diversi, e nessuno se ne sarebbe accorto. Adesso li legge dalla scheda tecnica che il costruttore invia **insieme al nome dell'auto**: è una risposta che l'integrazione si faceva già mandare, quindi non c'è nessun nuovo tipo di domanda ai server del costruttore.
- **Se imposti una durata che la tua auto non accetta, te lo diciamo.** Il cursore «Durata clima» arriva a 30 minuti, ma non tutte le vetture li accettano: l'Omoda 9, per esempio, ammette solo 5, 10 o 15 minuti. Prima le veniva chiesto un valore che non capiva; adesso si usa il valore ammesso **subito inferiore** a quello che hai scelto — mai uno più lungo, non sarebbe ciò che hai chiesto — e **lo trovi scritto** nell'esito del comando, invece di scoprirlo dal fatto che l'auto si spegne prima.
- **Al primo avvio dopo l'aggiornamento l'integrazione fa una domanda in più all'auto, una volta sola.** Chi ha già l'integrazione installata aveva la scheda tecnica letta con le informazioni di allora, che non comprendevano questi valori: senza rileggerla, la novità qui sopra non sarebbe mai arrivata a chi c'è già. Succede una volta e poi non più.
- **Un limite che preferiamo dirti.** Se la tua auto ammette durate brevi — mettiamo 5 minuti — l'auto spegne il climatizzatore dopo 5 minuti, ma l'interruttore in Home Assistant resta acceso ancora per qualche minuto prima di tornare da solo su «spento». È solo l'interruttore a essere indietro: nessun comando sbagliato parte, e sull'Omoda 9 non capita affatto. Lo sistemeremo con calma, in un aggiornamento che non tocchi anche i comandi del clima.
- **Su un'Omoda 9 non cambia assolutamente nulla.** I valori che il costruttore dichiara per questa vettura sono esattamente quelli che c'erano scritti a mano. Questo aggiornamento serve alle **altre** auto della famiglia: è un pezzo del lavoro per far funzionare l'integrazione anche su Jaecoo e sui modelli solo elettrici.
- **«Raffredda tutto» e «Riscalda tutto»: ora vale sempre l'ultima cosa che hai premuto.** Se spegnevi e subito riaccendevi (o il contrario), i due comandi potevano arrivare all'auto **in ordine invertito**: l'auto partiva e poi si spegneva da sola, mentre l'interruttore restava acceso — e riprovando sembrava che non ripartisse più. Il motivo: prima di mandare il comando l'integrazione deve svegliare l'auto, e l'attesa è molto più lunga se l'auto dorme; la prima pressione la sveglia, così la seconda faceva meno strada e arrivava per prima. Adesso il comando sorpassato viene semplicemente lasciato cadere: all'auto arriva solo l'ultima cosa che hai chiesto.
- **Mentre l'auto si sveglia adesso te lo diciamo.** Per una mezza minuto buono, dopo aver premuto, non compariva nulla: era il silenzio a far ripremere il tasto, cioè proprio la causa del problema qui sopra. Ora nell'«Esito comando» compare *«Sveglio l'auto: il comando parte fra ~35 secondi»*.
- **Dopo un riavvio di Home Assistant l'interruttore non resta più acceso a vuoto.** La preclimatizzazione dura un quarto d'ora e poi l'interruttore si spegne da solo; ma se nel frattempo Home Assistant veniva riavviato — o aggiornavi l'integrazione — quel promemoria andava perso e l'interruttore restava acceso a tempo indeterminato, annunciando qualcosa che l'auto aveva già finito. Ora riprende il conto da dove era rimasto, e se nel frattempo il quarto d'ora è passato si presenta già spento.
- **Se lo spegnimento non riesce, l'interruttore non dice più «spento».** Quando il comando non riusciva a partire, l'interruttore si metteva comunque su spento mentre l'auto continuava tranquillamente a raffreddare. Adesso resta com'era, che è la verità.
- **Quando l'auto spegne la preclimatizzazione, l'interruttore adesso se ne accorge.** «Raffredda tutto» e «Riscalda tutto» non guardavano affatto quello che l'auto racconta di sé: se i due si disallineavano — perché avevi usato l'app ufficiale, perché l'auto aveva finito prima, o perché avevi spento tutto dal cruscotto — l'interruttore restava acceso fino allo scadere del quarto d'ora, e non c'era modo di rimetterlo a posto se non a mano. Ora, quando l'auto comunica che il climatizzatore è spento, l'interruttore la segue. **Solo in quel verso**: il clima acceso per altri motivi non fa comparire da solo un «Raffredda tutto» che non hai chiesto.
- **Gli interruttori non tornano più indietro da soli subito dopo averli premuti.** Accendevi il sedile ventilato, l'interruttore si accendeva, e pochi secondi dopo tornava spento pur essendo il sedile acceso. Succedeva perché bastava un messaggio qualsiasi dell'auto — anche uno che non parlava affatto di quel sedile, come la conferma del comando stesso — per far ricadere l'interruttore sull'ultimo valore misurato, che era quello di prima. Adesso si aspetta che l'auto dica qualcosa **su quella funzione**. Vale per sedili, sbrinamenti, volante, serratura, baule, finestrini, tetto e per la scheda del clima.
- **Un blocco raro che rendeva l'integrazione muta fino al riavvio.** Se un comando veniva interrotto a metà — capita con le automazioni impostate su «riavvia» — il posto in coda non veniva più restituito a nessuno: da quel momento ogni comando successivo, anche premuto giorni dopo, falliva con «L'auto è ancora impegnata coi comandi precedenti» e l'unico rimedio era riavviare Home Assistant. Ora il posto torna libero in ogni caso.
- **Antifurto: dopo ogni comando ricontrolliamo com'è messo davvero.** È l'unica funzione di cui l'auto non manda mai lo stato da sola: finora il valore mostrato era quello letto all'avvio di Home Assistant, e poteva restare sbagliato per tutta la giornata. Adesso, subito dopo aver acceso o spento l'antifurto, l'integrazione richiede al costruttore lo stato aggiornato. **Non cambia quello che vedi sul momento**: quello resta ciò che hai chiesto, perché la risposta arriva prima che l'auto abbia finito di eseguire.
- **Una sola sveglia alla volta.** Quando l'auto dorme va svegliata prima di poterle parlare, e capitava che la preclimatizzazione e l'aggiornamento automatico la svegliassero nello stesso momento, ciascuno per conto suo: la seconda sveglia arrivava a vuoto e l'auto la rifiutava come «sono occupata», rallentando il comando vero. Adesso chi arriva secondo aspetta la sveglia già in corso.
- **Niente più avvisi quando «Raffredda tutto» fa quel che può.** Se usi l'automazione pronta che ti avverte dei comandi non riusciti (il *blueprint* «Avviso comando non riuscito»), fino a ieri ti compariva un avviso a **ogni** pressione di «Raffredda tutto» e «Riscalda tutto»: l'auto ferma accende il climatizzatore ma non i sedili ventilati, e questo veniva segnalato come «eseguito solo in parte». Non è un guasto, è come funziona l'auto — e un avviso che compare sempre e non chiede niente insegna solo a ignorare anche quelli veri. Adesso ricevi il popup **solo quando un comando non parte davvero**. Se quel dettaglio ti interessa c'è una nuova opzione per riaverlo, ed è comunque sempre scritto in «Esito comando».
- **Gli avvisi dei comandi non spariscono più in un lampo.** Quando l'integrazione corregge o salta qualcosa prima di mandare un comando — una durata che la tua auto non accetta, una funzione che il costruttore non autorizza — te lo scrive in «Esito comando». Solo che quel messaggio veniva subito coperto dal passaggio successivo: **misurato sull'auto, restava leggibile 12 millesimi di secondo.** Era scritto, ma nessuno poteva leggerlo. Adesso resta attaccato all'esito del comando e sopravvive anche alla conferma che l'auto manda qualche secondo dopo. Se gli avvisi sono tanti e non entrano tutti nello spazio disponibile, ti diciamo **quanti ne restano fuori** invece di troncarne uno a metà: un avviso tagliato sembra completo, ed è peggio di un avviso assente. Su un'Omoda 9 con le impostazioni normali non compare nulla di nuovo — gli avvisi escono solo quando c'è davvero qualcosa da dire.

## v1.12.1 — 2026-08-10

### 🇬🇧 English

- **New sensor: "Scheduled departure".** The car was already sending us, on every connection, the departure plan you set in the official app — time and days — and we were throwing it away without looking. You can now see it in Home Assistant: the time, the days of the week, and whether the plan is on or off. **It is read-only**: to change the plan you still use the app. It adds no request to the manufacturer's servers, because the data was already arriving.
- **Scheduled charging also shows the plan the car actually holds.** Until now the switch showed only the preferences set in here: if you changed the schedule from the official app, Home Assistant never knew. Now, when the car reports its plan, you get time, duration and days **as the car has them**. They appear when the car sends them, that is when something changes: their absence does not mean there is no plan.
- **One date we deliberately do not show you.** The departure plan arrives with a "created on" and a "modified on" that look like they say when you set it. They do not: the manufacturer rewrites them on every query, which is why they are always a few seconds old. We left them out, because an invented figure that looks authoritative is worse than a missing one.

### 🇮🇹 Italiano

- **Nuovo sensore: «Partenza programmata».** L'auto ci mandava già, a ogni collegamento, il piano di partenza impostato dall'app ufficiale — orario e giorni — e noi lo buttavamo via senza guardarlo. Ora lo vedi in Home Assistant: l'orario, i giorni della settimana e se il piano è attivo o spento. **È solo una lettura**: per cambiare il piano si usa ancora l'app. Non aggiunge nessuna richiesta ai server del costruttore, perché è un dato che arrivava già.
- **La ricarica programmata mostra anche il piano che ha davvero l'auto.** Finora l'interruttore mostrava soltanto le preferenze impostate qui dentro: se cambiavi la programmazione dall'app ufficiale, Home Assistant non lo sapeva. Adesso, quando l'auto comunica il suo piano, trovi orario, durata e giorni **come li ha lei**. Compaiono quando l'auto li manda, cioè quando qualcosa cambia: se non ci sono, non vuol dire che non ci sia un piano.
- **Una data che non ti mostriamo, di proposito.** Il piano di partenza arriva accompagnato da un «creato il» e un «modificato il» che sembrano dire quando l'hai impostato. Non lo dicono: il costruttore li riscrive a ogni interrogazione, e infatti risultano sempre di pochi secondi fa. Li abbiamo lasciati fuori, perché un dato inventato che sembra autorevole è peggio di un dato assente.

## v1.12.0 — 2026-08-10

### 🇬🇧 English

- **New switch: "Windshield defog".** The car can do two different things to the front glass, and until now the integration offered only one. The existing "Windshield defrost" **heats the glass** with its electric elements. This new one instead blows **the climate system's air onto the windshield**, which is the quick way to clear condensation. They are separate commands and the car keeps them apart.
- ⚠️ **Worth knowing before you use it: it also switches the climate control on** for about 15 minutes, because it is the climate system itself that blows the air onto the glass. This is not a fault, it is how the car works. For the same reason, switching the defog off switches the climate off.
- **Alarm: if your car does not authorise it, you are now told up front.** On some vehicles the manufacturer does not enable the alarm commands at all. You used to get only an error, indistinguishable from a malfunction. The integration now tells you it is the manufacturer withholding the function — so you do not go hunting for a problem that is not there.
- **Scheduled charging: a warning when the chosen days are not allowed.** Some cars accept scheduling on every day of the week only, others only on selected days. If yours does not accept the one the integration is about to send, it now says so beforehand instead of leaving you with an unexplained refusal. **It does not change the days for you**: a charge starting on a day you did not pick would be worse than an honest error.
- **A clarification on an old note of ours, for those who read the code.** A thorough review raised the suspicion that scheduled charging might start one or two hours away from the time you set. **The suspicion was checked and is unfounded: the time was and is correct.** Nothing changes in how it works; we corrected the internal note that caused the doubt.

### 🇮🇹 Italiano

- **Nuovo interruttore: «Disappannamento parabrezza».** L'auto sa fare due cose diverse sul vetro davanti, e finora l'integrazione ne offriva una sola. Quella che c'era già, «Sbrinamento parabrezza», **scalda il vetro** con le resistenze elettriche. Questa nuova soffia invece **l'aria del climatizzatore sul parabrezza**, che è il modo rapido per togliere la condensa. Sono comandi distinti e l'auto li tiene separati.
- ⚠️ **Da sapere prima di usarlo: accende anche il climatizzatore** per circa 15 minuti, perché è il climatizzatore stesso a soffiare l'aria sul vetro. Non è un difetto, è come funziona sull'auto. Per lo stesso motivo, spegnere il disappannamento spegne il clima.
- **Antifurto: se la tua auto non lo autorizza, ora te lo dice prima.** Su alcune vetture il costruttore non abilita affatto i comandi dell'antifurto. Prima ricevevi solo un errore, identico a quello di un guasto. Ora l'integrazione ti avvisa che è il costruttore a non permettere quella funzione — così non perdi tempo a cercare un problema che non c'è.
- **Ricarica programmata: avviso quando i giorni scelti non sono ammessi.** Alcune auto accettano solo la programmazione su tutti i giorni della settimana, altre solo su giorni scelti. Se la tua non ammette quella che l'integrazione sta per mandare, adesso lo dice prima invece di lasciarti davanti a un rifiuto senza spiegazione. **Non cambia i giorni al posto tuo**: una ricarica che parte in un giorno che non hai scelto sarebbe peggio di un errore onesto.
- **Un chiarimento su una nostra vecchia nota, per chi legge il codice.** Una verifica approfondita ha fatto sospettare che l'orario della ricarica programmata partisse spostato di un'ora o due rispetto a quello impostato. **Il sospetto è stato controllato ed è infondato: l'orario era ed è corretto.** Nulla cambia nel funzionamento; abbiamo corretto la nota interna che aveva dato origine al dubbio.

## v1.11.1 — 2026-08-10

### 🇬🇧 English

- **A fix to yesterday's feature: on some cars it never kicked in at all.** To decide whether to change route, the integration looked only at the individual function and not at the whole category. On a car whose permission list is shorter — one that does not list the individual functions but denies the group as a whole — it concluded the usual road was open and never tried the alternative: the function stayed broken **on exactly the cars this feature was written for**. It now looks at both.
- **And when nothing can be done, it now says so.** If the manufacturer does not authorise a function on your car at all, there is nothing to remove and no alternative road: you used to get the same error as always, with no way to tell why the update had changed nothing. The integration now says it plainly.

### 🇮🇹 Italiano

- **Correzione alla novità di ieri: su alcune auto non si attivava affatto.** Per decidere se cambiare strada, l'integrazione guardava solo la singola funzione e non l'intera categoria. Su un'auto il cui elenco dei permessi è più corto — cioè che non elenca le singole funzioni ma nega il gruppo intero — concludeva che la strada abituale fosse aperta e non provava quella alternativa: la funzione restava rotta **proprio sulle auto per cui questa novità era stata scritta**. Ora guarda tutte e due.
- **E quando non c'è nulla da fare, adesso te lo dice.** Se il costruttore non autorizza affatto una funzione sulla tua auto, non c'è niente da togliere e nessuna strada alternativa: prima ricevevi lo stesso errore di sempre, senza capire perché l'aggiornamento non avesse cambiato niente. Ora l'integrazione lo scrive chiaramente.

## v1.11.0 — 2026-08-10

### 🇬🇧 English

- **Commands no longer stop at the first obstacle.** Every car has a list, set by the manufacturer, of what may be controlled remotely — and it differs from model to model. Until now the integration ignored it: if even one of the functions a command carries was not enabled on your car, the manufacturer rejected **the whole command**, including the parts your car could perform perfectly well. You pressed "Heat everything" and nothing happened. The integration now asks the car what it is allowed to do and **removes only the parts that are not enabled**: the rest goes through and works. If something was skipped it tells you, instead of letting you believe it was done.
- **And if a function exists but goes down another road, it takes it.** Some cars enable seat heating or rear-window defrosting through a different route than the one the integration always used. That used to be a dead end: the command failed even though the car could do it, and the official app managed fine. Now, when the usual road is closed, the integration tries the open one — the same the app uses. Going that way also switches the climate on: it tells you, so it is not a surprise.
- **If something goes wrong, nothing is taken away from you.** If the list cannot be read — because the manufacturer's service is not answering, for instance — the integration behaves **exactly as before** and sends the command in full. No function ever disappears because of a network problem.
- **If you have an Omoda 9 you will notice no difference:** on that car everything the integration uses is already enabled, so there is nothing to remove and no road to change. Same commands, same results, same entities as before.
- Thanks to **ThomasMeyer1970** and his Jaecoo 7, where this whole investigation started.

### 🇮🇹 Italiano

- **I comandi non si fermano più al primo ostacolo.** Ogni auto ha un elenco, deciso dal costruttore, di ciò che si può comandare a distanza — e cambia da modello a modello. Finora l'integrazione lo ignorava: se anche una sola delle funzioni che un comando porta con sé non era abilitata sulla tua auto, il costruttore rifiutava **tutto il comando**, comprese le parti che la tua auto sapeva fare benissimo. Premevi «Riscalda tutto» e non succedeva niente. Adesso l'integrazione chiede all'auto cosa le è permesso e **toglie dal comando solo i pezzi non abilitati**: il resto parte e funziona. Se qualcosa è stato saltato te lo dice, invece di lasciartelo credere fatto.
- **E se una funzione c'è ma passa da un'altra strada, la usa.** Alcune auto abilitano il riscaldamento dei sedili o lo sbrinamento del lunotto per una via diversa da quella che l'integrazione usava sempre. Prima era un muro: il comando falliva anche se l'auto quella cosa la sapeva fare, e dall'app ufficiale funzionava. Ora, quando la strada abituale è chiusa, l'integrazione prova quella aperta — la stessa che usa l'app. Quando passa di lì si accende anche il clima: te lo scrive, così non è una sorpresa.
- **Se qualcosa non funziona, non ti toglie niente.** Se l'elenco non si riesce a leggere — per esempio perché il servizio del costruttore non risponde — l'integrazione si comporta **esattamente come prima**, mandando il comando per intero. Nessuna funzione sparisce mai per colpa di un problema di rete.
- **Chi ha una Omoda 9 non nota alcuna differenza:** su quell'auto tutto ciò che l'integrazione usa è già abilitato, quindi non c'è niente da togliere e niente da cambiare di strada. Stessi comandi, stessi risultati, stesse entità di prima.
- Grazie a **ThomasMeyer1970** e alla sua Jaecoo 7, da cui è partita tutta questa indagine.

## v1.10.1 — 2026-08-09

### 🇬🇧 English

- **An error message that sent you the wrong way.** When the car refuses a command because the manufacturer has not enabled that function on that vehicle, the integration used to say "command PIN rejected — reconfigure it in the settings": you ended up re-entering a PIN that was already correct, and nothing got fixed. It now says clearly that **this is not your PIN** and that the function is not authorised on that car. The message is written in both Italian and English, so it reads anywhere. Nothing else changes: commands that worked keep working exactly as before. The problem came to light thanks to **ThomasMeyer1970**, who has a Jaecoo 7 on which some comfort commands are not enabled by the manufacturer.
- **The project has moved to a shared organisation on GitHub.** The project address has changed: the links to the documentation and to issue reporting — the ones on the integration's page inside Home Assistant — now point to the new address. There is nothing for you to do: updating through HACS keeps working exactly as before and your setup is left untouched.

### 🇮🇹 Italiano

- **Un messaggio d'errore che mandava fuori strada.** Quando l'auto rifiuta un comando perché il costruttore non ha abilitato quella funzione su quel veicolo, l'integrazione diceva «PIN comandi rifiutato — riconfiguralo nelle impostazioni»: si finiva a reinserire un PIN che era già giusto, senza risolvere niente. Ora dice chiaramente che **non è il PIN** e che quella funzione non è autorizzata su quell'auto. Il messaggio è scritto in italiano e in inglese, così si legge ovunque. Per il resto non cambia nulla: i comandi che funzionavano continuano a funzionare esattamente come prima. Il problema è emerso grazie a **ThomasMeyer1970**, che ha una Jaecoo 7 dove alcuni comandi di comfort non sono abilitati dal costruttore.
- **Il progetto si è trasferito in un'organizzazione condivisa su GitHub.** È cambiato l'indirizzo del progetto: i collegamenti alla documentazione e alla segnalazione dei problemi — quelli che trovi nella scheda dell'integrazione dentro Home Assistant — ora portano al nuovo indirizzo. Da parte tua non c'è niente da fare: l'aggiornamento da HACS continua a funzionare come sempre e la tua configurazione resta intatta.

## v1.10.0 — 2026-08-09

### 🇬🇧 English

- **The integration now adapts to fully electric cars.** Until now it was tailored to the Omoda 9, which also has a petrol engine: on a pure EV the fuel gauges showed up anyway and stayed empty forever. The integration now asks the car what kind of engine it has and adjusts by itself: on a fully electric car those gauges are gone, and in their place you get **charging power**, the **official WLTP range** and **efficiency**. Total range, which on a hybrid is electric plus petrol, on an EV is simply the electric range.
- **The climate temperature uses your car's real limits.** The slider used to be fixed at 16 to 30 degrees for everyone; now, when the car declares them, its own limits are used (some models have different ends, or half-degree steps instead of full ones).
- **Speed can be shown in miles per hour.** For anyone running Home Assistant with imperial units: it used to be locked to km/h.
- **If you have an Omoda 9 or a hybrid Jaecoo you will notice no difference:** the adaptation only kicks in when the car explicitly declares itself electric, never by assumption. When in doubt, everything stays as it was.
- Thanks to **JackRonan**, author of the English version of this integration ([omoda-jaecoo-ha](https://github.com/JackRonan/omoda-jaecoo-ha)), who carried the work forward on the Omoda E5 and from whose fork these improvements come.

### 🇮🇹 Italiano

- **Ora l'integrazione si adatta alle auto solo elettriche.** Fin qui era tarata sull'Omoda 9, che ha anche il motore a benzina: su un'auto puramente elettrica comparivano lo stesso i contatori del carburante, e restavano vuoti per sempre. Adesso l'integrazione chiede all'auto che tipo di motore ha, e si regola da sola: se è solo elettrica quei contatori non compaiono più, e al loro posto arrivano la **potenza di ricarica**, l'**autonomia dichiarata WLTP** e l'**efficienza**. L'autonomia totale, che sulle ibride è elettrica più benzina, su un'elettrica è semplicemente l'autonomia elettrica.
- **La temperatura del clima usa i limiti veri della tua auto.** Prima il cursore era fisso da 16 a 30 gradi per tutti; ora, quando l'auto li dichiara, si usano i suoi (alcuni modelli hanno estremi diversi, o mezzo grado di scatto invece di uno).
- **La velocità si può vedere in miglia orarie.** Per chi usa Home Assistant con le unità britanniche: prima era bloccata in km/h.
- **Chi ha una Omoda 9 o una Jaecoo ibrida non nota alcuna differenza:** l'adattamento scatta solo quando l'auto dichiara esplicitamente di essere elettrica, mai per esclusione. In caso di dubbio resta tutto com'era.
- Grazie a **JackRonan**, autore della versione inglese dell'integrazione ([omoda-jaecoo-ha](https://github.com/JackRonan/omoda-jaecoo-ha)), che ha portato avanti il lavoro sull'Omoda E5 e da cui arrivano queste migliorie.

## v1.9.0 — 2026-08-02

### 🇬🇧 English

- **You can now change how you receive the code.** Under "Configure" you choose whether the code is sent by **email** or by **SMS**, and you can correct the address or the number. Before, the channel stayed the one picked at first setup, and the only way to change it was to delete and re-add the integration.

### 🇮🇹 Italiano

- **Ora puoi cambiare come ricevere il codice.** In «Configura» scegli se farti mandare il codice via **email** o via **SMS**, e puoi correggere l'indirizzo o il numero. Prima il canale restava quello scelto alla prima configurazione e l'unico modo di cambiarlo era eliminare e riaggiungere l'integrazione.

## v1.8.0 — 2026-08-02

### 🇬🇧 English

- **You can now sign in with your phone number.** If your Omoda/Jaecoo account is registered with a phone number instead of an email address, pick "Sign in with phone number": the verification code arrives by **SMS**.

### 🇮🇹 Italiano

- **Ora si può accedere con il numero di telefono.** Se il tuo account Omoda/Jaecoo è registrato con un numero invece che con un indirizzo email, scegli «Accedi con numero di telefono»: il codice di verifica ti arriva via **SMS**.

## v1.7.2 — 2026-08-02

### 🇬🇧 English

- **The integration finally has its own logo.** The OMODA | JAECOO mark now shows up in HACS and on the Home Assistant integrations page, instead of an empty box. A light version is included for anyone on a dark theme, so it reads well either way.

### 🇮🇹 Italiano

- **L'integrazione ha finalmente il suo logo.** Il marchio OMODA | JAECOO compare adesso in HACS e nella pagina delle integrazioni di Home Assistant, al posto del riquadro vuoto. C'è anche la versione chiara per chi usa il tema scuro, così si vede bene in entrambi i casi.

## v1.7.1 — 2026-08-02

### 🇬🇧 English

- **The battery percentage no longer drops back on its own.** Right after charging ends the car shuts down its electrical system and sends one last "empty" reading: the percentage in it is wrong, and it used to stay on screen for hours. You could see 97% in Home Assistant while the car itself showed 100%. Those readings are now recognised and discarded.
- **Same for the range.** The electric range no longer falls to 0 km, and the total range no longer loses a hundred kilometres at once, just because the car is resting.
- **When a reading is missing, the last real one is kept.** Before, an old value could reappear — the one frozen at the last Home Assistant restart. Now it always falls back to the most recent reading actually received from the car.
- **"Cool everything" and "Heat everything" start much sooner.** If the car is already awake the command goes out almost immediately, instead of always waiting nearly a minute: that wait was only there to rouse a sleeping car, and now it happens only when it is actually needed.
- **No more "car busy" error when you press twice.** People who saw nothing happening pressed again, the two commands overlapped and the car rejected the second one. Now the second command really does wait its turn.
- **The final message tells it straight.** When the car starts the climate control but not the ventilated seats, you now read that the command only partly succeeded and which parts refused, instead of a generic alarm followed by a string of numbers.
- **No more false alarm when you switch the climate off.** On every switch-off the car sends a note about the climate control that reports no fault at all: it was being read as a problem, so a warning appeared even when everything had gone perfectly. That note on its own no longer raises any alarm.
- **The seats have names.** In the summary of a partly successful command you now read "driver seat heating" or "driver seat ventilation" instead of an anonymous "module 4".

### 🇮🇹 Italiano

- **La carica della batteria non torna più indietro da sola.** Appena finita la ricarica l'auto spegne l'impianto elettrico e manda un'ultima lettura "a vuoto": la percentuale che contiene è sbagliata e restava lì per ore. Capitava di vedere 97% in Home Assistant mentre sull'auto c'era 100%. Ora quelle letture vengono riconosciute e scartate.
- **Stessa cosa per l'autonomia.** L'autonomia elettrica non scende più a 0 km, e quella totale non perde di colpo un centinaio di chilometri, quando l'auto è solo a riposo.
- **Quando un dato manca, si tiene l'ultimo vero.** Prima in quei casi poteva ricomparire un valore vecchio, fermo all'ultimo riavvio di Home Assistant: ora si torna sempre all'ultima lettura davvero arrivata dall'auto.
- **«Raffredda tutto» e «Riscalda tutto» partono molto prima.** Se l'auto è già sveglia il comando parte quasi subito, invece di aspettare quasi un minuto come faceva sempre: quell'attesa serviva solo a svegliare un'auto addormentata, e ora si fa soltanto quando serve davvero.
- **Basta l'errore «auto occupata» quando si preme due volte.** Chi non vedeva succedere nulla ripremeva il tasto, i due comandi si accavallavano e l'auto rifiutava il secondo. Ora il secondo comando aspetta sul serio il suo turno.
- **Il messaggio finale dice le cose come stanno.** Quando l'auto avvia il clima ma non i sedili ventilati, ora si legge che il comando è riuscito solo in parte e quali parti hanno fatto storie, invece di un allarme generico seguito da una sfilza di numeri.
- **Niente più falso allarme quando si spegne il clima.** Spegnendo, l'auto manda sempre una nota sul clima che non segnala alcun guasto: veniva scambiata per un problema, così compariva un avviso anche quando tutto era andato benissimo. Ora quella nota, da sola, non fa più scattare nessun allarme.
- **I sedili hanno un nome.** Nel riepilogo di un comando riuscito a metà si legge «sedile guida riscaldato» o «sedile guida ventilato» invece di un anonimo «modulo 4».

## v1.7.0 — 2026-07-22

### 🇬🇧 English

- **No more verification codes you didn't ask for.** When the connection to the car expired, the integration emailed a code by itself — and did it again at every Home Assistant restart. Now no code is sent unless you ask for one.
- **Re-authentication without dead ends.** The page lets you choose between "Send me a new code" and "I already have a code", and after a wrong code it takes you back there, so you can always request another.
- **A notification when you need to step in.** If the connection expires, a notification explains what to do, and it disappears on its own once everything is back.
- **A more stable connection.** It renews hours in advance instead of at the last moment, stops insisting when the car service refuses, and a flaky connection no longer makes you waste a code.
- **The "Wake car" button works again.** In some cases it replied "car already awake" and did nothing.
- **More honest sensors.** "Car data updated" now marks when the data really changes; "Combined range" was actually the petrol range in miles and has been renamed and corrected; "Remaining charge time" returns to "unknown" when not charging.
- **More privacy.** The car's location no longer ends up in history, in the diagnostics file or in the technical log: it only feeds the map.

### 🇮🇹 Italiano

- **Basta codici di verifica non richiesti.** Quando il collegamento con l'auto scadeva, l'integrazione spediva un'email col codice da sola — e lo rifaceva a ogni riavvio di Home Assistant. Ora nessun codice parte se non lo chiedi tu.
- **Riautenticazione senza vicoli ciechi.** La pagina ti fa scegliere fra «Inviami un codice nuovo» e «Ho già un codice», e dopo un codice sbagliato ti riporta lì: puoi sempre chiederne un altro.
- **Un avviso quando serve il tuo intervento.** Se il collegamento scade compare una notifica che spiega cosa fare, e sparisce da sola quando tutto torna a posto.
- **Collegamento più stabile.** Si rinnova con ore di anticipo invece che all'ultimo momento, non insiste quando il servizio dell'auto rifiuta, e una connessione ballerina non ti fa più sprecare un codice.
- **Il pulsante «Sveglia auto» torna a funzionare.** In certi casi rispondeva «auto già sveglia» senza fare nulla.
- **Sensori più onesti.** «Dati auto aggiornati» ora segna quando i dati cambiano davvero; «Autonomia combinata» era in realtà l'autonomia a benzina in miglia ed è stata rinominata e corretta; «Tempo di ricarica residuo» torna a "sconosciuto" fuori dalla ricarica.
- **Più riservatezza.** La posizione dell'auto non finisce più nello storico, nel file di diagnostica né nel registro tecnico: continua ad alimentare solo la mappa.

## v1.6.1 — 2026-07-20

### 🇬🇧 English

- **Cleaner startup and faster Home Assistant shutdown.** At startup the integration
  loaded and then immediately reloaded itself a second time, while fetching your car's
  name. That was wasted work, and it could also **slow down Home Assistant's shutdown or
  restart** if it happened at the wrong moment. The integration now reloads **only when
  it actually needs to**, that is when you change the settings yourself.
- Changing the command PIN also caused two reloads in a row: now just one. Nothing
  changes in what you see, it is simply tidier and faster.
- **Fixed a defect in the internal diagnostic tooling** — the tooling the integration's
  developer can switch on to investigate a reported problem. In some cases the file it
  produces could contain the **car's location** instead of omitting it as intended. That
  tooling stays switched off unless deliberately enabled, so in all likelihood this never
  affected you — but if you were ever asked to send a diagnostic file, from this version
  it is properly redacted again, as promised.

### 🇮🇹 Italiano

- **Avvio più pulito e spegnimento più rapido di Home Assistant.** All'avvio
  l'integrazione si caricava e, subito dopo, si ricaricava una seconda volta da sola:
  succedeva mentre andava a recuperare il nome della tua auto. Un lavoro inutile, che in
  più poteva **rallentare lo spegnimento o il riavvio di Home Assistant** se capitava
  nel momento sbagliato. Ora l'integrazione si ricarica **solo quando serve davvero**,
  cioè quando cambi tu le impostazioni.
- Anche cambiando il PIN dei comandi l'integrazione si ricaricava due volte di fila:
  ora una sola. Non cambia nulla in ciò che vedi, è tutto più ordinato e veloce.
- **Corretto un difetto negli strumenti interni di diagnostica**, quelli che chi sviluppa
  l'integrazione può accendere per indagare un problema segnalato. In certi casi il file
  che producono poteva contenere la **posizione dell'auto** invece di ometterla come
  previsto. Quegli strumenti restano spenti a meno che non vengano attivati apposta,
  quindi con ogni probabilità non ti ha mai riguardato — ma se ti fosse mai stato chiesto
  di inviare un file di diagnostica, da questa versione è di nuovo oscurato come promesso.

## v1.6.0 — 2026-07-20

### 🇬🇧 English

- **Major internal clean-up: nothing changes in what you see and use.** No new features,
  no buttons moved, no entities added or removed. What changed is how the integration is
  written under the hood.
- **Why we did it.** Some serious problems seen in recent months — the PIN locking itself
  out, automatic updates that kept polling the car even when switched off, the wrong error
  message sending you to change a PIN that was actually correct — had been fixed one by
  one. We have now changed the foundations so that this *kind* of problem **can no longer
  happen at all**, rather than fixing it each time it appears.
- **The most important change is invisible.** The integration now has a battery of **184
  automated checks** that verify on their own, in a few seconds, that everything works:
  commands, sign-in, telemetry, warnings, even the exact count of the 105 entities.
  Previously the only way to test a change was **to try it on the real car**. That is no
  longer needed: future changes arrive already verified.
- **Groundwork for multiple cars on the same Home Assistant.** Not enabled yet, but the
  technical obstacle that prevented it has been removed.
- **A little more privacy.** Your PIN and email address no longer pass through an area of
  memory that other installed integrations could read.
- **You can update safely:** behaviour is identical to before.

### 🇮🇹 Italiano

- **Grande lavoro di riordino interno: non cambia nulla in ciò che vedi e usi.** Nessuna
  funzione nuova, nessun pulsante spostato, nessuna entità in più o in meno. Cambia il
  modo in cui l'integrazione è scritta sotto il cofano.
- **Perché l'abbiamo fatto.** Alcuni problemi seri visti nei mesi scorsi — il PIN che si
  bloccava da solo, gli aggiornamenti automatici che continuavano a interrogare l'auto
  anche da spenti, il messaggio d'errore sbagliato che ti mandava a cambiare un PIN in
  realtà corretto — erano stati sistemati uno per uno. Ora abbiamo cambiato le fondamenta
  perché quel genere di problema **non possa più ripresentarsi**, invece di correggerlo
  ogni volta che salta fuori.
- **La novità più importante non si vede.** L'integrazione ha ora una batteria di **184
  controlli automatici** che verificano da soli, in pochi secondi, che tutto funzioni:
  comandi, accesso, telemetria, avvisi e persino il conteggio esatto delle 105 entità.
  Prima l'unico modo di provare una modifica era **provarla sull'auto vera**. Da oggi non
  serve più: le modifiche future arrivano già verificate.
- **Preparato il supporto a più auto sullo stesso Home Assistant.** Non è ancora attivo,
  ma l'ostacolo tecnico che lo impediva è stato rimosso.
- **Un po' più di riservatezza.** Il PIN e l'indirizzo email non transitano più in una
  zona di memoria che altre integrazioni installate potevano leggere.
- **Puoi aggiornare tranquillamente:** il comportamento è identico a prima.

## v1.5.29 — 2026-07-19

### 🇬🇧 English

- **Maintenance update: nothing changes for you.** No new features and no visible fixes — just a
  refinement to the integration developer's internal tooling. It stays switched off and does not
  affect how anything works: you can update safely.

### 🇮🇹 Italiano

- **Aggiornamento di manutenzione: per te non cambia nulla.** Nessuna nuova funzione e nessuna
  correzione visibile: solo una rifinitura agli strumenti interni di chi sviluppa l'integrazione.
  Restano spenti e non influiscono sul funzionamento: puoi aggiornare tranquillamente.

## v1.5.28 — 2026-07-19

### 🇬🇧 English

- **Maintenance update: nothing changes for you.** No new features and no visible fixes. This
  release only adds internal tooling that helps the integration's developer investigate reported
  problems. It stays switched off and has no effect whatsoever on behaviour or resource usage —
  you can update safely.

### 🇮🇹 Italiano

- **Aggiornamento di manutenzione: per te non cambia nulla.** Non ci sono nuove funzioni né
  correzioni visibili. Questa versione aggiunge solo strumenti interni che aiutano chi sviluppa
  l'integrazione a capire meglio i problemi segnalati. Restano spenti e non influiscono in alcun
  modo sul funzionamento né sui consumi: puoi aggiornare tranquillamente.

## v1.5.27 — 2026-07-19

### 🇬🇧 English

- **No more "please sign in again" when it's just the internet acting up.** If the connection to
  the car's server dropped for a moment, you could be asked to sign in again with a new email
  code — pointless, since the session was still fine. The integration now tells a genuinely
  expired session apart from a passing network glitch, and only bothers you when it really matters.
- **One less sign-in to do by hand.** In some cases the session could have been renewed silently on
  its own, but the integration didn't try and asked you for the email code straight away. It now
  attempts the automatic renewal first: often you won't have to do anything.
- **No more false "wrong PIN".** When the car refused a command for reasons that have nothing to do
  with the PIN (for example, the account lacks permissions on that vehicle), you were still told
  the PIN was wrong and asked to change it. Worse, that refusal counted as a failed attempt and
  pushed you closer to having your PIN locked. Every refusal is now recognised for what it is: the
  message states the real cause, a correct PIN is no longer questioned, and attempts are no longer
  used up because of errors that aren't yours.
- **Your PIN is no longer shown in plain text.** On the screens for changing the command PIN, the
  code was displayed in full. It is now masked with dots, like any normal password.
- **The email code is better protected.** Your email address and verification code are no longer
  passed in a way that, on some systems, could make them visible to other running programs. Also,
  when you shut down or remove the integration, the PIN and email no longer linger in memory.
- **The diagnostics file no longer reveals where you keep your certificates.** If you send it in to
  get help, the folder path (which often contains your username) is now hidden, just as your email,
  VIN and location already were.
- **The "Car data updated" sensor name is now translated** into both Italian and English, like all
  the others.
- **For those helping us track down problems:** you can now ask Home Assistant for the integration's
  detailed logs from its own page, without editing configuration files by hand.

### 🇮🇹 Italiano

- **Non ti chiede più di rifare l'accesso quando è solo internet che fa i capricci.** Se il
  collegamento con il server dell'auto cadeva per un attimo, poteva comparire la richiesta di
  rientrare con un nuovo codice via email — inutile, perché la sessione era ancora buona. Ora
  l'integrazione distingue "sessione davvero scaduta" da "problema di rete passeggero" e ti
  disturba solo quando serve per davvero.
- **Un accesso in meno da rifare a mano.** In alcuni casi la sessione poteva essere rinnovata da
  sola, in silenzio, ma l'integrazione non ci provava e ti chiedeva subito il codice via email.
  Ora tenta prima il rinnovo automatico: spesso non dovrai fare nulla.
- **Basta con il falso "PIN sbagliato".** Quando l'auto rifiutava un comando per motivi che col
  PIN non c'entrano nulla (per esempio l'account non ha i permessi su quella vettura), ti veniva
  comunque detto che il PIN era errato e ti veniva chiesto di cambiarlo. Peggio: quel rifiuto
  veniva contato come tentativo sbagliato e ti avvicinava al blocco del PIN. Ora ogni rifiuto
  viene riconosciuto per quello che è: il messaggio dice la causa vera, il PIN corretto non viene
  più messo in discussione e non si consumano tentativi per colpa di errori che non sono tuoi.
- **Il PIN non si vede più in chiaro.** Nelle schermate per cambiare il PIN dei comandi, il codice
  appariva scritto per esteso. Ora è mascherato con i pallini, come una normale password.
- **Il codice via email è più al riparo.** Email e codice di verifica non vengono più passati in un
  modo che, su alcuni sistemi, poteva renderli visibili ad altri programmi in esecuzione. Inoltre,
  quando spegni o rimuovi l'integrazione, PIN ed email non restano più in memoria.
- **Il file di diagnostica non rivela più dove tieni i certificati.** Se lo invii per farti aiutare,
  ora il percorso della cartella (che spesso contiene il tuo nome utente) viene oscurato come già
  accadeva per email, targa e posizione.
- **Il nome del sensore "Dati auto aggiornati" ora è tradotto** anche in italiano e in inglese,
  come tutti gli altri.
- **Per chi ci aiuta a trovare i problemi:** ora è possibile chiedere a Home Assistant i log
  dettagliati dell'integrazione dalla sua pagina, senza smanettare nei file di configurazione.

## v1.5.26 — 2026-07-19

### 🇬🇧 English

- **Less risk of locking your car's PIN.** If two requests started at the same moment (for example
  pressing "Wake" twice, or sending a command while the car is waking up), they could try the
  security code in parallel and burn more attempts than intended — with a wrong PIN that meant
  getting closer to an account lockout. Requests are now queued and the attempt limit the
  integration sets for itself is properly respected.
- **Re-entering the same PIN now really unblocks it.** If after an error you confirmed the very
  same PIN (because the problem wasn't the PIN after all), the safety block stayed active and
  commands kept failing for several minutes. Now every time you confirm the PIN — from the repair
  notice or from the settings — it starts fresh.
- **If waking the car fails, you're now told.** When the wake-up attempt failed because of the PIN
  or an expired session, the error stayed hidden in the logs: no notice, no request to re-enter the
  code. Now you get the proper notice, exactly as when you press a button: fix the PIN or sign in
  again, then retry.
- **No more background readings after switching the integration off.** If you reloaded or removed
  the integration while the car was charging, an automatic check could stay alive and keep querying
  the server afterwards. It now stops together with everything else.
- **The "Automatic update" switch now stops everything.** Turning it off while the car was charging
  did not stop the close-interval charge tracking. Now, when it is off, the integration no longer
  contacts the car on its own — as you would expect.

### 🇮🇹 Italiano

- **Meno rischio di bloccare il PIN dell'auto.** Se due richieste partivano nello stesso momento
  (per esempio premi "Sveglia" due volte, o un comando mentre l'auto si sta svegliando), potevano
  provare il codice di sicurezza in parallelo e "consumare" più tentativi del previsto: con un PIN
  sbagliato si rischiava di avvicinarsi al blocco dell'account. Ora le richieste si mettono in fila
  e viene rispettato il limite di tentativi che l'integrazione si è data.
- **Reinserire lo stesso PIN ora sblocca davvero.** Se dopo un errore riconfermavi il PIN identico
  a prima (perché in realtà il problema non era il PIN), il blocco di sicurezza restava attivo e i
  comandi continuavano a non partire per diversi minuti. Ora, ogni volta che confermi il PIN
  — dall'avviso di riparazione o dalle impostazioni — si riparte puliti.
- **Se la sveglia dell'auto fallisce, ora te lo dice.** Quando il tentativo di risveglio non
  riusciva per PIN o sessione scaduta, l'errore restava nascosto nei log: nessun avviso, nessuna
  richiesta di reinserire il codice. Ora compare l'avviso giusto, esattamente come quando premi un
  pulsante: correggi il PIN o rifai l'accesso e riprovi.
- **Niente più letture in sottofondo dopo aver spento l'integrazione.** Se ricaricavi o rimuovevi
  l'integrazione mentre l'auto era in carica, un controllo automatico poteva restare acceso e
  continuare a interrogare il server anche dopo. Ora si ferma insieme a tutto il resto.
- **L'interruttore "Aggiornamento automatico" ora ferma tutto.** Spegnendolo mentre l'auto era
  sotto carica, il controllo ravvicinato della ricarica proseguiva lo stesso. Ora quando è spento
  l'integrazione non contatta più l'auto da sola, come ci si aspetta.

## v1.5.25 — 2026-07-11

### 🇬🇧 English

- **Faster commands.** Every command used to redo the full PIN check with the server: the
  authorisation is now reused for about ten minutes, so most commands go straight through. If the
  car rejects it as expired, the integration renews it and retries on its own, without showing you
  an error.
- **No more "another command is still in progress".** The car runs one command at a time: before, a
  second press while the first was in flight was rejected with an error. Now it **waits its turn**
  and runs as soon as the car has confirmed the previous one.
- **Security and privacy.** Three fixes: the integration no longer writes the raw vehicle data to
  disk (it contained the VIN and the GPS position); the diagnostics file you can share when asking
  for help **no longer contains the VIN**; the files holding your access credentials are now
  readable by their owner only.
- **Setup: correcting your email now works.** If you mistyped your email, every retry kept using the
  old one and failed until you restarted Home Assistant. Each attempt now uses the email you just
  typed. Also, when the code can't be sent, **the reason is now shown** under the form (previously
  it appeared nowhere).
- **No more old code running after an update.** In some cases, after an update, Home Assistant kept
  running the previous version of some internal parts. They are now always reloaded from scratch:
  updating and restarting is enough.
- **Removed a duplicate engine indicator.** There were two entries for the engine state ("Engine"
  and "Engine running") showing the exact same information: only one remains ("Engine"), the
  original. No functionality lost, just a bit tidier.
- **More precise diagnosis when a command is rejected because of the PIN.** When the car doesn't
  accept the command security code, the integration now **shows and logs the exact code** returned
  by the server. This tells a genuine "wrong PIN" apart from other causes (vehicle permissions, a
  temporary server issue): useful if commands still won't go through after you've corrected the PIN.

### 🙏 Grazie / Credits

Le migliorie di questa versione (velocità dei comandi, coda, correzioni di sicurezza e privacy,
setup, ricarica del codice dopo un update) nascono dal lavoro di **[JackRonan](https://github.com/JackRonan)**
nel suo fork inglese [omoda-jaecoo-ha](https://github.com/JackRonan/omoda-jaecoo-ha), da cui sono
state riportate qui. Grazie di cuore per averle trovate, risolte e condivise. — *The improvements in
this release (command speed, queueing, security and privacy fixes, setup, code reloading after an
update) come from **JackRonan**'s work on his English fork, and were ported back here. Thank you!*

### 🇮🇹 Italiano

- **Comandi più veloci.** Prima ogni comando rifaceva da capo la verifica del PIN col server: ora
  l'autorizzazione ottenuta viene riusata per una decina di minuti, quindi la maggior parte dei
  comandi parte subito. Se l'auto la rifiuta perché scaduta, l'integrazione la rinnova e riprova
  da sola, senza mostrarti un errore.
- **Niente più "un altro comando è in corso".** L'auto esegue un comando alla volta: prima, se ne
  premevi un secondo mentre il primo era in volo, veniva rifiutato con un errore. Ora **si mette in
  coda** e parte da solo appena l'auto ha confermato il precedente.
- **Sicurezza e riservatezza.** Tre correzioni: l'integrazione non scrive più su disco i dati grezzi
  dell'auto (che contenevano telaio e posizione GPS); il file di diagnostica che puoi condividere per
  chiedere aiuto **non contiene più il numero di telaio**; i file con le credenziali di accesso sono
  ora leggibili solo dal proprietario.
- **Configurazione iniziale: correggere l'email adesso funziona.** Se sbagliavi a digitare l'email,
  ogni nuovo tentativo continuava a usare quella vecchia e falliva finché non riavviavi Home
  Assistant. Ora ogni tentativo usa l'email che hai appena scritto. In più, se il codice non parte,
  ora **vedi scritto il motivo** sotto al modulo (prima non appariva da nessuna parte).
- **Basta codice vecchio dopo un aggiornamento.** In certi casi, dopo un update, Home Assistant
  continuava a far girare la versione precedente di alcune parti interne. Ora vengono ricaricate
  sempre da zero: aggiornare e riavviare basta.
- **Tolto un doppione tra gli indicatori del motore.** C'erano due voci per lo stato del motore
  ("Motore" e "Motore acceso") che mostravano la stessa identica informazione: ne resta una sola
  ("Motore"), quella storica. Nessuna funzione persa, solo un po' di ordine in più.
- **Diagnosi più precisa quando un comando viene rifiutato per il PIN.** Quando l'auto non accetta
  il codice di sicurezza dei comandi, ora l'integrazione **mostra e registra il codice esatto**
  restituito dal server. Serve a distinguere con certezza un vero "PIN sbagliato" da altre cause
  (permessi del veicolo, problema temporaneo del server): utile se, dopo aver corretto il PIN, i
  comandi continuassero a non partire.

## v1.5.24 — 2026-07-06

### 🇬🇧 English

- **Fixed the nastiest problem: commands that looked successful while the car did nothing.** If the
  **4-digit remote-command PIN** is wrong, the car rejects every command — but until now the switch
  in Home Assistant stayed on "done" and everything looked fine (while windows, climate, lock, etc.
  didn't move). Now, in this case, **the switch snaps back to its real state** and a clear message
  appears: **"Wrong command PIN"**.
- **You can fix the PIN without deleting and re-adding the integration.** A Home Assistant **repair**
  notice appears (Settings → the usual banner at the top) that, with one click, lets you **enter the
  correct PIN** and sorts everything out. Alternatively you'll find the same under **Settings →
  Devices & services → Omoda 9 → Reconfigure**. No email code is needed: the command PIN has nothing
  to do with logging in. (Tip: don't keep retrying with a wrong PIN, to avoid locking the account.)
- **If your session expires (which happens if you open the official phone app) it now tells you
  clearly.** Previously the only way to restore the session was to hunt for "hidden" buttons; now
  Home Assistant shows the standard **"Re-authentication required"** notice: click it, get a **code
  by email**, enter it — and the data comes back. The old OTP buttons remain available as a fallback.

### 🇮🇹 Italiano

- **Risolto il problema più insidioso: comandi che sembravano riusciti ma l'auto non faceva
  nulla.** Se il **PIN a 4 cifre dei comandi remoti** è sbagliato, l'auto rifiuta ogni comando:
  finora però l'interruttore in Home Assistant restava sul "fatto" e sembrava tutto a posto
  (mentre finestrini, clima, serratura ecc. non si muovevano). Ora, in questo caso, **l'interruttore
  torna subito allo stato reale** e compare un chiaro messaggio: **«PIN comandi errato»**.
- **Puoi correggere il PIN senza dover eliminare e riaggiungere l'integrazione.** Compare un avviso
  di **riparazione** di Home Assistant (Impostazioni → il classico avviso in alto) che, con un clic,
  ti fa **inserire il PIN corretto** e sistema tutto da solo. In alternativa trovi la stessa cosa in
  **Impostazioni → Dispositivi e servizi → Omoda 9 → Riconfigura**. Non serve alcun codice via email:
  il PIN dei comandi non c'entra con l'accesso. (Consiglio: non insistere con un PIN errato, per non
  rischiare il blocco dell'account.)
- **Se l'accesso scade (capita se apri l'app ufficiale sul telefono) ora te lo dice chiaramente.**
  Prima l'unico modo per rimettere a posto la sessione era cercare dei pulsanti "nascosti"; ora
  Home Assistant mostra l'avviso standard **«Ri-autenticazione necessaria»**: premi, ricevi un
  **codice via email** e lo inserisci — e i dati tornano. I vecchi pulsanti OTP restano comunque
  disponibili come riserva.

## v1.5.23 — 2026-07-06

### 🇬🇧 English

- **Battery and mileage stay fresh even while the car is parked, and the car is "woken up" far less
  than before.** We found that the car stays reachable from the cloud for hours after you use it:
  during that window the integration reads battery, mileage, range and tyres **read-only, without
  waking it**. So the wake-up (which slightly uses the 12V battery and can interfere with the
  official phone app) now happens **only when actually needed** — i.e. when the car is genuinely
  asleep; if it's already reachable, the data refreshes on its own with no wake-up at all. We also
  added a new **"Car data updated"** indicator showing the time of the last data received from the
  car, so you know how fresh what you see is. Driving detection was also improved (in some cases the
  car looked stationary while actually moving). Everything strictly **read-only**.
- **Switches no longer show a fake "done" when the car rejects the command.** If you send a
  command (close, climate, lock…) while the car is already doing something else, it's busy and
  won't run it: previously the switch stayed on as if it had succeeded, and you had to wait
  several seconds before retrying. Now the switch **snaps back to its real state**, a clear notice
  appears ("car busy, try again in a few seconds") and you can **retry right away**. The same
  applies to the car's other rejections (feature not allowed on this vehicle, session needs
  re-login): no more false "executed".
- **New indicators and a more realistic total range.** Added four new live-verified indicators:
  **Engine running**, **High voltage active**, **Low fuel warning** and **Charge needed warning**.
  In exchange we removed a few indicators this vehicle simply doesn't transmit (they stayed
  "unknown" forever and only caused confusion: cabin temperature, some trip odometers, charging
  power, average speed, instant consumption, fast-charge times). Finally, **Total range** is now
  computed as **electric + petrol** (it previously used a dashboard value that, verified in the
  field, stayed fixed and didn't follow the charge) → the number shown is finally consistent with
  the real battery and tank state.

### 🇮🇹 Italiano

- **Batteria e chilometri restano aggiornati anche ad auto ferma, e la macchina viene "svegliata"
  molto meno di prima.** Abbiamo scoperto che l'auto resta raggiungibile dal cloud per ore dopo
  averla usata: in questa finestra l'integrazione legge batteria, chilometri, autonomia e gomme
  **in sola lettura, senza svegliarla**. Quindi ora la sveglia (che consuma un pochino la batteria
  da 12V e può dare fastidio all'app ufficiale sul telefono) parte **solo quando serve davvero**,
  cioè quando l'auto è effettivamente "addormentata"; se è già raggiungibile, i dati si aggiornano
  da soli senza alcun risveglio. È stato aggiunto anche un nuovo indicatore **"Dati auto
  aggiornati"** che mostra a che ora risale l'ultimo dato ricevuto dall'auto, così sai quanto è
  fresco quello che vedi. Migliorato infine il riconoscimento della marcia (in certi casi l'auto
  risultava ferma pur essendo in movimento). Tutto rigorosamente **a sola lettura**.
- **Gli interruttori non mostrano più un finto "fatto" quando l'auto rifiuta il comando.** Se
  invii un comando (chiudi, clima, serratura…) mentre l'auto sta già eseguendo qualcos'altro, è
  occupata e non lo esegue: prima l'interruttore restava acceso come se fosse andato a buon fine
  e bisognava aspettare diversi secondi per riprovare. Ora l'interruttore **torna subito allo
  stato reale**, compare un avviso chiaro («auto occupata, riprova tra qualche secondo») e puoi
  **ritentare immediatamente**. Lo stesso vale per gli altri rifiuti dell'auto (funzione non
  consentita su questa vettura, sessione da rifare): niente più falsi "eseguito".
- **Nuovi indicatori e autonomia totale più realistica.** Aggiunti quattro nuovi indicatori
  verificati dal vivo: **Motore acceso**, **Alta tensione attiva**, **Avviso carburante basso**
  e **Avviso ricarica necessaria**. In cambio abbiamo tolto alcuni indicatori che questa vettura
  non trasmette proprio (restavano per sempre "sconosciuto" e non facevano che confondere:
  temperatura abitacolo, alcuni contachilometri parziali, potenza di ricarica, velocità media,
  consumo istantaneo, tempi di ricarica rapida). Infine l'**Autonomia totale** ora è calcolata
  come **elettrica + benzina** (prima usava un valore del cruscotto che, verificato sul campo,
  restava fisso e non seguiva la carica) → il numero mostrato è finalmente coerente con lo stato
  reale di batteria e serbatoio.

## v1.5.22 — 2026-06-24

### 🇬🇧 English

- **Your car's data now updates by itself while you drive.** Until now, during a trip, values like
  battery, distance travelled and range stayed frozen until you manually pressed the "Refresh full
  status" button: a moving car doesn't send updates on its own. Now the integration notices this by
  itself and, while you're driving, refreshes the data roughly every minute with no action from you.
  When the car is parked or charging nothing changes compared to before. This is **read-only**: no
  command is ever sent to the car and it doesn't drain the battery. It works with the "Automatic
  update" switch turned on (as it already was).

### 🇮🇹 Italiano

- **Ora i dati dell'auto si aggiornano da soli mentre guidi.** Prima, durante un viaggio, valori
  come batteria, chilometri percorsi e autonomia restavano fermi finché non premevi a mano il
  pulsante "Aggiorna stato completo": l'auto in movimento, infatti, non invia aggiornamenti
  spontanei. Adesso l'integrazione se ne accorge da sola e, mentre sei in marcia, aggiorna i dati
  da sola circa ogni minuto, senza che tu debba toccare niente. A vettura ferma o in ricarica non
  cambia nulla rispetto a prima. Tutto questo avviene **solo a lettura**: non viene inviato alcun
  comando all'auto e non si consuma la batteria. Funziona con l'interruttore "Aggiornamento
  automatico" acceso (come già era).

## v1.5.21 — 2026-06-23

### 🇬🇧 English

- **Fixed: the integration could no longer be added (error "not_implemented").**
  Anyone installing the integration from scratch, under **Add integration → Omoda 9 / Jaecoo**,
  immediately got a "not_implemented" error and couldn't enter their email and PIN. The login
  screen wasn't shown at all. The setup process (email → code received by mail → optional vehicle
  selection) now works correctly again. Anyone who had already configured the integration was not
  affected by this problem.

### 🇮🇹 Italiano

- **Risolto: non si riusciva più ad aggiungere l'integrazione (errore "not_implemented").**
  Chi installava l'integrazione da zero, alla voce **Aggiungi integrazione → Omoda 9 / Jaecoo**,
  riceveva subito un errore "not_implemented" e non riusciva a inserire email e PIN. La schermata
  di accesso non veniva proposta per niente. Ora la procedura di configurazione (email → codice
  ricevuto via mail → eventuale scelta dell'auto) funziona di nuovo correttamente. Chi aveva già
  configurato l'integrazione in precedenza non era interessato dal problema.

## v1.5.20 — 2026-06-23

- **Nomi delle entità in italiano o inglese, in automatico secondo la lingua di Home
  Assistant.** Finora i nomi delle entità (Batteria, Autonomia, Porte…) erano sempre in
  italiano. Ora ogni entità è **tradotta**: chi usa Home Assistant in inglese vede "Battery",
  "Total range", "Front left door"…, chi lo usa in italiano vede "Batteria", "Autonomia
  totale", "Porta anteriore SX". Il nome del veicolo fa da prefisso (es. **"Omoda 9 Battery"**,
  o **"Jaecoo 7 Battery"** per chi ha un Jaecoo). `entity_id`, storico, automazioni e dashboard
  **non cambiano**. (Se avevi rinominato a mano qualche entità, il tuo nome personalizzato
  resta e ha la precedenza.)

## v1.5.19 — 2026-06-23

- **Il dispositivo prende il nome reale della tua auto (Omoda 9, Jaecoo 7…).** Prima il
  dispositivo si chiamava sempre "Omoda 9", anche per chi ha un Jaecoo. Ora il nome (e
  marca/modello) vengono **rilevati automaticamente dall'auto** — è lo stesso nome che vedi
  nell'app. Se preferisci, puoi cambiarlo a mano in **Impostazioni → Dispositivi e servizi →
  Omoda 9 / Jaecoo → Configura → "Nome veicolo"**. Gli `entity_id`, lo storico, le automazioni
  e le dashboard **non cambiano** (il dispositivo è identificato dal numero di telaio).

## v1.5.18 — 2026-06-23

- **Il sensore "Connessa" si chiama ora "Connessione".** È sempre lo stesso sensore (uno
  solo, con stato **Connesso/Disconnesso**): il nome neutro si legge meglio quando l'auto
  è offline. Niente di tecnico cambia e i riferimenti esistenti restano validi.

## v1.5.17 — 2026-06-23

- **"Autonomia totale" corretta + nuovo dato "Autonomia benzina".** Il valore che
  l'integrazione chiamava "Autonomia totale" (215 km) in realtà era **solo l'autonomia
  a benzina**, non la somma con l'elettrico: lo si è verificato perché restava fermo a
  215 km mentre l'autonomia elettrica calava (e il serbatoio era invariato). Ora:
  **"Autonomia benzina"** mostra i km col solo motore termico, e **"Autonomia totale"**
  mostra il valore corretto = **elettrico + benzina** (es. 27 + 215 = 242 km).
- **Pressione gomme in bar (come nell'app).** Le quattro pressioni degli pneumatici ora
  sono mostrate in **bar** invece che in kPa (es. 2,79 bar invece di 279 kPa), così
  coincidono con quanto vedi nell'app dell'auto. Potresti vedere una notifica una-tantum
  di "unità cambiata": si risolve da sola, lo storico viene convertito automaticamente.

## v1.5.16 — 2026-06-23

- **L'aggiornamento automatico della ricarica ora parte subito anche dopo un riavvio
  di Home Assistant.** Nella versione precedente, se riavviavi Home Assistant mentre
  l'auto era già in carica, il monitoraggio in tempo reale poteva non avviarsi da solo
  finché non scattava il controllo periodico (anche mezz'ora dopo) — perché l'auto, da
  ferma, non "annuncia" nulla. Ora, **pochi secondi dopo l'avvio**, l'integrazione fa
  una lettura: se trova l'auto in carica (o in marcia) **fa partire immediatamente**
  l'aggiornamento ogni paio di minuti. Sempre in sola lettura, nessun comando all'auto.

## v1.5.15 — 2026-06-23

- **Piccola regolazione del controllo periodico durante la ricarica (ogni 30 minuti
  invece di 39).** È solo una rete di sicurezza: a seguire la carica in tempo reale
  ci pensa già l'aggiornamento automatico ogni paio di minuti introdotto qui sopra.
  Nessun cambiamento visibile nell'uso di tutti i giorni.

## v1.5.14 — 2026-06-23

- **La carica si segue da sola: mentre l'auto è attaccata alla colonnina, batteria,
  tempo che manca alla fine e potenza di ricarica si aggiornano automaticamente.**
  Prima, anche durante la ricarica i dati potevano restare "fermi" all'ultimo valore
  per ore (l'auto non li manda da sola): bisognava premere "Aggiorna stato completo"
  per vederli. Ora, **appena colleghi il cavo, l'integrazione inizia a rileggere i
  dati di carica ogni paio di minuti** e li tiene aggiornati per tutta la durata della
  ricarica — vedi la percentuale che sale e il tempo residuo che scende senza fare
  nulla. Quando stacchi il cavo, smette da sola. Tutto in sola lettura: **nessun
  comando viene inviato all'auto** (durante la carica i dati veri sono già disponibili).

## v1.5.13 — 2026-06-23

- **I chilometri e la batteria ora si aggiornano da soli quando guidi.** Era
  emerso che l'odometro restava "fermo" all'ultimo valore e la batteria sembrava
  bloccata. Il motivo: l'auto comunica i dati **veri** (chilometri totali, carica
  della batteria, tensione) **solo quando l'alta tensione è accesa** — cioè mentre
  la guidi o la ricarichi. A macchina parcheggiata e spenta non c'è nessun dato
  nuovo da leggere (vale anche per l'app ufficiale). Ora, **appena l'auto si
  accende o va in carica, l'integrazione legge i dati freschi più volte di
  seguito**, così i chilometri salgono e la batteria si aggiorna **automaticamente
  durante e dopo ogni viaggio**, senza che tu debba fare nulla.
- **Nuovo pulsante "Aggiorna stato completo".** Se vuoi vedere subito i
  chilometri e la batteria aggiornati mentre l'auto è parcheggiata, premilo:
  accende il **clima per circa un minuto** (è l'unico modo per "risvegliare"
  l'alta tensione), legge i dati reali e poi **rispegne il clima da solo**. Da
  usare solo quando ti serve il dato fresco al volo: nell'uso normale non serve,
  perché ora si aggiorna da sé quando guidi.
- **Niente più "batteria 0%" fuorviante.** Se l'integrazione non ha ancora mai
  letto una carica reale, mostra **"sconosciuto"** invece di un falso 0% — finché
  non arriva il primo dato vero (al primo viaggio/ricarica o col pulsante qui
  sopra).

## v1.5.12 — 2026-06-22

- **La batteria non va più a 0 quando l'auto è parcheggiata.** Quando l'auto è
  ferma e spenta non comunica la carica reale della batteria (manda uno "zero"
  segnaposto): prima questo faceva apparire la **batteria allo 0%** e la
  **tensione/corrente** dell'alta tensione azzerate. Ora l'integrazione riconosce
  questi valori finti e **mantiene l'ultimo valore reale** — esattamente come fa
  l'app ufficiale, che mostra sempre l'ultima carica nota. I valori "veri" di
  batteria, tensione, corrente e consumo elettrico tornano ad aggiornarsi da soli
  quando l'auto è **in marcia o in ricarica** (gli unici momenti in cui l'auto li
  trasmette davvero).

## v1.5.11 — 2026-06-22

- **Login e avvio più robusti.** Migliorata la stabilità in alcune situazioni
  poco comuni: se il server dell'auto risponde in modo inatteso durante l'invio
  del codice OTP o la verifica del captcha, ora l'integrazione **riprova invece
  di bloccarsi**. All'avvio, se qualcosa va storto, **non lascia più processi o
  controlli automatici "appesi"** in sottofondo, e durante lo spegnimento fa
  pulizia in modo più ordinato. Il file con le credenziali dell'auto viene salvato
  in modo **a prova di interruzione** (non può più corrompersi se Home Assistant
  si chiude proprio in quel momento). Infine, quando spegni l'interruttore
  **"Aggiornamento automatico"**, l'aggiornamento periodico si ferma **davvero**,
  senza più riattivarsi da solo. Sono tutti miglioramenti "dietro le quinte": l'uso
  di tutti i giorni non cambia.

## v1.5.10 — 2026-06-22

- **Più facile chiedere aiuto se qualcosa non va.** Aggiunto il pulsante **"Scarica
  diagnostica"** nella pagina dell'integrazione (menù ⋮): con un clic scarichi un file da
  inviare per farti aiutare, **già reso anonimo** — la tua email, il PIN, il numero di
  telaio e soprattutto la **posizione dell'auto** sono nascosti automaticamente, e di
  password e certificati non viene mai mostrato il contenuto. Nel manuale (README) trovi ora
  una sezione **"Risoluzione problemi"** che spiega in parole semplici dove trovare i log e
  come inviarli in sicurezza.

## v1.5.9 — 2026-06-22

- **"Raffredda tutto" e "Riscalda tutto" ora si spengono davvero del tutto (sedili
  posteriori inclusi).** Per spegnere tutto usa lo stesso pulsante **"Raffredda tutto"**
  (o "Riscalda tutto") e mettilo su **OFF**: così spegni aria + **tutti** i sedili, anche
  quelli posteriori. ⚠️ Attenzione: il pulsante **"Clima"** spegne solo l'aria condizionata
  (e, sull'auto, i sedili anteriori che le sono collegati), ma **non** i sedili posteriori —
  quelli sono indipendenti. Inoltre l'interruttore ora **resta acceso** mentre il preset è
  attivo (prima si rispegneva subito e non riuscivi a comandarne lo spegnimento), e **si
  spegne da solo** dopo circa 15 minuti, quando l'auto chiude il preset. Anche lo spegnimento
  sveglia l'auto da solo, così arriva fino ai sedili posteriori.

## v1.5.8 — 2026-06-22

- **"Raffredda tutto" e "Riscalda tutto": basta un tocco, anche con l'auto parcheggiata.**
  I sedili, il volante e gli sbrinatori l'auto li accende solo quando è **sveglia**: se la
  premevi a vettura ferma da un po', l'auto era "addormentata" e rispondeva con un errore.
  Ora la macro **sveglia l'auto da sola e aspetta qualche secondo** prima di mandare il
  comando, quindi ti basta premere una volta e funziona (ci mette ~40 secondi a partire:
  è normale, sta svegliando l'auto). Inoltre il pulsante ora fa **sempre l'accensione**
  quando lo premi: prima, se era rimasto "acceso", il tocco mandava per sbaglio lo
  spegnimento (che dava errore). 💡 Per il momento miglior risultato, usalo con l'**auto
  spenta**.

## v1.5.7 — 2026-06-22

- **"Raffredda tutto" e "Riscalda tutto" ora accendono DAVVERO tutto** (e si corregge
  quanto detto nelle due note precedenti). Le macro tornano a fare ciò che ti aspetti, con
  un unico comando come l'app ufficiale:
  - **❄️ Raffredda tutto** = aria condizionata al massimo freddo **+ ventilazione di tutti
    e quattro i sedili**.
  - **🔥 Riscalda tutto** = aria calda al massimo **+ riscaldamento di tutti e quattro i
    sedili + volante riscaldato + sbrinatore parabrezza + sbrinatore lunotto**.

  Perché prima sembravano "non disponibili": i comandi del comfort (sedili, volante,
  sbrinatori) l'auto li accetta **solo a vettura spenta e con il clima acceso**. Se l'auto
  è accesa/occupata, o se si prova ad accendere un sedile col clima spento, l'auto li
  rifiuta con un errore — e questo mi aveva tratto in inganno facendomi credere, a torto,
  che certi comfort non fossero installati. Verificato dal vivo a motore spento: clima,
  tutti i sedili, volante, parabrezza e lunotto rispondono correttamente. **Consiglio
  d'uso:** lancia "Raffredda/Riscalda tutto" con l'**auto spenta**.

## v1.5.6 — 2026-06-21

- **"Raffredda tutto" e "Riscalda tutto" ora sono vere macro su misura per la tua auto.**
  Abbiamo provato sul campo, uno per uno, tutti i comfort dell'auto per vedere quali
  rispondono davvero ai comandi a distanza. Su questa vettura risultano installati (e
  funzionanti) soltanto il **sedile guidatore ventilato** e lo **sbrinatore del lunotto**;
  riscaldamento dei sedili, volante riscaldato, sbrinatore del parabrezza e ventilazione
  dei sedili passeggero/posteriori **non sono presenti** e andavano solo in errore. Quindi
  adesso:
  - **❄️ Raffredda tutto** = aria condizionata al massimo freddo **+ ventilazione del
    sedile guidatore**.
  - **🔥 Riscalda tutto** = aria calda al massimo **+ sbrinatore del lunotto**.

  I comandi vengono inviati **in sequenza, uno alla volta** (l'auto ne esegue uno per
  volta), quindi la macro impiega qualche secondo in più a completarsi ma non si "accavalla"
  e non genera più gli errori che vedevi. Niente più tentativi sui comfort che la tua auto
  non ha.

## v1.5.5 — 2026-06-21

- **"Raffredda tutto" e "Riscalda tutto" ora funzionano davvero.** Prima questi due
  pulsanti usavano un comando "tutto-in-uno" che la tua auto non riesce a eseguire: dava un
  finto "comando inviato" e subito dopo un errore, e il clima non partiva. Ora usano il
  comando del climatizzatore semplice (lo stesso, affidabile, del termostato "Clima"):
  **"Raffredda tutto"** accende l'aria al massimo freddo, **"Riscalda tutto"** al massimo
  caldo (e accende anche gli sbrinatori di parabrezza e lunotto). Il riscaldamento/la
  ventilazione dei **sedili** non fanno più parte di questi due pulsanti — l'auto non li
  accettava in quel comando — ma restano comandabili dai loro interruttori dedicati.

## v1.5.4 — 2026-06-21

- **Niente più comandi accavallati se premi troppe volte.** L'auto esegue **un comando
  alla volta**: ora, finché un comando è in corso, le pressioni successive vengono
  ignorate con un avviso ("attendi qualche secondo, un comando è già in corso") invece di
  accavallarsi e farsi rifiutare dall'auto come "occupato". Appena l'auto conferma, il
  comando successivo riparte subito. Vale per tutti i comandi che **agiscono** sull'auto
  (clima, serrature, baule/finestrini/tetto, ricarica, sedili, antifurto, "Raffredda/
  Riscalda tutto").

## v1.5.3 — 2026-06-21

- **L'aggiornamento automatico ora parte SPENTO.** Per non svegliare l'auto senza che tu
  lo voglia, la funzione "Aggiornamento automatico" è **disattivata di default**: quando la
  vuoi, accendi tu l'interruttore **"Aggiornamento automatico"** (e regoli gli intervalli
  dalle opzioni). Resta valido il pulsante "Aggiorna posizione" per un aggiornamento manuale.

## v1.5.2 — 2026-06-21

- **Aggiornamento automatico dei dati dell'auto.** Ora Home Assistant aggiorna **da solo**,
  a intervalli regolari, le informazioni dell'auto (posizione, batteria, autonomia, gomme,
  consumi…) svegliando brevemente la vettura. Di **default ogni 60 minuti**, e **ogni 39
  minuti quando l'auto è attaccata alla colonnina** (così segui meglio la ricarica).
  - Puoi cambiare i due intervalli — o disattivarli mettendo **0** — dalle opzioni
    dell'integrazione: **Impostazioni → Dispositivi e servizi → Omoda 9 → Configura**.
  - C'è anche un nuovo interruttore **"Aggiornamento automatico"** per accendere o spegnere
    tutto con un tocco, senza entrare nelle opzioni.
  - ⚠️ Quando è attivo l'auto viene svegliata periodicamente: comodo per avere dati sempre
    freschi, ma comporta un piccolo consumo della batteria a vettura ferma. Se preferisci,
    spegnilo e aggiorna a mano col pulsante "Aggiorna posizione".

- **Stati della ricarica più chiari.** Le informazioni "Stato ricarica", "Presa ricarica
  rapida" e "Ricarica programmata" ora mostrano un **testo leggibile** (es. "Non in ricarica",
  "In ricarica", "Collegata") invece di un codice numerico.

## v1.5.1 — 2026-06-21

- **Correzione: le nuove informazioni dall'auto ora compaiono davvero.** Per un problema
  tecnico, i dati che l'auto comunica quando è sveglia — autonomia, chilometri, pressione e
  temperatura delle gomme, consumi, carburante, tensione della batteria, e perfino **livello
  batteria e velocità** — non venivano letti e restavano vuoti. Ora vengono letti
  correttamente: i relativi sensori si popolano non appena l'auto si sveglia.

- **Avviso quando un comando all'auto non riesce (opzionale).** Ora è disponibile un
  "blueprint" pronto all'uso: se lo importi, ricevi un **popup in Home Assistant** (e, se
  vuoi, una notifica sul telefono) ogni volta che un comando all'auto non va a buon fine —
  ad esempio quando l'auto è occupata da un altro comando, non è raggiungibile, o la
  sessione è scaduta. Riconosce solo i veri errori, quindi non disturba quando va tutto
  bene. L'integrazione di suo continua a **non inviare nessuna notifica**: il blueprint è
  del tutto facoltativo e si attiva con un clic dal README.

## v1.5.0 — 2026-06-21

- **Tante nuove informazioni che arrivano direttamente dall'auto.** Quando l'auto è
  sveglia, Home Assistant ora mostra molti più dati utili, finora non disponibili:
  - **Autonomia**: quanti chilometri restano in elettrico e in totale (elettrico + benzina).
  - **Chilometri totali** dell'auto (contachilometri) e chilometri percorsi in ibrido.
  - **Gomme**: pressione e temperatura di ognuna delle quattro ruote, con un **avviso**
    dedicato per ciascuna gomma se qualcosa non va.
  - **Consumi medi**, sia di benzina sia di energia elettrica.
  - **Carburante rimasto** nel serbatoio (in litri).
  - **Batteria di trazione**: tensione e corrente (informazioni tecniche).
  - **Clima**: la temperatura impostata sui due lati dell'abitacolo.
  - **Ricarica**: stato della presa, stato della ricarica programmata e, quando l'auto è
    in carica, il tempo che manca al termine.
  - **Avviso "batteria scarica"** quando il livello è basso.

  Sono tutte informazioni di **sola lettura** (l'auto non riceve nessun comando) e si
  aggiornano quando l'auto si sveglia. Le trovi sotto il dispositivo "Omoda 9": quelle
  più tecniche (temperature gomme, tensione batteria, ecc.) sono raggruppate tra i
  "dettagli diagnostici".

## v1.4.0 — 2026-06-21

- **Nuovo interruttore "Antifurto".** Puoi accendere e spegnere l'allarme antifurto
  dell'auto direttamente da Home Assistant. Quando è acceso, l'auto fa scattare l'allarme
  e ti avvisa in caso di movimento non autorizzato del veicolo, tentativi di scasso delle
  porte, rottura dei finestrini o altre potenziali effrazioni. L'interruttore mostra anche
  se l'antifurto è già attivo (lo legge dall'auto).
- **Due nuovi tasti "comfort": Raffredda tutto e Riscalda tutto.** Con un solo
  interruttore prepari l'abitacolo per la stagione. **"Raffredda tutto"** accende il
  clima al massimo del freddo e avvia la **ventilazione di tutti i sedili**.
  **"Riscalda tutto"** accende il clima al massimo del caldo e attiva insieme lo
  **sbrinamento di parabrezza e lunotto, il volante riscaldato e il riscaldamento di
  tutti i sedili**. I due tasti si escludono a vicenda: accendendone uno, l'altro si
  spegne. Comodi per scaldare o rinfrescare l'auto in un colpo solo prima di partire.
- **Ricarica programmata: ora scegli l'orario al minuto.** L'ora di inizio della
  ricarica programmata era un cursore a sole ore intere (es. solo "le 8"); adesso c'è un
  vero **selettore d'orario** "Ricarica · orario di inizio" con cui imposti anche i minuti
  (es. **07:45**). La durata resta il cursore in ore. ⚠️ Dopo l'aggiornamento il vecchio
  cursore "Ricarica · ora di inizio" resterà "non disponibile" e si può togliere: al suo
  posto usa il nuovo selettore d'orario.

## v1.3.0 — 2026-06-21

- **Il clima ora si imposta alla temperatura che vuoi.** Prima c'era un semplice
  interruttore che accendeva il clima fisso a 21°; ora trovi un vero **termostato**:
  scegli la temperatura desiderata (da 16° a 30°) e l'auto la applica, riscaldando o
  raffreddando l'abitacolo. Puoi anche regolare per quanti minuti deve restare acceso.
  ⚠️ Dopo l'aggiornamento, al posto del vecchio interruttore "Clima" comparirà il nuovo
  termostato "Clima": se avevi messo il vecchio interruttore in una schermata, sostituiscilo
  con il nuovo (il vecchio resterà "non disponibile" e si può togliere).
- **Comandi per la ricarica elettrica.** Due nuovi interruttori: **"Ricarica"** per
  avviare o fermare subito la ricarica, e **"Ricarica programmata"** per far caricare
  l'auto in una fascia oraria scelta (imposti ora di inizio e durata con i due cursori
  dedicati). Funzionano quando l'auto è collegata alla colonnina/wallbox.
- **I sedili e gli sbrinamenti non si toccano più accendendo il clima.** Il nuovo
  termostato agisce solo sull'aria: riscaldamento sedili, volante e sbrinamenti restano
  controlli a parte e non vengono spenti quando accendi o spegni il clima.

## v1.2.0 — 2026-06-21

- **Comandi anche per i sedili passeggero e posteriori.** Finora potevi accendere e
  spegnere solo il sedile del posto guida; ora trovi gli stessi interruttori (caldo e
  aria) anche per il **passeggero** e per i due **sedili posteriori** (sinistro e
  destro). Come per il guida, su ogni sedile caldo e aria si escludono a vicenda.
- **Nuove informazioni dall'auto.** Compaiono tre nuove indicazioni quando l'auto è
  sveglia: se la **spina di ricarica è collegata**, se il **motore è acceso**, e lo
  stato di movimento del **tetto apribile** (quest'ultimo tra i dettagli tecnici).
- **L'esito dei comandi ora arriva davvero dall'auto.** Prima la voce "Esito comando"
  diceva solo che il comando era stato *accettato* dal server; adesso, quando l'auto
  risponde, viene aggiornata con l'esito **reale**: comando eseguito e confermato,
  ancora in corso, oppure non riuscito (con il motivo segnalato dall'auto).

- **Riscaldamenti e sbrinamenti ora si spengono con un tocco.** Sbrinamento
  parabrezza, sbrinamento lunotto, volante riscaldato e i sedili (caldo/aria) del
  posto guida diventano dei normali interruttori: prima potevi solo accenderli (e si
  spegnevano da soli dopo 15 minuti), ora li accendi **e li spegni** quando vuoi,
  vedendo lo stato acceso/spento nella stessa card.
- **Sedile guida più furbo.** Caldo e aria del sedile guida non possono stare accesi
  insieme: accendendo l'aria il riscaldamento si spegne (e viceversa), proprio come
  fa l'auto — e ora la card lo mostra subito.
- **Tasto "Sveglia auto" più affidabile.** Se la sveglia via SMS non risponde
  (capitava che l'auto restasse a riposo), l'integrazione prova in automatico a
  contattare l'auto con la richiesta di posizione, che la sveglia al primo colpo e
  in più aggiorna la posizione GPS.
- **Schermata più pulita.** Un paio di indicazioni che l'auto non comunica mai da
  ferma (tendina del tetto, riscaldamento parabrezza) sono state spostate tra i
  dettagli diagnostici, così non restano "in dubbio" tra i controlli principali.

## v1.0.0 — 2026-06-21

- **Versione 1.0: l'integrazione diventa stabile e più affidabile.** Tante piccole
  rifiniture sotto il cofano per un funzionamento più solido di tutti i giorni.
- **Connessione all'auto più robusta.** Se il collegamento cade viene ristabilito
  da solo, senza lasciare l'integrazione "appesa"; meno disconnessioni inattese e
  un avvio più pulito quando l'auto non è raggiungibile.
- **Accesso più sicuro e protetto.** Migliorata la gestione dell'accesso per evitare
  che la sessione si perda da sola; aggiunta una protezione che ferma i tentativi se
  il PIN risulta sbagliato, così l'account non rischia il blocco.
- **Informazioni sempre veritiere dopo un riavvio.** Dopo aver riavviato Home
  Assistant, gli esiti dei comandi non mostrano più un risultato vecchio: o è
  aggiornato o resta vuoto, niente informazioni fuorvianti.
- **Stati più coerenti.** Porte, serratura, baule, finestrini, tetto e clima
  vengono interpretati in modo uniforme: niente più "acceso" o "aperto" mostrati
  per sbaglio quando il dato non c'è.
- **Comandi con conferma a schermo.** Quando premi un comando (chiudi/apri/clima)
  la card si aggiorna subito e, se qualcosa non va a buon fine, te lo segnala invece
  di restare bloccata su uno stato mai raggiunto.
- **Pronta anche fuori dall'Europa.** In fase di configurazione si può ora indicare
  il server dell'auto della propria zona, così l'integrazione funziona anche fuori
  dalla regione europea.
- **La posizione GPS resta salvata.** L'ultima posizione nota viene conservata e
  ricompare dopo un riavvio, invece di sparire.

## v0.3.0 — 2026-06-21

- **La serratura ora è un vero lucchetto.** La blocchi e la sblocchi con un solo
  tocco, e vedi lo stato (chiusa/aperta) nella stessa card. Prima erano
  un'indicazione separata e due pulsanti distinti.
- **Il clima ora è un interruttore.** Lo accendi e lo spegni come una normale luce
  (l'accensione avvia la climatizzazione a 21° per 15 minuti).
- **Baule, finestrini e tetto si comandano come tapparelle.** Apri e chiudi
  direttamente, con stato e comando insieme. (La ventilazione finestrini resta un
  pulsante a parte.)
- **Schermata principale più pulita.** Le informazioni di servizio — esiti dei
  comandi, orari dell'ultimo contatto, stato della sessione e campo del codice OTP —
  sono state spostate nella sezione "diagnostica" del dispositivo, così in primo
  piano restano solo i controlli che usi davvero.
- **Andamenti nel tempo per batteria e velocità.** Ora vengono registrate
  storicamente: puoi vederne i grafici e usarle nelle statistiche.

## v0.2.6 — 2026-06-21

- Aggiunto questo elenco delle novità (changelog), così a ogni aggiornamento
  vedi in chiaro cosa è cambiato.
- README più chiaro: per iniziare bastano **email + PIN** del tuo account
  (più un **codice OTP** via email al primo accesso). Tutto il resto è automatico.

## v0.2.4 — 21 giugno 2026

- **Certificati automatici.** Non devi più procurarti o inserire alcun
  certificato: l'integrazione li installa da sola in base alla tua regione.
  L'attivazione richiede ora soltanto email e PIN.

## v0.2.1 — 21 giugno 2026

- **Accesso più semplice.** Ora puoi accedere direttamente da Home Assistant
  inserendo email e PIN e confermando il codice OTP ricevuto via email, senza
  strumenti esterni e su qualunque installazione (anche Home Assistant OS).

## Versioni precedenti

- Prime versioni dell'integrazione: collegamento dell'auto a Home Assistant
  (stato porte/serrature/baule/cofano/finestrini/tetto/clima/sedili), posizione
  GPS su richiesta, batteria e velocità ad auto in marcia, pulsanti dei comandi.
