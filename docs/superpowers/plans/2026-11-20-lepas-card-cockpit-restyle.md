# LepasCard Horizontal Desktop Cockpit UX Restyle & Flicker Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to execute task-by-task.

**Goal:** Restructure `custom:lepas-card` desktop Cockpit into a Horizontal 2-Column Split (Left: Hero + 4 KPIs + Sync moved below the car image, no duplicate quick actions; Right: 3 operational switcher buttons `Climate | Charging | Security` on top + active panel below, with Charging/Departures switcher inside Charging), eliminate full-DOM flicker on warning updates, and align editor placeholder version.

**Architecture:** All implementation changes live in the single-bundle ES5 Web Component `custom_components/lepas/lovelace/lepas-card.js` (CSS `.cockpit-left` / `.cockpit-right` wrappers using `display: contents` on mobile/compact and 2-column horizontal grid on desktop `>= 680px` `auto` / `>= 560px` `cockpit` + `@supports not` parity, `_buildSkeletonHtml`, `_renderInner`, `_applyBindingsInner`, `_handleClick`, `LepasCardEditor`), paired with falsifiable tests in `tests/lepas_card.test.mjs`, Python compatibility checks in `tests/test_lepas_card.py` & `tests/test_lovelace_card.py`, and refreshed preview renders in `docs/images/`.

**Tech Stack:** Vanilla ES5 Shadow DOM Web Component, CSS Container Queries + CSS Grid (`@supports not` fallback), Node.js `node:test`, Python `pytest`.

**Spec:** `docs/superpowers/specs/2026-11-20-lepas-card-cockpit-restyle-design.md`

## Global Constraints
- Strictly ES5 inside `custom_components/lepas/lovelace/lepas-card.js`: `var` and `function` only, NO `?.`, NO `??` anywhere outside comments (enforced by `tests/test_lepas_card.py` and `node --check`).
- Preserve `AB-LEP-008` (`window.customCards` `type: "lepas-card"`, `"frontend"` in `after_dependencies`).
- Preserve `AB-LEP-016`: `wake_car`, `refresh_location`, `refresh_full`, `open_stats`, and charging controls remain exempt from `carInUse` gating.
- Preserve PII redaction / XSS escaping (`escapeHtml` / `self._h`) — zero VIN or GPS coordinates in DOM.
- Keep `compact` (`< 680px` `auto` or `data-layout="compact"`) vertical 4-tab UX intact for Overview quick actions and stacked Charging/Departures.

## BlastRadius
- `direct_files`:
  - `custom_components/lepas/lovelace/lepas-card.js`
  - `tests/lepas_card.test.mjs`
  - `docs/images/lepas-card-cockpit.png`
  - `docs/images/lepas-card-security.png`
- `transitively_affected`:
  - `tests/test_lepas_card.py` (verifies ES5 syntax and `?v=<manifest.version>` alignment)
  - `tests/test_lovelace_card.py` (verifies HA card registration & frontend asset serving)
  - `README.md` (links `docs/images/lepas-card-cockpit.png` and `docs/images/lepas-card-security.png`)
- `uncertain`:
  - None (backend Python entities/services untouched).

## StateGraph
- **DOM Rebuild (`_renderInner` at `L3654-3684`)**:
  - `onSuccess` (unchanged `structKey`, e.g. warning text/count change, tab click, or `[data-schedule-tab]` click): skips `shadowRoot.innerHTML` rebuild -> `warnsRow`, active tab classes, or `_scheduleTab` classes patch incrementally (zero flicker).
  - `onFailure` / structural change (`lang`, `layout`, `show_all`, `extraSig`, `allowedExtrasSig`, `cliDurOptsSig`, `entityIdsSig` changed): captures scroll & active element -> resets `this._lastWarnSig = ""` and `this._lastStatsChartSig = ""` -> rebuilds skeleton -> `_applyBindingsInner` repopulates `warnsRow`, syncs tabs + `.is-desktop-fallback`, and syncs `_scheduleTab`.
- **Right-Column Tab Selection (`_activeTab` + `.is-desktop-fallback`)**:
  - `onSuccess` (`_activeTab` in `"climate" | "charging" | "security"`): both mobile and desktop highlight that tab and display that panel.
  - `onFailure` / Overview default (`_activeTab === "overview"`): mobile/compact shows Overview tab + Overview panel; desktop hides `[data-tab="overview"]` and shows Overview in `.cockpit-left`, while `.is-desktop-fallback` activates `security` in `.cockpit-right` without mutating `_activeTab`.
- **Schedule Sub-Tab Switcher (`_scheduleTab` in `"charge" | "departure"`)**:
  - `onSuccess` (both `[data-schedule-panel="charge"]` and `[data-schedule-panel="departure"]` exist and user clicks `[data-schedule-tab]`): calls `ev.stopPropagation()`, updates `this._scheduleTab`, calls `_syncScheduleTabUi(root)` without DOM rebuild.
  - `onFailure` (only one schedule panel exists, or mode is `compact` / `< 680px` `auto`): switcher omitted or hidden by CSS; `.is-schedule-hidden` never applied when only one panel exists and has no `display: none` outside desktop `auto`/`cockpit`.
- **Verification Gate**:
  - `onSuccess`: `node --test tests/lepas_card.test.mjs`, `node --check custom_components/lepas/lovelace/lepas-card.js`, and `.venv/bin/pytest -q --tb=short --maxfail=2` exit `0`.
  - `onFailure`: enter Fix Loop targeting failing CSS/DOM contract.

## Domain Skills & Sub-Agent Roster
- **Cohesive Domain 1 — Lovelace Card UX & Tests (`frontend_ui_worker`, `Model: 'pro'` since `lepas-card.js` is `>600L`)**:
  - **Primary Skill**: `senior-frontend` (`/home/federico/skills_library/senior-frontend/SKILL.md`)
  - **Companions**: `antislop-ui` (`/home/federico/skills_library/antislop-ui/SKILL.md`), `antislop-code` (`/home/federico/skills_library/antislop-code/SKILL.md`)
  - **Files Owned**: `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`

---

### Task 1: TDD Tests for Horizontal 2-Column Cockpit, Desktop Tab Fallback, Schedule Switcher, Zero-Flicker `warnsRow` & Editor Placeholder
**Files:**
- Modify: `tests/lepas_card.test.mjs:3545`

**Interfaces:**
- Consumes: `createCard`, `createEditor`, `makeFullHass`, `makeState`, `LepasCard._helpers.CARD_VERSION` in `tests/lepas_card.test.mjs`.
- Produces: Falsifiable assertions for CSS horizontal 2-column `.cockpit-left` / `.cockpit-right` rules (`@container` + `@supports not`), mobile `display: contents` + `order`, `.quick-actions-surface` / `.cockpit-wake-btn` scoping, `.is-desktop-fallback` behavior when `default_tab: "overview"`, `.schedule-switcher` no-rebuild switching + single-panel guard, zero-rebuild `warnsRow` incremental updates + XSS escaping, and `CARD_VERSION` editor placeholder.

- [ ] **Step 1: Write failing tests in `tests/lepas_card.test.mjs`**

```javascript
test("Horizontal 2-column Cockpit places Hero+Overview on left, 3-tab operational switcher on right, hides duplicate quick actions, and toggles schedules without rebuild", () => {
  const card = createCard({ layout: "cockpit", default_tab: "overview" }, makeFullHass({
    "switch.lepas_automatic_updates": undefined,
    "binary_sensor.lepas_high_voltage_active": makeState("binary_sensor.lepas_high_voltage_active", "on", { car_in_use: true }),
    "climate.lepas_climate": makeState("climate.lepas_climate", "off", { car_in_use: true }),
  }, "it"));
  const root = card.shadowRoot;
  const cssText = root.querySelector("style").textContent;

  // Desktop 2-column split (auto >= 680px, cockpit >= 560px) in @container and @supports not fallback, with equal-height stretch
  assert.match(cssText, /@container\s*\(min-width:\s*680px\)\s*\{[\s\S]*?ha-card\[data-layout="auto"\]\s+\.cockpit-grid[\s\S]*?grid-template-columns:\s*minmax\(0,\s*0\.92fr\)\s+minmax\(0,\s*1\.12fr\);\s*align-items:\s*stretch;[\s\S]*?ha-card\[data-layout="auto"\]\s+\.tabs-bar\s+\[data-tab="overview"\]\s*\{\s*display:\s*none;\s*\}[\s\S]*?\.quick-actions-surface\s*\{\s*display:\s*none;\s*\}[\s\S]*?\.cockpit-wake-btn\s*\{\s*display:\s*inline-flex;\s*\}[\s\S]*?\.schedule-switcher\s*\{\s*display:\s*grid;\s*\}[\s\S]*?\.is-schedule-hidden\s*\{\s*display:\s*none;\s*\}/);
  assert.match(cssText, /@supports not \(container-type:\s*inline-size\)[\s\S]*?@media\s*\(min-width:\s*680px\)[\s\S]*?ha-card\[data-layout="auto"\]\s+\.cockpit-grid[\s\S]*?ha-card\[data-layout="auto"\]\s+\.quick-actions-surface\s*\{\s*display:\s*none;\s*\}/);
  assert.match(cssText, /ha-card\[data-layout="cockpit"\]\s+\.tabs-bar\s+\[data-tab="overview"\]\s*\{\s*display:\s*none;\s*\}/);

  // Ensure bare global rules (shared with compact) do NOT hide .quick-actions-surface or .is-schedule-hidden
  const beforeContainer = cssText.split("@container")[0];
  assert.ok(!/^\s*\.quick-actions-surface\s*\{\s*display:\s*none/m.test(beforeContainer));
  assert.ok(!/^\s*\.is-schedule-hidden\s*\{\s*display:\s*none/m.test(beforeContainer));

  // Structural DOM placement: left col holds hero + overview, right col holds tabs-bar + operational panels
  const leftCol = root.querySelector(".cockpit-left");
  const rightCol = root.querySelector(".cockpit-right");
  assert.ok(leftCol && rightCol);
  assert.ok(leftCol.querySelector(".hero-region"));
  assert.ok(leftCol.querySelector('[data-panel="overview"]'));
  assert.ok(rightCol.querySelector(".tabs-bar"));
  assert.ok(rightCol.querySelector('[data-panel="climate"]'));
  assert.ok(rightCol.querySelector('[data-panel="charging"]'));
  assert.ok(rightCol.querySelector('[data-panel="security"]'));

  // When default_tab is "overview", desktop fallback activates Security on the right without losing overview tab state
  const secTab = root.querySelector('[data-tab="security"]');
  const secPanel = root.querySelector('[data-panel="security"]');
  const cliTab = root.querySelector('[data-tab="climate"]');
  const cliPanel = root.querySelector('[data-panel="climate"]');
  assert.equal(secTab.classList.contains("is-desktop-fallback"), true);
  assert.equal(secPanel.classList.contains("is-desktop-fallback"), true);
  cliTab.click();
  assert.equal(secTab.classList.contains("is-desktop-fallback"), false);
  assert.equal(secPanel.classList.contains("is-desktop-fallback"), false);
  assert.equal(cliTab.classList.contains("is-active"), true);
  assert.equal(cliPanel.classList.contains("is-active"), true);

  // Schedule switcher toggles without DOM rebuild
  const chgBtn = root.querySelector('[data-schedule-tab="charge"]');
  const depBtn = root.querySelector('[data-schedule-tab="departure"]');
  const chgPanel = root.querySelector('[data-bind="schedChgSurface"]');
  const depPanel = root.querySelector('[data-bind="depSurface"]');
  const heroBefore = root.querySelector('[data-bind="heroImg"]');
  assert.ok(chgBtn && depBtn && chgPanel && depPanel && heroBefore);
  depBtn.click();
  assert.equal(root.querySelector('[data-bind="heroImg"]'), heroBefore, "Schedule tab toggle must not rebuild shadowRoot");
  assert.equal(chgBtn.getAttribute("aria-pressed"), "false");
  assert.equal(depBtn.getAttribute("aria-pressed"), "true");
  assert.equal(chgPanel.classList.contains("is-schedule-hidden"), true);
  assert.equal(depPanel.classList.contains("is-schedule-hidden"), false);

  // Wake button inside sync surface stays exempt from car_in_use gating even without auto_updates
  const cockpitWake = root.querySelector(".cockpit-wake-btn");
  assert.ok(cockpitWake);
  assert.equal(cockpitWake.disabled, false);
  assert.equal(cockpitWake.classList.contains("is-car-in-use"), false);

  // Single-panel schedule guard
  const cardChargeOnly = createCard({ layout: "cockpit" }, makeFullHass({
    "sensor.lepas_next_departure": undefined,
    "sensor.lepas_scheduled_departure": undefined,
    "switch.lepas_quick_departure": undefined,
    "switch.lepas_departure_mon_enabled": undefined,
    "switch.lepas_departure_wed_enabled": undefined,
    "switch.lepas_departure_fri_enabled": undefined,
    "button.lepas_apply_departure_schedule": undefined,
    "switch.lepas_battery_pack_heat": undefined,
    "time.lepas_battery_pack_heat_time": undefined,
    "switch.lepas_sync_battery_heat_to_departure": undefined,
  }, "it"));
  assert.equal(cardChargeOnly.shadowRoot.querySelector(".schedule-switcher"), null);
  const chargeOnlyPanel = cardChargeOnly.shadowRoot.querySelector('[data-schedule-panel="charge"]');
  assert.ok(chargeOnlyPanel);
  assert.equal(chargeOnlyPanel.classList.contains("is-schedule-hidden"), false);

  // Compact layout preserves quick actions & overview-extras tab isolation
  const compactCard = createCard({ layout: "compact", show_all: true, default_tab: "climate" }, makeFullHass({}, "it"));
  const cRoot = compactCard.shadowRoot;
  assert.ok(cRoot.querySelector('[data-bind="quickActionsSurface"]'));
  const extras = cRoot.querySelector('[data-bind="overviewExtras"]');
  assert.ok(extras);
  assert.equal(extras.closest('[data-panel="overview"]'), null);
  assert.equal(extras.classList.contains("is-active"), false);
  cRoot.querySelector('.tab-btn[data-tab="overview"]').click();
  assert.equal(extras.classList.contains("is-active"), true);
});

test("warnsRow updates incrementally without shadowRoot rebuild and escapes XSS; editor placeholder tracks CARD_VERSION", () => {
  const card = createCard({ layout: "cockpit" }, makeFullHass({}, "it"));
  const root = card.shadowRoot;
  const heroImgBefore = root.querySelector('[data-bind="heroImg"]');
  const warnsRow = root.querySelector('[data-bind="warnsRow"]');
  assert.ok(warnsRow);
  assert.equal(warnsRow.classList.contains("hidden"), true);

  card.hass = makeFullHass({
    "binary_sensor.lepas_tire_warning_front_left": makeState("binary_sensor.lepas_tire_warning_front_left", "on", { friendly_name: "Tire <img src=x onerror=alert(1)>" }),
  }, "it");
  assert.equal(root.querySelector('[data-bind="heroImg"]'), heroImgBefore, "Warning addition must NOT rebuild shadowRoot");
  assert.equal(warnsRow.classList.contains("hidden"), false);
  assert.equal(warnsRow.querySelectorAll(".warn-chip").length, 1);
  assert.ok(!warnsRow.innerHTML.includes("<img"), "Raw <img tag must not appear in warnsRow");
  assert.ok(warnsRow.innerHTML.includes("&lt;img"), "Warning text must be HTML-escaped");

  card.hass = makeFullHass({
    "binary_sensor.lepas_tire_warning_front_left": makeState("binary_sensor.lepas_tire_warning_front_left", "off"),
  }, "it");
  assert.equal(root.querySelector('[data-bind="heroImg"]'), heroImgBefore, "Warning removal must NOT rebuild shadowRoot");
  assert.equal(warnsRow.classList.contains("hidden"), true);
  assert.equal(warnsRow.querySelectorAll(".warn-chip").length, 0);

  const ed = createEditor({ type: "custom:lepas-card" }, makeFullHass({}, "it"));
  const imgInput = ed.shadowRoot.querySelector('input[data-field="image"]');
  assert.ok(imgInput);
  assert.ok(imgInput.getAttribute("placeholder").includes(`?v=${LepasCard._helpers.CARD_VERSION}`));
});
```

- [ ] **Step 2: Run test to verify RED**
  Run: `node --test tests/lepas_card.test.mjs`
  Expected: FAIL on missing `.cockpit-left`/`.cockpit-right`, CSS horizontal split rules, `.schedule-switcher`, `[data-bind="warnsRow"]`, and `?v=1.30.0` placeholder.

---

### Task 2: Implement Horizontal 2-Column Cockpit Split, Zero-Flicker `warnsRow` & Editor Placeholder
**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js:2227-2263,2430,2461,2979-3004,3654-3885,3892-4520,4551-4625`

**Interfaces:**
- Consumes: `ctx.warns`, `ctx.schedChgHtml`, `ctx.depHtml`, `ctx.wakeBtn`, `CARD_VERSION` inside `LepasCard` & `LepasCardEditor`.
- Produces: `.cockpit-left` / `.cockpit-right` layout containers (`display: contents` + CSS `order` on mobile/compact; 2-column horizontal split on desktop `auto >= 680px` / `cockpit >= 560px` + `@supports not` parity), `.is-desktop-fallback` on `[data-tab="security"]` / `[data-panel="security"]` when `_activeTab === "overview"`, `.overview-extras` sibling, `.quick-actions-surface` desktop hide + `.cockpit-wake-btn` sync-row mirror, `.schedule-switcher` + `_syncScheduleTabUi(root)`, incremental `warnsRow` with `_lastWarnSig` reset on rebuild, and `CARD_VERSION` placeholder in `LepasCardEditor`.

- [ ] **Step 1: Initialize `_scheduleTab` and `_lastWarnSig` in `LepasCard.constructor()` (`L2461`)**
  Add `this._scheduleTab = "charge";` and `this._lastWarnSig = "";` inside `LepasCard.constructor()`.

- [ ] **Step 2: Update `buildStyles()` (`L2227-2263`) for Horizontal 2-Column Cockpit + Mobile `display: contents` Fallback**
  - Replace the old `L2227-2263` layout rules with:
    ```javascript
    ".cockpit-left, .cockpit-right { display: contents; }",
    ".hero-region { order: 1; }",
    ".tabs-bar { order: 2; }",
    ".panel { order: 3; }",
    ".overview-extras { display: none; order: 4; }",
    ".overview-extras.is-active { display: flex; flex-direction: column; gap: 12px; }",
    ".cockpit-wake-btn { display: none; }",
    ".schedule-switcher { display: none; grid-template-columns: repeat(2, minmax(0, 1fr)); }",
    "ha-card[data-layout=\"cockpit\"] .cockpit-left, ha-card[data-layout=\"cockpit\"] .cockpit-right { display: flex; flex-direction: column; gap: 12px; min-width: 0; }",
    "ha-card[data-layout=\"cockpit\"] .tabs-bar { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }",
    "ha-card[data-layout=\"cockpit\"] .tabs-bar [data-tab=\"overview\"] { display: none; }",
    "ha-card[data-layout=\"cockpit\"] .panel[data-panel=\"overview\"] { display: flex; flex: 1; }",
    "ha-card[data-layout=\"cockpit\"] .cockpit-right > .panel.is-active, ha-card[data-layout=\"cockpit\"] .cockpit-right > .panel.is-desktop-fallback { flex: 1; }",
    "ha-card[data-layout=\"cockpit\"] .panel[data-panel=\"overview\"] > .surface:last-of-type, ha-card[data-layout=\"cockpit\"] .cockpit-right > .panel > .surface:last-of-type, ha-card[data-layout=\"cockpit\"] .panel[data-panel=\"charging\"] > .surface[data-schedule-panel]:not(.is-schedule-hidden) { flex: 1; }",
    "ha-card[data-layout=\"cockpit\"] .panel.is-desktop-fallback { display: flex; }",
    "ha-card[data-layout=\"cockpit\"] .tab-btn.is-desktop-fallback { background: #262B34; color: var(--lp-text); border-color: rgba(255, 255, 255, 0.16); font-weight: 700; }",
    "ha-card[data-layout=\"cockpit\"] .tab-btn.is-desktop-fallback::after { content: \"\"; position: absolute; left: 22%; right: 22%; bottom: 3px; height: 2.5px; border-radius: 999px; background: #E5E7EB; }",
    "ha-card[data-layout=\"cockpit\"] .overview-extras { display: flex; flex-direction: column; gap: 12px; }",
    "ha-card[data-layout=\"cockpit\"] .quick-actions-surface { display: none; }",
    "ha-card[data-layout=\"cockpit\"] .cockpit-wake-btn { display: inline-flex; }",
    "ha-card[data-layout=\"cockpit\"] .schedule-switcher { display: grid; }",
    "ha-card[data-layout=\"cockpit\"] .is-schedule-hidden { display: none; }",
    "@container (min-width: 560px) {",
    "  ha-card[data-layout=\"cockpit\"] .cockpit-grid { display: grid; grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.12fr); align-items: stretch; }",
    "}",
    "@container (min-width: 680px) {",
    "  ha-card[data-layout=\"auto\"] .cockpit-grid { display: grid; grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.12fr); align-items: stretch; }",
    "  ha-card[data-layout=\"auto\"] .cockpit-left, ha-card[data-layout=\"auto\"] .cockpit-right { display: flex; flex-direction: column; gap: 12px; min-width: 0; }",
    "  ha-card[data-layout=\"auto\"] .tabs-bar { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }",
    "  ha-card[data-layout=\"auto\"] .tabs-bar [data-tab=\"overview\"] { display: none; }",
    "  ha-card[data-layout=\"auto\"] .panel[data-panel=\"overview\"] { display: flex; flex: 1; }",
    "  ha-card[data-layout=\"auto\"] .cockpit-right > .panel.is-active, ha-card[data-layout=\"auto\"] .cockpit-right > .panel.is-desktop-fallback { flex: 1; }",
    "  ha-card[data-layout=\"auto\"] .panel[data-panel=\"overview\"] > .surface:last-of-type, ha-card[data-layout=\"auto\"] .cockpit-right > .panel > .surface:last-of-type, ha-card[data-layout=\"auto\"] .panel[data-panel=\"charging\"] > .surface[data-schedule-panel]:not(.is-schedule-hidden) { flex: 1; }",
    "  ha-card[data-layout=\"auto\"] .panel.is-desktop-fallback { display: flex; }",
    "  ha-card[data-layout=\"auto\"] .tab-btn.is-desktop-fallback { background: #262B34; color: var(--lp-text); border-color: rgba(255, 255, 255, 0.16); font-weight: 700; }",
    "  ha-card[data-layout=\"auto\"] .tab-btn.is-desktop-fallback::after { content: \"\"; position: absolute; left: 22%; right: 22%; bottom: 3px; height: 2.5px; border-radius: 999px; background: #E5E7EB; }",
    "  ha-card[data-layout=\"auto\"] .overview-extras { display: flex; flex-direction: column; gap: 12px; }",
    "  ha-card[data-layout=\"auto\"] .quick-actions-surface { display: none; }",
    "  ha-card[data-layout=\"auto\"] .cockpit-wake-btn { display: inline-flex; }",
    "  ha-card[data-layout=\"auto\"] .schedule-switcher { display: grid; }",
    "  ha-card[data-layout=\"auto\"] .is-schedule-hidden { display: none; }",
    "}",
    "@container (max-width: 340px) { .bp-stage { grid-template-columns: minmax(60px, 1fr) minmax(92px, 120px) minmax(60px, 1fr); gap: 5px; } }",
    "@supports not (container-type: inline-size) {",
    "  @media (min-width: 560px) {",
    "    ha-card[data-layout=\"cockpit\"] .cockpit-grid { display: grid; grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.12fr); align-items: stretch; }",
    "  }",
    "  @media (min-width: 680px) {",
    "    ha-card[data-layout=\"auto\"] .cockpit-grid { display: grid; grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.12fr); align-items: stretch; }",
    "    ha-card[data-layout=\"auto\"] .cockpit-left, ha-card[data-layout=\"auto\"] .cockpit-right { display: flex; flex-direction: column; gap: 12px; min-width: 0; }",
    "    ha-card[data-layout=\"auto\"] .tabs-bar { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }",
    "    ha-card[data-layout=\"auto\"] .tabs-bar [data-tab=\"overview\"] { display: none; }",
    "    ha-card[data-layout=\"auto\"] .panel[data-panel=\"overview\"] { display: flex; flex: 1; }",
    "    ha-card[data-layout=\"auto\"] .cockpit-right > .panel.is-active, ha-card[data-layout=\"auto\"] .cockpit-right > .panel.is-desktop-fallback { flex: 1; }",
    "    ha-card[data-layout=\"auto\"] .panel[data-panel=\"overview\"] > .surface:last-of-type, ha-card[data-layout=\"auto\"] .cockpit-right > .panel > .surface:last-of-type, ha-card[data-layout=\"auto\"] .panel[data-panel=\"charging\"] > .surface[data-schedule-panel]:not(.is-schedule-hidden) { flex: 1; }",
    "    ha-card[data-layout=\"auto\"] .panel.is-desktop-fallback { display: flex; }",
    "    ha-card[data-layout=\"auto\"] .tab-btn.is-desktop-fallback { background: #262B34; color: var(--lp-text); border-color: rgba(255, 255, 255, 0.16); font-weight: 700; }",
    "    ha-card[data-layout=\"auto\"] .tab-btn.is-desktop-fallback::after { content: \"\"; position: absolute; left: 22%; right: 22%; bottom: 3px; height: 2.5px; border-radius: 999px; background: #E5E7EB; }",
    "    ha-card[data-layout=\"auto\"] .overview-extras { display: flex; flex-direction: column; gap: 12px; }",
    "    ha-card[data-layout=\"auto\"] .quick-actions-surface { display: none; }",
    "    ha-card[data-layout=\"auto\"] .cockpit-wake-btn { display: inline-flex; }",
    "    ha-card[data-layout=\"auto\"] .schedule-switcher { display: grid; }",
    "    ha-card[data-layout=\"auto\"] .is-schedule-hidden { display: none; }",
    "  }",
    "}",
    ```

- [ ] **Step 3: Update `LepasCardEditor._render()` (`L2430`)**
  Replace `placeholder="/lepas_card/lepas-hero-grey.png?v=1.30.0"` with `'placeholder="/lepas_card/lepas-hero-grey.png?v=' + CARD_VERSION + '"'`.

- [ ] **Step 4: Remove `warnSig` from `structKey` (`L3659-3685`), reset `_lastWarnSig`, and pass `warns` to `_applyBindings`**
  - Remove `warnSig` from `structKey` array.
  - Add `this._lastWarnSig = "";` inside `if (structKey !== this._lastStructKey && !this._dialogCtrl.inFlight)` right after `this._lastStatsChartSig = "";`.
  - Add `warns: warns,` to `this._applyBindings(hass, { ... })`.

- [ ] **Step 5: Update `_buildSkeletonHtml()` (`L3892-4520`)**
  - Replace conditional `warnsHtml` with permanent `<div class="warns-row hidden" data-bind="warnsRow" hidden></div>` in `heroHtml`.
  - Tag Quick Actions surface (`L4040`) with `class="surface quick-actions-surface" data-bind="quickActionsSurface"`.
  - Inside Overview Sync/Freshness surface (`L4050-4055`), render `cockpitWakeBtn` inside the `refreshLocBtn || refreshFullBtn || wakeBtn` `<div class="btn-row">` gated strictly by `ctx.wakeBtn`:
    ```javascript
    ((ctx.refreshLocBtn || ctx.refreshFullBtn || ctx.wakeBtn)
      ? '<div class="btn-row">' +
          (ctx.refreshLocBtn ? '<button type="button" class="ctrl-btn" data-action-id="refresh_location" data-confirm-key="refresh_location">' + svgIcon("refresh", "btn-ico") + "<span>" + self._h(t.refreshLoc) + "</span></button>" : "") +
          (ctx.refreshFullBtn ? '<button type="button" class="ctrl-btn" data-action-id="refresh_full" data-confirm-key="refresh_full">' + svgIcon("refresh", "btn-ico") + "<span>" + self._h(t.refreshFull) + "</span></button>" : "") +
          (ctx.wakeBtn ? '<button type="button" class="ctrl-btn cockpit-wake-btn" data-action-id="wake_car" data-confirm-key="wake_car">' + svgIcon("wake", "btn-ico") + "<span>" + self._h(t.wakeCar) + "</span></button>" : "") +
        "</div>"
      : "")
    ```
  - Move `extraRowsHtml` out of `overviewHtml` into `var overviewExtrasHtml = extraRowsHtml ? '<section class="overview-extras" data-bind="overviewExtras">' + extraRowsHtml + "</section>" : "";`.
  - Add `data-bind="schedChgSurface" data-schedule-panel="charge"` to `schedChgHtml`'s `.surface` and `data-schedule-panel="departure"` to `depHtml`'s `.surface`.
  - Render `.schedule-switcher` inside `chargingHtml` ONLY when both `schedChgHtml` and `depHtml` are non-empty, using localized `t.scheduledCharging` and `t.departures`.
  - Wrap `.cockpit-grid` children into `.cockpit-left` (`heroHtml + overviewHtml + overviewExtrasHtml`) and `.cockpit-right` (`tabsHtml + climateHtml + chargingHtml + securityHtml`):
    ```javascript
    '<div class="cockpit-grid">' +
      '<div class="cockpit-left">' + heroHtml + overviewHtml + overviewExtrasHtml + "</div>" +
      '<div class="cockpit-right">' + tabsHtml + climateHtml + chargingHtml + securityHtml + "</div>" +
    "</div>"
    ```

- [ ] **Step 6: Add `_syncScheduleTabUi(root)`, wire `[data-schedule-tab]` in `_handleClick`, and update tabs + `.is-desktop-fallback` + `warnsRow` + `overviewExtras` in `_applyBindingsInner`**
  - In `_applyBindingsInner` (`L4560-4571`):
    - Toggle `.is-active` on tabs/panels as before, plus toggle `.is-desktop-fallback` ONLY on `[data-tab="security"]` and `[data-panel="security"]` when `this._activeTab === "overview"`.
    - Null-safe toggle: `var overviewExtras = root.querySelector('[data-bind="overviewExtras"]'); if (overviewExtras) overviewExtras.classList.toggle("is-active", this._activeTab === "overview");`.
    - Call `this._syncScheduleTabUi(root);`.
    - Incrementally update `warnsRow` via `this._lastWarnSig` (`w.id + ":" + (w.amber ? "1" : "0") + ":" + w.text`) escaping `w.id` and `w.text` with `self._h(...)`.
  - Add `_syncScheduleTabUi(root)` and handle `[data-schedule-tab]` in `_handleClick` (`ev.stopPropagation()`, no DOM rebuild).

- [ ] **Step 7: Run tests & syntax checks (GREEN)**
  - Run `node --test tests/lepas_card.test.mjs` -> all pass (`0` failed).
  - Run `node --check custom_components/lepas/lovelace/lepas-card.js` -> `exit 0`.
  - Run `.venv/bin/pytest -q --tb=short --maxfail=2` -> all pass (`exit 0`).

- [ ] **Step 8: Refresh Cockpit/Security preview renders, release sync (when approved for push) & visual inspection**
  - Run `.venv/bin/python /home/federico/.gemini/antigravity/brain/3392bf38-3fe3-4720-aaec-b67a76fec812/scratch/capture_screenshots.py` and visually inspect `docs/images/lepas-card-cockpit.png` & `docs/images/lepas-card-security.png`.
  - When ready to commit/push to `main` (per `.agents/AGENTS.md` §5): bump version to `1.32.0` across `manifest.json`, `pyproject.toml`, `lepas-card.js` (`CARD_VERSION` + `?v=1.32.0`), `README.md`, and `CHANGELOG.md`.
