# Specifica: Sensori di Consumo a Lunga Durata (EV / Ibrida) e Integrazione Card

**Data:** 2026-11-19
**Stato:** Design approvato dall'utente (in attesa di revisione specifica e piano implementativo)
**Ambito:** `custom_components/lepas/*`, `custom_components/lepas/lovelace/lepas-card.js`, `tests/*`

---

## 1. Contesto e Obiettivo

La piattaforma Chery EU / Lepas L8 (`/asr/manager/realtime`) fornisce nativamente solo le medie mobili sugli ultimi 50 km del quadro strumenti (`averageFuel` in `L/100 km` e `avgHkPowerKwh50km` in `kWh/100 km`). Il veicolo non trasmette contatori trip A/B (`aOdoMeter`, `bOdoMeter`), consumo istantaneo (`insFuelConsum`) né un campo esplicito `drivingMode`.

L'obiettivo è introdurre in Home Assistant **6 nuovi sensori persistenti a lunga durata**, suddivisi per singola modalità di propulsione (**Solo Elettrica / EV** e **Ibrida / HEV**) su **3 orizzonti** (`100 km`, `1000 km`, `From Start`), un pulsante di reset per `From Start`, la capacità batteria utilizzabile configurabile nelle Opzioni e un riquadro compatto dedicato nella tab **Overview** di `lepas-card.js`.

---

## 2. Architettura e Decisioni Chiave

1. **Finestre per singola modalità**: `100 km` e `1000 km` misurano rispettivamente gli ultimi 100 km / 1000 km percorsi *in modalità EV* e gli ultimi 100 km / 1000 km percorsi *in modalità Ibrida*, evitando che percorrenze prevalenti in una modalità svuotino o falsino la finestra dell'altra.
2. **6 sensori principali + bilancio elettrico negli attributi Ibridi**:
   - **EV** (`kWh/100 km`): `100 km`, `1000 km`, `From Start`
   - **Ibrida** (`L/100 km`): `100 km`, `1000 km`, `From Start` (con attributo `electric_consumption_kwh_100km` per il bilancio elettrico netto in modalità ibrida, oltre a `sampled_km`, `window_target_km`, `progress_pct`, `energy_kwh`, `fuel_l`).
3. **Media progressiva sotto soglia**: prima di raggiungere `100 km` o `1000 km` nella singola modalità, i sensori mostrano la media reale progressiva non appena superata una soglia anti-rumore (`5.0 km` per EV, `10.0 km` per Ibrida per attenuare la quantizzazione a `1 L` di `oilSurplus`). Sotto soglia il valore resta `None` (`unknown`).
4. **Persistenza autonoma (`Store`)**: lo stato dei segmenti e dei totali *From Start* viene salvato tramite `homeassistant.helpers.storage.Store` (`lepas.<entry_id>.consumption`), indipendente dal `recorder` SQLite (che di default purga dopo 10 giorni) e resiliente ai riavvii di Home Assistant.
5. **Capacità batteria HV configurabile**: poiché `dumpEnergy` è espresso in `%` (nessun campo API in `kWh`), la conversione `% → kWh` usa l'opzione configurabile `battery_capacity_kwh` in `LepasOptionsFlow` con default **`18.4` kWh** (Lepas L8 PHEV).

---

## 3. Motore di Calcolo (`custom_components/lepas/consumption.py`)

Modulo puro Python (zero dipendenze dal loop Home Assistant, 100% testabile in isolamento):

- **Costanti**:
  - `DEFAULT_BATTERY_CAPACITY_KWH = 18.4`
  - `WINDOW_100_KM = 100.0`
  - `WINDOW_1000_KM = 1000.0`
  - `MAX_STEP_GAP_KM = 50.0`
  - `MIN_SAMPLE_KM_EV = 5.0`
  - `MIN_SAMPLE_KM_HYBRID = 10.0`
- **Ingestione (`ConsumptionTracker.ingest`)**:
  - Input: `odometer`, `soc_pct`, `fuel_l`, `engine_on`, `charging_or_plugged`, `degraded_battery`, `battery_capacity_kwh`.
  - Scarta frame invalidi o segnaposto (`odometer is None or odometer <= 0`, `degraded_battery`, `soc_pct is None or soc_pct <= 0`).
  - **Primo campione valido**: inizializza i baseline (`last_odo`, `last_soc`, `last_fuel`) senza generare segmenti.
  - **Gap/Anomalie**: se `delta_km < 0` o `delta_km > MAX_STEP_GAP_KM` (es. viaggio con `poll_enabled` spento), riallinea i baseline senza sporcare le medie.
  - **Veicolo fermo / Ricarica / Rifornimento (`delta_km == 0`)**: aggiorna `last_soc` se in carica o in crescita e `last_fuel` se in crescita (rifornimento da fermo), senza creare segmenti di percorrenza.
  - **Segmento valido (`0 < delta_km <= MAX_STEP_GAP_KM`)**:
    - **Modalità**: `"hev"` se `engine_on` è `True`, altrimenti `"ev"`.
    - **Carburante**: se `fuel_l` e `last_fuel` sono validi, `fuel_used = 0.0` se `fuel_l > last_fuel` (rifornimento), altrimenti `last_fuel - fuel_l`.
    - **Elettrico**: se `charging_or_plugged` è `True`, `kwh_used = 0.0`; altrimenti `kwh_used = ((last_soc - soc_pct) / 100.0) * battery_capacity_kwh`.
    - Accoda il micro-segmento alla coda FIFO della modalità (`ev_segments` o `hev_segments`), taglia proporzionalmente il segmento più vecchio se la somma supera `1000.0 km`, e aggiorna i totali cumulativi `from_start`.
- **Calcolo finestra (`window_stats(mode, target_km)`)**:
  - Scorre i segmenti dal più recente al più vecchio fino a `target_km` (`100.0` o `1000.0`), scalando proporzionalmente il segmento al bordo della finestra; per `target_km is None` legge i cumulativi `from_start`.
- **Reset (`reset_from_start()`)**:
  - Azzera `ev_km`, `ev_kwh`, `hev_km`, `hev_fuel_l`, `hev_kwh` dei contatori `from_start` mantenendo intatte le code mobili `100 km` / `1000 km` e i baseline correnti.

---

## 4. Integrazione Coordinator, Entità & Opzioni

- **`coordinator.py`**:
  - Lock dedicato `self._consumption_lock = threading.Lock()` (mai annidato con `_state_lock` o `_hv_lock` per rispetto di `AB-LEP-007` / `AB-LEP-014`).
  - Caricamento asincrono dello `Store` all'avvio (`async_load_consumption`), salvataggio debounced (`async_delay_save`) ad ogni variazione in `_on_probe_data`, e flush sincronizzato allo scaricamento (`async_flush_consumption` in `async_unload_entry` / `async_stop`).
  - Espone `consumption_stats(mode, target_km)` e `async_reset_consumption_from_start()`.
- **Nuove entità**:
  - `sensor.py` (`LepasConsumptionSensor(LepasEntity, SensorEntity)`):
    - `sensor.lepas_ev_consumption_100km` (`translation_key="ev_consumption_100km"`, `kWh/100 km`, `MEAS`)
    - `sensor.lepas_ev_consumption_1000km` (`translation_key="ev_consumption_1000km"`, `kWh/100 km`, `MEAS`)
    - `sensor.lepas_ev_consumption_from_start` (`translation_key="ev_consumption_from_start"`, `kWh/100 km`, `MEAS`)
    - `sensor.lepas_hybrid_consumption_100km` (`translation_key="hybrid_consumption_100km"`, `L/100 km`, `MEAS`) — nascosto su BEV (`is_pure_electric()`)
    - `sensor.lepas_hybrid_consumption_1000km` (`translation_key="hybrid_consumption_1000km"`, `L/100 km`, `MEAS`) — nascosto su BEV
    - `sensor.lepas_hybrid_consumption_from_start` (`translation_key="hybrid_consumption_from_start"`, `L/100 km`, `MEAS`) — nascosto su BEV
  - `button.py` (`LepasActionButton`):
    - `button.lepas_reset_consumption_from_start` (`EntityCategory.CONFIG`, `translation_key="reset_consumption_from_start"`, icona `mdi:restart`).
- **Config Flow (`config_flow.py` & `const.py`)**:
  - `CONF_BATTERY_CAPACITY_KWH = "battery_capacity_kwh"` in `LepasOptionsFlow` (`5.0..150.0` kWh, step/float, default `18.4`).
- **Traduzioni**:
  - Chiavi sincronizzate in `strings.json`, `translations/en.json`, `translations/it.json`, `translations/nl.json`.

---

## 5. Integrazione Lovelace Card (`lepas-card.js`)

- Nella tab **Overview**, subito sotto `.metrics-grid`, nuovo pannello compatto `.surface` (**Consumi medi / Average consumption**):
  - **Riga EV (`kWh/100 km`)**: `50 km` (`sensor.lepas_average_energy_consumption`) · `100 km` · `1000 km` · `Da inizio`.
  - **Riga Ibrida (`L/100 km`)**: `50 km` (`sensor.lepas_average_fuel_consumption`) · `100 km` · `1000 km` · `Da inizio` (nascosta automaticamente se il veicolo è BEV / assenti i sensori ibridi).
  - Ogni cella espone `data-e="<entity_id>"` così il click/tastiera apre il popup nativo `hass-more-info` di Home Assistant.
  - Traduzioni complete `it`, `en`, `nl` in `I18N`.

---

## 6. Verifica e Criteri di Successo

- Test unitari puri su `ConsumptionTracker` (EV/HEV, rifornimenti, ricariche, frame degradati, gap `> 50 km`, taglio proporzionale `100/1000 km`, persistenza JSON, soglie minime, reset `From Start`).
- Test HA su `sensor.py`, `button.py`, `coordinator.py`, `config_flow.py`, `test_entity_count.py`, `test_traduzioni_complete.py`, `test_translation_key_declared.py`.
- Test JS Node (`tests/lepas_card.test.mjs`) per rendering blocco consumi, caso BEV, click `hass-more-info`, traduzioni IT/EN/NL.
- `uv run ruff check custom_components/ tests/` e `uv run ruff format --check custom_components/ tests/` verdi.
