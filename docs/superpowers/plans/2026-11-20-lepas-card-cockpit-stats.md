# LepasCard Cockpit Balanced Desktop Restyle & Inline Statistics — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to execute task-by-task.

**Goal:** Finalize the user-approved balanced desktop Cockpit CSS (`cockpit` and `auto >= 680px` parity via shared `desktopLayoutRules` helper, `16 / 9` hero, capped `.cockpit-stats-row` `max-height: 152px`, enriched Security TPMS/blueprint stage, airy Climate surfaces, and compact 3-column 12-extra `Departure scheduler` keeping 100% of Mobile controls) and align `tests/lepas_card.test.mjs`, screenshots, and Dual-Gate Audit.

**Architecture:** Extract a single ES5 CSS generator `desktopLayoutRules(cardSel, indent)` inside `buildStyles()` in `custom_components/lepas/lovelace/lepas-card.js` so `ha-card[data-layout="cockpit"]`, `@container (min-width: 680px) { ha-card[data-layout="auto"] ... }`, and `@supports not (container-type: inline-size)` `@media (min-width: 680px)` stay 100% synchronized with zero duplicated CSS strings; update the Cockpit Statistics & layout assertions in `tests/lepas_card.test.mjs` to test the 3 inline KPI slots (`chgToday`, `consEv50`, `consHyb50`) and desktop-only balance rules; refresh `docs/images/lepas-card-cockpit.png` & `docs/images/lepas-card-security.png` via Chromium CDP and run full JS + Python verification.

**Tech Stack:** Vanilla ES5 Shadow DOM Web Component, CSS Container Queries + `@supports not` parity, Node.js `node:test`, Python `pytest`, Chromium CDP.

**Spec:** `docs/superpowers/specs/2026-11-20-lepas-card-cockpit-stats-design.md`

## Global Constraints
- Strictly ES5 inside `custom_components/lepas/lovelace/lepas-card.js`: `var` and `function` only, NO `?.`, NO `??` anywhere outside comments.
- Keep Mobile/Compact (`< 680px` `auto` & `data-layout="compact"`) visually 100% identical: `.cockpit-stats-surface` stays `display: none;`, `.hero-stage` stays `2 / 1`, `.climate-extras-grid` stays 2-column, and `[data-panel="overview"]` contains zero `.cons-section`.
- Preserve `AB-LEP-008`, `AB-LEP-014` (`car_in_use: true -> false`), `AB-LEP-016` (`open_stats` & `.cockpit-wake-btn` exempt from `car_in_use`), and XSS escaping (`escapeHtml` / `self._h`).
- Zero settings removed between Mobile and Desktop (`Departure scheduler` retains all 12 `allowed_climate_extras` and battery preheating controls).

## BlastRadius
- `direct_files`:
  - `custom_components/lepas/lovelace/lepas-card.js`
  - `tests/lepas_card.test.mjs`
  - `docs/images/lepas-card-cockpit.png`
  - `docs/images/lepas-card-security.png`
- `transitively_affected`:
  - `tests/test_lepas_card.py`
  - `tests/test_lovelace_card.py`
  - `README.md`
  - *Versioning note:* `manifest.json`, `pyproject.toml`, `CHANGELOG.md`, and `CARD_VERSION` + `?v=` remain untouched until user approves commit/push to `main` (per `.agents/AGENTS.md` §5).
- `uncertain`: None

## StateGraph
- **Desktop vs Mobile CSS Scoping (`desktopLayoutRules`)**:
  - `onSuccess` (`data-layout="cockpit"` or `data-layout="auto"` at `>= 680px` container/viewport): applies `16 / 9` hero, `.cockpit-stats-row` (`flex: 1; align-items: stretch; max-height: 152px;`), Security expanded `.bp-stage` + `.tpms-box { padding: 11px 12px; }` + `50px` buttons, Climate `14px 13px` surface padding + `48px` buttons, and `depSurface` 3-col `.climate-extras-grid` (`repeat(3, minmax(0, 1fr))`).
  - `onFailure` (`data-layout="compact"` or `< 680px` `auto`): none of the desktop overrides match; Mobile CSS defaults remain active (`2 / 1` hero, 2-col `.climate-extras-grid`, `.cockpit-stats-surface { display: none; }`).
- **Inline Statistics Mirror (`cockpitStatsSurface`)**:
  - `onSuccess` (`ctx.chgToday || ctx.hasAnyCons`): renders up to 3 inline slots (`chgTodayCell`, `consEv50Cell`, `consHyb50Cell`), updates live on `hass` changes and `<dialog>` unit toggles (`kWh/100 <-> kWh/km`, `L/100 <-> km/L`) without skeleton rebuild; `open_stats` stays enabled under `car_in_use: true` and `true -> false`.
  - `onFailure` (pure BEV or missing stats entities): `consHybridRow` stays `.hidden` + `hidden`, dead cells render `"—"`, full `.cockpit-stats-surface` omitted when neither `chgToday` nor `hasAnyCons` exists.

## Domain Skills & Sub-Agent Roster
- **Lovelace Card UX & Tests (`frontend_ui_worker`, `Model: 'pro'`)**:
  - **Primary**: `senior-frontend` (`/home/federico/skills_library/senior-frontend/SKILL.md`)
  - **Companions**: `antislop-ui` (`/home/federico/skills_library/antislop-ui/SKILL.md`), `antislop-code` (`/home/federico/skills_library/antislop-code/SKILL.md`)
  - **Files Owned**: `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`

---

### Task 1: Update `tests/lepas_card.test.mjs` for 3-KPI Inline Statistics & Balanced Desktop CSS (RED)
**Files:**
- Modify: `tests/lepas_card.test.mjs:4797-4942`

**Interfaces:**
- Consumes: `createCard`, `makeFullHass`, `makeState` in `tests/lepas_card.test.mjs`.
- Produces: Falsifiable assertions verifying:
  1. All 3 desktop CSS blocks (`cockpit`, `@container (min-width: 680px)`, `@supports not` `@media (min-width: 680px)`) include `.hero-stage { aspect-ratio: 16 / 9; }`, `.cockpit-stats-row { flex: 1; align-items: stretch; max-height: 152px; }`, `.panel[data-panel="security"] .tpms-box { padding: 11px 12px; }`, `.panel[data-panel="climate"] > .surface { padding: 14px 13px; gap: 12px; }`, and `.panel[data-panel="charging"] .climate-extras-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 5px; }`, while `beforeDesktop` (`compact` / `< 680px`) does NOT contain `repeat(3, minmax(0, 1fr))` for `.climate-extras-grid` or `aspect-ratio: 16 / 9` on `.hero-stage`.
  2. Inline `.cockpit-stats-surface` displays the 3 inline slots (`chgTodayVal`, `consEv50Val`, `consHyb50Val`), keeps `chgToday` locked to `"all"` scope when `<dialog>` switches to `"home"`, updates live on `card.hass = ...` without skeleton rebuild, mirrors unit toggles (`0.182 kWh/km`, `15.6 km/L`) with `try/finally` reset, keeps `open_stats` enabled across `car_in_use: true -> false`, hides `consHybridRow` on BEV, and omits `.cockpit-stats-surface` when `chgToday` + `hasAnyCons` are absent.

- [ ] **Step 1: Update `tests/lepas_card.test.mjs:4814-4895` with the balanced desktop CSS assertions and 3-KPI inline slot checks**
- [ ] **Step 2: Run `node --test --test-name-pattern="compact Statistics card" tests/lepas_card.test.mjs` to verify RED on missing desktop projection CSS**

---

### Task 2: Extract `desktopLayoutRules(cardSel, indent)` & Apply Balanced Desktop CSS in `lepas-card.js` (GREEN)
**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js:2281-2350`

**Interfaces:**
- Consumes: Existing `buildStyles()` desktop blocks (`cockpit`, `@container (min-width: 680px)`, `@supports not` `@media (min-width: 680px)`).
- Produces: ES5 helper `desktopLayoutRules(cardSel, indent)` emitting identical desktop rules across all 3 blocks:
  - Layout split & visibility (`.cockpit-left`, `.cockpit-right`, `.tabs-bar`, `.panel[data-panel="overview"]`, `.cockpit-stats-surface`, `.has-cockpit-stats`, `.panel.is-desktop-fallback`, `.overview-extras`, `.quick-actions-surface`, `.cockpit-wake-btn`, `.schedule-switcher`, `.is-schedule-hidden`).
  - Hero `16 / 9` + `.cockpit-stats-row { flex: 1; align-items: stretch; max-height: 152px; }` + `.cockpit-stats-slot > .cons-cell { justify-content: center; gap: 4px; }`.
  - Security `.bp-stage`, `.tpms-col`, `.tpms-box`, `> .surface:last-of-type`, `.btn-grid`, `.ctrl-btn`.
  - Climate `> .surface`, `.ctrl-btn`, `.seat-btns .ctrl-btn`.
  - Charging `[data-bind="depSurface"]` spacing (`gap: 7px; padding: 10px 12px;`), `[data-bind="depSurface"] .ctrl-btn` / `.ctrl-input` / `.ctrl-select` (`min-height: 36px;`), `.dep-summary-row`, `.day-chip`, `.dep-subbox`, `.climate-extras-grid` (`repeat(3, minmax(0, 1fr))`), `.climate-extra-chip`.

- [ ] **Step 1: Replace duplicated desktop CSS rules (`L2281-2349`) with `desktopLayoutRules(cardSel, indent)` + balanced desktop projection rules**
- [ ] **Step 2: Verify `node --check custom_components/lepas/lovelace/lepas-card.js`, `node --test tests/lepas_card.test.mjs`, and `.venv/bin/pytest -q --tb=short --maxfail=2` all pass**
- [ ] **Step 3: Regenerate `docs/images/lepas-card-cockpit.png` and `docs/images/lepas-card-security.png` (and verify rendered heights across Climate / Charging / Security in Chromium), inspect screenshots via `read_file`, run `graphify update .`, and complete Tier 3 Dual-Gate Audit**
