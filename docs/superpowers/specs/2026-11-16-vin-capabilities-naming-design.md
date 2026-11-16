# Design Spec — Auto-apprendimento Capability per VIN, Fix `unknown` & Revisione Nomenclature

**Data:** 2026-11-16
**Stato:** Bozza completa da brainstorming (Opzione 1 approvata) — in attesa di conferma finale spec prima del piano implementativo
**Obiettivo:** Eliminare le entità fantasma/`unknown` non supportate dal singolo veicolo tramite auto-apprendimento per-VIN basato su `vmc/queryVehicleAuthority` (`permessi`), correggere il ripristino post-riavvio di `binary_sensor.lepas_at_home`, migliorare la leggibilità degli stati `unknown` residui e riallineare `strings.json` e le traduzioni IT/EN/NL.

---

## 1. Auto-apprendimento per VIN (`vmc/queryVehicleAuthority`) & Filtraggio Entità

### 1.1 Fonte dati & Persistenza (`DATA_CAPS_PROBED_V3`, *fail-open*)
- **Fonte primaria per optional/accessori:** `POST /tsp/v1/app/vmc/queryVehicleAuthority` (`permessi.leggi()` in `custom_components/lepas/core/permessi.py`).
  - Verifica empirica su Lepas L8 PHEV (2026-11-16): `queryList.skylightType` vale `0` anche su vettura con tetto apribile motorizzato reale, mentre `queryVehicleAuthority` riflette fedelmente tutti i `308` permessi reali del VIN (`207=1` tetto, `208=0` volante, `215=0` parabrezza elettrico, `220=0` ricarica immediata, `401=0` antifurto, `2145..2148=0` sedili posteriori, `2141..2144=1` sedili anteriori, `2045=1` disappannamento clima, `232=1` lunotto).
- **Raccolta:**
  - In `config_flow.py` (`_discover` / `async_step_pick` o creazione entry) e nel backfill di `coordinator.py` (`_fetch_vehicle_identity` / `async_ensure_vehicle_identity`): accanto a `vmc/queryList`, chiamare in sola lettura `permessi.leggi(ctx, token, tuid)` (usando il `token` e `tuid` già risolti, senza refresh OAuth concorrenti né PIN) e aggiornare `self._ctx.permessi` se valorizzato.
  - Introdurre il marcatore versionato `DATA_CAPS_PROBED_V3` in `const.py` così anche le installazioni esistenti con `DATA_CAPS_PROBED_V2` rieseguano la lettura **una sola volta** al primo avvio dopo l'aggiornamento.
- **Persistenza compatta in `entry.data`:**
  - Chiave `DATA_VEHICLE_FEATURES = "vehicle_features"`: dizionario `dict[str, bool]` contenente solo le feature booleane derivate dai permessi (non l'intero payload da 308 ID).
  - **Regola *fail-open*:** se `permessi.leggi()` fallisce per rete (`IGNOTO`) o un ID permesso è assente dalla risposta, quella feature **non** viene marcata `False` (default `True` = visibile). Solo un esplicito `0` dal backend imposta `False`.

### 1.2 Tabella Mappatura Feature → Entità HA
Ogni feature è calcolata da una funzione pura in `const.py` (`features_from_permissions(perms: dict[int, int]) -> dict[str, bool]`):

| Feature key | Regola esplicita `False` (`0` nel dict `perms`) | Entità escluse se `False` |
| :--- | :--- | :--- |
| `steering_wheel_heating` | `208 == 0` o (`2081 == 0` e `2082 == 0`) | `switch.lepas_steering_wheel_heating` |
| `front_windshield_electric` | `215 == 0` e (`20416 == 0` o `20416 not in perms`) | `switch.lepas_windshield_defrost` |
| `front_windshield_defog` | `2045 == 0` | `switch.lepas_windshield_defog`, `binary_sensor.lepas_windshield_heating` |
| `rear_window_heating` | `232 == 0` e (`20411 == 0` o `20411 not in perms`) | `switch.lepas_rear_window_heating` |
| `instant_charging` | `220 == 0` | `switch.lepas_charging` |
| `scheduled_charging` | `213 == 0` | `switch.lepas_scheduled_charging` |
| `alarm` | `401 == 0` | `switch.lepas_alarm` (salta anche `querySwitch`), `button.lepas_alarm_on`, `button.lepas_alarm_off` |
| `driver_seat_heating` | `2141 == 0` e `2047 == 0` | `switch.lepas_driver_seat_heating` |
| `driver_seat_ventilation` | `2143 == 0` e `2049 == 0` | `switch.lepas_driver_seat_ventilation` |
| `passenger_seat_heating` | `2142 == 0` e `2048 == 0` | `switch.lepas_passenger_seat_heating` |
| `passenger_seat_ventilation` | `2144 == 0` e `20410 == 0` | `switch.lepas_passenger_seat_ventilation` |
| `rear_left_seat_heating` | `2145 == 0` e `20412 == 0` | `switch.lepas_rear_left_seat_heating` |
| `rear_left_seat_ventilation` | `2147 == 0` e `20414 == 0` | `switch.lepas_rear_left_seat_ventilation` |
| `rear_right_seat_heating` | `2146 == 0` e `20413 == 0` | `switch.lepas_rear_right_seat_heating` |
| `rear_right_seat_ventilation` | `2148 == 0` e `20415 == 0` | `switch.lepas_rear_right_seat_ventilation` |
| `rear_center_seat` | tutti i sedili posteriori `2145..2148 == 0` | `sensor.lepas_rear_center_seat_heating`, `sensor.lepas_rear_center_seat_ventilation` *(inoltre `isBackCenter` è `false` nell'APK)* |
| `sunroof` | `207 == 0` | `cover.lepas_sunroof`, `button.lepas_vent_sunroof`, `sensor.lepas_sunroof_movement_state`, `binary_sensor.lepas_sunroof_blind` |
| `windows` | `206 == 0` | `cover.lepas_windows`, `button.lepas_vent_windows`, `binary_sensor.lepas_*_window` (4) |
| `trunk` | `205 == 0` | `cover.lepas_trunk`, `binary_sensor.lepas_tailgate_moving` |
| `locks` | `203 == 0` | `lock.lepas_lock` |
| `find_car` | `202 == 0` | `button.lepas_find_car_flash_lights` |
| `air_purification` | `2046 == 0` | `binary_sensor.lepas_air_purification` |
| `climate` | `204 == 0` | `climate.lepas_climate`, `number.lepas_climate_duration` |
| `cool_everything` | `210 == 0` e `204 == 0` | `switch.lepas_cool_everything`, `button.lepas_cool_everything`, `button.lepas_cool_everything_off` |
| `heat_everything` | `209 == 0` | `switch.lepas_heat_everything`, `button.lepas_heat_everything`, `button.lepas_heat_everything_off` |

### 1.3 `sunshadeState` & Pulizia Registro Entità
- **`binary_sensor.lepas_sunroof_blind` (`sunshadeState`):** nell'APK ufficiale ha `0` occorrenze (`rus_car_state_model.dart`), ma il veicolo ha tendina fisica e non è ancora stato catturato un push `5A02` durante il movimento tetto/tendina. Impostiamo **`_attr_entity_registry_enabled_default = False`** (e solo se `sunroof` è `True`; se `sunroof` è `False`, esclusa del tutto). Sulle installazioni esistenti in cui non è ancora disabilitata dall'utente, la disabilitiamo con `RegistryEntryDisabler.INTEGRATION` se mai popolata, o semplicemente la lasciamo disabilitabile/riattivabile senza rumore `unknown`.
- **Pulizia entità confermate `False`:** dopo aver salvato/letto `vehicle_features` (e al setup in `__init__.py` prima di `async_forward_entry_setups` se `DATA_CAPS_PROBED_V3` è già presente), rimuoviamo dal registro entità (`er.async_get(hass).async_remove(...)`) le entità di questo `entry_id` mappate alle feature esplicitamente `False` in `vehicle_features` (mai toccare entità di altri `entry_id` o con feature `None`/`True`), evitando entità orfane `unavailable`.
- **Reload sicuro al backfill:** quando `async_ensure_vehicle_identity` popola per la prima volta `DATA_CAPS_PROBED_V3` e `vehicle_features` contiene almeno una feature `False`, schedula `hass.config_entries.async_schedule_reload(self.entry.entry_id)` una volta sola (così le piattaforme si riallineano subito senza attendere il riavvio manuale).

---

## 2. Fix `at_home` & Miglioramento Stati `unknown` Residui

1. **`binary_sensor.lepas_at_home` (e zona ricarica) post-riavvio:**
   - Aggiungere in `LepasCoordinator` il metodo `restore_position(self, lat: float, lon: float) -> None`:
     - Sotto `self._state_lock`, solo se `self.data.get("position") is None` e `self.position is None`, imposta `geo = {"lat": lat, "lon": lon}` in `self.position` e aggiorna `self.data` tramite `self._update({"position": dict(geo)})` (senza toccare `last_pos_fix`, così in diagnostica rimane tracciabile la differenza tra fix live e posizione ripristinata).
   - Chiamare `self.coordinator.restore_position(self._restored_lat, self._restored_lon)` alla fine di `LepasTracker.async_added_to_hass()` (`device_tracker.py`) quando entrambi i valori sono validi.
   - Effetto: `binary_sensor.lepas_at_home` e `in_zona_casa` (`home_charging_energy` / `away_charging_energy`) funzionano subito dopo ogni riavvio di HA.

2. **`sensor.lepas_remaining_charge_time` (`remainChargeTime`) → `0 min` a carica ferma:**
   - In `LepasRealtimeSensor.native_value` (`sensor.py`), quando `self._spec.volatile` (`remainChargeTime`):
     - Se `_live_value()` è valorizzato → restituisce il valore numerico live.
     - Se `_live_value()` è `None`: se l'auto **non è in carica** (`not _in_ricarica(_rt(self.coordinator, "chargeState"))`), restituisce **`0`** (`0 min`). Se invece `chargeState` indica ricarica attiva ma `remainChargeTime` manca transitoriamente, restituisce `None` (`unknown`) per non mostrare un falso `0 min`.
   - Aggiornare il test di regressione `test_tempo_ricarica_sparisce_a_carica_finita` in `tests/test_sensors.py` affinché verifichi `0` / `"0"` al passaggio a `_A_RIPOSO` (`chargeState = "0"`).

3. **`sensor.lepas_sunroof_movement_state` (`sunroofMoveState`) → `"In attesa"`:**
   - In `LepasFieldSensor._live_value()` (`sensor.py`), quando `self._key == "sunroofMoveState"` e non esiste né valore live né `_restored` (in `native_value`), restituisce `"In attesa"` (o `"Waiting"` se `hass.config.language` non inizia per `"it"`). Appena arriva un `5A02` reale, mostra e conserva il valore ricevuto.

4. **Sensori diagnostici esiti HA (`command_result`, `wake_up_result`, `location_probe_result`) → `"In attesa"`:**
   - Restano in `EntityCategory.DIAGNOSTIC` come pannello di controllo per i comandi/azioni inviati da Home Assistant.
   - In `LepasTextSensor.native_value` (`sensor.py`), quando `_live_value()` è `None`, restituisce `"In attesa"` (o `"Waiting"` se lingua non `"it"`) al posto di `unknown`, mantenendo la protezione anti-stantio (`_restored` continua a non essere usato per vecchi esiti di ieri).

5. **`binary_sensor.lepas_windshield_heating` (`fWinHeatingState`):**
   - Resta abilitato (legato alla feature `front_windshield_defog` / `2045`) con nome chiarito per distinguerlo dal parabrezza elettrico `215`.

---

## 3. Revisione Nomenclature & Traduzioni (`strings.json`, `it.json`, `en.json`, `nl.json`)

Tutti gli `entity_id` esistenti restano **invariati** per retrocompatibilità di automazioni e recorder.

### 3.1 Fix in `strings.json` (template base inglese)
- `entity.binary_sensor.at_home.name`: `"A casa"` → `"At home"`
- `entity.sensor.home_charging_energy.name`: `"Energia ricarica a casa"` → `"Home charging energy"`
- `entity.sensor.away_charging_energy.name`: `"Energia ricarica fuori casa"` → `"Away charging energy"`

### 3.2 Affinamento nomi approvati (allineati in `strings.json`, `en.json`, `it.json` e `nl.json`)

| Chiave entità | Nuovo nome IT (`it.json`) | Nuovo nome EN (`strings.json` / `en.json`) | Nuovo nome NL (`nl.json`) |
| :--- | :--- | :--- | :--- |
| `switch.windshield_defrost` | `"Sbrinamento elettrico parabrezza"` | `"Heated windshield"` | `"Voorruitverwarming"` |
| `binary_sensor.windshield_heating` | `"Disappannamento parabrezza (stato)"` | `"Windshield defog status"` | `"Voorruitontwaseming (status)"` |
| `binary_sensor.tailgate_moving` | `"Baule in movimento"` | `"Trunk moving"` | `"Kofferbak beweegt"` |
| `binary_sensor.charging_cable` | `"Cavo di ricarica"` | `"Charging cable"` | `"Laadkabel"` *(invariato se già corretto)* |
| `sensor.hv_battery_voltage` | `"Tensione alta tensione"` | `"HV battery voltage"` | `"Hoogspanning batterijspanning"` *(invariato se già corretto)* |
| `sensor.hv_battery_current` | `"Corrente alta tensione"` | `"HV battery current"` | `"Hoogspanning batterijstroom"` *(invariato se già corretto)* |

---

## 4. Vincoli di Sicurezza, Qualità e Test
- **Nessuna modifica a `channelId = "6"` né a `LepasConfigFlow.VERSION = 2`** (migrazione `v1 → v2` già completata e verificata in `v1.16.5`).
- **Crash Antibodies (`AB-LEP-001`..`AB-LEP-006`):** nessuna chiamata extra a `checkPassword`, nessun refresh token concorrente, redazione rigorosa di VIN/PII in `diagnostics.py` e log.
- **Test falsificabili previsti:**
  - `features_from_permissions()` (fail-open su vuoto/parziale, esclusione su `0` esplicito, caso reale Lepas L8 `308` voci, caso UK con `215=1`, `208=1`, `2145..2148=1`).
  - Setup & cleanup registro entità HA con `MockConfigEntry` (`vehicle_features` con feature `False`, marcatore `DATA_CAPS_PROBED_V3`).
  - `LepasTracker` restore → `coordinator.data["position"]` → `binary_sensor.lepas_at_home` popolato subito dopo boot senza GPS live.
  - `remaining_charge_time` → `0` a carica ferma (`chargeState="0"`), valore reale durante ricarica (`chargeState="1"`).
  - `LepasTextSensor` & `sunroofMoveState` → `"In attesa"` / `"Waiting"` prima del primo evento, poi valore live.
  - Allineamento `strings.json` vs `translations/{en,it,nl}.json` (nessuna stringa italiana in `strings.json`, parità chiavi 100%).
