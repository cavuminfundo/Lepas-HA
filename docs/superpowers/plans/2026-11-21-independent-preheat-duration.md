# Independent Pre-Heating Duration, Comfort Duration Propagation & Departure Seat Sync — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Dual-Gate Plan Audit Matrix (Verified Before User Presentation)

| Gate Stage | Sub-Agent Role | Model | Conversation ID | Verdict | Notes Incorporated |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Stage 1 (Domain & Archaeology Pre-Audit)** | `plan_auditor` | `flash` | `3e9724e1-4eda-4fef-8a2f-ddead4aec11c` | `NEEDS_CHANGES` -> Resolved | Keep `sync_charge` default `False` in `async_added_to_hass`; write HA state once before `super()._handle_coordinator_update()`; lock `_last_cmd_key`; optional args on `_wake_then`. |
| **Stage 2 (Six-Pillars Sentinel Control Gate)** | `sentinel_auditor` | `inherit` | `0e1dd4fe-e667-4048-a785-08cda17352c2` | **`APPROVED`** | Clear `_exclusive` on `token is None` rollback; pass `depCliDur` to `_buildSkeletonHtml`, `_applyBindings` & `hasDepSection`; handle `CancelledError` in `_maybe_trigger_preclimate`; include `tests/test_lovelace_card.py` in `direct_files`. |

---

**Goal:** Split manual Climate/Comfort duration (`number.lepas_climate_duration`, 5/10/15 min) from an independent Departure Pre-heating duration (`number.lepas_departure_preclimate_duration`, 5/10/15 min), propagate each duration to both climate and seat/defrost comfort commands, expose separate chips in `LepasCard`, and ensure scheduled departure comfort extras update optimistically in HA and settle via 15s-graced `CMD_PROBE` telemetry with `WARNING` logs on ECU rejection.

**Architecture:** Reuse `LepasConfigNumber` (`air_durations()` snapping + `RestoreNumber`) for the new `number.lepas_departure_preclimate_duration` entity, route `times`/`duration` overrides through a single shared helper `commands.duration_params_for_command()`, decouple `coordinator.next_departure_occurrence()` and `_maybe_trigger_preclimate()` onto `departure_preclimate_duration`, bridge scheduled extra optimistic triggers via `coordinator.data["scheduled_opt"]` to `LepasComfortSwitch`, unblock comfort `META` keys under `PROBE_MQTT_GRACE_S` (`15s`) in `_on_probe_data` while keeping `frontHVACState` under `awake_window` (`300s`), and render a separate chip row in `LepasCard`'s Departures panel.

**Tech Stack:** Python 3.12+, Home Assistant Core (`RestoreNumber`, `DataUpdateCoordinator`, `SwitchEntity`), vanilla ES5-compatible Shadow DOM Web Component (`lepas-card.js`), `pytest`, `node:test`, `ruff`.

**Spec:** `docs/superpowers/specs/2026-11-21-independent-preheat-duration-design.md`

---

## Global Constraints
- `custom_components/lepas/lovelace/lepas-card.js` MUST NOT contain optional chaining (`?.`), nullish coalescing (`??`), or top-level `import`/`export` anywhere (including comments/strings).
- Zero plaintext VINs, tokens, coordinates, or secrets in logs/diagnostics/tests (`AB-LEP-002`).
- `frontHVACState` MUST remain protected under `awake_window` (`300s`) in `_on_probe_data` (`AB-LEP-017` / `tests/test_closure_sync.py:259`).
- `clima_on` MUST NOT arm `CMD_PROBE` (`tests/test_closure_sync.py:350`).
- `LepasCoordinator._state_lock` is non-reentrant: never call `_auto_e_sveglia()` inside `with self._state_lock:` (`AB-LEP-007`).
- Every test must be falsifiable against real behavior (zero tautological mocks).

---

## Blast Radius & StateGraph

### `BlastRadius` (from CodeGraph + Archaeology)
- **`direct_files`**:
  - `custom_components/lepas/core/commands.py` (add `duration_params_for_command`)
  - `custom_components/lepas/number.py` (add `partenza_preclima_durata` spec, generalize `air_durations` snapping & `notify_schedule_changed`)
  - `custom_components/lepas/naming.py` (add `ENGLISH_KEYS` & `ENTITY_IDS` entries)
  - `custom_components/lepas/const.py` (add `ENTITY_FEATURE_MAP` entry)
  - `custom_components/lepas/coordinator.py` (add `departure_preclimate_duration`, `_scheduled_opt` signal, `_COMFORT_PROBE_META_KEYS`, `_COMFORT_PROBE_COMMANDS`, `_LOGGER.warning` on ECU rejection)
  - `custom_components/lepas/switch.py` (pass `duration_params_for_command` in `LepasComfortSwitch` & `LepasClimaMacroSwitch`, sync `scheduled_opt` in `LepasComfortSwitch._handle_coordinator_update`)
  - `custom_components/lepas/translations/{it,en,nl}.json` (add `departure_preclimate_duration` & clarify `climate_duration` labels)
  - `custom_components/lepas/lovelace/lepas-card.js` (render independent `departure_preclimate_duration` chip row in Departures panel, register `number.set_value` actions, update `structKey`, update I18N labels)
  - `tests/test_scheduler.py`, `tests/test_config_ux.py`, `tests/test_native_departure_battery.py`, `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`
- **`transitively_affected`**:
  - `custom_components/lepas/climate.py`: reads `coordinator.clima_duration` (remains unchanged, unaffected by `departure_preclimate_duration`).
  - `custom_components/lepas/sensor.py`: `LepasNextDepartureSensor` reads `coordinator.next_departure_occurrence(now)` (automatically reflects `departure_preclimate_duration`).
  - `custom_components/lepas/__init__.py`: `notify_schedule_changed()` listeners stay intact; no service signature changes.
- **`uncertain`**:
  - Live vehicle firmware behavior on `seatControl` / `backDefrostingControl` / `frontWindshieldControl` when receiving `"times": "5"` or `"10"` instead of `"15"`: mitigated by `CMD_PROBE` (`25s / 65s`) settling real telemetry from `/asr/manager/realtime`.

### `StateGraph` (`onSuccess:` / `onFailure:`)
- **`_maybe_trigger_preclimate` scheduled extra dispatch (`coordinator.py`)**:
  - Pre-command: `_set_scheduled_opt(cmd_key, active=True)` sets optimistic token -> `LepasComfortSwitch` marks `is_on = True` (and `_exclusive = False`).
  - `onSuccess:` `async_send_command(cmd_key, extra_params)` returns HTTP `200 A00079` -> arms `CMD_PROBE` (`25s / 65s`); if MQTT `110F` carries `reason` rejecting `cmd_key`'s field (`cmd_rejected_fields` / `cmd_rejected_other`), `_on_car_message` logs `WARNING` and `LepasOptimisticMixin._rifiuto_arrivato()` rolls back `_opt_value` to `None` (real telemetry state) + clears `_exclusive`. If MQTT confirms silently, `CMD_PROBE` past `PROBE_MQTT_GRACE_S` (`15s`) updates `_fields` and settles `_opt_value`.
  - `onFailure:` `async_send_command(cmd_key, extra_params)` raises `Exception` or `asyncio.CancelledError`:
    - On `Exception`: if `not self._timers.closing`, `_set_scheduled_opt(cmd_key, active=False)` clears optimistic state on both `LepasComfortSwitch` (`self`) and `self._exclusive` (guarded by `hass`/`entity_id` and matching `_opt_anchor`), logs `WARNING`, and continues remaining extras without resetting `_fired_climate_key`.
    - On `asyncio.CancelledError`: if `not self._timers.closing`, `_set_scheduled_opt(cmd_key, active=False)`, then re-raises `CancelledError` cleanly.
- **`LepasClimaMacroSwitch._wake_then` (`switch.py`)**:
  - `onSuccess:` sets `_arma_scadenza(preset_min * 60 + 60 if preset_min is not None else MACRO_PRESET_S)`.
  - `onFailure:` (`Exception` or `CancelledError`) `finally:` clears `_invio_in_corso` and restores `prima_on` / `prima_resto` when `mia == self._gen.n`.
- **Timer / Lock Invariants**:
  - `CMD_PROBE` armed only when `not self._timers.closing and self.poll_enabled` (`GRUPPO_POLL` auto-cancels on disable/stop).
  - `_state_lock` touched only inline without calling `_auto_e_sveglia()`; `_last_cmd_key` read inside the existing `with self._state_lock:` block in `_on_car_message` before logging outside the lock.

---

## Domain Skills & Sub-Agent Roster

- **Stage 1 Pre-Audit (`Model: 'flash'`, CID `3e9724e1-4eda-4fef-8a2f-ddead4aec11c`)**: completed (`NEEDS_CHANGES` -> resolved).
- **Stage 2 Sentinel Control Gate (`Model: 'inherit'`, CID `0e1dd4fe-e667-4048-a785-08cda17352c2`)**: completed (`APPROVED` — reused via `send_message` for Tier 3 Pass 2 final sign-off).
- **Cohesive Execution Workers (`Model: 'pro'` — files `>600L`, `>=3` interdependent files)**:
  1. **`backend_ha_worker` (`Model: 'pro'`, `Workspace: 'inherit'`)**:
     - Skills: `async-python-patterns` + `ponytail` + `antislop-code` (`lookup.py "home assistant async python coordinator"`).
     - Owns end-to-end backend contract: `core/commands.py`, `number.py`, `naming.py`, `const.py`, `coordinator.py`, `switch.py`, `translations/{it,en,nl}.json`, and Python tests (`tests/test_scheduler.py`, `tests/test_config_ux.py`, `tests/test_native_departure_battery.py`).
  2. **`frontend_card_worker` (`Model: 'pro'`, `Workspace: 'inherit'`)**:
     - Skills: `frontend-ui-engineering` + `antislop-ui` + `antislop-code` (`lookup.py "frontend javascript custom element ui"`).
     - Owns UI contract: `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`.
- **Verification**: Executed strictly by Master Agent (`uv run --with pytest pytest ...`, `node --test tests/lepas_card.test.mjs`, `uv run ruff check/format`).

---

## Tasks

### Task 1: Shared Duration Override Helper & New `departure_preclimate_duration` Number Entity
**Files:**
- Modify: `custom_components/lepas/core/commands.py` (near `CMD_MAP` / `_adatta_durata`)
- Modify: `custom_components/lepas/number.py:33-151`
- Modify: `custom_components/lepas/naming.py:77-80, 200-204`
- Modify: `custom_components/lepas/const.py:265-270`
- Modify: `custom_components/lepas/translations/{it,en,nl}.json`
- Test: `tests/test_config_ux.py`, `tests/test_scheduler.py`

**Interfaces:**
- Produces: `core.commands.duration_params_for_command(cmd_key: str, duration_min: int) -> dict[str, str] | None`
- Produces: entity `number.lepas_departure_preclimate_duration` writing `coord.departure_preclimate_duration`

- [ ] **Step 1: Write failing tests** in `tests/test_config_ux.py` and `tests/test_scheduler.py`:
  - Assert `ENTITY_FEATURE_MAP[("number", "partenza_preclima_durata")] == "climate"` and `entity_allowed` gates it.
  - Assert `number.lepas_departure_preclimate_duration` registers with `allowed_durations == [5, 10, 15]`, defaults to `15`, snaps invalid values via `durata_ammessa`, calls `notify_schedule_changed()` (with `sync_charge=False` on boot restore and on `set_value`) updating `sensor.lepas_next_departure`, while changing `number.lepas_climate_duration` does NOT shift `sensor.lepas_next_departure`.
  - Assert `duration_params_for_command("sedile_guida_caldo", 10) == {"times": "10"}`, `duration_params_for_command("clima_riscalda_on", 10) == {"duration": "10"}`, and `duration_params_for_command("volante_caldo", 10) is None`.
- [ ] **Step 2: Implement `duration_params_for_command` in `core/commands.py`**:
  ```python
  def duration_params_for_command(cmd_key: str, duration_min: int) -> dict[str, str] | None:
      """Return `times` or `duration` override dict if supported by `CMD_MAP[cmd_key]`."""
      spec = CMD_MAP.get(cmd_key)
      body = spec.get("body") if isinstance(spec, dict) else None
      if not isinstance(body, dict):
          return None
      dur_str = str(max(1, int(duration_min)))
      for field in ("times", "duration"):
          if field in body:
              return {field: dur_str}
      return None
  ```
- [ ] **Step 3: Add `partenza_preclima_durata` in `number.py`, `naming.py`, `const.py`, and `translations/*.json`**:
  - In `number.py`: add `("Lepas Durata preriscaldamento partenza", "partenza_preclima_durata", "departure_preclimate_duration", 5, 30, 5, 15, UnitOfTime.MINUTES, "mdi:car-clock")` to `NUMBERS`; snap both `"clima_duration"` and `"departure_preclimate_duration"` via `coord.air_durations()`; in `async_added_to_hass`, call `notify_schedule_changed()` (default `sync_charge=False`) only when `self._attr in ("charge_duration_hours", "departure_preclimate_duration")`, and in `async_set_native_value` pass `sync_charge=(self._attr == "charge_duration_hours")` only for those same two attributes.
  - Update `naming.py`, `const.py`, and `translations/{it,en,nl}.json`.

---

### Task 2: Coordinator Decoupling, Comfort Switch Duration Propagation, Scheduled Optimistic Sync & `CMD_PROBE`
**Files:**
- Modify: `custom_components/lepas/coordinator.py:493-525, 1036-1048, 1789-1855, 2220-2245, 2774-2779, 3230-3245`
- Modify: `custom_components/lepas/switch.py:180-232, 485-627`
- Test: `tests/test_native_departure_battery.py`, `tests/test_scheduler.py`

**Interfaces:**
- Consumes: `core.commands.duration_params_for_command`, `coord.clima_duration`, `coord.departure_preclimate_duration`
- Produces: `coord.data["scheduled_opt"]`, `_COMFORT_PROBE_META_KEYS`, `_COMFORT_PROBE_COMMANDS`

- [ ] **Step 1: Write failing tests** in `tests/test_native_departure_battery.py` & `tests/test_scheduler.py`:
  - `coord.departure_preclimate_duration = 10` with `coord.clima_duration = 5`: `next_departure_occurrence` uses `10` min lead time; `_maybe_trigger_preclimate` sends `clima_on` (`times: "10"`) and `sedile_guida_caldo` (`times: "10"`), while `volante_caldo` gets `params=None`.
  - Manual `switch.lepas_driver_seat_heating` `turn_on` sends `times: str(coord.clima_duration)` (`5`) even when `coord.departure_preclimate_duration == 10`; `LepasClimaMacroSwitch` sends `duration: str(coord.clima_duration)` and arms expiry `(5 * 60 + 60)`.
  - During `_maybe_trigger_preclimate`, `switch.lepas_driver_seat_heating` immediately becomes `on` (`_opt_value is True`) and its exclusive twin (`switch.lepas_driver_seat_ventilation`) clears optimistically to `False`; if `async_send_command` raises, both `self` and `self._exclusive` clear `_opt_value` back immediately; if MQTT `reason` `[4:95]` rejects, both roll back and a `WARNING` is logged (no VIN); once past `PROBE_MQTT_GRACE_S` (`15s`), `realtime` `dSeatHeatingState` updates `_fields` even while `car_awake` is active (`frontHVACState` remains protected under `300s`).
  - Sending `sedile_guida_caldo` arms `CMD_PROBE` when `poll_enabled=True` (and `clima_on` still does NOT arm `CMD_PROBE`).
- [ ] **Step 2: Implement coordinator changes in `coordinator.py`**:
  - Add `self.departure_preclimate_duration: int = 15`, `self._sched_opt_seq: int = 0`, `self._scheduled_opt: dict[str, int] = {}` in `__init__`.
  - Update `next_departure_occurrence` to pass `self.departure_preclimate_duration`.
  - Add `_set_scheduled_opt(self, cmd_key: str, active: bool) -> None` and call it around `async_send_command(cmd_key, extra_params)` in `_maybe_trigger_preclimate` (passing `dur = int(self.departure_preclimate_duration or 15)` to both `clima_on` and `duration_params_for_command(cmd_key, dur)`, guarding `_set_scheduled_opt(cmd_key, active=False)` with `if not self._timers.closing:` on both `Exception` and `asyncio.CancelledError` before re-raising `CancelledError`).
  - Add `_COMFORT_PROBE_META_KEYS` (the 12 comfort switch fields, excluding `frontHVACState`) and `_COMFORT_PROBE_COMMANDS = frozenset(DEPARTURE_CLIMATE_EXTRAS_COMMANDS.values())`; use `PROBE_MQTT_GRACE_S` in `_on_probe_data` and arm `_schedule_cmd_probe_sequence(0)` in `async_send_command`.
  - In `_on_car_message`, when `is_confirmation` reports `rej_fields or rej_other`, read `cmd_key = self._last_cmd_key` inside the existing `with self._state_lock:` block before emitting `_LOGGER.warning` outside the lock (no PII).
- [ ] **Step 3: Implement switch changes in `switch.py`**:
  - In `LepasComfortSwitch`: override `_handle_coordinator_update()` to detect `scheduled_opt.get(self._on_cmd)` before `super()._handle_coordinator_update()`:
    - On a new integer token `!= self._last_sched_opt_token`: set `self._last_sched_opt_token = token`, initialize optimistic fields (`_opt_value = True`, `_opt_anchor`, `_opt_probe_seq`, `_opt_at`), and set `self._exclusive` optimistically to `False` (writing `self._exclusive.async_write_ha_state()` only when `getattr(self._exclusive, "hass", None) is not None and getattr(self._exclusive, "entity_id", None) is not None`).
    - If `self._last_sched_opt_token is not None` and `token is None`: clear `self._last_sched_opt_token = None`, remember `prev_anchor = self._opt_anchor`, call `self._clear_optimistic()` if `self._opt_value is True`, and also clear `self._exclusive._clear_optimistic()` + `self._exclusive.async_write_ha_state()` (guarded by `hass`/`entity_id`) when `self._exclusive._opt_value is False` and `self._exclusive._opt_anchor == prev_anchor`.
    - Then call `super()._handle_coordinator_update()` (which performs normal settlement/expiry when not newly triggered and writes HA state once).
  - In `async_turn_on()`, pass `duration_params_for_command(self._on_cmd, int(getattr(self.coordinator, "clima_duration", 15) or 15))` to `self._run_command(...)`.
  - In `LepasClimaMacroSwitch`: keep `params: dict[str, str] | None = None, preset_min: int | None = None` optional on `_wake_then(...)` so `async_turn_off()` stays unchanged, pass `duration_params_for_command` and `preset_min=dur` in `async_turn_on()`, forward `params` to `async_send_command`, and use `self._arma_scadenza(preset_min * 60 + 60 if preset_min is not None else MACRO_PRESET_S)` when `target` is `True`.

---

### Task 3: Independent Selectors in `LepasCard` (`lepas-card.js`) & JS/Python Card Tests
**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js`
- Test: `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`

**Interfaces:**
- Consumes: `number.lepas_climate_duration`, `number.lepas_departure_preclimate_duration`
- Produces: independent chip rows `[data-action-id="climate_duration"]` (Climate tab) and `[data-action-id="departure_preclimate_duration"]` (Departures panel)

- [ ] **Step 1: Write failing tests** in `tests/lepas_card.test.mjs` and `tests/test_lovelace_card.py`:
  - Verify Climate tab renders `[data-action-id="climate_duration"]` calling `number.set_value` on `number.lepas_climate_duration` with updated label (`Durata clima e comfort` / `Climate & comfort duration`).
  - Verify Departures panel renders `[data-action-id="departure_preclimate_duration"]` chips (`5m/10m/15m`) calling `number.set_value` on `number.lepas_departure_preclimate_duration`, with `[data-bind="depCliDurText"]` readout and automatic chip rebuild when `allowed_durations` updates.
  - Verify JS syntax guard passes (`no ?., ??, import/export`).
- [ ] **Step 2: Implement `lepas-card.js` updates**:
  - Lookup `depCliDur = this._findDomain(items, "number", "departure_preclimate_duration")` alongside `cliDur`.
  - Pass `depCliDur` to BOTH `_buildSkeletonHtml` and `_applyBindings`, and include `Boolean(ctx.depCliDur)` inside `hasDepSection`.
  - Register `departure_preclimate_duration_<v>` actions in `_renderInner` using `resolveClimateDurationOptions(depCliDur.s)` and include `depCliDurOptsSig` in `structKey`.
  - Build `depDurHtml` inside `depHtml` (below `depCliMode`, mirroring `durHtml` with `data-action-id="departure_preclimate_duration"` and `data-bind="depCliDurText"`), add `I18N` keys (`it/en/nl`) for `duration` (`"Durata clima e comfort"`, `"Climate & comfort duration"`, `"Klimaat- en comfortduur"`) and `depPreheatDuration` (`"Durata preriscaldamento"`, `"Pre-heating duration"`, `"Voorverwarmingsduur"`), and bind `depCliDurText` + `is-active` chips in `_applyBindings`.
