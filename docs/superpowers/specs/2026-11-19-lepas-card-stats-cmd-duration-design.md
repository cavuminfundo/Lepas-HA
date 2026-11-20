# LepasCard Integrated Statistics, Command Badge TTL & Climate Duration Alignment — Design Spec

**Date:** 2026-11-19  
**Path Classification:** Architectural  
**Target Files:**
- `custom_components/lepas/lovelace/lepas-card.js`
- `custom_components/lepas/number.py`
- `tests/lepas_card.test.mjs`
- `tests/test_lovelace_card.py`
- `tests/test_config_ux.py`

---

## 1. Goals & Scope

Consolidate vehicle charging and consumption statistics directly inside `LepasCard` via an on-demand popup modal (removing the separate `lepas-stats-card` custom card), reduce visual noise from `cmdResultBadge` across secondary tabs and stale/idle states, and align `number.lepas_climate_duration` and `LepasCard` climate duration chips with the vehicle's declared `maxAirDuration` capabilities.

---

## 2. Design Details

### 2.1 Integrated Statistics Modal in `LepasCard` & Removal of `LepasStatsCard`

- **Entry Point inside `LepasCard`**:
  - Inside `.hero-overlay-top`, group the right-side hero controls in `.hero-overlay-actions` containing:
    1. A compact icon button `<button type="button" class="stats-btn" data-action-id="open_stats" ...>` with `mdi:chart-box-outline` SVG icon (`svgIcon("chart", ...)`), localized `aria-label` and `title` (`t.statsCardDefaultTitle`).
    2. The existing `.soc-btn` battery SoC pill.
  - CSS `.hero-overlay-top` keeps `pointer-events: none`, while `.hero-overlay-top .status-pill, .hero-overlay-top .soc-btn, .hero-overlay-top .stats-btn` have `pointer-events: auto`.
  - The 4 navigation tabs (`Plancia | Clima | Ricarica | Sicurezza`) and responsive `auto` / `compact` / `cockpit` (2-col / 3-col) layouts remain unchanged.
- **Dedicated Statistics Modal (`<dialog class="stats-dialog" data-bind="statsDialog">`)**:
  - Rendered inside `LepasCard`'s `shadowRoot` before `confirmDialog` (so if `confirmDialog` opens for a reset confirmation while `statsDialog` is open, `confirmDialog` stacks cleanly on top in both native top-layer and DOM/test fallback mode).
  - Includes an internal dismissible error banner (`[data-bind="statsErrorBanner"]`) synchronized with `_errorMsg` so reset/service errors remain visible and dismissible inside the modal's top-layer when `statsDialog` is open via `showModal()`, plus `cancel`/outside-click isolation whenever `confirmDialog` is open on top.
  - Opened by `.stats-btn` via `dlg.showModal()` (with `dlg.setAttribute("open", "")` fallback when `showModal` is unavailable in test DOMs), and closed via the modal header close button (`data-dialog-action="close-stats"`), `Esc` (`cancel` event), or backdrop click (`pointerdown`/`pointerup` outside dialog rect).
  - Contains two sections matching the full feature set previously in `LepasStatsCard`:
    1. **Charging Statistics**:
       - Scope toggle (`Tutte | Casa | Fuori` -> `all | home | away`).
       - 4 KPI cards (`Oggi`, `Mese`, `Anno`, `Dall'inizio`) bound to `sensor.*charging_energy_{today,month,year,from_start}` (`home_kwh`, `away_kwh`, `sessions_count`); clicking a KPI dispatches `hass-more-info`.
       - Chart range selector (`7g | 30g | 12m` -> `7d | 30d | 12m`), interactive SVG bar chart (`buildChargingChartData`, `renderChargingChartSvg`), and hover/focus/click tooltip (`[data-bind="chartTooltip"]`).
       - Reset button (`data-stats-reset="charging"`) invoking `button.press` on `button.*reset_charging_from_start`.
    2. **Average Consumption**:
       - EV row (`average_energy_consumption`, `100 km`, `1000 km`, `from_start`) with unit toggle (`kWh/100km` <-> `km/kWh` persisted via `loadConsUnitModes` / `saveConsUnitMode`).
       - Hybrid row (`average_fuel_consumption`, `100 km`, `1000 km`, `from_start`, hidden on BEV vehicles when hybrid sensors and `fuelRange` are absent) with unit toggle (`L/100km` <-> `km/L`).
       - Clickable metric cells (`[data-e]`) dispatching `hass-more-info`.
       - Reset button (`data-stats-reset="consumption"`) invoking `button.press` on `button.*reset_consumption_from_start`.
- **Reset Confirmation & In-Flight Lock**:
  - Extend `createConfirmDialogController(host, opts)` so `open(spec, t, actionEl)` honors an optional `spec.closeOnConfirmImmediate` boolean override (falling back to the controller's default `closeOnConfirmImmediate`).
  - Existing vehicle command confirmations keep `closeOnConfirmImmediate: true`.
  - Stats reset confirmations pass `closeOnConfirmImmediate: false` and an async `execute` callback; `confirm()` keeps the confirmation dialog open with `inFlight = true` and disables reset buttons until the `button.press` Promise settles, then closes `confirmDialog` cleanly.
- **Removal of Separate Card**:
  - Remove `LepasStatsCard`, `LepasStatsCardEditor`, `customElements.define("lepas-stats-card", ...)`, `customElements.define("lepas-stats-card-editor", ...)`, and the `lepas-stats-card` entry from `window.customCards`.
  - Keep shared helper functions (`VALID_STATS_SCOPES`, `VALID_STATS_CHARTS`, `buildChargingChartData`, `renderChargingChartSvg`, `formatConsumptionCell`, etc.) inside the IIFE and keep `LepasCard._helpers` clean (including `VALID_STATS_SCOPES`, `VALID_STATS_CHARTS`, `buildChargingChartData`).
  - `LepasCardEditor` remains focused on `LepasCard` layout/theme options without adding redundant stats checkboxes.

---

### 2.2 `cmdResultBadge` Plancia-Only & 5-Minute Success TTL

- **Remove Secondary Tab Duplicate**:
  - Remove `<div class="climate-meta-bar hidden" data-bind="climateCmdBar"><span class="badge hidden" data-bind="cmdResultBadge"></span></div>` from the *Clima* tab skeleton, its `.climate-meta-bar` CSS rule, and `climateCmdBar` handling in `_applyBindings`.
  - `[data-bind="cmdResultBadge"]` remains only in the *Plancia* footer.
- **Visibility & Expiry Rules (`formatCommandOutcome(cmdStateObj, localFeedback, lang, nowMs)`)**:
  - Accept optional `nowMs` (defaults to `Date.now()`) for deterministic testing.
  - **Waiting Placeholder Suppression**: When `cmdStateObj` is the active source (not superseded by a newer `_lastCmdFeedback`), if `String(cmdStateObj.state || "").trim().toLowerCase()` matches a waiting placeholder (`"in attesa"`, `"waiting"`, `"wachten"`), return `null`.
  - **Persistent Errors**: When `ok === false`, return the error outcome regardless of timestamp age so failures remain visible until cleared or superseded.
  - **5-Minute Success TTL**: Define `CMD_SUCCESS_TTL_MS = 5 * 60 * 1000` (`300000`). When `ok === true`, parse `chosenTs` via `parseOutcomeTsMs`; if `!Number.isFinite(tsMs)` or `(nowMs - tsMs) > CMD_SUCCESS_TTL_MS`, return `null`.
  - **Auto-Hide Timer in `LepasCard`**: When `outcome && outcome.ok` with finite `tsMs`, schedule a single `_cmdTtlTimer` (`setTimeout`) for `Math.max(50, CMD_SUCCESS_TTL_MS - (nowMs - tsMs) + 50)` ms to re-run `_applyBindings` (or re-render) when the 5-minute window elapses without waiting for a new Home Assistant state event. Clear `_cmdTtlTimer` whenever a new outcome renders, hides, or in `disconnectedCallback()`.

---

### 2.3 Climate Duration Alignment (`number.py` + `LepasCard`) with `maxAirDuration`

- **Backend (`custom_components/lepas/number.py`)**:
  - In `LepasConfigNumber.__init__`: when `attr == "clima_duration"`, read `allowed = coord.air_durations() if hasattr(coord, "air_durations") else []` and normalize to sorted unique positive integers `self._allowed_durations`.
  - When `self._allowed_durations` is non-empty (e.g. `[5, 10, 15]` from `maxAirDuration: "5,10,15"` on Lepas L8):
    - `_attr_native_min_value = min(self._allowed_durations)`
    - `_attr_native_max_value = max(self._allowed_durations)`
    - `_attr_native_step = math.gcd(*diffs)` across adjacent sorted differences (fallback `step` if single element).
    - Expose `extra_state_attributes` property returning `{"allowed_durations": list(self._allowed_durations)}` when `self._allowed_durations` is non-empty (otherwise `None`).
    - Clamp/snap via `durata_ammessa(val, self._allowed_durations)` from `.core.commands`: applied to `default` in `__init__`, to restored `last.native_value` in `async_added_to_hass`, and to `value` in `async_set_native_value` before `_push()` and `notify_schedule_changed()`.
  - Preserve existing `notify_schedule_changed(sync_charge=(self._attr == "charge_duration_hours"))` behavior on both restore and `async_set_native_value`, ensuring `sensor.lepas_next_departure` (`climate_start_at`) stays synchronized immediately.
- **Frontend (`custom_components/lepas/lovelace/lepas-card.js`)**:
  - Add pure helper `resolveClimateDurationOptions(cliDurState)` exposed on `LepasCard._helpers`:
    - If `cliDurState && cliDurState.a && Array.isArray(cliDurState.a.allowed_durations)` contains valid positive integers, return sorted unique integers.
    - Otherwise filter `[5, 10, 15, 20, 25, 30]` within `[cdMin, cdMax]` (falling back to `[cdMin, cdMax]` if empty).
  - Track the serialized duration options key alongside `min`/`max` in `_renderInner` so chips and registered `climate_duration_<v>` actions rebuild automatically if `allowed_durations` changes at runtime.

---

## 3. Global Constraints & Compatibility

- **JavaScript Syntax Guard**: `custom_components/lepas/lovelace/lepas-card.js` MUST NOT contain optional chaining (`?.`), nullish coalescing (`??`), or top-level `import`/`export` anywhere in the file (including comments/strings).
- **No PII / Secrets**: Diagnostics and card views must not expose VINs, tokens, or coordinates.
- **Test Falsification**: All new unit and integration tests must verify real behavior and fail if the production logic is broken (no tautological `MagicMock` assertions).
