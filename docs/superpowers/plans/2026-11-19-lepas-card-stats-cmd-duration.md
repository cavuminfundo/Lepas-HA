# LepasCard Integrated Statistics, Command Badge TTL & Climate Duration Alignment — Implementation Plan

## Dual-Gate Audit Matrix

| Gate | Conversation ID | Model | Verdict | Notes |
|---|---|---|---|---|
| **Stage 1 (Domain & Archaeology Pre-Audit)** | `81509f59-b365-4d56-b764-119eeb4e6261` | `flash` | `FAIL -> FIXED` | Corrected HA `ServiceValidationError` expectation, `_snap_value`/`bool`/`__init__` edge cases, dynamic `?v=<manifest.version>`, `createConfirmDialogController` `inFlight` contract, `CMD_WAITING_STATES` ordering, `SVG_PATHS.chart` & timer teardown. |
| **Stage 2 (Six-Pillars Sentinel Control Gate)** | `be2b9aff-c044-4f6a-a081-31136db7ad78` | `inherit` | `PASS` | Verified all 6 pillars after resolving `formatCommandOutcome` timestamp precedence, `statsErrorBanner` inside `statsDialog` top-layer, `_cmdTtlTimer -> this._render()`, and `?v=1.30.1` across `HERO_IMAGES` / `DEFAULT_HERO`. |

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the charging and consumption statistics view inside `LepasCard` via a dedicated modal dialog (removing `LepasStatsCard`/`LepasStatsCardEditor`/`lepas-stats-card`), restrict `cmdResultBadge` to the *Plancia* tab with a 5-minute TTL on successes (hiding idle `"In attesa"`/`"Waiting"` while keeping errors visible), and align `number.lepas_climate_duration` and `LepasCard` duration chips with the vehicle's `maxAirDuration` capabilities (`[5, 10, 15]` on Lepas L8).

**Architecture:** `number.py` reads `coord.air_durations()` for `clima_duration`, constrains `min`/`max`/`step`, snaps restored/incoming values via existing `core.commands.durata_ammessa`, and exposes `extra_state_attributes["allowed_durations"]` while preserving `notify_schedule_changed()`. `lepas-card.js` removes the standalone `LepasStatsCard`/`LepasStatsCardEditor` classes and `lepas-stats-card` registrations, adds a `.stats-btn` in `.hero-overlay-top` opening `<dialog class="stats-dialog" data-bind="statsDialog">` (extending `createConfirmDialogController` for per-open `closeOnConfirmImmediate: false` on stats reset), restricts `cmdResultBadge` to *Plancia* with a 5-minute success TTL + one-shot auto-hide timer, and dynamically resolves climate duration chips from `allowed_durations` or `min`/`max`.

**Tech Stack:** Python >=3.12 (Home Assistant `RestoreNumber`), ES5-compatible browser JavaScript (Shadow DOM Custom Element + SVG), `pytest`, `node:test`, `ruff`.

**Spec:** `docs/superpowers/specs/2026-11-19-lepas-card-stats-cmd-duration-design.md`

## Global Constraints
- `custom_components/lepas/lovelace/lepas-card.js` MUST NOT contain optional chaining (`?.`), nullish coalescing (`??`), or top-level `import`/`export` anywhere (including comments/strings).
- `window.customCards` MUST register only `type: "lepas-card"` (never `custom:` prefix and no `lepas-stats-card`).
- Every HA I/O / timer / dialog resource must clean up cleanly (`disconnectedCallback`, `try/finally`, `inFlight` lock).
- `number.lepas_climate_duration` MUST keep calling `coord.notify_schedule_changed(sync_charge=False)` on restore and `async_set_native_value` so `sensor.lepas_next_departure` updates immediately.
- Synchronized SemVer release (`v1.30.1`) across `manifest.json`, `pyproject.toml`, `lepas-card.js` (`?v=1.30.1` in `CARD_VERSION`, `HERO_IMAGES`, `DEFAULT_HERO`), and bilingual `CHANGELOG.md` on commit/tag/push.

---

## Domain Skills & Sub-Agent Roster

| Domain | Worker Name & Model | Companions (`lookup.py`) | Cohesive Scope (Files Owned) |
|---|---|---|---|
| **Backend Climate Duration & Config UX** | `backend_duration_worker` (`Model: 'flash'`) | `ponytail`, `antislop-code` | `custom_components/lepas/number.py`, `tests/test_config_ux.py` |
| **Frontend Lovelace Card & Card Tests** | `frontend_card_worker` (`Model: 'pro'`, file `>600L` & `>=3` files) | `antislop-ui`, `ponytail`, `antislop-code` | `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py` |
| **Release & Live HA Deploy** | Master Direct (post-tests & post-Tier-3) | — | `custom_components/lepas/manifest.json`, `pyproject.toml`, `CHANGELOG.md`, `lepas-card.js` (`CARD_VERSION`/`HERO_IMAGES`/`DEFAULT_HERO`), `scp` -> `192.168.88.231`, `ha_restart` |

---

## Blast Radius & StateGraph

### `BlastRadius`
- `direct_files`:
  - `custom_components/lepas/number.py` (51-94)
  - `custom_components/lepas/lovelace/lepas-card.js` (throughout card IIFE, CSS, `LepasCard`, removal of `LepasStatsCard`/`LepasStatsCardEditor`)
  - `tests/test_config_ux.py`
  - `tests/lepas_card.test.mjs`
  - `tests/test_lovelace_card.py`
  - Release metadata (post-verification): `custom_components/lepas/manifest.json`, `pyproject.toml`, `CHANGELOG.md`
- `transitively_affected`:
  - `custom_components/lepas/coordinator.py` (`air_durations()`, `notify_schedule_changed()`, `clima_duration`, `next_departure_occurrence()`) — read/invoked by `number.py`, no edits required.
  - `custom_components/lepas/core/commands.py` (`durata_ammessa`) — imported and reused by `number.py`, no edits required.
  - `custom_components/lepas/sensor.py` (`LepasNextDepartureSensor`, `LepasTextSensor` `cmd_status`) — consumed by `number.py` notifications and `lepas-card.js`, no edits required.
  - `custom_components/lepas/__init__.py` (`_async_register_card` reads `manifest.json` dynamically for `?v=<version>`) — transitively serves updated JS URL without edits.
  - Live Home Assistant VM (`192.168.88.231:/config/custom_components/lepas/`) — updated via `scp` + `ha_restart` after push.
- `uncertain`:
  - Existing user Lovelace dashboards referencing `custom:lepas-stats-card` (intentional breaking removal requested by user in Opzione 1; stats are now accessed from inside `LepasCard`).

### `StateGraph` (`onSuccess:` / `onFailure:`)
1. **Confirm Dialog Async Reset Lock (`createConfirmDialogController`)**:
   - `open({ ..., closeOnConfirmImmediate: false, execute })` (saving `closeOnConfirmImmediate` and `execute` onto `ctrl.pendingAction`):
     - `onSuccess`: sets `ctrl.inFlight = true`, disables `confirmBtn`, `cancelBtn`, and `[data-stats-reset]`, guards `close()`/`onCancel`/`onPointerUp` while `inFlight` (except internal `finalize`/`destroy`), awaits `execute()` -> `finalize()` (with `settled` guard) clears `inFlight = false`, re-enables buttons, closes `confirmDialog`, refreshes card state.
     - `onFailure`: if `execute()` throws synchronously or returns a rejected Promise, `try/catch` + `finally` ensures `finalize()` clears `ctrl.inFlight = false`, re-enables buttons, surfaces error in `_errorMsg` (mirrored into `[data-bind="statsErrorBanner"]` inside `statsDialog` top-layer!), and closes/unlocks `confirmDialog` so the modal is never wedged.
2. **Command Outcome 5-Minute TTL Timer (`_cmdTtlTimer`)**:
   - `onSuccess`: clears any existing `_cmdTtlTimer`; if connected (`this.isConnected !== false`) and `outcome && outcome.ok && Number.isFinite(outcome.tsMs)`, schedules single `setTimeout` for remaining TTL + 50ms -> calls `this._render()` (using `this._hass`, never `_applyBindings()` without arguments!) to hide the expired badge.
   - `onFailure` / Teardown: `disconnectedCallback()` and non-expiring states (`null` or error) clear `_cmdTtlTimer` so no dangling timer runs on detached elements (and Node tests always call `disconnectedCallback()` / clean up).
3. **Live Home Assistant Deploy (`192.168.88.231`)**:
   - `onSuccess`: create explicit timestamped remote backup (`ssh ... "mkdir -p /tmp/lepas_bak && cp -a /config/custom_components/lepas /tmp/lepas_bak/lepas_$(date +%s)"`) BEFORE `scp`, transfer updated files, run `ha_restart` (`AB-LEP-005`), verify HA comes back online (`ha_get_entity_state` + `ha_core_logs` for zero import/frontend errors).
   - `onFailure`: if `scp` or `ha_restart` fails, report exact error to user without claiming live HA verification; restore `/tmp/lepas_bak/lepas_*` if partial copy occurred.

### Test Falsification Mandate
- **Backend Duration Alignment (`tests/test_config_ux.py`)**: Test extends `_setup_entry` with `air_durations: list[int] | None = None` (`DATA_AIR_DURATIONS`, default `None` so existing `value=20` test stays valid). With `air_durations=[5, 10, 15]`, verifies `number.lepas_climate_duration` exposes `min == 5`, `max == 15`, `step == 5`, `allowed_durations == [5, 10, 15]`, raises `ServiceValidationError` on out-of-range `number.set_value(value=30)` per HA Core validation, snaps in-range `number.set_value(value=12) -> 10` (and `[5, 15]` `value=10 -> 5`), snaps out-of-range `30 -> 15` via both `mock_restore_cache` (`State(..., "30")`) and direct `entity.async_set_native_value(30)`, and updates `sensor.lepas_next_departure.attributes["climate_start_at"]` immediately on `value: 10`. Fails immediately if `number.py` ignores `air_durations()`, omits `allowed_durations`, fails to snap, or drops `notify_schedule_changed()`.
- **Stats Modal & Removal (`tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`)**:
  - Verify `tests/test_lovelace_card.py` checks dynamic `?v=<manifest.json version>` (per `AB-LEP-008`) and asserts `"lepas-stats-card"` does NOT appear anywhere in `lepas-card.js` (not even in comments).
  - Verify `window.customCards` does NOT include `"lepas-stats-card"` and `customElements.get("lepas-stats-card")` is undefined.
  - Verify clicking `[data-action-id="open_stats"]` opens `[data-bind="statsDialog"]` (and stays **enabled** when `car_in_use: true` per `AB-LEP-014`), renders real charging KPIs (`today`, `month`, `year`, `from_start`), updates values on `home`/`away` scope click, switches SVG chart bars on `7d`/`30d`/`12m`, renders EV & Hybrid consumption rows (including `50 km` / `avgEnergy50` / `avgFuel50`, `statsEmptyCard`, `hass-more-info` on `[data-e]` cells, and hides Hybrid on BEV), toggles units in `localStorage`, and executes `button.press` via `confirmDialog` with in-flight lock + error surfacing inside `[data-bind="statsErrorBanner"]` + unlock on sync throw / async rejection. Fails if modal doesn't open, bindings are missing, or reset lock wedges.
- **Command Badge TTL & Plancia-Only (`tests/lepas_card.test.mjs`)**:
  - Verify `[data-bind="climateCmdBar"]` does not exist in DOM.
  - Verify `formatCommandOutcome` (per Spec §2.2) uses timestamp precedence: when `cmdStateObj` is active (`!useLocal`) and matches `"In attesa"`/`"Waiting"`/`"Wachten"`, returns `null`; a newer `localFeedback` (always carrying `ts: Date.now()` in `_callService`) supersedes an older waiting `cmdStateObj`, while a newer waiting `cmdStateObj` hides an older `localFeedback`; returns outcome for success with finite `tsMs` `<= 300000 ms`, returns `null` for success `> 300000 ms` (or missing `tsMs`), and keeps errors visible even after `> 300000 ms`.
  - Verify live card timer hides success badge after 5 minutes (calling `this._render()` via `mock.timers` + `disconnectedCallback()` cleanup). Fails if TTL is ignored, waiting text shows, or timer leaks.
- **Duration Chips (`tests/lepas_card.test.mjs`)**:
  - Verify `resolveClimateDurationOptions` rejects booleans/non-integers, deduplicates `[cdMin, cdMax]` when `cdMin === cdMax`, and rendered `[data-action-id="climate_duration"]` buttons show `[5, 10, 15]` when `allowed_durations: [5, 10, 15]` is present and `[5, 10, 15, 20, 25, 30]` when absent (`min: 5, max: 30`). Fails if hardcoded `[5, 10, 15, 20, 30]` remains.

---

## Tasks

### Task 1: Backend Climate Duration Alignment (`backend_duration_worker`)

**Files:**
- Modify: `custom_components/lepas/number.py:13-94`
- Test: `tests/test_config_ux.py:1-85, 301-356` (plus new test function after `L355`)

**Interfaces:**
- Consumes: `coord.air_durations() -> list[int]` (`coordinator.py:3186`), `durata_ammessa(minuti, durate) -> int | None` (`core/commands.py:708`)
- Produces: `number.lepas_climate_duration` (`LepasConfigNumber`) with `native_min_value`, `native_max_value`, `native_step`, `extra_state_attributes == {"allowed_durations": list[int]}` (when `air_durations()` is non-empty), snapped `coord.clima_duration`, and immediate `coord.notify_schedule_changed(sync_charge=False)`

- [ ] **Step 1: Write failing test in `tests/test_config_ux.py`**
  Import `DATA_AIR_DURATIONS` from `custom_components.lepas.const` and add optional `air_durations: list[int] | None = None` to `_setup_entry` (default `None` so existing `test_number_notify_schedule_and_climate_target_temp_sync` with `value=20` remains untouched). Add `test_climate_duration_aligned_to_air_durations_and_clamps`:
  - Setup entry with `air_durations=[5, 10, 15]`, assert `state.attributes["min"] == 5`, `state.attributes["max"] == 15`, `state.attributes["step"] == 5`, `state.attributes["allowed_durations"] == [5, 10, 15]`.
  - Assert `pytest.raises(ServiceValidationError)` when calling `number.set_value` with `value=30` (HA Core range check).
  - Call `number.set_value` with `value=12` -> snapped to `10` (`coord.clima_duration == 10`), and verify `sensor.lepas_next_departure.attributes["climate_start_at"]` updates immediately (`06:50:00+00:00` for `07:00` departure).
  - Test direct `entity.async_set_native_value(30)` -> snapped to `15`, non-contiguous `[5, 15]` with `number.set_value(value=10) -> 5`, and `mock_restore_cache` (`State("number.lepas_climate_duration", "30")`) -> restored as `15` and pushed to `coord.clima_duration == 15`.
- [ ] **Step 2: Implement `allowed_durations` alignment in `custom_components/lepas/number.py`**
  - Import `math` and `from .core.commands import durata_ammessa`.
  - In `LepasConfigNumber.__init__`:
    ```python
    self._allowed_durations: list[int] = []
    if attr == "clima_duration" and hasattr(coord, "air_durations"):
        raw_allowed = coord.air_durations()
        allowed = sorted(
            {
                int(d)
                for d in raw_allowed
                if isinstance(d, int) and not isinstance(d, bool) and d > 0
            }
        )
        if allowed:
            self._allowed_durations = allowed
            vmin = min(allowed)
            vmax = max(allowed)
            if len(allowed) >= 2:
                diffs = [b - a for a, b in zip(allowed, allowed[1:]) if b > a]
                step = math.gcd(*diffs) if diffs else step
            else:
                step = min(step, allowed[0])
    ```
    Initialize `self._value = self._snap_value(default)` and call `self._push()` (instead of raw `setattr(coord, attr, default)`).
  - Add helper `_snap_value(self, value: float) -> float`:
    ```python
    def _snap_value(self, value: float) -> float:
        try:
            num = float(value)
        except (TypeError, ValueError):
            return self._value if hasattr(self, "_value") else float(self._allowed_durations[0])
        if not math.isfinite(num):
            return self._value if hasattr(self, "_value") else float(self._allowed_durations[0])
        if not self._allowed_durations:
            return num
        corrected = durata_ammessa(num, self._allowed_durations)
        return float(corrected) if corrected is not None else float(int(num))
    ```
  - In `async_added_to_hass`: when `restored`, parse/snap inside `try/except (TypeError, ValueError, OverflowError)` (`self._value = self._snap_value(last.native_value)`), then `self._push()` and preserve `if restored and hasattr(self.coordinator, "notify_schedule_changed"): self.coordinator.notify_schedule_changed()` (with `sync_charge=(self._attr == "charge_duration_hours")`).
  - In `async_set_native_value`: `self._value = self._snap_value(value)`, `self._push()`, `notify_schedule_changed(sync_charge=(self._attr == "charge_duration_hours"))`, `self.async_write_ha_state()`.
  - Add `@property def extra_state_attributes(self) -> dict[str, list[int]] | None:` returning `{"allowed_durations": list(self._allowed_durations)}` if `self._allowed_durations` else `None`.

---

### Task 2: Frontend `LepasCard` Stats Modal, Removal of `LepasStatsCard`, `cmdResultBadge` TTL & Climate Duration Chips (`frontend_card_worker`)

**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js`
- Modify: `tests/lepas_card.test.mjs`
- Modify: `tests/test_lovelace_card.py`

**Interfaces:**
- Consumes: `number.lepas_climate_duration` (`attributes.allowed_durations`, `min`, `max`), `sensor.*command_result`, `sensor.*charging_energy_{today,month,year,from_start}`, `sensor.*average_{energy,fuel}_consumption`, `sensor.*{ev,hybrid}_consumption_{100km,1000km,from_start}`, `button.*reset_{charging,consumption}_from_start`
- Produces:
  - `LepasCard` with `.stats-btn` opening `<dialog class="stats-dialog" data-bind="statsDialog">`
  - `formatCommandOutcome(cmdStateObj, localFeedback, lang, nowMs)` (5-min success TTL, persistent errors, waiting suppression)
  - `resolveClimateDurationOptions(cliDurState)` exposed on `LepasCard._helpers`
  - Removal of `LepasStatsCard`, `LepasStatsCardEditor`, and `lepas-stats-card` registrations

- [ ] **Step 1: Add I18N keys, `SVG_PATHS.chart`, `CMD_WAITING_STATES`, `CMD_SUCCESS_TTL_MS`, `resolveClimateDurationOptions`, and update `formatCommandOutcome` in `lepas-card.js`**
  - Add `statsBtnLabel` / `closeDialog` in `I18N.{it,en,nl}` (`it`: `"Statistiche"`, `"Chiudi"`; `en`: `"Statistics"`, `"Close"`; `nl`: `"Statistieken"`, `"Sluiten"`).
  - Ensure `SVG_PATHS.chart` is defined (e.g., `mdi:chart-box-outline` path) for `.stats-btn`.
  - Add `CMD_SUCCESS_TTL_MS = 5 * 60 * 1000;` and `CMD_WAITING_STATES = ["in attesa", "waiting", "wachten"];`.
  - Update `formatCommandOutcome(cmdStateObj, localFeedback, lang, nowMs)`:
    - `var now = typeof nowMs === "number" && Number.isFinite(nowMs) ? nowMs : Date.now();`
    - Keep timestamp precedence aligned with Spec §2.2 (`_callService` always sets `ts: Date.now()` on `this._lastCmdFeedback`): compare `fbMs` vs `cmdMs` when both exist (`useLocal` if `!cmdAlive || (hasLocal && (!Number.isFinite(cmdMs) || (Number.isFinite(fbMs) && fbMs >= cmdMs)))`).
    - When `!useLocal` (i.e. `cmdStateObj` is active): if `CMD_WAITING_STATES.indexOf(String(cmdStateObj.state || "").trim().toLowerCase()) >= 0`, return `null`.
    - Parse `tsMs = parseOutcomeTsMs(chosenTs)`.
    - If `ok`: if `!Number.isFinite(tsMs) || (now - tsMs) > CMD_SUCCESS_TTL_MS`, return `null`.
    - Return `{ text: ..., ok: ok, tsMs: tsMs }`.
  - Add `resolveClimateDurationOptions(cliDurState)` using NO `?.` and NO `??`:
    - Read `attrs = (cliDurState && (cliDurState.a || cliDurState.attributes)) || null;` (supporting both internal VM `.a` and raw HA state `.attributes`).
    - Check `attrs && Array.isArray(attrs.allowed_durations)`: collect integers `typeof d === "number" && Number.isInteger(d) && d > 0` (excluding booleans/floats), deduplicate and sort ascending; if non-empty, return it.
    - Else parse numeric `cdMin` (fallback `5`) / `cdMax` (fallback `30`), filter `[5, 10, 15, 20, 25, 30]` within `[cdMin, cdMax]`; if empty, return `cdMin === cdMax ? [cdMin] : [cdMin, cdMax]`.

- [ ] **Step 2: Extend `createConfirmDialogController` for per-open `closeOnConfirmImmediate` & `execute` + add `statsDialog` HTML/CSS**
  - In `createConfirmDialogController`:
    - `open(spec, t, actionEl)` stores `closeOnConfirmImmediate` and `execute` on `ctrl.pendingAction`.
    - While `ctrl.inFlight` is `true`, disable `confirmBtn`, `cancelBtn`, and all `[data-stats-reset]` buttons inside `host.shadowRoot`, and ignore `close()` (unless forced by `finalize`/`destroy`), `onCancel`, and `onPointerUp`.
    - `confirm(onExecute)` resolves `closeImmediate = (pending && typeof pending.closeOnConfirmImmediate === "boolean") ? pending.closeOnConfirmImmediate : Boolean(options.closeOnConfirmImmediate);` and `runner = (pending && typeof pending.execute === "function") ? pending.execute : onExecute;`.
    - Use a `settled` guard in `finalize` and wrap `runner(pending, finalize)` in `try/catch` + Promise `.then(..., ...)` so both sync throws and async rejections release `inFlight`, re-enable buttons, surface error in `_errorMsg`, and close `confirmDialog`.
  - Add CSS for `.hero-overlay-actions`, `.stats-btn`, `.stats-dialog`, `.stats-dialog-header`, `.stats-dialog-body` (reusing `.cons-*`, `.stats-*`, `.scope-btn`, `.chart-range-btn` styles). Ensure `.hero-overlay-top .stats-btn` has `pointer-events: auto`.
  - Remove `.climate-meta-bar` CSS and `<div class="climate-meta-bar hidden" data-bind="climateCmdBar">...</div>` HTML + `climateCmdBar` bindings in `_applyBindings`.

- [ ] **Step 3: Integrate Stats Modal HTML, state (`_statsScope`, `_statsChartRange`, `_statsOpen`), handlers, bindings & reset flow into `LepasCard`**
  - In `LepasCard.constructor()`: initialize `_statsScope = "all"`, `_statsChartRange = "7d"`, `_statsOpen = false`, `_cmdTtlTimer = null`, `_statsOutsidePress = false`, `_renderedCliDurKey = ""`, `_chartMeta = null`.
  - In `.hero-overlay-top`: wrap `.stats-btn` (`data-action-id="open_stats"`, never disabled by `carInUse` per `AB-LEP-014`) and `.soc-btn` inside `.hero-overlay-actions`.
  - Render `<dialog class="stats-dialog" data-bind="statsDialog">` before `confirmDialog` in `_buildSkeletonHtml` containing:
    - Modal header + close button (`data-dialog-action="close-stats"`).
    - Internal dismissible error banner (`[data-bind="statsErrorBanner"]`, `[data-bind="statsErrorText"]`, `[data-dismiss-error]`) synchronized with `this._errorMsg` so errors stay visible and clickable inside the top-layer.
    - Charging KPIs (`today`, `month`, `year`, `from_start`) + scope toggle (`all|home|away`) + range toggle (`7d|30d|12m`) + SVG chart (`chartTooltip`, `_handleChartInteraction`) + Reset button + EV/Hybrid Consumption rows (including `50 km` / `avgEnergy50` / `avgFuel50`, `statsEmptyCard` `t.statsNoData`, `[data-e]` `hass-more-info`) + unit toggles + Reset button.
  - Handle opening/closing `statsDialog` (`showModal()` with `setAttribute("open", "")` fallback, close button, `cancel`, outside click — isolating `cancel`/outside clicks so `statsDialog` ignores them while `this._dialogCtrl.isOpen()` is `true`), scope/chart toggles, chart bar tooltip (`_handleChartInteraction`), consumption unit toggles, and reset buttons (`_openStatsResetDialog` passing `closeOnConfirmImmediate: false` and `execute` to `this._dialogCtrl.open(...)` calling `button.press`).
  - Update `_applyBindings` to bind stats data cleanly (including `statsErrorBanner`), manage `_cmdTtlTimer` cleanly (only schedule if `this.isConnected !== false`, clear in `disconnectedCallback()` and on outcome change/clear; timer callback invokes `this._render()` using `this._hass`, never `_applyBindings()` without args), and use `resolveClimateDurationOptions(cliDur)` in both `_renderInner` (for `_renderedCliDurKey` + `regAction("climate_duration_" + v, ...)`) and `_buildSkeletonHtml`.

- [ ] **Step 4: Remove `LepasStatsCard`, `LepasStatsCardEditor`, and `lepas-stats-card` registrations from `lepas-card.js`**
  - Delete `LepasStatsCardEditor` class, `LepasStatsCard` class, `customElements.define("lepas-stats-card-editor", ...)`, `customElements.define("lepas-stats-card", ...)`, and the `lepas-stats-card` entry in `window.customCards`. Ensure `"lepas-stats-card"` does not appear anywhere in `lepas-card.js` (not even in comments).
  - Expose `resolveClimateDurationOptions` on `LepasCard._helpers`.
  - Run `node --check` and confirm zero `?.` or `??` anywhere in `lepas-card.js`.

- [ ] **Step 5: Update `tests/test_lovelace_card.py` and `tests/lepas_card.test.mjs`**
  - In `tests/test_lovelace_card.py:125-152`: read `manifest.json["version"]` dynamically and verify `?v=<version>` (per `AB-LEP-008`), verify `type: "lepas-card"` in `window.customCards`, and assert `"lepas-stats-card" not in source`.
  - In `tests/lepas_card.test.mjs`:
    - Remove `LepasStatsCard` / `LepasStatsCardEditor` imports & `createStatsCard` helper; add assertion that `customElements.get("lepas-stats-card")` and `window.customCards` entry for `"lepas-stats-card"` do not exist.
    - Migrate/rewrite all stats KPI, scope, chart, consumption, BEV hiding, unit persistence, reset dialog + in-flight lock + sync/async error recovery, and XSS/i18n tests to run through `LepasCard` + clicking `[data-action-id="open_stats"]` and inspecting `[data-bind="statsDialog"]`.
    - Add tests for:
      - `climateCmdBar` absent from DOM and `cmdResultBadge` only in *Plancia*.
      - `formatCommandOutcome` following timestamp precedence (hiding `"In attesa"`/`"Waiting"`/`"Wachten"` when active, fresh `localFeedback` with `ts` superseding older waiting state and vice versa, expiring success after 5 min `300001 ms` or missing `tsMs`, keeping errors visible after `> 5 min`), and auto-hide timer behavior on live card calling `_render()` with `disconnectedCallback()` cleanup.
      - `resolveClimateDurationOptions` (supporting `.a` and `.attributes`, bool/float rejection, `[cdMin, cdMax]` dedup) + rendered chips `[5, 10, 15]` when `allowed_durations: [5, 10, 15]` and `[5, 10, 15, 20, 25, 30]` fallback, plus `[data-action-id="open_stats"]` remaining enabled when `car_in_use: true`.

---

### Task 3: Full Verification, Dual-Gate Tier 3 Audit, Release `v1.30.1`, Push & Live HA Deploy (Master)

- [ ] **Step 1: Run full test & lint suites**
  - `/home/federico/.local/bin/uv run --with pytest pytest -q --tb=short --maxfail=2`
  - `node --test tests/lepas_card.test.mjs`
  - `uv run ruff check custom_components/ tests/` and `uv run ruff format --check custom_components/ tests/`
- [ ] **Step 2: Tier 3 Dual-Gate Audit**
  - Pass 1: `python3 /home/federico/skills_library/scripts/local_llm_offload.py --task review-hygiene --files custom_components/lepas/number.py custom_components/lepas/lovelace/lepas-card.js --json` (and `'flash'` review if UI / fallback required).
  - Pass 2: Reuse Stage 2 `sentinel_auditor` (`Model: 'inherit'`, CID `be2b9aff-c044-4f6a-a081-31136db7ad78`) via `send_message` to audit final implementation on Six Pillars and seal `APPROVED_TREE=$(git write-tree)`.
- [ ] **Step 3: Bump Version `v1.30.1` & Update `CHANGELOG.md` + Docs/Graphify**
  - Update `custom_components/lepas/manifest.json` (`1.30.1`), `pyproject.toml` (`1.30.1`), `CARD_VERSION = "1.30.1"` AND `?v=1.30.1` in `HERO_IMAGES` and `DEFAULT_HERO` (`lepas-card.js:86-93`, or derive from `CARD_VERSION`) per `AB-LEP-008`, and `CHANGELOG.md` (`## v1.30.1 — 2026-11-19` bilingual EN/IT).
  - Run `graphify update .` and re-run `pytest` + `ruff` + `node --test`.
  - Commit, `git tag -f v1.30.1`, `git push origin main`, `git push -f origin v1.30.1`.
- [ ] **Step 4: Deploy to Live Home Assistant (`192.168.88.231`) & Restart HA**
  - Create remote backup (`ssh -i ~/.ssh/id_ed25519 root@192.168.88.231 "mkdir -p /tmp/lepas_bak && cp -a /config/custom_components/lepas /tmp/lepas_bak/lepas_$(date +%s)"`), then copy updated `custom_components/lepas/number.py`, `custom_components/lepas/manifest.json`, and `custom_components/lepas/lovelace/lepas-card.js` via `scp -i ~/.ssh/id_ed25519` to `root@192.168.88.231:/config/custom_components/lepas/`.
  - Trigger `ha_restart` via `home-assistant` MCP tool and verify HA comes back healthy (`ha_get_entity_state` on `number.lepas_climate_duration` / `sensor.lepas_next_departure` AND `ha_core_logs` for zero import/frontend errors).
