# Crash Antibodies — Lepas (Chery EU Connected Vehicle Integration)

## [AB-LEP-001] Chery EU Auth Token Refresh Serialization & 12V Battery Drain Guard
- **Target Files**: `custom_components/lepas/**/*.py`
- **Root Cause**: Richieste concorrenti di refresh del token OAuth Chery EU invalidano il refresh token attivo, e un polling forzato (`wake_up`) troppo frequente a veicolo spento scarica la batteria 12V.
- **Invariant**: Serializzare il refresh del token sotto `asyncio.Lock` nel `DataUpdateCoordinator` e rispettare rigorosamente il backoff passivo quando il veicolo è in stato `sleep`/parcheggiato.
- **onFailure Mandate**: Su errore `401/403` dopo 1 retry sotto lock, sollevare `ConfigEntryAuthFailed` senza ciclare in loop.
- **Forbidden Regex**: `while\s+True:\s*await\s+self\.async_refresh_token`

## [AB-LEP-002] `ID_PREFIX = "lepas"` Entity Registry Alignment & PII Redaction
- **Target Files**: `custom_components/lepas/**/*.py`
- **Root Cause**: L'uso di prefissi incoerenti (`chery_` vs `lepas_`) duplica le entità nel registro di Home Assistant, e il log raw dei payload API espone VIN, coordinate GPS e token.
- **Invariant**: Tutte le `unique_id` devono usare `ID_PREFIX = "lepas"` e i log diagnostici devono oscurare `vin`, `lat`, `lon`, `access_token` e `refresh_token`.
- **onFailure Mandate**: Filtrare i campi sensibili tramite `async_redact_data` prima di qualsiasi output di diagnostica o log.
- **Forbidden Regex**: `_LOGGER\.(?:info|warning|error)\([^)]*access_token`

## [AB-LEP-003] Secondary Account `tUserId == "0"` Normalization, APK URL Strip & Hard Gate
- **Target Files**: `custom_components/lepas/core/{lepas_auth,wake,commands,provision,permessi}.py`, `custom_components/lepas/{config_flow,coordinator,diagnostics}.py`
- **Root Cause**: Sugli account secondari/condivisi `POST /tsp/v1/app/auth/login` restituisce `"tUserId": "0"` (truthy in Python) causando `A00361` in `checkPassword`; `lepas_auth` firmava `/tsp/...` invece di `/v1/...` (APK `http_utils.dart:1207-1234` rimuove il primo segmento servizio), e `commands._checkpassword` chiamava `checkPassword` anche con `tUserId == ""`.
- **Invariant**: Normalizzare sempre `tUserId` tramite `wake._valid_tuserid()` (rifiutando `""`, `"None"`, `"0"`), normalizzare la firma BFF via `lepas_auth._normalize_sig_url()` (`/tsp/` e `/marketing/` -> `/v1/...`, lasciando `/auth/oauth2/token` invariato), risolvere via `GET /tsp/v1/app/auth/getTuserId` (`userId` obbligatorio); `checkPassword` usa `scene=0` come primo tentativo con un singolo fallback controllato a `scene=2` (default APK `RusApiService::checkPassword`) su `A00361`.
- **onFailure Mandate**: Se `tuid_str` è vuoto dopo `_resolve_tuserid`, sollevare subito `CommandError(..., reason="config")` PRIMA di `setVecDefault`/`checkPassword` (zero consumo lockout); su `A00361` con `tuid_source == "login"`, consentire al massimo 1 retry con `getTuserId` alternativo diverso, seguito da 1 fallback controllato con `scene=2` (default APK); loggare solo stato non-PII (`tuid_source`, `len`, `http`, `code`).
- **Forbidden Regex**: `if\s+not\s+tuid\s*:|headers_post\([^)]*method\s*=\s*["']GET["']`

## [AB-LEP-004] OAuth Refresh `user_id` Preservation & Atomic `token.json` Locking
- **Target Files**: `custom_components/lepas/core/wake.py`, `custom_components/lepas/{config_flow,diagnostics}.py`
- **Root Cause**: `/auth/oauth2/token?grant_type=refresh_token` restituisce `access_token`/`refresh_token` senza `user_id`; riscrivere `token.json` col solo JSON di risposta cancella `user_id`, rendendo impossibile chiamare `getTuserId`.
- **Invariant**: `_refresh_token_detail` deve copiare i metadati identitari (`user_id`, `userId`, `username`, `phone`, `email`) dal `token.json` esistente prima di riscrivere; se assente, recuperare `data.id` via `GET /marketing/v1/app/user` (`UserState::getUserInfo`) e persisterlo sotto `ctx.stato.lock_token` tramite `_write_token_atomic` (`0o600`, cleanup `.tmp`). In `config_flow.py` / `diagnostics.py`, ogni I/O su `token.json` o `_check_session` deve girare via `async_add_executor_job`.
- **onFailure Mandate**: Su fallimento HTTP/JSON di `getUserInfo`, loggare solo `type(err).__name__`/`http`/`code`/`has_id` a `DEBUG`, non modificare `token.json` e non chiamare `getTuserId` senza `userId`.
- **Forbidden Regex**: `json\.dump\(j,\s*f`

## [AB-LEP-005] Secondary Account Backend `A00361` Across TSP Microservices (`cpm/vmc/vac`) & HA Module Reload
- **Target Files**: `custom_components/lepas/core/commands.py`, `custom_components/lepas/core/permessi.py`
- **Root Cause**: Un account secondario (`authorizeType=1`) può ottenere `tUserId` da `auth/login` e `getTuserId`, `vmc/queryList` (`code=0`) e `vmc/setVecDefault` (`code=0`), ma ricevere comunque `A00361` ("User does not exist") su `cpm/checkPassword` (anche con header 1:1 APK `1.0.4`, `User-Agent: Dart/3.4 (dart:io)`, `scene=0/2` e `userId` alternativo), `vmc/queryVehicleAuthority` e `vac/queryAuthRemoteList`, e `A00120` su `vac/query`. L'app ufficiale (`RusCarCntrolViewModel::_refreshTaskIdIfInvalid`) evita la chiamata finché ha `taskId` in cache; su `eu-lepas`, senza registrazione/attivazione profilo TSP (`auth/register`) o con account diverso dal profilo registrato in CPM/VMC, il backend rifiuta il `tUserId` secondario. Inoltre `homeassistant.reload_config_entry` NON ricarica i moduli già importati in `custom_components/lepas/core/*.py`.
- **Invariant**: Loggare al fallimento di `checkPassword` solo metadati non-PII (`tuid_source`, `tuid_len`, `ql_code`, `auth_type`, `sv_code`, `scene`, `bff`, `ch`, `tenant`, `country`, `pin_len`, `pin_dig`, `cp_http`, `cp_key`, `ql_keys`) senza mai inventare chiamate HTTP extra né eludere `A00361` come errore PIN. Per test dal vivo su moduli `core/*.py` in HA è obbligatorio `ha_restart`.
- **onFailure Mandate**: Classificare `A00361` in `routing.py` come `reason="config"` senza incrementare il contatore di lockout PIN; evitare retry non deterministi e rimuovere sempre eventuali sonde prima di chiudere.
- **Forbidden Regex**: `probe_a|queryAuthRemoteList.*_LOGGER\.warning`

## [AB-LEP-006] Lepas EU `channelId: "6"` Alignment & ConfigEntry v1→v2 Migration
- **Target Files**: `custom_components/lepas/**/*.py`
- **Root Cause**: L'app ufficiale Lepas EU include `.env.prod` (`CHANNELID=1`), ma a runtime sovrascrive il canale interrogando `/tsp/v1/app/env/defaultEnv` che ritorna `channelId: 6`. Usare `"1"` provoca `A00361` ("User does not exist") su `cpm/checkPassword`, `vmc/queryVehicleAuthority` e `vac/queryAuthRemoteList`.
- **Invariant**: `PRESET_LEPAS_EU`, `DEFAULTS[CONF_CHANNEL_ID]`, `DEFAULT_CHANNEL_ID` e `CHANNEL_ID` devono restare `"6"`, con `LepasConfigFlow.VERSION >= 2` e `async_migrate_entry` per aggiornare le entry `v1` Lepas EU preservando `chery_eu` (`"2"`) e `custom`.
- **onFailure Mandate**: Su ricomparsa di `A00361`, verificare `GET /tsp/v1/app/env/defaultEnv` e `entry.data[CONF_CHANNEL_ID]` prima di toccare il flow PIN/lockout.
- **Forbidden Regex**: `PRESET_LEPAS_EU[^}]*CONF_CHANNEL_ID:\s*["']1["']`

## [AB-LEP-007] `/asr/manager/realtime` `META` Fields Propagation & `_state_lock` Non-Reentrancy
- **Target Files**: `custom_components/lepas/coordinator.py`
- **Root Cause**: Lepas L8 non invia push `5A02` spontanei su MQTT durante la marcia o l'apertura porte, ma `/asr/manager/realtime` restituisce già i campi `META` di stato fisico (`frontLeftDoor`, `doorLock`, `trunkDoor`, `sunroofState`, `sunroofMoveState`, ecc.); `_on_probe_data` aggiornava solo `patch["realtime"]` lasciando `self._fields` vuoto (`unknown` sulle entità non-realtime). Inoltre `self._state_lock` è un `threading.Lock` non rientrante usato anche da `_auto_e_sveglia()`.
- **Invariant**: In `_on_probe_data`, propagare in `self._fields` i campi `k in META` non `None` (esclusi `CMD_CONFIRM_META`, `"time"`, `GEO_KEYS`) senza emettere `msg_fields`; calcolare `awake = bool(self._last_msg_ts) and (time.time() - self._last_msg_ts) < self.awake_window` atomicamente dentro `with self._state_lock:` (senza mai chiamare `_auto_e_sveglia()` dentro il lock) e, se `awake` è `True`, riempire solo le chiavi assenti per non sovrascrivere un `5A02` live recente.
- **onFailure Mandate**: Se `data` non è un `dict`, saltare la propagazione senza sollevare né toccare `self._fields`; non chiamare mai `_auto_e_sveglia()` dentro `with self._state_lock:`.
- **Forbidden Regex**: `with\s+self\._state_lock:[^#]*self\._auto_e_sveglia\(`

### AB-LEP-008: `window.customCards` must register tag name without `custom:` prefix
- **Root Cause**: In `v1.19.0`, `lepas-card.js` pushed `{ type: "custom:lepas-card" }` into `window.customCards`. Home Assistant's Lovelace card picker prepends `custom:` automatically to `entry.type`, causing missing picker discovery / malformed `custom:custom:lepas-card`. Additionally, `manifest.json` lacked `"frontend"` in `after_dependencies` before `add_extra_js_url`.
- **Invariant**: `window.customCards` entries MUST use `type: "lepas-card"` (matching `customElements.define("lepas-card", ...)`), never `custom:lepas-card`, and `manifest.json` MUST keep `"frontend"` in `after_dependencies`.
- **onFailure Mandate**: Check `window.customCards` in `lepas-card.js` and `tests/lepas_card.test.mjs`, verify `?v=<manifest.version>` matches `manifest.json`, and run `tests/test_lovelace_card.py` + `tests/lepas_card.test.mjs`.
- **Forbidden Regex**: `customCards\.push\(\{[^}]*type:\s*["']custom:`

### [AB-LEP-009] `appointmentTravelSetVOS.travelTime` UTC Minutes vs `chargeAppointPlans.startTime` Local Minutes
- **Target Files**: `custom_components/lepas/sensor.py`
- **Root Cause**: By analogy with `chargeAppointPlans.startTime` (which is local minutes since midnight), `LepasDeparturePlan` read `appointmentTravelSetVOS[0]["travelTime"]` directly as local `HH:MM`, causing a `-1h` (CET) / `-2h` (CEST) drift vs the official Lepas app (`05:05` in HA when `06:05` CET was set in app).
- **Invariant**: Always convert `appointmentTravelSetVOS.travelTime` from UTC minutes since midnight into Home Assistant's configured local timezone (`hass.config.time_zone` / `dt_util.DEFAULT_TIME_ZONE`) via `_orario_locale`, and shift `travelDate` weekdays by `day_delta` when crossing UTC midnight. Keep `chargeAppointPlans.startTime` in local minutes.
- **onFailure Mandate**: If `travelTime` is out of `0..1439` or non-numeric, return `None` without shifting `travelDate` or raising.
- **Forbidden Regex**: `return _orario\(piano\.get\(["']travelTime["']\)\)`

### [AB-LEP-010] `LepasCoordinator.set_poll_enabled` Must Notify Listeners on Restore/Toggle
- **Target Files**: `custom_components/lepas/coordinator.py`
- **Root Cause**: During concurrent `async_forward_entry_setups` on boot, `LepasTracker` (`device_tracker`) could call `restore_position()` before `LepasPollingSwitch` (`switch`) restored `poll_enabled = True`; because `set_poll_enabled()` did not call `async_update_listeners()`, `LepasAtHome` (`available = bool(poll_enabled)`) remained stuck on `unavailable`.
- **Invariant**: `LepasCoordinator.set_poll_enabled(on)` MUST call `self.async_update_listeners()` when `not self._timers.closing`, so availability-dependent entities (`LepasAtHome`, `LepasChargedEnergy`) immediately reflect the restored or toggled `poll_enabled` state regardless of platform setup order.
- **onFailure Mandate**: Guard with `if not self._timers.closing:` so teardown never dispatches listener updates during unload.
- **Forbidden Regex**: `def set_poll_enabled\([^)]*\):(?![\s\S]*async_update_listeners)`

### [AB-LEP-011] `LepasClimate.target_temperature` Sync from `realtime.frontSetTempLeft`
- **Target Files**: `custom_components/lepas/climate.py`
- **Root Cause**: `LepasClimate._target` was initialized to `DEFAULT_TEMP` (`21.0`) or restored via `RestoreEntity` and updated only by HA `async_set_temperature`, ignoring `frontSetTempLeft`/`frontSetTempRight` in `coordinator.data["realtime"]`; changing temperature inside the vehicle (`23 °C`) updated `sensor.lepas_set_temperature_left`/`right` but left `climate.lepas_climate` (`21.0 °C`) out of sync.
- **Invariant**: On boot and coordinator updates (`_opt_on is None`), sync `self._target` and `coordinator.climate_target_temp` whenever `frontSetTempLeft` (fallback `frontSetTempRight`) changes to a valid number within `[min_temp, max_temp]`, tracking `_last_rt_temp` so repeated identical realtime payloads never clobber a manual HA override while `OFF`.
- **onFailure Mandate**: Ignore non-dict `realtime`, non-numeric values, or sentinel temperatures outside `[min_temp, max_temp]`.
- **Forbidden Regex**: `def _handle_coordinator_update\(self\) -> None:(?![\s\S]*_sync_target_from_realtime)`

### [AB-LEP-012] `tspconsole-eu` `appointmentTravel` / `/asd/travelManage/*` Endpoints, Non-Empty `travelWeekday`, & `HTTP >= 400` Fail-Closed Guard
- **Target Files**: `custom_components/lepas/core/{commands,permessi}.py`, `custom_components/lepas/{coordinator,sensor}.py`
- **Root Cause**: `libapp.so` (Flutter Dart AOT) exposes MethodChannel action names (`travelAppointControl`, `travelAppointQuery`, `queryBatteryPackHeat`), whereas the native Java/Ijiami layer routes to different `tspconsole-eu` REST paths (`404 Not Found` on `/asc/vehicleControl/travelAppointControl`, `/asd/travelAppointManage/travelAppointQuery`, and `/asc/vehicleControl/queryBatteryPackHeat`). Furthermore: (1) `commands.send()` previously silently treated Spring Boot `HTTP 404` JSON as success; (2) `appointmentTravel` rejects `travelWeekday: ""` on `partenza_prog_off` with `A07900` even while awake; (3) `/asd/travelManage/travelQuery` returns `{mainSwitcher: 0}` without `appointmentTravelSetVOS` when cleared.
- **Invariant**: Departure control MUST use `/asc/vehicleControl/appointmentTravel` (`endpoint = "appointmentTravel"` in `commands.CMD_MAP`, `permessi.CATEGORIA["appointmentTravel"] == 212`, `permessi.CICLO["appointmentTravel"]`) with non-empty `travelWeekday` even on `partenza_prog_off`; read-only queries MUST use `/asd/travelManage/travelQuery` and `/asd/travelManage/queryBatteryPackHeat`; `commands.send()` MUST raise `CommandError` on `status >= 400`; and `LepasDeparturePlan` MUST report `"Disattivata"` (`attiva: False`) when `field_on(rt.get("mainSwitcher")) is False` even if `appointmentTravelSetVOS` is absent.
- **onFailure Mandate**: Never infer TSP write URLs from Flutter MethodChannel names alone; verify route existence and payload schema via read-only `/asd/travelManage/*` or empty `POST {}` / no-`taskId` `POST` before committing, and fail closed on any `HTTP >= 400`.
- **Forbidden Regex**: `"endpoint":\s*["']travelAppointControl["']|travelAppointQuery|/asc/vehicleControl/queryBatteryPackHeat|"travelWeekday":\s*""

### [AB-LEP-013] `appointmentTravel` Write Schema (`appointmentTravelAOS` + `travelWeekday: list[str]`) vs Read Schema (`appointmentTravelSetVOS`)
- **Target Files**: `custom_components/lepas/core/commands.py`, `custom_components/lepas/coordinator.py`
- **Root Cause**: `CVAppointGoParam` in the official Lepas app (`blutter_out` `i18n_car_quest_model.dart`) splits read and write keys: `/asd/travelManage/travelQuery` returns `appointmentTravelSetVOS` (`fromJson`), whereas `/asc/vehicleControl/appointmentTravel` expects **`appointmentTravelAOS`** (`toJson`) with **`travelWeekday`** formatted as `List<String>` (`["1", "3", "5"]`), NOT `"appointmentTravelSetVOS"` or CSV strings (`"1,3,5"`). Sending `appointmentTravelSetVOS` caused the backend to accept `HTTP 200 A00079` and MQTT confirm while ignoring the activation (`partenza_prog_off` only appeared to work because `mainSwitcher: "0"` is top-level). Additionally, `_on_probe_data` must preserve existing `mainSwitcher` / `appointmentTravelSetVOS` when `probe_once()` omits both keys.
- **Invariant**: Write payloads to `/asc/vehicleControl/appointmentTravel` (`commands.CMD_MAP` and `LepasCoordinator._build_native_departure_payload`) MUST use `"appointmentTravelAOS"` and `"travelWeekday": list[str]`; `realtime` reads (`_async_refresh_travel_appoint_realtime`, `sensor.LepasDeparturePlan`, `_native_departure_server_id`) keep reading `"appointmentTravelSetVOS"`; and `_on_probe_data` preserves `mainSwitcher`/`appointmentTravelSetVOS` from previous `realtime` when both keys are absent from a probe payload.
- **onFailure Mandate**: Verify `appointmentTravel` payloads against both `tsp_sign._flatten_value` (which flattens nested `list[str]`) and `permessi.ciclo_non_autorizzato` (`_giorni` handles list of weekday strings), plus trigger `async_apply_departure_schedule` with post-settle refresh.
- **Forbidden Regex**: `"partenza_prog_(?:on|off)"[\s\S]{0,200}"appointmentTravelSetVOS"|\{"mainSwitcher":\s*"[01]",\s*"appointmentTravelSetVOS"`

### [AB-LEP-014] Optimism Rollback on ECU `reason`, `_solo_clima` (`0:95`) Guard & `_hv_lock` Session Latch
- **Target Files**: `custom_components/lepas/{coordinator,entity,switch,climate,binary_sensor}.py`, `custom_components/lepas/lovelace/lepas-card.js`
- **Root Cause**: ECU comfort rejections via MQTT `reason` (e.g., `[{"modelId": "0", "code": "95"}, {"modelId": "4", "code": "95"}]`) do not populate `msg_fields`, leaving `LepasOptimisticMixin` stuck `on` for `OPT_MAX_S = 900s`. Additionally, `/asr/manager/realtime` has no `accState`/`gearPos` fields, stale `realtime` can mask fresh `5A02` pushes in `_on_car_message`, and `btn.disabled || carInUse` in JS makes non-`_applyBtnState` comfort buttons permanently disabled after `car_in_use: true -> false`.
- **Invariant**: Map non-`"0"` rejection `modelId`s via `REASON_FIELD_MAP` while preserving `_solo_clima(reason)` (`0:95`), clear mutually exclusive `LepasComfortSwitch` twins sharing `_opt_anchor`, serialize `_hv_session_in_use` / `_hv_session_start_odo` under dedicated `self._hv_lock` (never nested with `self._state_lock`), and enforce `msg_fields > rt > fields` precedence in `_on_car_message` vs `rt > fields` in `_on_probe_data`.
- **onFailure Mandate**: Set `self._poll_busy = True` synchronously inside `@callback _schedule_probe_on_loop` with `try/finally` reset in `_run_guarded_probe`; in `lepas-card.js`, set `btn.disabled = carInUse` directly on non-`_applyBtnState` controls and test `car_in_use: true -> false` on the same rendered card instance.
- **Forbidden Regex**: `REASON_FIELD_MAP\s*=\s*\{[^}]*["']0["']:`

### [AB-LEP-015] `car_in_use` HV Latch Reset on Plugged-In Charging & PHEV `chargingPower` Availability
- **Target Files**: `custom_components/lepas/{coordinator,sensor}.py`, `custom_components/lepas/lovelace/lepas-card.js`
- **Root Cause**: `_evaluate_car_in_use` cleared `_hv_session_in_use` only when `hVoltageState` was observed `False`; driving straight to home plug-in/charging within a poll window kept `hVoltageState == "1"` continuously (plus `odo > _hv_session_start_odo`), latching `car_in_use = True` and locking remote climate while charging. Additionally, `potenza_ricarica` (`chargingPower`) was gated inside `_RT_SENSORI_BEV` based on an unplugged capture, even though Lepas L8 PHEV sends `chargingPower` during active charging.
- **Invariant**: Clear `_hv_session_in_use = False` and align `_hv_session_start_odo = odo` (if `> 0`) whenever `plugged and not eng_on and not speed_pos and not any_door_open and not comfort_rejected` inside `_hv_lock`; keep `potenza_ricarica` (`volatile=True`) in `_RT_SENSORS` for all vehicles.
- **onFailure Mandate**: Never clear `_hv_session_in_use` if `eng_on`, `speed_pos`, `any_door_open`, or `comfort_rejected` is active, and verify `car_in_use` transitions across driving -> door open -> plugged charging -> unplug pre-climate in `tests/test_car_in_use_optimism.py`.
- **Forbidden Regex**: `if\s+hv_on\s+is\s+False\s+and\s+not\s+eng_on\s+and\s+not\s+speed_pos:\s*\n\s*self\._hv_session_in_use\s*=\s*False`
