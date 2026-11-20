# LepasCard Horizontal Desktop Cockpit UX Restyle & Flicker Fix — Design Spec

**Date:** 2026-11-20  
**Target Version:** `v1.32.0` (minor feature/UX enhancement)  
**Primary Component:** `custom_components/lepas/lovelace/lepas-card.js`  
**Tests:** `tests/lepas_card.test.mjs`, `tests/test_lepas_card.py`, `tests/test_lovelace_card.py`  

## 1. Problem Statement
Observed from live Home Assistant desktop screenshots and video (`2026-11-20`):
1. **Unbalanced Tall Multi-Column Desktop Layout**: Stacking Overview, Live Charging, Scheduled Charging, Weekly Departures, and Battery Preheat created huge vertical scrolling and an empty dark void on the right side of the dashboard.
2. **Duplicate Controls in Desktop Mode**: Overview's *Quick Actions* (`Unlock`, `Climate OFF`, `Trunk`, `Flash lights`) duplicated adjacent buttons in *Security & Closures* and *Climate*.
3. **Full-DOM Rebuild Flicker on Warning Changes**: `warnSig` was included in `structKey`, causing `shadowRoot.innerHTML` to be wiped and rebuilt whenever a warning state changed transiently.
4. **Stale Editor Placeholder**: `LepasCardEditor` image input placeholder still displayed `?v=1.30.0` instead of `CARD_VERSION`.

## 2. Approved Architecture (Horizontal 2-Column Cockpit Split)
1. **Desktop Horizontal Split (`>= 680px` for `auto`, `>= 560px` for `cockpit`)**:
   - Uses `align-items: stretch` on `.cockpit-grid` paired with `flex: 1` on the active panels and bottom `.surface` cards in `.cockpit-left` and `.cockpit-right` so both columns always share the exact same outer height and bottom edge alignment.
   - **Left Column (`.cockpit-left`, always visible)**:
     - **Hero Card** (2:1 vehicle render, `status-pill`, gradient SoC ring, vehicle title/subtitle, charging badge, Statistics modal button, incremental `warnsRow`, `errorBanner`).
     - **Overview Telemetry & Sync** moved directly under the car image: 2×2 `metrics-grid` (EV Range, Total Range, Charging kW, Odometer) + Freshness/Sync surface (`Updated`, `cmdResultBadge`, `Refresh location`, `Refresh full status`, `Wake car` via `.cockpit-wake-btn`, `Auto updates`).
     - **No Duplicate Quick Actions on Desktop**: `.quick-actions-surface` is hidden via CSS inside desktop `auto`/`cockpit`, while remaining fully visible in `compact` / mobile `< 680px` mode.
     - Optional `.overview-extras` (`cfg.entities` / `cfg.show_all`) renders cleanly at the bottom of the left column (or full-width row below) without disturbing right-column tab alignment.
   - **Right Column (`.cockpit-right`, interactive switcher at top)**:
     - **Top Switcher Bar (`.tabs-bar`)**: hides `[data-tab="overview"]` on desktop (`auto >= 680px` / `cockpit >= 560px`) so the 3 operational buttons **`Climate` | `Charging` | `Security`** sit cleanly across the top of the right column.
     - **Active Operational Panel**: displays only the selected panel (`climate`, `charging`, or `security`), driven by `default_tab` (`is-active`) with `.is-desktop-fallback` automatically activating `security` on desktop whenever `this._activeTab === "overview"` (preserving `overview` if resized back to mobile).
     - Inside **Charging** (`[data-panel="charging"]`): **Live Charging** stays visible on top, with a compact **Schedule Switcher** (`Scheduled Charging | Departures`) toggling between `schedChgSurface` and `depSurface` (including `depExtrasBox` and `batteryHeatBox`) in place without rebuilding `shadowRoot.innerHTML`.
2. **Mobile / Vertical Compact Mode (`< 680px` `auto` or `data-layout="compact"`)**:
   - `.cockpit-left` and `.cockpit-right` flatten via `display: contents` with CSS `order` (`hero-region` -> 4-tab `.tabs-bar` -> active `.panel` -> `.overview-extras`), preserving 100% of existing vertical mobile UX (`quickActionsSurface` visible, `Scheduled Charging` & `Departures` stacked).
3. **Zero-Flicker Incremental `warnsRow`**:
   - Remove `warnSig` from `structKey`; render permanent `<div class="warns-row hidden" data-bind="warnsRow" hidden></div>` in `hero-region` and patch incrementally in `_applyBindingsInner` via `this._lastWarnSig`.
4. **Editor Placeholder Alignment**:
   - Update `LepasCardEditor` image placeholder to `"/lepas_card/lepas-hero-grey.png?v=" + CARD_VERSION`, keeping `"Auto"` as the default first swatch when `config.color` is unset or `"auto"`.
