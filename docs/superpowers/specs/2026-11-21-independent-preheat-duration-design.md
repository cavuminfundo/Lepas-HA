# Independent Pre-Heating Duration, Comfort Duration Propagation & Departure Seat Sync — Design Spec

**Date:** 2026-11-21  
**Path Classification:** Architectural  
**Target Files:**
- `custom_components/lepas/number.py`
- `custom_components/lepas/naming.py`
- `custom_components/lepas/const.py`
- `custom_components/lepas/coordinator.py`
- `custom_components/lepas/switch.py`
- `custom_components/lepas/lovelace/lepas-card.js`
- `custom_components/lepas/translations/it.json`
- `custom_components/lepas/translations/en.json`
- `custom_components/lepas/translations/nl.json`
- `tests/test_native_departure_battery.py`
- `tests/test_config_ux.py`
- `tests/lepas_card.test.mjs`

---

## 1. Goals & Scope

1. **Decouple Manual Climate & Comfort Duration from Departure Pre-Heating Duration**:
   - Keep `number.lepas_climate_duration` (`coord.clima_duration`, `5/10/15` min via `air_durations()`) exclusively for the **Climate** section: manual `climate.lepas_climate`, comfort macros (`raffredda_tutto` / `riscalda_tutto`), and manual comfort switches (`LepasComfortSwitch`: seats, defrosters/defogger) that accept `times`.
   - Introduce a dedicated independent entity **`number.lepas_departure_preclimate_duration`** (`coord.departure_preclimate_duration`, `5/10/15` min via `air_durations()`, default `15`) exclusively for the **Departures / Pre-heating** section:
     - Determines the pre-heating lead time (`climate_start_at = departure_at - departure_preclimate_duration`) for `next_departure_occurrence()` and `sensor.lepas_next_departure`.
     - Determines the `times` duration sent by `_maybe_trigger_preclimate()` to **both** `clima_on` and all departure comfort extras that accept `times` (heated/ventilated seats, defrosters/defogger).
2. **Expose Separate Selectors in `LepasCard`**:
   - **Climate tab**: keep the chip selector for `number.lepas_climate_duration` with clear "Climate & comfort duration" labeling (`IT/EN/NL`).
   - **Charging & Departures tab (`depSurface`)**: add an independent chip selector for `number.lepas_departure_preclimate_duration` ("Pre-heating duration" / "Durata preriscaldamento") right below `depClimateMode`, driving `number.set_value` independently.
3. **Fix Immediate Visibility & Telemetry Settlement for Scheduled Comfort Extras**:
   - Set immediate optimistic `ON` state on `LepasComfortSwitch` when `_maybe_trigger_preclimate()` dispatches a comfort extra, with automatic rollback on command exception or MQTT `reason` rejection (`_rifiuto_arrivato`).
   - Gate comfort `META` state keys (`dSeatHeatingState`, `dSeatVentilateState`, `pSeat*`, `lSeat*`, `rSeat*`, `frontWindshieldHeat`, `fWinHeatingState`, `rWinHeatingState`, `steerWheelHeating`) under `PROBE_MQTT_GRACE_S` (`15s`) in `_on_probe_data` (keeping `frontHVACState` protected by `awake_window` `300s` per `AB-LEP-017` and `tests/test_closure_sync.py`), and trigger `CMD_PROBE` (`25s`, `65s`) on comfort extra commands so `/asr/manager/realtime` settles real telemetry in ~25s instead of 5 minutes.
   - Emit a non-PII `_LOGGER.warning` in `_on_car_message` whenever a command confirmation reports a real ECU rejection (`rej_fields` or `rej_other`).

---

## 2. Architecture & Component Design

### 2.1 Entities, Naming & Feature Gating

- **`custom_components/lepas/number.py`**:
  - Add `("Lepas Durata preriscaldamento partenza", "partenza_preclima_durata", "departure_preclimate_duration", 5, 30, 5, 15, UnitOfTime.MINUTES, "mdi:car-clock")` to `NUMBERS`.
  - Generalize `LepasConfigNumber.__init__` so both `clima_duration` and `departure_preclimate_duration` snap `min`, `max`, `step`, `extra_state_attributes["allowed_durations"]`, `default`, restored value, and `async_set_native_value` against `coord.air_durations()` using `durata_ammessa`.
  - In `LepasConfigNumber`:
    - `async_added_to_hass`: call `self.coordinator.notify_schedule_changed()` (with default `sync_charge=False`) only when `self._attr in ("charge_duration_hours", "departure_preclimate_duration")`.
    - `async_set_native_value`: call `self.coordinator.notify_schedule_changed(sync_charge=(self._attr == "charge_duration_hours"))` only when `self._attr in ("charge_duration_hours", "departure_preclimate_duration")`, so changing `clima_duration` no longer shifts departure pre-climate start times.
- **`custom_components/lepas/naming.py`**:
  - `ENGLISH_KEYS`: add `"durata_preriscaldamento_partenza": "departure_preclimate_duration"`.
  - `ENTITY_IDS`: add `("number", "partenza_preclima_durata"): "number.lepas_departure_preclimate_duration"`.
- **`custom_components/lepas/const.py`**:
  - `ENTITY_FEATURE_MAP`: add `("number", "partenza_preclima_durata"): "climate"`.
- **`custom_components/lepas/translations/{it,en,nl}.json`**:
  - Add `entity.number.departure_preclimate_duration.name` (`"Durata preriscaldamento"`, `"Pre-heating duration"`, `"Voorverwarmingsduur"`) and update `entity.number.climate_duration.name` to clarify Climate/comfort scope (`"Durata clima e comfort"`, `"Climate & comfort duration"`, `"Klimaat- en comfortduur"`).

### 2.2 Duration Propagation Rules

- **Shared helper for `times` / `duration` overrides**:
  - In `custom_components/lepas/core/commands.py` (or a small helper read by `switch.py` and `coordinator.py` from `CMD_MAP`):
    - Given `cmd_key` and `dur: int`, check `CMD_MAP[cmd_key]["body"]`:
      - If `"times"` is in the template body, pass `params={"times": str(dur)}`.
      - If `"duration"` is in the template body (macros `clima_raffredda_on`, `clima_riscalda_on`), pass `params={"duration": str(dur)}`.
      - Otherwise (e.g., `volante_caldo` whose `steeringWheelControl` body is `{"controlType": "1"}` with no duration field), pass `params=None`.
    - Reuse one shared helper `duration_params_for_command(cmd_key: str, dur: int) -> dict[str, str] | None` so `switch.py` and `coordinator.py` never duplicate key-checking logic.
- **Manual Climate section (`climate.py` & `switch.py`)**:
  - `LepasClimate._params()` continues reading `self.coordinator.clima_duration`.
  - `LepasComfortSwitch.async_turn_on` passes `duration_params_for_command(self._on_cmd, int(getattr(self.coordinator, "clima_duration", 15) or 15))` to `self._run_command(...)`.
  - `LepasClimaMacroSwitch.async_turn_on` passes `duration_params_for_command(self._on_cmd, int(getattr(self.coordinator, "clima_duration", 15) or 15))` to `self._wake_then(...)` (which forwards `params` to `async_send_command`, and uses `dur * 60 + 60` for `self._arma_scadenza(...)` instead of a stale hardcoded 15 min when `dur` is `5`/`10`/`15`).
- **Departure Pre-heating section (`coordinator.py`)**:
  - `LepasCoordinator.__init__`: add `self.departure_preclimate_duration: int = 15`.
  - `LepasCoordinator.next_departure_occurrence`: pass `self.departure_preclimate_duration` instead of `self.clima_duration` to `compute_next_occurrence(...)`.
  - `LepasCoordinator._maybe_trigger_preclimate`:
    - Read `dur = int(self.departure_preclimate_duration or 15)`.
    - Send `"clima_on"` with `{"temperature": f"{temp:.1f}", "times": str(dur)}`.
    - For each allowed `extra_key`, compute `extra_params = duration_params_for_command(cmd_key, dur)` and send `await self.async_send_command(cmd_key, extra_params)`.

### 2.3 Scheduled Comfort Switch Optimistic Sync, Realtime Grace & Rejection Logging (`coordinator.py` + `switch.py`)

- **Scheduled Optimistic Trigger**:
  - In `LepasCoordinator`: track `self._sched_opt_seq: int = 0` and `self._scheduled_opt: dict[str, int] = {}`.
  - Add helper `_set_scheduled_opt(self, cmd_key: str, active: bool) -> None`:
    - When `active=True`, increment `self._sched_opt_seq`, store `self._scheduled_opt[cmd_key] = self._sched_opt_seq`, and call `self._apply_update({"scheduled_opt": dict(self._scheduled_opt)})`.
    - When `active=False` (on send failure in `_maybe_trigger_preclimate`), pop `cmd_key` from `self._scheduled_opt` and call `self._apply_update({"scheduled_opt": dict(self._scheduled_opt)})`.
  - In `LepasComfortSwitch._handle_coordinator_update()`:
    - Track `self._last_sched_opt_token: int | None = None`.
    - Inspect `(self.coordinator.data or {}).get("scheduled_opt", {}).get(self._on_cmd)` before `super()._handle_coordinator_update()`:
      - If a new integer `token != self._last_sched_opt_token` arrives: set `self._last_sched_opt_token = token`, initialize optimistic fields (`_opt_value = True`, `_opt_anchor`, `_opt_probe_seq`, `_opt_at`), and set `self._exclusive` optimistically to `False` (writing its HA state only when `hass` and `entity_id` are present); then `super()._handle_coordinator_update()` writes HA state once.
      - If `self._last_sched_opt_token is not None` and the key was removed (`token is None`, indicating send failure before confirmation): clear `self._last_sched_opt_token = None` and call `self._clear_optimistic()` if `self._opt_value is True` before `super()._handle_coordinator_update()`.
    - Run `LepasOptimisticMixin._handle_coordinator_update()` normally when no new `scheduled_opt` token arrives (so settlement/rollback via `_rifiuto_arrivato` / `_verita_arrivata` continues cleanly).
- **Comfort Telemetry Grace & `CMD_PROBE`**:
  - Define `_COMFORT_PROBE_META_KEYS` (the 12 comfort `META` fields mapped by `LepasComfortSwitch`: `dSeatHeatingState`, `dSeatVentilateState`, `pSeatHeatingState`, `pSeatVentilateState`, `lSeatHeatingState2`, `lSeatVentilateState2`, `rSeatHeatingState2`, `rSeatVentilateState2`, `frontWindshieldHeat`, `fWinHeatingState`, `rWinHeatingState`, `steerWheelHeating` — explicitly excluding `frontHVACState`) and `_COMFORT_PROBE_COMMANDS = frozenset(DEPARTURE_CLIMATE_EXTRAS_COMMANDS.values())` (plus `*_off` equivalents if desired, or all comfort switch commands).
  - In `_on_probe_data`: `blocked = mqtt_recent if (k in CLOSURE_META_KEYS or k in _COMFORT_PROBE_META_KEYS) else awake`.
  - In `async_send_command`: `if key in CLOSURE_PROBE_COMMANDS or key in _COMFORT_PROBE_COMMANDS: self._schedule_cmd_probe_sequence(0)`.
- **ECU Rejection Warning**:
  - In `_on_car_message`, when `is_confirmation` has `rej_fields or rej_other`, emit `_LOGGER.warning("[cmd] comando rifiutato dall'auto (%s): %s", self._last_cmd_key or "?", patch["cmd_status"])` (no VIN/PII).

### 2.4 Lovelace Card (`custom_components/lepas/lovelace/lepas-card.js`)

- **Entity Lookup & ViewModel**:
  - Lookup `depCliDur = this._findDomain(items, "number", "departure_preclimate_duration")` alongside `cliDur = this._findDomain(items, "number", "climate_duration")`.
  - Reuse `resolveClimateDurationOptions(depCliDur.s)` for `depCliDur` options and include `depCliDurOptsSig` in `structKey` so chips rebuild cleanly if `allowed_durations` updates.
  - Register actions `departure_preclimate_duration_<v>` calling `number.set_value` on `depCliDur.id`.
- **UI Placement**:
  - **Climate tab**: keep chip row bound to `cliDur`, update heading label `t.duration` to `"Durata clima e comfort"` / `"Climate & comfort duration"` / `"Klimaat- en comfortduur"`.
  - **Departures panel (`depSurface`)**: render independent chip row (`data-action-id="departure_preclimate_duration"`) below `depCliMode` and above `weekDays` / `depExtrasBox`, with heading `t.depPreheatDuration` (`"Durata preriscaldamento"` / `"Pre-heating duration"` / `"Voorverwarmingsduur"`) and readout `[data-bind="depCliDurText"]`, keeping the chips interactive regardless of `depCliMode` (consistent with `depExtrasBox`).
- **Syntax Guard**:
  - Zero `?.`, `??`, or top-level `import`/`export` anywhere in `lepas-card.js`.

---

## 3. Global Constraints & Verification

- **No PII / Secrets**: Logs, sensor attributes, and card bindings never expose VINs, tokens, or coordinates.
- **Test Falsification**: Every test asserts real state transitions, payloads, or scheduler outputs and fails if production logic is reverted or broken (zero tautological mocks).
- **Verification**:
  - Python: `/home/federico/.local/bin/uv run --with pytest pytest -q --tb=short --maxfail=2`
  - Lint: `uv run ruff check custom_components/ tests/` and `uv run ruff format --check custom_components/ tests/`
  - Card JS: `node --test tests/lepas_card.test.mjs` + `tests/test_lovelace_card.py`
  - Release compliance (on commit/push): SemVer `minor` bump (`manifest.json`, `pyproject.toml`, `lepas-card.js?v=`), `CHANGELOG.md`, Git tag.
