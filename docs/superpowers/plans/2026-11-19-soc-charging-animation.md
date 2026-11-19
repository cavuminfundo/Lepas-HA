# SoC Ring Charging Animation & AC/DC Mode Slide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Dual-Gate Pre-Audit Matrix
| Gate | Conversation ID | Model | Verdict | Notes |
| --- | --- | --- | --- | --- |
| Stage 1 (`plan_stage1_auditor`) | `11a13c55-aa05-4ae4-89da-edf50b434291` | `flash` | `PASS` | 4 minor findings applied (`.soc-chg-ico:not(.hidden)` specificity, `chgFlowTrack` reuse confirmed, CSS reduced-motion assertions, `4122L`) |
| Stage 2 (`sentinel_auditor`) | `b64c7e97-e779-4cd4-a821-71ac86e4f63d` | `inherit` | `APPROVED` | Six Pillars passed; non-blocking items folded (`pctText`, `niet.*opladen`, `socModeIco` flex align + `data-mode` guard, `heroStateBadge` + `en`/`nl` test assertions) |

**Goal:** Add an unmistakable GPU-composited orbital charging animation and internal `% ↔ AC/DC` vertical slide to the Lovelace card SoC ring (`54×54 px`) that activates exclusively during active charging and distinguishes normal (AC) vs fast (DC) charging.

**Architecture:** Extract a pure, unit-testable `resolveSocChargingState(vm, helpers)` helper in `custom_components/lepas/lovelace/lepas-card.js` that handles multi-language charging states (`"In ricarica"` / `"Charging"` / `"Opladen"` / `"1"`, rejecting `"Non in ricarica"` / `"Ricarica completata"`) and classifies `"normal"` vs `"fast"` charging from `fastPort`, `chgPower`, or `hvVolt × |hvCurr|`. Drive a sibling `<svg class="soc-svg-orbit">` overlay (safe across WebView/Safari without inner SVG `transform-origin` quirks) and a CSS `@keyframes lp-soc-slide` two-slot vertical viewport, respecting `@media (prefers-reduced-motion: reduce)` with a static fallback icon and localized `aria-label`s.

**Tech Stack:** Vanilla ES5-safe Web Component JS (zero `?.`, zero `??`, zero top-level `import`/`export`), CSS3 `@keyframes` + `@media (prefers-reduced-motion: ...)`, SVG, Node 20+ `node:test`, Pytest.

**Spec:** `docs/superpowers/specs/2026-11-19-soc-charging-animation-design.md`

---

## Global Constraints

- **Syntax compatibility (`tests/test_lovelace_card.py`):** Zero optional chaining (`?.`), zero nullish coalescing (`??`), zero top-level `import`/`export` anywhere in `custom_components/lepas/lovelace/lepas-card.js` (including comments and strings).
- **Matte Titanium OEM palette:** Keep all required palette tokens (`#111317`, `#181B20`, `#21252C`, `#F3F4F6`, `#34D399`, `#60A5FA`, `#F59E0B`, `#EF4444`); `#00D2FF` and `:host-context()` are strictly forbidden.
- **Reduced motion & compositor safety:** Animate only `transform` / `opacity`; wrap continuous animations (`lp-spin`, `lp-soc-slide`) inside `@media (prefers-reduced-motion: no-preference)`; under `@media (prefers-reduced-motion: reduce)` keep `76%` readable and show `.soc-btn.is-charging .soc-chg-ico:not(.hidden)` static AC/DC indicator while hiding `.soc-mode-slide`.
- **Active-charging-only rule:** Plugged-in / waiting on scheduled charge (`chgSwitch=off`, `chgStatus="Non in ricarica"`, `fastPort="Collegata"`) MUST NOT trigger `.is-charging`, orbit, or slide.
- **Release sync (`.agents/AGENTS.md` §5):** Bump version `1.25.0` → `1.26.0` synchronously in `custom_components/lepas/manifest.json`, `pyproject.toml`, `custom_components/lepas/lovelace/lepas-card.js` (`CARD_VERSION` + `?v=1.26.0`), `tests/test_lovelace_card.py`, `tests/lepas_card.test.mjs` (if any version assertion exists), and `CHANGELOG.md`.

---

## Blast Radius & StateGraph

### `BlastRadius`
- `direct_files`:
  - `custom_components/lepas/lovelace/lepas-card.js` (`>600L`, `4122L` — SVG icon, CSS rules, `I18N`, `resolveSocChargingState`, `_buildSkeletonHtml`, `_applyBindingsInner`, `LepasCard._helpers`, version bump `1.26.0`)
  - `tests/lepas_card.test.mjs` (new tests for `resolveSocChargingState` and DOM SoC ring charging/idle/AC/DC/transition/reduced-motion markup + `heroStateBadge` + `en`/`nl` `aria-label` + version check if present)
  - `tests/test_lovelace_card.py` (update `\?v=1\.25\.0\b` → `\?v=1\.26\.0\b`)
  - `custom_components/lepas/manifest.json` (`1.25.0` → `1.26.0`)
  - `pyproject.toml` (`1.25.0` → `1.26.0`)
  - `CHANGELOG.md` (new `## v1.26.0 — 2026-11-19` EN/IT entry)
- `transitively_affected`:
  - `custom_components/lepas/__init__.py` (serves `lepas-card.js` via `/lepas_card/lepas-card.js?v=<manifest.version>`; untouched, picks up `manifest.json` version automatically)
  - `heroStateBadge` and `chgFlowTrack` inside `lepas-card.js` (consume the unified `isCharging` boolean from `resolveSocChargingState`, gaining Italian `"In ricarica"` parity without breaking existing `"Charging"` behavior)
  - `tests/test_lovelace_card.py` (`test_lepas_card_node_unit_suite` invokes `node --test tests/lepas_card.test.mjs`)
- `uncertain`:
  - Live Home Assistant Companion Android/iOS WebView CSS rendering of `.soc-svg-orbit` rotation and `.soc-track` vertical slide (mitigated by rotating the `<svg class="soc-svg-orbit">` element itself rather than an inner `<circle>`, and keeping pure `transform: translateY(-22px)`).

### `StateGraph` (`onSuccess:` / `onFailure:`)
No backend locks, Proxmox nodes, or SSH state mutations exist in this UI task. Every DOM state transition inside `_applyBindingsInner` MUST be idempotent and reversible on the same rendered card instance:
- **Transition `idle → normal charging`:**
  - `onSuccess`: `socBtn` gains `.is-charging` (removes `.is-fast-charge`), `socOrbit` removes `.hidden`, `socModeSlide` removes `.hidden` and sets `bolt` icon + `"AC"` label (updating SVG only when `data-mode` changes), `socChgIco` removes `.hidden`, `socBtn`/`socProgress` `aria-label` updated.
  - `onFailure` (missing/dead entities): `socBtn` has neither `.is-charging` nor `.is-fast-charge`; `socOrbit`, `socModeSlide`, `socChgIco` remain `.hidden`; `socText` shows `"—"`.
- **Transition `normal ↔ fast charging`:**
  - `onSuccess`: `socBtn.classList.toggle("is-fast-charge", isFast)` toggles emerald vs amber styling and speed, `socModeIco` and `socChgIco` swap SVG body (`bolt` ↔ `fast_charge`) via `data-mode` guard, `socModeLbl` swaps `"AC"` ↔ `"DC"`.
- **Transition `charging → unplugged / completed / waiting`:**
  - `onSuccess`: `socBtn` removes `.is-charging` and `.is-fast-charge`; `socOrbit`, `socModeSlide`, `socChgIco` add `.hidden`; `socText` remains visible at `translateY(0)` and `aria-label` reverts to `"<pct>%"`.

### Test Falsification Mandate
- Every test MUST exercise the real `LepasCard` DOM rendering (`createCard` + `card.hass = makeFullHass(...)`) and `LepasCard._helpers.resolveSocChargingState` without mocking the helper or DOM class toggles:
  - Removing `"In ricarica"` support or misclassifying `"Non in ricarica"` / `"Ricarica completata"` immediately fails the waiting-plugged, `heroStateBadge`, and Italian-status assertions.
  - Leaving `.is-fast-charge` or `.is-charging` sticky across `hass` updates on the same `card` instance immediately fails the transition test.
  - Forgetting `manifest.json` / `pyproject.toml` / `lepas-card.js` `?v=1.26.0` sync immediately fails `test_card_version_and_matte_titanium_design_tokens`.

---

### Domain Skills & Sub-Agent Roster
- **Selected Domain Skills (via `lookup.py`):**
  - Transversal Companions: `antislop-ui` (`/home/federico/skills_library/antislop-ui/SKILL.md`), `antislop-code` (`/home/federico/skills_library/antislop-code/SKILL.md`), `ponytail` (`/home/federico/skills_library/ponytail/SKILL.md`)
  - Web Platform Reference: `modern-web-guidance` (`motion`: GPU compositor `transform`/`opacity` + `@media (prefers-reduced-motion: no-preference|reduce)`)
- **Cohesive Worker Roster:**
  1. **`lepas_card_worker` (`Model: 'pro'`, `Workspace: 'inherit'`)** — Sole cohesive frontend + release contract owner (justified `'pro'` from Round 1 because `lepas-card.js` is `4122L > 600L` and touches 6 coupled files):
     - Files: `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`, `custom_components/lepas/manifest.json`, `pyproject.toml`, `CHANGELOG.md`.

---

### Task 1: TDD RED — Charging State Helper & SoC Ring DOM Tests (`tests/lepas_card.test.mjs`)

**Files:**
- Modify: `tests/lepas_card.test.mjs:2820-2845`

**Interfaces:**
- Consumes: `LepasCard._helpers.resolveSocChargingState(vm, helpers)` (to be added in Task 2), `createCard`, `makeFullHass`, `makeState`.
- Produces: Failing tests proving helper semantics and DOM class/element transitions.

- [ ] **Step 1: Append failing tests to `tests/lepas_card.test.mjs`**

```javascript
test("resolveSocChargingState distinguishes active AC/DC charging from plugged-in waiting", () => {
  const fn = LepasCard._helpers.resolveSocChargingState;
  assert.equal(typeof fn, "function");

  const helpers = {
    isOn: (ent) => Boolean(ent && ent.s && ent.s.state === "on"),
    num: (s) => {
      if (!s || s.state === "unknown" || s.state === "unavailable") return null;
      const n = Number(s.state);
      return Number.isFinite(n) ? n : null;
    },
    dead: (s) => !s || s.state === "unknown" || s.state === "unavailable",
  };

  // Plugged in & waiting for schedule ("Non in ricarica", switch off) -> NOT charging
  const waiting = fn({
    chgSwitch: { s: makeState("switch.lepas_charging", "off") },
    chgStatus: { s: makeState("sensor.lepas_charging_status", "Non in ricarica") },
    fastPort: { s: makeState("sensor.lepas_fast_charging_port", "Collegata") },
    chgPower: { s: makeState("sensor.lepas_charging_power", "0") },
  }, helpers);
  assert.deepEqual(waiting, { isCharging: false, isFast: false, mode: "none" });

  // Charge completed -> NOT charging
  const completed = fn({
    chgSwitch: { s: makeState("switch.lepas_charging", "off") },
    chgStatus: { s: makeState("sensor.lepas_charging_status", "Ricarica completata") },
    fastPort: { s: makeState("sensor.lepas_fast_charging_port", "Collegata (ricarica rapida)") },
  }, helpers);
  assert.deepEqual(completed, { isCharging: false, isFast: false, mode: "none" });

  // Italian active normal AC charging
  const acIt = fn({
    chgSwitch: { s: makeState("switch.lepas_charging", "off") },
    chgStatus: { s: makeState("sensor.lepas_charging_status", "In ricarica") },
    fastPort: { s: makeState("sensor.lepas_fast_charging_port", "Scollegata") },
    hvVolt: { s: makeState("sensor.lepas_hv_battery_voltage", "380") },
    hvCurr: { s: makeState("sensor.lepas_hv_battery_current", "16") },
  }, helpers);
  assert.deepEqual(acIt, { isCharging: true, isFast: false, mode: "normal" });

  // Fast DC charging via fastPort "Collegata (ricarica rapida)"
  const dcPort = fn({
    chgSwitch: { s: makeState("switch.lepas_charging", "on") },
    chgStatus: { s: makeState("sensor.lepas_charging_status", "In ricarica") },
    fastPort: { s: makeState("sensor.lepas_fast_charging_port", "Collegata (ricarica rapida)") },
  }, helpers);
  assert.deepEqual(dcPort, { isCharging: true, isFast: true, mode: "fast" });

  // Fast DC charging via high power >= 15 kW fallback
  const dcPower = fn({
    chgSwitch: { s: makeState("switch.lepas_charging", "on") },
    chgStatus: { s: makeState("sensor.lepas_charging_status", "Charging") },
    fastPort: { s: makeState("sensor.lepas_fast_charging_port", "Connected") },
    chgPower: { s: makeState("sensor.lepas_charging_power", "42.5") },
  }, helpers);
  assert.deepEqual(dcPower, { isCharging: true, isFast: true, mode: "fast" });
});

test("SoC ring animates only during active charging, differentiates AC/DC, and resets cleanly", () => {
  // 1. Plugged in & waiting ("Non in ricarica", switch off) -> static ring
  const card = createCard({ layout: "compact" }, makeFullHass({
    "switch.lepas_charging": makeState("switch.lepas_charging", "off"),
    "sensor.lepas_charging_status": makeState("sensor.lepas_charging_status", "Non in ricarica"),
    "sensor.lepas_charging_power": makeState("sensor.lepas_charging_power", "0"),
    "sensor.lepas_fast_charging_port": makeState("sensor.lepas_fast_charging_port", "Collegata"),
  }, "it"));
  const socBtn = card.shadowRoot.querySelector('[data-bind="socBtn"]');
  const socOrbit = card.shadowRoot.querySelector('[data-bind="socOrbit"]');
  const socModeSlide = card.shadowRoot.querySelector('[data-bind="socModeSlide"]');
  const socModeLbl = card.shadowRoot.querySelector('[data-bind="socModeLbl"]');
  const socChgIco = card.shadowRoot.querySelector('[data-bind="socChgIco"]');
  const socText = card.shadowRoot.querySelector('[data-bind="socText"]');
  const socProg = card.shadowRoot.querySelector('[data-bind="socProgress"]');
  const heroBadge = card.shadowRoot.querySelector('[data-bind="heroStateBadge"]');

  assert.ok(socBtn && socOrbit && socModeSlide && socModeLbl && socChgIco && socText && socProg && heroBadge);
  assert.equal(socText.textContent, "78%");
  assert.equal(socBtn.classList.contains("is-charging"), false);
  assert.equal(socBtn.classList.contains("is-fast-charge"), false);
  assert.equal(socOrbit.classList.contains("hidden"), true);
  assert.equal(socModeSlide.classList.contains("hidden"), true);
  assert.equal(socChgIco.classList.contains("hidden"), true);
  assert.equal(heroBadge.classList.contains("hidden"), true);

  // 2. Active normal AC charging ("In ricarica")
  card.hass = makeFullHass({
    "switch.lepas_charging": makeState("switch.lepas_charging", "off"),
    "sensor.lepas_charging_status": makeState("sensor.lepas_charging_status", "In ricarica"),
    "sensor.lepas_charging_power": makeState("sensor.lepas_charging_power", "6.6"),
    "sensor.lepas_fast_charging_port": makeState("sensor.lepas_fast_charging_port", "Scollegata"),
  }, "it");
  assert.equal(socBtn.classList.contains("is-charging"), true);
  assert.equal(socBtn.classList.contains("is-fast-charge"), false);
  assert.equal(socOrbit.classList.contains("hidden"), false);
  assert.equal(socModeSlide.classList.contains("hidden"), false);
  assert.equal(socModeLbl.textContent, "AC");
  assert.equal(socChgIco.classList.contains("hidden"), false);
  assert.equal(heroBadge.classList.contains("hidden"), false);
  assert.match(heroBadge.textContent || "", /^In carica/);
  assert.match(socBtn.getAttribute("aria-label") || "", /78%.*AC/);
  assert.equal(socProg.getAttribute("aria-label"), socBtn.getAttribute("aria-label"));

  // 3. Switch to active fast DC charging on same card instance
  card.hass = makeFullHass({
    "switch.lepas_charging": makeState("switch.lepas_charging", "on"),
    "sensor.lepas_charging_status": makeState("sensor.lepas_charging_status", "In ricarica"),
    "sensor.lepas_charging_power": makeState("sensor.lepas_charging_power", "45.0"),
    "sensor.lepas_fast_charging_port": makeState("sensor.lepas_fast_charging_port", "Collegata (ricarica rapida)"),
  }, "it");
  assert.equal(socBtn.classList.contains("is-charging"), true);
  assert.equal(socBtn.classList.contains("is-fast-charge"), true);
  assert.equal(socModeLbl.textContent, "DC");
  assert.match(socBtn.getAttribute("aria-label") || "", /78%.*DC/);

  // 4. Unplugged -> clean rollback on same rendered DOM
  card.hass = makeFullHass({
    "binary_sensor.lepas_charging_cable": makeState("binary_sensor.lepas_charging_cable", "off"),
    "switch.lepas_charging": makeState("switch.lepas_charging", "off"),
    "sensor.lepas_charging_status": makeState("sensor.lepas_charging_status", "Non in ricarica"),
    "sensor.lepas_charging_power": makeState("sensor.lepas_charging_power", "0"),
    "sensor.lepas_fast_charging_port": makeState("sensor.lepas_fast_charging_port", "Scollegata"),
  }, "it");
  assert.equal(socBtn.classList.contains("is-charging"), false);
  assert.equal(socBtn.classList.contains("is-fast-charge"), false);
  assert.equal(socOrbit.classList.contains("hidden"), true);
  assert.equal(socModeSlide.classList.contains("hidden"), true);
  assert.equal(socChgIco.classList.contains("hidden"), true);
  assert.equal(socBtn.getAttribute("aria-label"), "78%");
  assert.equal(socProg.getAttribute("aria-label"), "78%");

  // 5. EN & NL localized aria-label checks
  const enCard = createCard({ layout: "compact" }, makeFullHass({}, "en"));
  assert.equal(enCard.shadowRoot.querySelector('[data-bind="socBtn"]').getAttribute("aria-label"), "78% · Charging (AC)");
  const nlCard = createCard({ layout: "compact" }, makeFullHass({
    "sensor.lepas_fast_charging_port": makeState("sensor.lepas_fast_charging_port", "Collegata (ricarica rapida)"),
  }, "nl"));
  assert.equal(nlCard.shadowRoot.querySelector('[data-bind="socBtn"]').getAttribute("aria-label"), "78% · Snelladen (DC)");

  // 6. CSS contract: GPU keyframes & reduced-motion static fallback
  const styleEl = card.shadowRoot.querySelector("style");
  const cssText = styleEl ? styleEl.textContent : "";
  assert.match(cssText, /@keyframes lp-soc-slide/);
  assert.match(cssText, /prefers-reduced-motion:\s*no-preference[\s\S]*?\.soc-btn\.is-charging\s+\.soc-track/);
  assert.match(cssText, /prefers-reduced-motion:\s*reduce[\s\S]*?\.soc-mode-slide[\s\S]*?\.soc-chg-ico:not\(\.hidden\)/);
});
```

- [ ] **Step 2: Verify RED** — Run `node --test tests/lepas_card.test.mjs` (Master runs tests, expected FAIL because `resolveSocChargingState`, `socOrbit`, `socModeSlide`, `socModeLbl` do not exist yet).

---

### Task 2: Implement SoC Ring Animation, AC/DC Mode Slide & CSS (`custom_components/lepas/lovelace/lepas-card.js`)

**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js` (`I18N`, `SVG_PATHS`, helpers, `buildStyles`, `_buildSkeletonHtml`, `_applyBindingsInner`, `LepasCard._helpers`)

**Interfaces:**
- Produces: `LepasCard._helpers.resolveSocChargingState`, `[data-bind="socOrbit"]`, `[data-bind="socModeSlide"]`, `[data-bind="socModeIco"]`, `[data-bind="socModeLbl"]`, `.soc-btn.is-charging`, `.soc-btn.is-fast-charge`.

- [ ] **Step 1: Add I18N labels (`chargingNormal`, `chargingFast`) in `it`, `en`, `nl` (`L158-L515`)**
  - `it`: `chargingNormal: "In carica (AC)"`, `chargingFast: "In carica rapida (DC)"`
  - `en`: `chargingNormal: "Charging (AC)"`, `chargingFast: "Fast charging (DC)"`
  - `nl`: `chargingNormal: "Opladen (AC)"`, `chargingFast: "Snelladen (DC)"`

- [ ] **Step 2: Add `fast_charge` icon path to `SVG_PATHS` (`L814-L853`) and `resolveSocChargingState(vm, helpers)` pure helper (`~L985`)**

```javascript
    fast_charge: '<polygon points="10.5 2 3.5 13 9 13 8 22 15.5 10.5 10.2 10.5 10.5 2"/><polygon points="18.5 4 14 11.5 17.5 11.5 16.5 18 21.5 9.5 18 9.5 18.5 4"/>',
```

```javascript
  function resolveSocChargingState(vm, helpers) {
    var h = helpers || {};
    var isOnFn = h.isOn || function () { return false; };
    var numFn = h.num || function () { return null; };
    var deadFn = h.dead || function (s) { return !s || s.state === "unknown" || s.state === "unavailable"; };
    var statusStr = (vm && vm.chgStatus && vm.chgStatus.s && !deadFn(vm.chgStatus.s))
      ? String(vm.chgStatus.s.state || "").trim().toLowerCase()
      : "";
    var statusSaysOff = Boolean(
      statusStr &&
      /^(?:non\s+in\s+ricaric|not\s+charg|niet(?:\s+aan\s+het)?\s+opladen|ricarica\s+completat|charge\s+complet|opladen\s+voltooid|complet|idle|off|0\b)/i.test(statusStr)
    );
    var statusSaysOn = Boolean(
      statusStr && !statusSaysOff &&
      (/^(?:in\s+ricarica|charging|opladen|1)$/i.test(statusStr) || /\bcharg(?:ing|e)\b/i.test(statusStr))
    );
    var powerKw = (vm && vm.chgPower && vm.chgPower.s && !deadFn(vm.chgPower.s))
      ? numFn(vm.chgPower.s)
      : null;
    var isCharging = Boolean(
      isOnFn(vm && vm.chgSwitch) ||
      statusSaysOn ||
      (!statusStr && !statusSaysOff && powerKw !== null && powerKw > 0.1)
    );
    if (!isCharging) {
      return { isCharging: false, isFast: false, mode: "none" };
    }
    var fastPortStr = (vm && vm.fastPort && vm.fastPort.s && !deadFn(vm.fastPort.s))
      ? String(vm.fastPort.s.state || "").trim().toLowerCase()
      : "";
    var fastByPort = Boolean(
      fastPortStr &&
      !/scolleg|disconnect|unplug|\b0\b/i.test(fastPortStr) &&
      /rapid|fast|quick|\b2\b|\bdc\b/i.test(fastPortStr)
    );
    var hvV = (vm && vm.hvVolt && vm.hvVolt.s && !deadFn(vm.hvVolt.s)) ? numFn(vm.hvVolt.s) : null;
    var hvA = (vm && vm.hvCurr && vm.hvCurr.s && !deadFn(vm.hvCurr.s)) ? numFn(vm.hvCurr.s) : null;
    var hvKw = (hvV !== null && hvA !== null) ? (Math.abs(hvV * hvA) / 1000) : null;
    var isFast = Boolean(
      fastByPort ||
      (powerKw !== null && powerKw >= 15) ||
      (hvKw !== null && hvKw >= 15)
    );
    return { isCharging: true, isFast: isFast, mode: isFast ? "fast" : "normal" };
  }
```
Expose `resolveSocChargingState: resolveSocChargingState` on `LepasCard._helpers` (`L4080-4104`).

- [ ] **Step 3: Update `.soc-*` CSS & `@media (prefers-reduced-motion: ...)` (`L1048-1057`, `L1248-1265`)**
  - Style `.soc-btn.is-charging { border-color: rgba(52, 211, 153, 0.55); }` and `.soc-btn.is-charging.is-fast-charge { border-color: rgba(245, 158, 11, 0.65); }`.
  - Add `.soc-btn svg.soc-svg-orbit { position: absolute; inset: 2px; width: 48px; height: 48px; pointer-events: none; }` and `.soc-ring-orbit { fill: none; stroke: var(--lp-emerald); stroke-width: 2.6; stroke-linecap: round; opacity: 0.92; }`, with `.soc-btn.is-fast-charge .soc-ring-orbit { stroke: var(--lp-amber); }`.
  - Add `.soc-viewport { position: relative; width: 38px; height: 22px; overflow: hidden; }`, `.soc-track { display: flex; flex-direction: column; will-change: transform; }`, `.soc-slide { height: 22px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }`, `.soc-mode-slide { gap: 2px; color: var(--lp-emerald); }`, `.soc-btn.is-fast-charge .soc-mode-slide { color: var(--lp-amber); }`, `[data-bind="socModeIco"] { display: inline-flex; align-items: center; justify-content: center; }`, `.soc-mode-ico { width: 12px; height: 12px; }`, `.soc-mode-lbl { font-size: 0.56rem; font-weight: 700; letter-spacing: 0.02em; line-height: 1; }`.
  - Keep `.soc-chg-ico` hidden under `no-preference` (`.soc-chg-ico { display: none; ... }`) and in `.soc-btn.is-fast-charge .soc-chg-ico { color: var(--lp-amber); }`.
  - Inside `@media (prefers-reduced-motion: no-preference)`:
    - Remove `.soc-btn.is-charging .soc-ring-fg { animation: lp-pulse-soft ...; }` (keep SoC arc crisp).
    - Add `.soc-btn.is-charging .soc-svg-orbit { animation: lp-spin 2.4s linear infinite; }`, `.soc-btn.is-charging.is-fast-charge .soc-svg-orbit { animation-duration: 1.35s; }`, `.soc-btn.is-charging .soc-track { animation: lp-soc-slide 5.2s ease-in-out infinite; }`.
  - Inside `@media (prefers-reduced-motion: reduce)`:
    - Keep `*, *::before, *::after { animation: none !important; transition: none !important; }`.
    - Add `.soc-mode-slide { display: none !important; } .soc-btn.is-charging .soc-chg-ico:not(.hidden) { display: inline-flex; }` so reduced-motion users see `76%` + static AC/DC icon cleanly without ever showing the bolt when idle.
  - Add `@keyframes lp-soc-slide { 0%, 40% { transform: translateY(0); } 48%, 88% { transform: translateY(-22px); } 96%, 100% { transform: translateY(0); } }`.

- [ ] **Step 4: Update `_buildSkeletonHtml` (`L2708-2718`) & `_applyBindingsInner` (`L3251-3313`; `chgFlowTrack` at `L3664-3665` already reuses the `L3251` `isCharging` local)**
  - Skeleton:
    - Add `<svg class="soc-svg-orbit hidden" data-bind="socOrbit" viewBox="0 0 52 52" aria-hidden="true"><circle class="soc-ring-orbit" cx="26" cy="26" r="21" stroke-dasharray="28 103.95"/></svg>`.
    - Wrap `socText` in `<div class="soc-viewport"><div class="soc-track"><div class="soc-slide"><span class="soc-val num" data-bind="socText">—</span></div><div class="soc-slide soc-mode-slide hidden" data-bind="socModeSlide"><span data-bind="socModeIco">' + svgIcon("bolt", "soc-mode-ico") + '</span><span class="soc-mode-lbl" data-bind="socModeLbl">AC</span></div></div></div>`.
    - Keep `<span class="soc-chg-ico hidden" data-bind="socChgIco">' + svgIcon("bolt", "soc-bolt") + "</span>"`.
  - `_applyBindingsInner`:
    - Compute `var chgInfo = resolveSocChargingState(vm, { isOn: this._isOn.bind(this), num: this._num.bind(this), dead: this._dead.bind(this) }); var isCharging = chgInfo.isCharging; var isFastCharge = chgInfo.isFast;`
    - Toggle `socBtn`: `.is-charging` = `isCharging`, `.is-fast-charge` = `isFastCharge`.
    - Toggle `.hidden` on `socOrbit`, `socModeSlide`, `socChgIco` (`!isCharging`).
    - Guard icon DOM updates with `data-mode`:
      ```javascript
      var modeKey = isFastCharge ? "fast" : "normal";
      var icoName = isFastCharge ? "fast_charge" : "bolt";
      var socModeIco = root.querySelector('[data-bind="socModeIco"]');
      if (socModeIco && socModeIco.getAttribute("data-mode") !== modeKey) {
        socModeIco.setAttribute("data-mode", modeKey);
        socModeIco.innerHTML = svgIcon(icoName, "soc-mode-ico");
      }
      if (socChgIco && socChgIco.getAttribute("data-mode") !== modeKey) {
        socChgIco.setAttribute("data-mode", modeKey);
        socChgIco.innerHTML = svgIcon(icoName, "soc-bolt");
      }
      ```
    - Set `socModeLbl.textContent = isFastCharge ? "DC" : "AC"`.
    - Inside `if (vm.bat)`: compute `var pctText = batNum === null ? "—" : Math.round(pct) + "%";`, set `socText.textContent = pctText`, build `var socAria = pctText + (isCharging ? " · " + (isFastCharge ? t.chargingFast : t.chargingNormal) : "");`, and set `aria-label` on both `socProg` and `socBtn` to `socAria`.

- [ ] **Step 5: Verify GREEN** — Master runs `node --test tests/lepas_card.test.mjs` and `.venv/bin/pytest tests/test_lovelace_card.py -q`.

---

### Task 3: Sync Version `1.26.0` & Release Artifacts

**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js:2,14,85-91` (`1.25.0` → `1.26.0`)
- Modify: `custom_components/lepas/manifest.json:23` (`"1.26.0"`)
- Modify: `pyproject.toml:3` (`"1.26.0"`)
- Modify: `tests/test_lovelace_card.py:126,129` (`v1.26.0` / `\?v=1\.26\.0\b`)
- Check: `tests/lepas_card.test.mjs` for any `1.25.0` assertions and update if present
- Modify: `CHANGELOG.md:17-19` (bilingual `## v1.26.0 — 2026-11-19` section)

- [ ] **Step 1: Bump versions synchronously and add bilingual `CHANGELOG.md` notes for `v1.26.0`**.
- [ ] **Step 2: Master verification** — Run full `.venv/bin/pytest -q --tb=short --maxfail=2`, `node --test tests/lepas_card.test.mjs`, `uv run ruff check custom_components/ tests/`, `uv run ruff format --check custom_components/ tests/`.
