# Design Spec — Lovelace Card `custom:lepas-card` v2 (Matte Titanium OEM, Responsive Mobile/Desktop, Blueprint SVG & 5 Colori Reali)

**Data:** 2026-11-17  
**Stato:** Bozza completa da brainstorming — in attesa di revisione utente prima del piano implementativo (`writing-plans`)  
**Target Release:** `v1.19.0` (`minor` SemVer)

---

## 1. Obiettivo & Direzione Estetica (*Matte Titanium OEM — Zero Neon*)

Ripensare `custom_components/lepas/lovelace/lepas-card.js` da zero per offrire una plancia automobilistica professionale, reattiva e coerente con la vera **Lepas L8**, eliminando qualsiasi effetto neon/cyberpunk a favore di un linguaggio **Matte Titanium OEM** (grafite opaca + accento platino + colori semantici pacati):

- **Superfici:**
  - Canvas base: `#111317`
  - Superficie moduli / pannelli: `#181B20`
  - Controlli e pulsanti elevati: `#21252C`
  - Bordi strutturali: `1px solid rgba(255, 255, 255, 0.08)` (zero bordi ciano luminosi, zero `box-shadow` neon).
- **Tipografia:**
  - Testi primari `#F3F4F6`, secondari `#9CA3AF`, etichette `#6B7280`.
  - Numeri telemetrici con `font-variant-numeric: tabular-nums` (allineamento verticale stabile in movimento).
- **Colori Semantici (solo dove indicano stato reale):**
  - **Platino spazzolato** (`#F3F4F6` su `#262B34` o riempimento pieno con testo `#111317`): tab attivo, controlli primari, durata selezionata, pulsante *Applica*.
  - **Smeraldo pacato** (`#34D399`): online, ricarica attiva, TPMS nominali.
  - **Blu ghiaccio sobrio** (`#60A5FA`): raffreddamento A/C, ventilazione sedili, finestrini/tetto ventilati.
  - **Ambra caldo** (`#F59E0B`): riscaldamento sedili, sbrinamento/lunotto/volante, avvisi lievi.
  - **Rosso corallo** (`#EF4444`): allarmi attivi (gomme, batteria bassa, offline prolungato, stato conferma azione critica).

---

## 2. Asset Veicolo Fedeli & 5 Varianti Colore (`grey` Predefinito)

### 2.1 Render Studio Fedeli della Vera Lepas L8
Le immagini attualmente presenti vengono sostituite da **5 render studio coerenti** generati a partire dalle 5 foto reali fornite dall'utente (preservando calandra arrotondata cromata a trama puntinata, firma `Lepas` sul cofano, DRL superiori sottili separati dai fari verticali, passaruota neri e cerchi bicolore reali), su sfondo scuro opaco `#111317` privo di riflessi neon sotto la scocca:

| Chiave `color` | Descrizione | File statico servito via `/lepas_card/` | Sorgente di riferimento |
| :--- | :--- | :--- | :--- |
| `grey` *(default)* | Grigio satinato opaco | `custom_components/lepas/lovelace/lepas-hero-grey.png` (e copia `lepas-hero.png`) | `media_1794947783220_6b6fd250.jpg` |
| `teal` | Verde ottanio / petrolio metallizzato | `custom_components/lepas/lovelace/lepas-hero-teal.png` | `media_1794947726017_43d9c3b6.jpg` |
| `violet` | Viola ametista metallizzato | `custom_components/lepas/lovelace/lepas-hero-violet.png` | `media_1794947726625_b5713d0b.jpg` |
| `black` | Nero ossidiana | `custom_components/lepas/lovelace/lepas-hero-black.png` | `media_1794947783129_1ca2a408.jpg` |
| `white` | Bianco perla | `custom_components/lepas/lovelace/lepas-hero-white.png` | `media_1794947783300_4cb80eb5.jpg` |

- `lepas-hero.png` resta aggiornato con il render **grigio opaco (`grey`)** per retrocompatibilità di `tests/test_repo_hygiene.py` e di eventuali configurazioni preesistenti.
- Ogni PNG viene ottimizzato per web/mobile (formato compatto ~800×450px) e caricato con `?v=1.19.0` per cache-busting HACS.
- `__init__.py` espone già l'intera directory `custom_components/lepas/lovelace/` su `/lepas_card/`, quindi non servono modifiche al backend Python per servire i nuovi file.

### 2.2 Risoluzione Immagine nella Card
Ordine di precedenza:
1. `config.image` (URL esplicito impostato dall'utente in YAML/Editor, validato con `_imgUrl`);
2. `attributes.vehicle_image` (se presente sulle entità);
3. `/lepas_card/lepas-hero-${resolvedColor}.png?v=1.19.0` dove `resolvedColor` normalizza `config.color` (default `"grey"`, con alias tolleranti es. `grigio`→`grey`, `nero`→`black`, `bianco`→`white`, `viola`/`purple`→`violet`, `verde`/`ottanio`/`green`→`teal`).

---

## 3. Configurazione & Editor Visuale Home Assistant

- **Opzioni configurabili su `custom:lepas-card`:**
  - `title` *(string, opzionale)*: nome visualizzato nell'header (default: nome veicolo da entità o `"Lepas"`).
  - `color` *(`"grey" | "teal" | "violet" | "black" | "white"`, default `"grey"`)*.
  - `image` *(string, opzionale)*: percorso/URL immagine personalizzata.
  - `layout` *(`"auto" | "compact" | "cockpit"`, default `"auto"`)*.
  - `default_tab` *(`"overview" | "climate" | "charging" | "security"`, default `"overview"`)*.
  - `show_all` *(bool, default `false`)*: mostra lista entità residue non mappate.
  - `entities` *(list, opzionale)*: entità extra da mostrare nella sezione dettagli.
  - `integration` *(string, default `"lepas"`)*.
  - `prefix` *(string, default `"lepas_"`)*.
- **Editor visuale (`LepasCardEditor` via `static getConfigElement()`):**
  - Elemento custom `<lepas-card-editor>` registrato nello stesso bundle ES `lepas-card.js` che espone in Home Assistant:
    - Selettore visuale dei **5 colori** con swatch reali + nome localizzato (IT/EN/NL);
    - Selettore **Layout** (`Auto`, `Compatto 4-Tab`, `Cockpit Desktop`);
    - Selettore **Tab iniziale**, campo **Titolo**, URL **Immagine opzionale** e toggle **`show_all`**.
- **Integrazione Sezioni Home Assistant (`getGridOptions()`):**
  - `getGridOptions()` dichiara `columns: 12, min_columns: 4, rows: "auto"` in modo che l'utente possa ridimensionare liberamente la card nelle dashboard a Sezioni di HA.

---

## 4. Architettura Responsive Adattiva (Unica Card Mobile + Desktop)

Un'unica istanza `custom:lepas-card` usa **CSS Container Queries (`container-type: inline-size`)** su `ha-card`:

- **Modalità `layout: auto` *(default)*:**
  - **`< 680px` (Smartphone / colonna dashboard stretta):** Layout **Compact a 4 Tab** (`Plancia`, `Clima`, `Ricarica`, `Sicurezza`) con barra tab segmentata e indicatore animato sotto l'Hero compatto. Target touch minimi `44×44px`, zero overflow orizzontale.
  - **`>= 680px` (Desktop / Tablet / Vista Panel / Sezione larga):** Layout **Cockpit a 3 colonne** senza bisogno di cambiare tab per vedere tutto a colpo d'occhio:
    - **Colonna Sinistra:** Hero compatto + Blueprint SVG Top-Down & TPMS + Comandi Sicurezza & Posizione.
    - **Colonna Centrale:** Griglia Metriche 2×2 + Ricarica Live & Programmata + Programmatore Partenze `v1.18.0`.
    - **Colonna Destra:** Hub Clima & Durata + Macro & Sbrinamenti + Matrice Sedili.
  - *(Su larghezze intermedie `680px..980px` la griglia Cockpit può compattarsi fluidamente a 2 colonne prima di aprire le 3 colonne sopra `980px`, senza tagli o sovrapposizioni).*
- **Modalità `layout: compact`:** Forza i 4 Tab anche su card larga (utile per chi preferisce una card compatta su desktop).
- **Modalità `layout: cockpit`:** Forza la griglia multi-colonna non appena la larghezza lo consente (`>= 560px`).

---

## 5. Mappatura Completa Entità & Comandi Reali (`Lepas v1.18.0`)

La card scopre dinamicamente le entità tramite `hass.entities` (filtrate su `platform === config.integration`) con fallback per prefisso `config.prefix`, **nascondendo o disabilitando con grazia** i controlli per cui un VIN non possiede la relativa entità (`entity_allowed` / feature gating). **Nessun dato inventato** (niente VIN in chiaro nell'header, niente SOH/tariffe/PM2.5/livelli sedili fittizi).

### 5.1 Header & Hero (Sempre Visibile)
- **Stato connessione & zona:** `binary_sensor.lepas_connection` (Online/Offline), `binary_sensor.lepas_at_home` (A casa / Fuori), `binary_sensor.lepas_car_awake` (Sveglia / A riposo).
- **Batteria SoC:** `sensor.lepas_battery` con anello SVG animato (`stroke-dashoffset`) e badge carica se `switch.lepas_charging == on` o `sensor.lepas_charging_status` attivo.
- **Sottotitolo sintetico:** `lock.lepas_lock` · `climate.lepas_climate` · `sensor.lepas_odometer` (mai VIN né coordinate GPS in chiaro).
- **Foto veicolo:** render fedele del colore scelto (con gradient scrim inferiore opaco verso `#181B20`).

### 5.2 Sezione `Plancia` (Tab 1 Mobile / Top-Center Desktop)
- **Griglia 2×2 Metriche:**
  1. **Autonomia EV:** `sensor.lepas_electric_range` (con barra proporzionale opzionale).
  2. **Autonomia Totale / Benzina:** `sensor.lepas_total_range` (o `fuel_range` / `petrol_range_miles` / `fuel_remaining`).
  3. **Ricarica:** `sensor.lepas_charging_power` + `sensor.lepas_remaining_charge_time` se in carica, altrimenti `sensor.lepas_charging_status` / `binary_sensor.lepas_charging_cable`.
  4. **Prossima Partenza / Odometro:** su Mobile `sensor.lepas_next_departure` (con orario clima) e `sensor.lepas_odometer` in header; su Desktop `sensor.lepas_odometer` + `sensor.lepas_next_departure`.
- **Banner Avvisi Dinamici** *(visibile solo quando almeno un allarme è attivo)*:
  - `binary_sensor.lepas_tire_warning_*` (4 angoli), `binary_sensor.lepas_low_battery`, `binary_sensor.lepas_connection == off`, portiere/finestrini aperti a veicolo bloccato.
- **Dock Comandi Rapidi:**
  - `lock.lepas_lock` (*Blocca* 1-tap, *Sblocca* con conferma inline),
  - `climate.lepas_climate` (toggle rapido ON/OFF al setpoint corrente),
  - `cover.lepas_trunk` (*Chiudi* 1-tap, *Apri* con conferma inline),
  - `button.lepas_find_car_flash_lights` (*Lampeggia*),
  - `button.lepas_wake_car` (*Sveglia auto*).
- **Footer:** timestamp freschezza (`sensor.lepas_car_data_updated` / `sensor.lepas_last_seen`), `sensor.lepas_command_result` inline se recente/errore, e pulsante `button.lepas_refresh_location`.

### 5.3 Sezione `Clima` (Tab 2 Mobile / Colonna Destra Desktop)
- **Hub Climatizzazione:**
  - `climate.lepas_climate`: toggle `HEAT_COOL` / `OFF`, stepper `-` / `+` sulla temperatura target (rispettando `min_temp`, `max_temp`, `target_temperature_step` reali dell'entità), lettura reale `sensor.lepas_set_temperature_left` / `right`, badge `binary_sensor.lepas_air_purification` se attivo.
  - **Durata A/C:** chip interattive sincronizzate con `number.lepas_climate_duration` (valori disponibili nel range reale `min..max` / step dell'entità, default `5 / 10 / 15 / 30 min`).
  - **Macro Comfort:** `switch.lepas_cool_everything` (*Raffredda tutto*) e `switch.lepas_heat_everything` (*Riscalda tutto*) — con pulsanti macro rapidi se presenti.
- **Sbrinamenti & Volante (4 toggle binari reali):**
  - `switch.lepas_windshield_defrost`, `switch.lepas_windshield_defog`, `switch.lepas_rear_window_heating`, `switch.lepas_steering_wheel_heating`.
- **Matrice Sedili 2×2 + Centrale:**
  - Guida (`driver_seat_heating` / `driver_seat_ventilation`), Passeggero (`passenger_seat_*`), Post. SX (`rear_left_seat_*`), Post. DX (`rear_right_seat_*`) con toggle ON/OFF reali;
  - Posteriore Centrale (`sensor.lepas_rear_center_seat_heating` / `ventilation`) come chip di sola lettura quando presente.

### 5.4 Sezione `Ricarica & Partenze` (Tab 3 Mobile / Centro-Basso Desktop)
- **Ricarica Live:**
  - Toggle `switch.lepas_charging`, stato cavo `binary_sensor.lepas_charging_cable`, presa rapida `sensor.lepas_fast_charging_port`, lettura `charging_power`, `hv_battery_voltage`, `hv_battery_current`, `remaining_charge_time`, contatori energia `home_charging_energy` e `away_charging_energy`.
- **Ricarica Programmata:**
  - Toggle `switch.lepas_scheduled_charging`, timeline 24h grafica generata dagli attributi reali di `sensor.lepas_scheduled_charging_window` (`start_time`, `end_time`, `next_day`, `days`, badge `synced_with_car`).
  - Controlli interattivi: input ora (`time.lepas_charge_start_time`), stepper/chip durata (`number.lepas_charge_duration`), selettore giorni (`select.lepas_charge_days` con preset + indicatore se il VIN usa fallback `[1..7]` per permesso `2131`) e pulsante `button.lepas_apply_charging_schedule`.
- **Programmatore Partenze (`v1.18.0`):**
  - Riepilogo `sensor.lepas_next_departure` (stato + `planned_charge_start` + `climate_mode`).
  - Toggle `switch.lepas_quick_departure` + input orario `time.lepas_quick_departure_time`, toggle `switch.lepas_sync_charge_to_departure`, selettore `select.lepas_departure_climate_mode` (`Solo a casa` / `Ovunque` / `Disattivato`).
  - Striscia compatta 7 giorni (`L M M G V S D` — `switch.lepas_departure_<day>_enabled`) con espansione inline sul giorno selezionato per modificare `time.lepas_departure_<day>_time` senza affollare la vista!

### 5.5 Sezione `Sicurezza & Gomme` (Tab 4 Mobile / Colonna Sinistra Desktop)
- **Blueprint SVG Top-Down Interattivo:**
  - Sagoma vettoriale pulita dall'alto della SUV con animazione fluida di apertura/chiusura per:
    - 4 porte (`front_left_door`, `front_right_door`, `rear_left_door`, `rear_right_door`),
    - Cofano (`hood`) e Baule (`cover.lepas_trunk` + `binary_sensor.lepas_tailgate_moving`),
    - 4 finestrini (`*_window`),
    - Tetto apribile (`cover.lepas_sunroof`, `sensor.lepas_sunroof_movement_state`) e tendina (`binary_sensor.lepas_sunroof_blind`).
  - **4 Angoli TPMS:** pressione (`sensor.lepas_tire_pressure_*`) e temperatura (`sensor.lepas_tire_temperature_*`) + stato avviso (`binary_sensor.lepas_tire_warning_*`) evidenziati sui 4 passaruota.
- **Azioni Sicurezza & Localizzazione:**
  - `lock.lepas_lock`, `cover.lepas_trunk`, `cover.lepas_windows` + `button.lepas_vent_windows`, `cover.lepas_sunroof` + `button.lepas_vent_sunroof`, `switch.lepas_alarm`, `button.lepas_remote_start`, `button.lepas_locate_car_gps`, `button.lepas_find_car_flash_lights`, più riga stato `device_tracker.lepas_location` (cliccabile per aprire il popup mappa nativo di HA via `hass-more-info`).

---

## 6. Sicurezza Operativa, UX Stato & Animazioni

### 6.1 Conferma Inline Anti-Tocco Accidentale
- **Azioni con conferma inline (2-step, finestra di 4 secondi con barra di scadenza):**
  - `lock.unlock`, apertura `cover.lepas_trunk`, apertura `cover.lepas_windows`, apertura `cover.lepas_sunroof`, `button.lepas_vent_windows`, `button.lepas_vent_sunroof`, `switch.lepas_alarm` (`turn_on` / `turn_off`), `button.lepas_remote_start`.
  - Al primo tap il pulsante mostra inline `"Conferma?"` (o `"Confirm?"` / `"Bevestig?"`) per 4 secondi senza modali invasive; al secondo tap esegue `hass.callService(...)` e mostra feedback pending locale fino all'aggiornamento stato.
- **Azioni 1-tap diretto:**
  - `lock.lock`, chiusura cover, `climate.*`, `number.*`, `time.*`, `select.*`, sedili, sbrinamenti, ricarica, partenze, `wake_car`, `refresh_location`, `find_car_flash_lights`, `apply_charging_schedule`.

### 6.2 Preservazione DOM & Stato Locale su Update `hass`
- Home Assistant invoca `set hass(hass)` ad ogni tick o variazione di qualunque entità dell'istanza.
- La card mantiene stato UI interno (`_activeTab`, `_expandedDay`, `_confirmAction` + timer, `_pendingServices`) **senza ricostruire l'intero albero Shadow DOM** se la struttura di tab/controlli non cambia, oppure preservando focus, input attivi (es. `<input type="time">` mentre l'utente sceglie l'ora) e scroll.
- Eventuali animazioni di transizione tab o apertura porte avvengono tramite classi CSS su `transform`, `opacity` e `stroke-dashoffset`, disabilitate automaticamente sotto `@media (prefers-reduced-motion: reduce)`.

### 6.3 Localizzazione & Sicurezza
- Lingua derivata da `(hass.locale?.language || hass.language || "en").slice(0, 2)` con dizionario completo `it` / `en` / `nl` (fallback `en`).
- Sanitizzazione rigorosa (`_h` escaping HTML, `_imgUrl` whitelist `https?://|/|data:image/`), zero uso di `eval` o HTML non escapato, nessun segreto/VIN/coordinata grezza stampata a schermo o in console.

---

## 7. Piano di Verifica & Test (`v1.19.0`)

- **Test unitari & contratto JS (eseguibili via `node --test` + wrapper `pytest` o verifica automatica in suite):**
  - Risoluzione immagine/colore (`grey` default, alias, fallback `image` custom).
  - Switching layout `compact` / `cockpit` / `auto`, tab switching con preservazione stato, controllo conferma inline 2-step (primo tap arma `confirm`, secondo tap chiama `hass.callService`, scadenza 4s resetta).
  - Mappatura entità reali (TPMS, clima, sedili, partenze `v1.18.0`, missing entities graceful handling, zero XSS in `title`/nomi).
- **Test Python esistenti & Versioning:**
  - Allineamento `tests/test_repo_hygiene.py` (tutti i nuovi PNG tracciati in Git e fuori da `tests/`), bump SemVer `1.19.0` sincronizzato in `manifest.json`, `pyproject.toml`, `lepas-card.js`, `CHANGELOG.md`.
- **Verifica visiva su browser reale:**
  - Servire una pagina di harness locale con stati finti realistici (carica attiva, porta aperta, clima acceso, allarme gomma) e ispezionare il rendering a **390px (Mobile)** e **1280px (Desktop)** per verificare assenza di overflow, contrasto e fluidità.
