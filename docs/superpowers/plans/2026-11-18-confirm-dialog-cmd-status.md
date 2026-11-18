# Confirm Dialog & Command Outcome Badge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 4s inline button confirmation with a native `<dialog>` confirmation modal for all stateless one-shot commands and the 5 sensitive stateful actions, and replace raw `sensor.lepas_command_result` debug strings with a concise localized badge (`Ultimo comando · HH:MM ✓` / `Errore invio comando · HH:MM ✕`), bundling the departure readout fixes into `v1.22.0`.

**Architecture:** All behavioral changes live in `custom_components/lepas/lovelace/lepas-card.js` (single-bundle ES5-compatible Web Component with Shadow DOM), keeping Home Assistant backend entities (`sensor.lepas_command_result`, `button.*`, `lock.*`, `cover.*`, `switch.*`) untouched so existing backend contracts and tests stay intact. A single native `<dialog data-bind="confirmDialog">` inside the card Shadow DOM handles modal confirmation (`showModal()` with `open` attribute fallback for older WebViews), while a pure exported helper `formatCommandOutcome()` normalizes backend outcome strings and timestamps into a two-state pill.

**Tech Stack:** Vanilla ES5-compatible JavaScript (Web Components, open Shadow DOM, native `<dialog>`), CSS (`dialog:modal`, `dialog::backdrop`, `overscroll-behavior: contain`), Node.js `node:test`, Python `pytest` (`tests/test_lovelace_card.py`).

**Spec:** `docs/superpowers/specs/2026-11-18-confirm-dialog-cmd-status-design.md`

## Global Constraints
- Compatibility: NO optional chaining (`?.`) or nullish coalescing (`??`) anywhere in `custom_components/lepas/lovelace/lepas-card.js` (older Android System WebView).
- Security/XSS: Escape all dynamic text inserted into HTML via `escapeHtml` / `self._h(...)`, or assign via `.textContent`. Zero VIN or raw GPS coordinates in DOM.
- Accessibility (`modern-web-guidance` `dialog`): Never add `role="dialog"`, `aria-modal`, manual focus traps, or `inert` toggling on native `<dialog>`; set `aria-labelledby`, put `autofocus` on the safe **Cancel** button, style `dialog:modal` + `dialog::backdrop` (`overscroll-behavior: contain`, `overflow: hidden`), reset `dialog.returnValue = ""` on `close`, and provide pointer-rect light-dismiss fallback when `closedBy` is unsupported.
- Versioning (`AGENTS.md` §5): Synchronize `1.22.0` across `custom_components/lepas/manifest.json`, `pyproject.toml`, `custom_components/lepas/lovelace/lepas-card.js` (`CARD_VERSION`, `?v=1.22.0`), `CHANGELOG.md` (EN/IT), and `tests/test_lovelace_card.py` / `tests/lepas_card.test.mjs`.

## Blast Radius & StateGraph

### `BlastRadius` (from CodeGraph + Archaeology)
- `direct_files`:
  - `custom_components/lepas/lovelace/lepas-card.js`
  - `tests/lepas_card.test.mjs`
  - `tests/test_lovelace_card.py`
  - `custom_components/lepas/manifest.json`
  - `pyproject.toml`
  - `CHANGELOG.md`
- `transitively_affected`:
  - `custom_components/lepas/__init__.py` (reads `manifest.json` version to register `/lepas_card/lepas-card.js?v=<version>`)
  - `tests/test_lovelace_card.py` (validates SemVer `?v=X.Y.Z` in `lepas-card.js` and executes `node --test tests/lepas_card.test.mjs`)
- `uncertain`:
  - Older Android System WebView builds without `HTMLDialogElement.prototype.showModal` or `closedBy` (mitigated via `typeof dlg.showModal === "function"` check + `open` attribute fallback + pointer bounding-rect light-dismiss).

### `StateGraph` (`onSuccess:` / `onFailure:`)
- **Action Trigger (`_triggerAction`)**:
  - `spec.needsConfirm === true` -> `_openConfirmDialog(spec, confirmKey)`:
    - `onSuccess` (user clicks `[data-dialog-action="confirm"]`): close dialog (`dlg.close("confirm")`), reset `dlg.returnValue = ""`, clear `_pendingDialogAction`, invoke `_callService(spec.domain, spec.service, spec.data, confirmKey)`.
    - `onFailure` / Cancel (`[data-dialog-action="cancel"]`) / `Esc` (`cancel` event) / backdrop click (`pointerdown`+`pointerup` outside `getBoundingClientRect()`): close dialog, reset `dlg.returnValue = ""`, clear `_pendingDialogAction`, zero `callService` invocation.
  - `structKey` rebuild during `set hass()`: fail-closed clear `_pendingDialogAction = null` before replacing `this.shadowRoot.innerHTML`.
  - `disconnectedCallback()`: close open `<dialog>` (`close()` or `removeAttribute("open")` fallback), reset `returnValue = ""`, clear `_pendingDialogAction = null`. Listeners remain scoped to `<dialog>` and `this._root` (zero `window`/`document` leaks).
- **Service Execution (`_callService`)**:
  - Sets `_pendingKeys.add(pendingKey)` before calling `hass.callService(...)`.
  - `onSuccess` (`Promise` resolves): `_pendingKeys.delete(pendingKey)`, sets `_lastCmdFeedback = { ok: true, ts: Date.now() }`, re-renders `cmdResultBadge` (`Ultimo comando · HH:MM ✓`).
  - `onFailure` (`Promise` rejects or throws synchronously): `_pendingKeys.delete(pendingKey)`, sets `_errorMsg` AND `_lastCmdFeedback = { ok: false, ts: Date.now() }`, re-renders `cmdResultBadge` (`Errore invio comando · HH:MM ✕`) and error banner.

### Domain Skills & Sub-Agent Roster
- **Domini identificati**:
  1. **Lovelace Web Component & Test Contract** (`lovelace_card_worker`, `Model: 'pro'` — single file `>600L`: `lepas-card.js` at 3648L + coupled `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`, and SemVer files `manifest.json`, `pyproject.toml`, `CHANGELOG.md`).
- **Companions (`lookup.py`)**: `modern-web-guidance` (`dialog`), `antislop-ui`, `antislop-code`, `ponytail`.

---

### Task 1: TDD RED — Dialog Shim, Modal Confirmation Tests & Command Outcome Tests

**Files:**
- Modify: `tests/lepas_card.test.mjs`
- Modify: `tests/test_lovelace_card.py`

**Interfaces:**
- Produces test expectations for:
  - `LepasCard._helpers.formatCommandOutcome(cmdStateObj, localFeedback, lang)` -> `{ text: string, ok: boolean } | null`
  - `LepasCard._helpers.CONFIRM_ACTIONS` (immutable list/map covering the 10 stateless + 5 sensitive stateful action keys)
  - `<dialog data-bind="confirmDialog">` inside `card.shadowRoot` with `[data-bind="confirmDialogAction"]`, `[data-dialog-action="cancel"]`, `[data-dialog-action="confirm"]`
  - `I18N[lang]` keys: `confirmModalTitle`, `confirmModalHint`, `confirmCancel`, `confirmSend`, `lastCommand`, `commandSendError`
- **Test Falsification Mandate**: Tests invoke real DOM clicks on `card.shadowRoot` buttons and real `<dialog>` methods (`showModal`, `close`, `cancel` event, backdrop `pointerdown`/`pointerup` coordinates); if `_triggerAction` bypasses the modal, fires `callService` on cancel/Esc/backdrop, leaks `.is-confirming`, or renders raw debug text in `cmdResultBadge`, assertions fail immediately.

- [ ] **Step 1: Extend `MiniEvent` & `MiniElement` in `tests/lepas_card.test.mjs` with `<dialog>` + pointer coordinate simulation**
  - In `MiniEvent`: add `this.clientX = init.clientX !== undefined ? init.clientX : 0; this.clientY = init.clientY !== undefined ? init.clientY : 0;`.
  - In `MiniElement`: add `open` getter/setter (synced with `open` attribute), `returnValue` string property, `showModal()` (sets `this.open = true`), `close(val)` (sets `if (val !== undefined) this.returnValue = String(val);` and dispatches `new MiniEvent("close")` ONLY if `this.open` was `true`, after setting `this.open = false`), and default `getBoundingClientRect()` returning `{ left: 100, right: 300, top: 100, bottom: 240 }`.
- [ ] **Step 2: Write RED tests in `tests/lepas_card.test.mjs` & bump version check in `tests/test_lovelace_card.py`**
  1. Grep `tests/lepas_card.test.mjs` for any click on `refresh_full`, `refresh_location`, `wake_car`, `locate_gps`, `flash_lights`, `sec_flash_lights`, `apply_charging_schedule`, `apply_departure_schedule`, `unlock`, `trunk_open`, `windows_open`, `sunroof_open`, `vent_windows`, `vent_sunroof`, `alarm_toggle`, `remote_start`, `data-confirming`, or `1.21.3`.
  2. Update existing tests (`L1030-1069` `sensitiveCases`, `L1087` `apply_charging_schedule`, `L1141`/`L1159`/`L1174` `unlock` + `set hass()` + rejected `callService`, `L1336-1342` `SVG icons`, `L1655-1662` `apply_departure_schedule`) to verify `<dialog data-bind="confirmDialog">` opens (`open === true`, zero `callService`), stays open across unrelated `set hass()`, closes without calling service on Cancel / `Esc` (`cancel` event) / outside backdrop (`pointerdown`+`pointerup` at `(10, 10)`), and calls `hass.callService` once on `[data-dialog-action="confirm"]`. Also verify zero `data-confirming` / `.confirm-bar` / `"Conferma?"` on `unlockBtn` while preserving SVG icon.
  3. Add test covering ALL 10 stateless commands + 5 sensitive stateful commands opening `<dialog>`, WebView fallback test (`dlg.showModal = undefined` -> `open` attribute toggled), and asserting stateful non-destructive controls (`lock_now`, `climate_toggle`, `temp_up`, `seat_driver_heat`, `quick_departure_toggle`, `day_chip`) stay 1-tap immediate.
  4. Add unit + DOM tests for `formatCommandOutcome` and `cmdResultBadge` (`Ultimo comando · HH:MM ✓` vs `Errore invio comando · HH:MM ✕` in IT/EN/NL, rejection feedback even when `sensor.lepas_command_result` is `unavailable`/`absent`, zero raw debug text `"Comando eseguito e confermato dall'auto"` in DOM).
  5. Update `?v=1.22.0` assertions in `tests/lepas_card.test.mjs` and `tests/test_lovelace_card.py`.
- [ ] **Step 3: Run `node --test tests/lepas_card.test.mjs` to confirm RED failure**
  Expected: FAIL on missing `<dialog>`, missing `formatCommandOutcome`, and `?v=1.22.0` mismatch.

---

### Task 2: Implementation GREEN — Native `<dialog>`, `formatCommandOutcome`, CSS & SemVer `1.22.0`

**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js`
- Modify: `custom_components/lepas/manifest.json`
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes expectations from Task 1 (`CONFIRM_ACTIONS`, `formatCommandOutcome`, `<dialog data-bind="confirmDialog">`, I18N keys).

- [ ] **Step 1: Add I18N keys (`it`, `en`, `nl`) and `CONFIRM_ACTIONS` allowlist/map in `lepas-card.js`**
  Add `confirmModalTitle`, `confirmModalHint`, `confirmCancel`, `confirmSend`, `lastCommand`, `commandSendError`, replace `isSensitiveAction`/`SENSITIVE_ACTIONS` with `CONFIRM_ACTIONS` (`requiresConfirmation(actionId)`), and pass dynamic localized `confirmLabel` in `regAction(..., confirmLabel)` (specifically resolving dynamic `"Applica su auto"` vs `"Disattiva su auto"` for `apply_departure_schedule` based on `haHasActiveDep` / `carActive`).
- [ ] **Step 2: Add `formatCommandOutcome(cmdStateObj, localFeedback, lang)` and CSS for `dialog:modal` / `dialog::backdrop` / `.is-coral` in `lepas-card.js`**
  Implement `dialog:modal { overscroll-behavior: contain; ... }`, `dialog::backdrop { overflow: hidden; overscroll-behavior: contain; ... }`, remove obsolete `.is-confirming` / `.confirm-bar` styles, and expose `formatCommandOutcome` + `CONFIRM_ACTIONS` on `LepasCard._helpers`. Zero `?.` or `??` anywhere in `lepas-card.js` (including comments/strings/regex).
- [ ] **Step 3: Render `<dialog data-bind="confirmDialog">` in `_buildSkeletonHtml`, wire modal lifecycle + backdrop fallback in `_bindListeners`/`_triggerAction`/`_callService`, and render concise `cmdResultBadge` in `_applyBindings`**
  - Use explicit `<button type="button" data-dialog-action="cancel" autofocus>` and `<button type="button" data-dialog-action="confirm">` inside `<dialog data-bind="confirmDialog" aria-labelledby="lp-confirm-title">` (no `<form method="dialog">`, no `role="dialog"`, no `aria-modal`).
  - Replace `_confirmState`/`_confirmTimer`/`_clearConfirm` with `_openConfirmDialog`/`_closeConfirmDialog` and `_pendingDialogAction`; bind `close`, `cancel`, `pointerdown`/`pointerup` light-dismiss directly on `<dialog>` / `this._root` (zero `window`/`document` listeners); reset `dlg.returnValue = ""` on close; clean up in `disconnectedCallback()` and before `structKey` skeleton rebuild.
  - Track `_lastCmdFeedback` on `callService` resolve/reject; compute `cmdStateAlive = (vm.cmdResult && !this._dead(vm.cmdResult.s)) ? vm.cmdResult.s : null`, pass to `formatCommandOutcome(cmdStateAlive, this._lastCmdFeedback, vm.lang)`, hide `cmdBadge` only when `outcome === null`, and toggle `.is-emerald` / `.is-coral` mutually exclusively.
- [ ] **Step 4: Bump SemVer `1.22.0` in `lepas-card.js`, `manifest.json`, `pyproject.toml`, and `CHANGELOG.md`**
  - Consolidate the departure readout improvements (`v1.21.3` draft in working tree) and the modal/outcome improvements into `## v1.22.0 — 2026-11-18` (EN/IT) in `CHANGELOG.md`.
- [ ] **Step 5: Run full verification**
  - `node --test tests/lepas_card.test.mjs` -> 100% PASS
  - `.venv/bin/pytest -q --tb=short --maxfail=2` -> 100% PASS
  - `local_llm_offload.py --task review-hygiene --files custom_components/lepas/lovelace/lepas-card.js --json` + `diff_gate.py` -> clean
  - Tier 3 Dual-Gate Audit (Pass 1 `flash` + Pass 2 Sentinel `inherit`, reusing Stage 2 Sentinel CID) + `git write-tree` + `graphify update .` -> commit, tag `v1.22.0`, push, and `ci_watch.py`.
