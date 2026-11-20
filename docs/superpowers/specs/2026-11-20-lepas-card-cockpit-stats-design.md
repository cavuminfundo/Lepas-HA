# LepasCard Cockpit Balanced Desktop Restyle & Compact Inline Statistics — Design Spec

**Date:** 2026-11-20  
**Target Version:** `v1.32.0` (paired with Horizontal 2-Column Cockpit Restyle)  
**Primary Component:** `custom_components/lepas/lovelace/lepas-card.js`  
**Tests:** `tests/lepas_card.test.mjs`, `tests/test_lepas_card.py`

## 1. Problem Statement
In the horizontal 2-column Cockpit layout:
1. Keeping Mobile/Compact (`< 680px` `auto` & `data-layout="compact"`) 100% unchanged while balancing the left column (`Hero` + `Overview` + `Sync` + `Statistics`) against all three right-hand operational tabs (`Climate`, `Charging` Manual & Departures, `Security`) requires proportional density across desktop panels without removing any Mobile setting or control.
2. Displaying all multi-period KPIs inside the left bottom Statistics box made the left column too tall, whereas **3 inline summary KPIs** (`Charging · Today`, `EV · 50 km`, `Fuel/Hybrid · 50 km`) keep the summary readable in one glance with 1-click access to the full `<dialog>` modal.
3. On Lepas L8 with all 12 `allowed_climate_extras` active, `Departure scheduler` vertically expanded to `1228 px` in 2 columns and stretched `.cockpit-stats-row` vertically.

## 2. Approved Architecture (`proj2-*.png`)
1. **Desktop-Only Compact Statistics Surface (`.cockpit-stats-surface`)**:
   - Rendered inside `.cockpit-left` (outside `[data-panel="overview"]`) right after `overviewHtml` when `ctx.chgToday || ctx.hasAnyCons`.
   - Hidden by default (`display: none;`) on Mobile and `data-layout="compact"`.
   - Shown ONLY in `ha-card[data-layout="cockpit"]` and `@container (min-width: 680px)` / `@supports not` `@media (min-width: 680px)` `ha-card[data-layout="auto"]`:
     - `.cockpit-stats-surface { display: flex; flex-direction: column; gap: 8px; flex: 1; }`
     - `.cockpit-stats-row { flex: 1; align-items: stretch; max-height: 152px; }` so KPI cells center neatly without over-stretching vertically on tall right panels (like 12-extra `Departure scheduler`).
     - `.cockpit-stats-slot > .cons-cell { justify-content: center; gap: 4px; }`
   - Displays up to **3 inline KPIs**: `Charging · Today` (`"all"` scope locked), `EV · 50 km`, and `Fuel/Hybrid · 50 km` (hidden automatically on pure BEV via `!vm.hasHybridCons`), synced via `data-stats-mirror`, `syncInteractiveCellAttrs`, `formatChargingKpiValue`, and `applyConsumptionBindings`.
   - Header button **`Charts & details`** (`t.statsExpandBtn`, `data-action-id="open_stats"`, exempt from `car_in_use` per `AB-LEP-016`) opens `<dialog data-bind="statsDialog">`.
2. **Left-Column `Updated / Sync` Placement (`[data-panel="overview"]`)**:
   - Remains inside `[data-panel="overview"]` on the left column directly above `.cockpit-stats-surface`, with `.cockpit-left.has-cockpit-stats .panel[data-panel="overview"]` and `> .surface:last-of-type` kept compact (`flex: 0 0 auto;`).
   - Right column `.cockpit-right` starts cleanly with `.tabs-bar` (`Climate | Charging | Security`).
3. **Desktop Ergonomics & Height Parity (`cockpit` & `auto >= 680px` only, shared via `desktopLayoutRules`)**:
   - **Hero**: `.hero-stage { aspect-ratio: 16 / 9; }`.
   - **Security (~900–915 px)**: `.bp-stage` expanded (`minmax(80px, 1fr) minmax(136px, 162px) minmax(80px, 1fr)`, `padding: 20px 6px`, `gap: 12px`), `.tpms-col { gap: 26px; }`, `.tpms-box { padding: 11px 12px; }`, bottom surface `gap: 14px; justify-content: space-between;`, `.btn-grid { gap: 11px; }`, `.ctrl-btn { min-height: 50px; }`.
   - **Climate (~910 px)**: `.panel[data-panel="climate"] > .surface { padding: 14px 13px; gap: 12px; }`, `.ctrl-btn { min-height: 48px; }`, `.seat-btns .ctrl-btn { min-height: 46px; }`.
   - **Charging — Manual (~888 px) & Full 12-Extra Departures (~1017 px, ZERO controls removed)**: `[data-bind="depSurface"] { gap: 7px; padding: 10px 12px; }`, `.ctrl-btn`/`.ctrl-input`/`.ctrl-select` `min-height: 36px;`, `.dep-summary-row { min-height: 38px; padding: 6px 10px; }`, `.day-chip { min-height: 44px; padding: 3px 2px; }`, `.dep-subbox { padding-top: 6px; gap: 5px; }`, `.climate-extras-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 5px; }`, `.climate-extra-chip { min-height: 34px; padding: 4px 6px; font-size: 0.7rem; }`.
4. **Zero Mobile Regression**:
   - All balance/ergonomics rules are emitted exclusively by `desktopLayoutRules(cardSel, indent)` inside `cockpit`, `@container (min-width: 680px)` `auto`, and `@supports not` `@media (min-width: 680px)` `auto`. Mobile/Compact retains 2-column `.climate-extras-grid`, `2 / 1` `.hero-stage`, and no `.cockpit-stats-surface`.
