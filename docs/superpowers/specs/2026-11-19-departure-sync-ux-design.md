# Design Spec — Departure Schedule Sync UX, Full-Plan Dirty Tracking & Disable Service

**Date:** 2026-11-19  
**Status:** Ready for Plan & Dual-Gate Audit  
**Target SemVer:** `v1.24.0` *(minor SemVer: new service `lepas.disable_departure_schedule`, new `sensor.lepas_scheduled_departure` attributes, and Lovelace card UX state machine)*

---

## 1. Problem Statement & User Requirements

Observed live on `v1.23.0` (`2026-11-19`):
1. **Partial-plan `synced_with_ha` blind spot:** [`LepasDeparturePlan._synced_with_ha`](file:///home/federico/Lepas/custom_components/lepas/sensor.py) only compares the vehicle's active slot (`appointmentTravelSetVOS`) against the **next single occurrence** (`next_departure_occurrence()`). If Thursday (`13:25`) is synced on the vehicle and the user edits Friday (`06:00` -> `07:30`) or Saturday in Home Assistant, `synced_with_ha` stays `True`. A button relying only on `synced_with_ha` would display **"Disattiva piano"** instead of **"Applica su auto"** and risk disabling the whole schedule instead of applying Friday's edit.
2. **Accidental intermediate syncs vs explicit apply:** While the user toggles multiple weekdays/times in the Lovelace card, each tap should remain a pending local edit until the user presses **"Applica su auto"**. Once applied, auto-advance across subsequent days (`native_departure_sync`) should activate automatically so Thursday `13:25` transitions automatically to Friday/Saturday `06:00` after `13:25` passes.
3. **3-state button UX in `lepas-card.js`:**
   - **Pending local changes OR car out of sync** (`has_pending_changes === true || synced_with_ha !== true`): show **"Applica su auto"** (primary) if HA has an active departure, or **"Disattiva piano"** if HA has no active departure while the car is still active.
   - **Full plan synced & active** (`has_pending_changes === false && synced_with_ha === true && carActive`): hide **"Applica su auto"** and show **"Disattiva piano"** (secondary, with confirmation dialog).
   - **Inactive everywhere** (`!haHasActiveDep && !carActive`): hide the button.
4. **Full clean disable:** Pressing **"Disattiva piano"** (via new service `lepas.disable_departure_schedule`) disables the schedule on the vehicle (`mainSwitcher: "0"`), turns off all weekly weekday switches and `quick_departure_enabled` in HA, clears the applied-plan signature, and turns off `switch.lepas_native_departure_sync` (`native_departure_sync = False`).

---

## 2. Architecture & Component Contracts

### 2.1 Full-Plan Signature & Coordinator State (`custom_components/lepas/coordinator.py`)

Add explicit full-plan tracking and serialization lock to `LepasCoordinator`:
- `self._departure_lock: asyncio.Lock = asyncio.Lock()` in `__init__` to serialize all mutating departure schedule flows (`async_apply_departure_schedule`, `async_disable_departure_schedule`, `async_set_quick_departure`, and `_departure_tick_cb`) without race conditions against async command sends.
  - Because `async_set_quick_departure` calls apply internally, use a non-reentrant private helper `_async_apply_departure_schedule_locked()` called under `async with self._departure_lock:`.
  - `_departure_tick_cb` checks `if self._timers.closing or self._departure_busy or self._departure_lock.locked(): return` and acquires `async with self._departure_lock:`.
- `self._applied_schedule_sig: str | None = None` (canonical JSON string produced by `departure_schedule_signature()`).
- `departure_schedule_signature() -> str`:
  - Deterministic canonical JSON (`json.dumps(..., separators=(",", ":"))`) over `{"q": quick_tuple, "w": weekly_tuple}`:
    - `q`: `[True, int(self.quick_departure_minutes) % 1440]` if `self.quick_departure_enabled` else `[False, None]`
    - `w`: `[[d, True, int(mins) % 1440] if enabled else [d, False, None] for d in range(1, 8)]`
  - Editing the time of an **inactive** (`enabled=False`) weekday does not dirty the signature until that day is enabled.
- `_weekly_signature_part(raw_sig: str | None) -> list | None`:
  - Parses `"w"` from a canonical signature string (returning `None` on invalid/empty input) so `_departure_tick_cb` can detect unapplied weekly draft edits when a quick departure expires.
- `has_active_departure_schedule() -> bool`:
  - `True` if `self.quick_departure_enabled` or any `d in 1..7` has `self.departure_weekly.get(d, (False, ...))[0] is True`.
- `has_pending_departure_changes() -> bool`:
  - `car_active = self._is_car_departure_active()` (reads `realtime.mainSwitcher` + `realtime.appointmentTravelSetVOS`; `None` if realtime is unavailable).
  - If `not self.has_active_departure_schedule()`:
    - Returns `True` if `car_active is True` or `(car_active is None and self._applied_schedule_sig is not None)` (car still needs disabling, or boot before realtime), else `False`.
  - If `self.has_active_departure_schedule()`:
    - Returns `True` if `self._applied_schedule_sig is None` or `self.departure_schedule_signature() != self._applied_schedule_sig`, else `False`.
- `restore_applied_schedule_sig(raw_sig: str | None) -> None`:
  - Restores `self._applied_schedule_sig` on boot (called from `LepasDeparturePlan.async_added_to_hass` only when `self._applied_schedule_sig is None` and `isinstance(raw_sig, str)` and `raw_sig` is non-empty), and calls `self.async_update_listeners()` guarded by `if not self._timers.closing:`.

### 2.2 Explicit Apply, Auto-Advance & Safe Disable (`coordinator.py`, `switch.py`, `time.py`, `__init__.py`, `services.yaml`)

1. **Local edits stay local (`switch.py`, `time.py`):**
   - `LepasWeeklyDepartureSwitch._set_enabled`, `LepasTimeEntity.async_set_value` (`quick_departure_minutes`), `LepasWeeklyDepartureTime.async_set_value`, and `LepasScheduleSwitch` with `sync_mode == "departure"` (`quick_departure`) pass `sync_native=False` to `notify_schedule_changed(...)`.
   - `notify_schedule_changed(sync_native=True)` itself keeps its existing implementation so turning on `switch.lepas_native_departure_sync` (`sync_mode="native"`) and existing unit tests calling `notify_schedule_changed(sync_native=True)` directly remain intact.
2. **Apply (`async_apply_departure_schedule` -> `_async_apply_departure_schedule_locked(*, enable_native_sync: bool = True)`):**
   - Acquires `self._departure_lock`, sends `partenza_prog_on` (if `occ is not None`) or `partenza_prog_off` (if `occ is None`), then updates state **only after** `async_send_command` succeeds:
     - If `occ is not None`: `self._applied_schedule_sig = self.departure_schedule_signature()`, and if `enable_native_sync` is `True` sets `self.native_departure_sync = True` (`async_apply_departure_schedule()` passes `enable_native_sync=True`, whereas `async_set_quick_departure(apply_native=True)` passes `enable_native_sync=False` to preserve one-shot `_quick_applied_native` semantics).
     - If `occ is None`: `self._applied_schedule_sig = None`, `self.native_departure_sync = False`, `self._quick_applied_native = False`.
     - Calls `self.async_update_listeners()`, `_async_refresh_travel_appoint_realtime()`, and schedules `_post_settle_travel_refresh()`.
3. **Disable (`async_disable_departure_schedule` + service `lepas.disable_departure_schedule`):**
   - Acquires `self._departure_lock`.
   - Sends `partenza_prog_off` via `self._build_native_departure_payload(None)` **first**. If `async_send_command` raises, local HA schedule switches and `_applied_schedule_sig` are **preserved** (fail-closed `onFailure`).
   - On success (`if not self._timers.closing`):
     - Sets `self.quick_departure_enabled = False`, `_quick_target_at = None`, `_quick_native_until = None`, `_quick_applied_native = False`.
     - Sets every day `d in 1..7` in `self.departure_weekly[d] = (False, existing_mins)`.
     - Sets `self.native_departure_sync = False`, `self._applied_schedule_sig = None`, `self._last_synced_native_dep_sig = None`, `self._last_attempted_native_dep_sig = None`.
     - Updates listeners (`self.async_update_listeners()`), if `self.sync_battery_heat_to_departure` is `True` calls `await self._async_sync_battery_for_occurrence(None)`, calls `await self._async_refresh_travel_appoint_realtime()`, and schedules `_post_settle_travel_refresh()`.
   - Register service `lepas.disable_departure_schedule` in `__init__.py` (both `_async_register_services` and `_async_unregister_services`) and `services.yaml` (optional `entry_id` selector, same pattern as `set_battery_pack_heat`). **Zero new HA entities** (`test_entity_count.py` unchanged).
4. **Quick departure service (`async_set_quick_departure`):**
   - Acquires `self._departure_lock`; when `apply_native is True` calls `_async_apply_departure_schedule_locked(enable_native_sync=False)` (preserving `self.native_departure_sync` and `_quick_applied_native`). When `apply_native is None` and `self.native_departure_sync` is `True`, if `_async_sync_native_departure(occ)` sends a command (`True`), updates `self._applied_schedule_sig` (provided weekly part is not dirty) and refreshes realtime.
5. **Minute Tick Auto-Advance (`_departure_tick_cb` + `_async_sync_native_departure`):**
   - `_async_sync_native_departure(occ) -> bool` returns `True` when `async_send_command` is executed and succeeds (and triggers `_async_refresh_travel_appoint_realtime()` / `_post_settle_travel_refresh()`), or `False` when skipped (dedup) or failed.
   - Inside `_departure_tick_cb` (under `self._departure_lock`, when `not holding_quick`):
     - Compute `weekly_dirty = (self._applied_schedule_sig is not None and self._weekly_signature_part(self.departure_schedule_signature()) != self._weekly_signature_part(self._applied_schedule_sig))`.
     - **Do not leak unapplied weekly drafts**:
       - Guard: `if (not weekly_dirty or (quick_expired and occ is None)) and (self.native_departure_sync or (quick_expired and self._quick_applied_native)):`
       - Inside this guard, call `sent_ok = await self._async_sync_native_departure(occ)`.
       - When `quick_expired` and `(sent_ok or sig == self._last_synced_native_dep_sig)`: clear `self._quick_applied_native = False`; if `occ is not None` set `self._applied_schedule_sig = self.departure_schedule_signature()`, else set `self._applied_schedule_sig = None` and `self.native_departure_sync = False`. If the send failed, preserve retry state so the next tick retries cleanly.
       - If `quick_expired` is `True` with `weekly_dirty` and `occ is not None`, clear `self._quick_applied_native = False` without sending or consolidating the unapplied weekly draft.

### 2.3 Sensor Attributes & Restore (`custom_components/lepas/sensor.py`)

In `LepasDeparturePlan`:
- In `async_added_to_hass`: call `last_state = await self.async_get_last_state()` (not `async_get_last_sensor_data()`), check `last_state is not None and isinstance(last_state.attributes, Mapping)`, and restore `last_state.attributes.get("applied_schedule_sig")` via `coord.restore_applied_schedule_sig(...)` if `coord._applied_schedule_sig is None`.
- In `extra_state_attributes`:
  - Even when `piano is None and not self._main_switcher_off()` (boot before first realtime), if `coord` exposes `has_pending_departure_changes`, return `{"has_pending_changes": coord.has_pending_departure_changes(), "applied_schedule_sig": getattr(coord, "_applied_schedule_sig", None)}` so HA persists/restores `applied_schedule_sig` and the card receives `has_pending_changes` immediately at startup.
  - When `piano is None` with `mainSwitcher == 0` or when `piano` is present: keep existing attributes (`attiva`, `orario`, `giorni`, `giorni_testo`, `riepilogo`, `synced_with_ha`) plus `"has_pending_changes"` and `"applied_schedule_sig"`.

### 2.4 Lovelace Card 3-State Button (`custom_components/lepas/lovelace/lepas-card.js`)

In `LepasCard` (keeping ES5 compatibility: no `?.`, no `??`):
1. I18N (`it`, `en`, `nl`):
   - `it`: `disableDeparturePlan: "Disattiva piano"`, `departureStatus: "Stato"`
   - `en`: `disableDeparturePlan: "Disable schedule"`, `departureStatus: "Status"`
   - `nl`: `disableDeparturePlan: "Schema uitschakelen"`, `departureStatus: "Status"`
   - Use `t.departureStatus` for the first row (`ctx.nextDep`) in `dep-summary` (`lepas-card.js:2948`), keeping `t.nextDeparture` intact for the Overview fallback tile (`lepas-card.js:3338`).
2. `CONFIRM_ACTIONS`:
   - Add `disable_departure_schedule: true`.
3. Action registration (`if (applyDepBtn)`):
   - Keep `regAction("apply_departure_schedule", ...)` and register `"disable_departure_schedule"` targeting service `"lepas"` / `"disable_departure_schedule"` with `this._currentEntryId ? { entry_id: this._currentEntryId } : {}` (verified at `lepas-card.js:2228`) and confirmation label `t.disableDeparturePlan`. Preserve `if (applyDepBtnEl && vm.applyDepBtn)` gating in `_applyBindingsInner` (`scheduled_departure_control` permission).
4. Null-safe attribute extraction & button state logic (`_applyBindingsInner`):
   - Always initialize `var sdRawAttrs = (schedDep && schedDep.s && !this._dead(schedDep.s) && schedDep.s.attributes) ? schedDep.s.attributes : {};` **before** reading any property (prevents `TypeError` when `schedDep` is missing/`unavailable`/`unknown`).
   - Extract `hasPending`: `typeof sdRawAttrs.has_pending_changes === "boolean" ? sdRawAttrs.has_pending_changes : null`.
   - Extract `isSynced`: `typeof sdRawAttrs.synced_with_ha === "boolean" ? sdRawAttrs.synced_with_ha : null`.
   - Helper `showDepBtn(label, actionId, variant, iconName)` sets **both** `applyDepBtnEl.classList.remove("hidden")` and `applyDepBtnEl.hidden = false` before calling `this._applyBtnState(...)`.
   - **When `hasPending !== null`:**
     - If `!haHasActiveDep && !carActive` -> `applyDepBtnEl.classList.add("hidden"); applyDepBtnEl.hidden = true;`
     - Else if `hasPending || isSynced === false`:
       - If `haHasActiveDep` -> `showDepBtn(t.applyDeparture, "apply_departure_schedule", "is-primary", "check")`
       - Else -> `showDepBtn(t.disableDeparturePlan, "disable_departure_schedule", "", "wake")`
     - Else if `haHasActiveDep && !hasPending && isSynced === true && carActive`:
       - `showDepBtn(t.disableDeparturePlan, "disable_departure_schedule", "", "wake")`
     - Else (`haHasActiveDep && !hasPending && isSynced === null`, or `!carActive` edge case):
       - If `haHasActiveDep` -> `showDepBtn(t.applyDeparture, "apply_departure_schedule", "is-primary", "check")`
       - Else -> `showDepBtn(t.disableDeparturePlan, "disable_departure_schedule", "", "wake")`
   - **Legacy fallback (`hasPending === null`):** preserve existing `(haHasActiveDep ? applyDeparture : carActive ? disableOnCar : hidden)` while explicitly setting `applyDepBtnEl.hidden = false` on visible branches and `applyDepBtnEl.hidden = true` on hidden branch.
5. **Accessibility (`modern-web-guidance` `accessibility`):**
   - Native `<button type="button">` retained; when hidden use both `.hidden` (`display: none`) and `btn.hidden = true` (removed from visual flow, screen readers, and keyboard focus order, per Content Visibility Decision Matrix *"Hidden for all: `hidden` attribute / `display: none`"*); do not apply `aria-hidden="true"` to focusable controls.

---

## 3. Versioning & Release Scope
- Synchronize `1.24.0` across `custom_components/lepas/manifest.json`, `pyproject.toml`, `custom_components/lepas/lovelace/lepas-card.js` (`CARD_VERSION` + header), `tests/test_lovelace_card.py`, `tests/lepas_card.test.mjs`, and `CHANGELOG.md` (with `v1.24.0` bilingual notes).
- Run full Python (`pytest`) and JS (`node --test`) suites + `ruff check --select F,E9` + `card.yml` JS checks before deploy/commit.
