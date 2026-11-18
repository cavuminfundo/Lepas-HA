# Design Spec — Native Scheduled Departure (`travelAppointControl`), Battery Preheating (`batteryPackHeat`) & Dynamic Departure Climate Extras

**Data:** 2026-11-18  
**Stato:** Design approvato in brainstorming — pronto per piano implementativo (`writing-plans`)  
**Target SemVer:** `v1.21.0` *(minor SemVer: nuove feature, entità HA, servizi e controlli Card Lovelace)*

---

## 1. Contesto & Schemi Verificati da `com.chery.eu.lepas` (`libapp.so`)

Analisi ARM64 + Dart 3.10.9 (`BASE_STR_OID = 1182`) di `libapp.so` e confronto con l'integrazione esistente (`custom_components/lepas/`):

1. **Partenza programmata nativa (`travelAppointControl` / `travelAppointQuery`) — Cat. `212`:**
   - **Permessi (`RusPermissionsProvider`)**: categoria radice **`212`**, ciclo personalizzato **`2121`** (`canAppointmentTravelWeek`), ciclo 7 giorni **`2122`**, multi-piano **`2124`**. Su veicoli EU noti (`CHERY_PHEV_EU` e Lepas L8), `212=1`, `2121=1`, `2122=0`, e `realtime["appointmentTravelSetVOS"]` mostra piani attivi con giorni `[1..7]` o `[1..5]`.
   - **Body request (`CVAppointGoParam` → `/asc/vehicleControl/travelAppointControl`)**:
     ```json
     {
       "mainSwitcher": "1",
       "appointmentTravelSetVOS": [
         {
           "planId": 1,
           "switcher": "1",
           "travelTime": "305",
           "travelWeekday": "1,2,3,4,5"
         }
       ]
     }
     ```
     - `id`: preservato da `realtime["appointmentTravelSetVOS"][0]["id"]` / `travelAppointQuery` quando presente, altrimenti omesso.
     - `travelTime`: minuti dalla mezzanotte **UTC** (`str(utc_minutes)`), convertiti dal fuso locale HA con slittamento giorno al passaggio della mezzanotte UTC (`CommonUtils.dateTimeZone(type=2)`).
     - `travelWeekday`: giorni **UTC** `1..7` formattati in stringa CSV (`"1,2,3..."` o `str` come costruito prima di `CVAppointGoDetail`), slittati di `day_delta` (`-1` / `+1`) quando la conversione Locale→UTC attraversa la mezzanotte.
     - I campi locali del bridge Android (`swi`, `firstAsyncTimeOut`, `secondAsyncTimeOut`) vengono omessi sul livello TSP (esattamente come `chargeAppointControl`); `send()` aggiunge `clientType`, `seq`, `taskId`, `vin`, `appId`, `sign`.
   - **Query read-only**: `query_travel_appoint(ctx)` chiama `/asc/vehicleControl/travelAppointQuery` (fallback `/asd/travelAppointManage/travelAppointQuery`) solo su richiesta / sveglia, mai durante il polling passivo ad auto spenta (`AB-LEP-001`).

2. **Preriscaldamento / Isolamento Batteria Plug-in (`batteryPackHeat` / `queryBatteryPackHeat`) — Cat. `216`:**
   - **Permessi (`RusPermissionsProvider`)**: categoria **`216`** (`canBatteryInsulation`). Gestita in modalità fail-open se assente e nascosta automaticamente (`entity_allowed`) se `perms[216] == 0` (evitando rifiuti `A00084`).
   - **Body request (`CVBatteryPackHeatParam` → `/asc/vehicleControl/batteryPackHeat`)**:
     ```json
     {
       "switchState": "1",
       "startTime": "305"
     }
     ```
     - `switchState`: `"1"` (ON) o `"0"` (OFF).
     - `startTime`: minuti dalla mezzanotte **UTC** come stringa numerica, convertiti dal fuso locale HA (`CommonUtils.dateTimeZone(type=2)` con `week=["0"]`).
   - **Query read-only**: `query_battery_pack_heat(ctx)` chiama `/asc/vehicleControl/queryBatteryPackHeat` e riconverte `data.startTime` UTC→Locale (`type=1`).

3. **`prepareScheduledControl` / `StandByPlan` (`Cat. 233..236`) — Escluso (YAGNI):**
   - Payload da 38 campi negato (`0`) sui PHEV EU noti; i controlli clima di partenza vengono orchestrati dinamicamente dal motore HA esistente.

---

## 2. Architettura Ibrida: Partenza + Batteria + Clima Dinamico HA

Tutti gli `entity_id` e servizi della v1.20.x restano **100% compatibili**.

### 2.1 Conversione Timezone Pura (`scheduler.py`)
- `local_schedule_to_utc(local_minutes: int, local_days: Sequence[int] | None, tzinfo) -> tuple[int, list[int]]`: calcola su `datetime` locale odierno in `tzinfo` (gestendo CET/CEST e zone IANA) la traslazione a `.astimezone(timezone.utc)`, ricava `utc_minutes = utc_dt.hour * 60 + utc_dt.minute` e `day_delta = (utc_dt.date() - local_dt.date()).days`, spostando ogni giorno `1..7` con `((d - 1 + day_delta) % 7) + 1`.
- `utc_schedule_to_local(utc_minutes: int, utc_days: Sequence[int] | None, tzinfo) -> tuple[int, list[int]]`: operazione inversa per `query_battery_pack_heat` / `appointmentTravelSetVOS`.
- `compute_battery_heat_start_for_departure(departure_minutes: int, lead_minutes: int = 30) -> int`: calcola `(departure_minutes - lead_minutes) % 1440` (anticipando il preriscaldamento batteria rispetto a $T_{\text{dep}}$).

### 2.2 Sincronizzazione Partenza Nativa (`travelAppointControl`)
- **`switch.lepas_native_departure_sync`** *(Config, `RestoreEntity`, default `OFF`, gated `scheduled_departure_control` / cat. `212`)*:
  - Quando attivo, a ogni modifica dello scheduler (`notify_schedule_changed`) o alla scadenza della partenza veloce:
    - se esiste `quick_departure_enabled` con target `occ.source == "quick"`, invia `travelAppointControl` con `mainSwitcher="1"`, `switcher="1"`, orario UTC di `quick` e `[occ.weekday]` (o fallback se `2121==0`);
    - altrimenti se ci sono giorni settimanali attivi, invia `travelAppointControl` con l'orario della prossima occorrenza settimanale e i giorni settimanali attivi abilitati a quell'orario (o i giorni settimanali attivi);
    - se nessuna partenza (né rapida né settimanale) è attiva, invia `partenza_prog_off` (`mainSwitcher="0"`, `switcher="0"`).
  - Deduplica per firma `(main_switcher, utc_min, tuple(utc_days))` + anti-retry-storm (`_last_synced_native_dep_sig` / `_last_attempted_native_dep_sig`), azzerati al cambio configurazione.
- **`button.lepas_apply_departure_schedule`** *(Config, gated `212`)*: invia manualmente su `travelAppointControl` lo stato corrente (incluso spegnimento `mainSwitcher="0"` se non ci sono partenze attive).
- **`sensor.lepas_scheduled_departure`**: aggiunge l'attributo `synced_with_ha` (`bool | None`) confrontando `appointmentTravelSetVOS` in `realtime` con l'ultima configurazione HA attesa.

### 2.3 Preriscaldamento Batteria Plug-in (`batteryPackHeat`, gated `216`)
- **`switch.lepas_battery_pack_heat`** *(Config, `LepasOptimisticMixin` + `RestoreEntity`, gated `battery_pack_heat`)*: legge lo stato da `fields["batteryPackHeatState"]` / cache `queryBatteryPackHeat` e invia `battery_heat_on` / `battery_heat_off` usando `coordinator.battery_heat_minutes`.
- **`time.lepas_battery_pack_heat_time`** *(Config, `RestoreEntity`, default `07:00`, gated `battery_pack_heat`)*: imposta `coordinator.battery_heat_minutes`; se `switch.lepas_battery_pack_heat` è ON al cambio orario (o tramite servizio), aggiorna `batteryPackHeat`.
- **`switch.lepas_sync_battery_heat_to_departure`** *(Config, `RestoreEntity`, default `OFF`, gated `battery_pack_heat`)*: emula l'app ufficiale legando `batteryPackHeat` alla partenza programmata (rapida o settimanale). Quando attivo, calcola `T_dep - 30 min` su `coordinator.battery_heat_minutes` e sincronizza `batteryPackHeat` (`switchState="1"`) insieme alla partenza (deduplicato per firma `(occ_iso_or_key, utc_min)`).
- Quando una **Partenza veloce** termina ed entra in auto-reset, il coordinator riesegue il sync sia di `travelAppointControl` (ripristina il piano settimanale o spegne con `mainSwitcher="0"`) sia di `batteryPackHeat` (riallinea o spegne se non ci sono altre partenze attive).

### 2.4 Clima Intelligente + Extra Dinamici alla Partenza
- Manteniamo invariato il pre-clima base in `_maybe_trigger_preclimate()`: all'ora $T_{\text{clima}} = T_{\text{dep}} - \text{durata\_clima}$ (con guardie `at_home`/`anywhere`/`off`, `engineState == 0`, `vehicleSpeed == 0`) invia `clima_on` (`temperature` da `climate.lepas_climate`, `times` da `number.lepas_climate_duration`).
- **Extra dinamici configurabili (`coordinator.departure_climate_extras: list[str]`)**:
  - Chiavi supportate mappate ai comandi reali in `core/commands.py` + gating `entity_allowed`:
    - `driver_seat_heating` (`sedile_guida_caldo`), `driver_seat_ventilation` (`sedile_guida_aria`) — mutua esclusione
    - `passenger_seat_heating` (`sedile_passeggero_caldo`), `passenger_seat_ventilation` (`sedile_passeggero_aria`) — mutua esclusione
    - `rear_left_seat_heating` (`sedile_post_sx_caldo`), `rear_left_seat_ventilation` (`sedile_post_sx_aria`) — mutua esclusione
    - `rear_right_seat_heating` (`sedile_post_dx_caldo`), `rear_right_seat_ventilation` (`sedile_post_dx_aria`) — mutua esclusione
    - `rear_window_heating` (`defrost_lunotto`)
    - `windshield_defrost` (`defrost_parabrezza`)
    - `windshield_defog` (`disappanna_parabrezza`)
    - `steering_wheel_heating` (`volante_caldo`)
  - Filtrati automaticamente contro le feature del VIN (`entity_allowed`) e inviati in sequenza subito dopo `clima_on` (senza bloccare o ritentare in loop su errore parziale del singolo extra).
  - Persistiti senza entità booleane extra tramite `RestoreEntity` su `sensor.lepas_next_departure` (attributo `climate_extras: list[str]`) e modificabili via servizio `lepas.set_departure_climate_extras`.

---

## 3. Servizi HA & Card Lovelace (`services.yaml`, `lepas-card.js`)

1. **Servizi (`__init__.py` + `services.yaml`)**:
   - `lepas.set_quick_departure`: aggiunge campo opzionale `apply_native: bool` (se `True`, forza `travelAppointControl` + eventuale `batteryPackHeat` anche se `native_departure_sync` è OFF).
   - `lepas.set_departure_climate_extras`: parametri `entry_id` (opz.), `extras: list[str]`.
   - `lepas.set_battery_pack_heat`: parametri `entry_id` (opz.), `enabled: bool` (opz.), `time: HH:MM` (opz.), `sync_to_departure: bool` (opz.).
2. **Card Lovelace ([lepas-card.js](file:///home/federico/Lepas/custom_components/lepas/lovelace/lepas-card.js))**:
   - Nel pannello *"Partenze programmate"* (`depHtml`):
     - Toggle **"Sync su auto"** (`switch.lepas_native_departure_sync`) + pulsante **"Applica partenza"** (`button.lepas_apply_departure_schedule`);
     - Sezione compatta **"Extra clima alla partenza"** con chip dinamici cliccabili per i soli accessori disponibili sull'auto (`climate_extras` su `sensor.lepas_next_departure`), aggiornati via `lepas.set_departure_climate_extras`;
     - Sotto-box **"Preriscaldamento batteria"** (visibile solo se cat. `216` espone le entità su HA): ON/OFF, `<input type="time">` e toggle **"Allinea alla partenza"**.
   - Localizzazione completa IT/EN/NL in `strings.json`, `translations/{it,en,nl}.json`, `I18N` in `lepas-card.js`, e `test_entity_count.py` aggiornato (`129 → 134` entità deliberate: `+3 switch`, `+1 button`, `+1 time`).
