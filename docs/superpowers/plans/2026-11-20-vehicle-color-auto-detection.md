# Vehicle Color Auto-Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Audit Matrix (Pre-Presentation Dual-Gate)

| Stage | Sub-Agent Role | Model | Conversation ID | Verdict | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Stage 1 | Domain & Archaeology Pre-Audit | `flash` | `2adaad91-530c-4c4e-acef-954717871b42` | `CONDITIONAL` → Risolto | Tutte le 3 condizioni recepite e verificate prima di Stage 2 |
| Stage 2 | Six-Pillars Sentinel Control Gate | `inherit` | `90d12fec-318e-4c01-81e3-61b05c090ab0` | `APPROVED` | Tutti e 6 i pilastri `PASS` alla revisione 2/2 (con verifica diretta `collectIntegrationItems` & `emitEditorConfig`) |

---

**Goal:** Automatically detect the vehicle paint color from `vmc/queryList` (`colorCode` / `colorNameEn`), persist it via `DATA_CAPS_PROBED_V6`, expose it on `LepasSessionStatus`, and auto-apply it in `lepas-card.js` when card color is unset or `"auto"`.

**Architecture:** `const.py` normalizes raw `colorCode` / `colorNameEn` into one of the 5 supported card colors (`black`, `grey`, `teal`, `violet`, `white`) inside `capabilities_from_item`; `coordinator.py` backfills existing `V5` entries once via `DATA_CAPS_PROBED_V6` and stores the metadata; `sensor.py` (`LepasSessionStatus`) exposes non-PII `vehicle_color*` attributes; `lepas-card.js` resolves `auto` from entity attributes for both hero PNG and Blueprint SVG while keeping explicit manual overrides first.

**Tech Stack:** Python 3.12+ (Home Assistant Core), Vanilla ES5-compatible Web Component JS (`lepas-card.js`), `pytest`, `node --test`, `ruff`.

**Spec:** [2026-11-20-vehicle-color-auto-detection-design.md](file:///home/federico/Lepas/docs/superpowers/specs/2026-11-20-vehicle-color-auto-detection-design.md)

## Global Constraints
- Compatibility constraints in `lepas-card.js`: NO optional chaining (`?.`), NO nullish coalescing (`??`), NO top-level ES module `import`/`export`.
- Zero PII/VIN in `extra_state_attributes`, diagnostics, or card DOM.
- Security invariant in `lepas-card.js`: raw `vehicle_color_name` and `vehicle_color_code` are NEVER interpolated into `innerHTML`, DOM attributes, CSS, or URLs — they are only mapped to the 5 canonical slugs in `VALID_COLORS`; existing `sanitizeUrl` checks for `config.image` / `attributes.vehicle_image` remain unchanged.
- Keep `LepasCard._helpers.COLORS` equal to `["grey", "teal", "violet", "black", "white"]` and `LepasCard.getStubConfig()` equal to `{ type: "custom:lepas-card" }`.
- Keep `DATA_CAPS_PROBED_V5: True` written alongside `DATA_CAPS_PROBED_V6: True` so existing V5 checks stay satisfied.

## Blast Radius & StateGraph

### BlastRadius
- `direct_files`:
  - `custom_components/lepas/const.py`
  - `custom_components/lepas/coordinator.py`
  - `custom_components/lepas/sensor.py`
  - `custom_components/lepas/diagnostics.py`
  - `custom_components/lepas/lovelace/lepas-card.js`
  - `tests/test_vehicle_color.py` (new Python test module)
  - `tests/lepas_card.test.mjs`
- `transitively_affected` *(verified invariant — zero edits required)*:
  - `tests/test_native_departure_battery.py` (all `DATA_CAPS_PROBED_V5: True` setup tests at `L594,891,1273,1323` already patch `async_ensure_vehicle_identity = no_backfill` via `_patch_entry_io`, and `test_v5_backfill_*` at `L241-280` starts from `V4` and asserts `DATA_CAPS_PROBED_V5 is True`, which continues to be written alongside `V6`)
  - `tests/test_capabilities_bev.py`, `tests/test_capabilities_scheda.py` (ignore unknown keys in `capabilities_from_item` dict; `capabilities_from_item({}) == {}` preserved)
  - `tests/test_diagnostics.py` (never asserts exact key set on `diag["vehicle"]`)
  - `tests/test_lovelace_card.py` (validates `lepas-card.js` and `manifest.json` alignment)
- `uncertain`:
  - Future Chery/Lepas paint codes outside `KME8` whose `colorNameEn` might lack standard English color tokens (handled fail-open: stored in `vehicle_color_name` / `vehicle_color_code`, card falls back safely to `"grey"`).

### StateGraph (`onSuccess:` / `onFailure:` / `onTeardown:`)
- `async_ensure_vehicle_identity` (`coordinator.py`):
  - `onSuccess:` `info` contains `DATA_CAPS_PROBED_V6: True` (+ `DATA_CAPS_PROBED_V5: True` + optional `DATA_VEHICLE_COLOR*`) → updates `self.vehicle_color*` in memory only for keys present in `info` (never clearing cached keys if absent), persists `entry.data` via `async_update_entry`, and calls `self.async_update_listeners()` ONLY if color attributes changed AND `not self._timers.closing`.
  - `onFailure:` `_fetch_vehicle_identity` catches network/JSON exceptions and returns `None` → does NOT write `DATA_CAPS_PROBED_V6`, keeps existing `self.vehicle_color` (`None` or cached), retries safely on next boot without blocking setup or touching OAuth refresh locks.
  - `onTeardown:` `self._timers.closing` is `True` or `self.entry.entry_id not in self.hass.data.get(DOMAIN, {})` → aborts immediately before `async_update_entry` and never calls `async_update_listeners()`.
- `LepasCard` / `resolveCardColor` (`lepas-card.js`):
  - `onSuccess:` explicit `cfg.color` (non-empty, `!== "auto"`) → `resolveColor(cfg.color)`; empty/`"auto"` → 3-pass scan over `items` (`vehicle_color` across all `items`, then `vehicle_color_name`, then `vehicle_color_code`, reading `(item.s && item.s.attributes) || item.attributes`) returning canonical color (`black`..`white`).
  - `onFailure:` missing attributes, unknown `colorCode`/`colorNameEn`, or non-array `items` → deterministic fallback `"grey"` without throwing.
- `LepasCardEditor` (`lepas-card.js`):
  - `onClick("auto")` → `_emitConfig({ color: "" })` with `clearKeys = ["title", "image", "color"]` deletes `config.color` (aligned with `getStubConfig()`) → `_syncValues()` selects `[data-color="auto"]` (and NOT `"grey"`).
  - `onUnrecognizedConfig(cfg.color)`: unknown explicit `cfg.color` falls back to `"grey"` via `resolveColor(cfg.color)` in `_syncValues()` so `"grey"` is selected instead of `"auto"`.

### Domain Skills & Sub-Agent Roster
- **Domain 1 — Backend Python (`backend_color_worker`, `Model: 'pro'` because `coordinator.py` > 600L & `sensor.py` > 600L & 4 interdependent Python files)**:
  - Skills: `ponytail`, `antislop-code`
  - Files: `custom_components/lepas/const.py`, `custom_components/lepas/coordinator.py`, `custom_components/lepas/sensor.py`, `custom_components/lepas/diagnostics.py`, `tests/test_vehicle_color.py`
- **Domain 2 — Frontend Lovelace Card (`card_color_worker`, `Model: 'pro'` because `lepas-card.js` > 600L)**:
  - Skills: `modern-web-guidance` (`styling-web-components`), `antislop-ui`, `ponytail`
  - Files: `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`

---

### Task 1: Backend Vehicle Color Extraction, Backfill (`V6`), & Attribute Exposure

**Files:**
- Modify: `custom_components/lepas/const.py:78-130,305-367`
- Modify: `custom_components/lepas/coordinator.py:45-56,373-385,3275-3365`
- Modify: `custom_components/lepas/sensor.py:490-530,854-864`
- Modify: `custom_components/lepas/diagnostics.py:235-245`
- Create: `tests/test_vehicle_color.py`

**Interfaces:**
- Produces in `const.py`:
  - `DATA_VEHICLE_COLOR = "vehicle_color"`
  - `DATA_VEHICLE_COLOR_CODE = "vehicle_color_code"`
  - `DATA_VEHICLE_COLOR_NAME = "vehicle_color_name"`
  - `DATA_CAPS_PROBED_V6 = "caps_probed_v6"`
  - `normalize_vehicle_color(code: object, name_en: object, name_local: object = None) -> str | None`
- Produces on `LepasSessionStatus` (`sensor.py`):
  - `extra_state_attributes` with keys `"vehicle_color"` (strictly one of `"black" | "grey" | "teal" | "violet" | "white"`), `"vehicle_color_code"`, `"vehicle_color_name"` (omitting `None`/empty values; returns `None` if empty).

- [ ] **Step 1: Write failing tests in `tests/test_vehicle_color.py`**
  - Test `normalize_vehicle_color`: `"KME8"` → `"black"`, `("", "New Carbon Black")` → `"black"`, `("X1", "Pearl White")` → `"white"`, `("X2", "Phantom Grey")` / `"Silver"` → `"grey"`, `("X3", "Aurora Teal")` / `"Emerald Green"` → `"teal"`, `("X4", "Amethyst Violet")` / `"Purple"` → `"violet"`, deterministic token-order `"Silver Black"` → `"grey"` (first matched token in text order), `("", "Unknown Hue")` → `None`, `("", "whiten")` → `None` (no substring trap `AB-HA-001`).
  - Test `capabilities_from_item`: valid `{"colorCode": "KME8", "colorNameEn": "New Carbon Black"}` sets `DATA_VEHICLE_COLOR == "black"`, `DATA_VEHICLE_COLOR_CODE == "KME8"`, `DATA_VEHICLE_COLOR_NAME == "New Carbon Black"`; fallback to `colorName` when `colorNameEn` is absent; non-string/`None`/whitespace values ignored; values >64 chars safely bounded to 64 chars.
  - Test `async_ensure_vehicle_identity` (`V5 → V6`):
    - On `V5` entry with `nome_in_cache=True` (`vehicle_name="My Car"`), re-queries `queryList` once, preserves `"My Car"`, writes `DATA_CAPS_PROBED_V6: True` + `DATA_CAPS_PROBED_V5: True`, updates `coord.vehicle_color == "black"`, calls `async_update_listeners()`, and does not re-query on a second call.
    - When color does not change on backfill, `async_update_listeners()` is NOT called; when `coord._timers.closing` is `True` mid-backfill, neither `async_update_entry` nor `async_update_listeners()` is called (`AB-LEP-010`).
  - Test `LepasSessionStatus.extra_state_attributes` returns `{"vehicle_color": "black", "vehicle_color_code": "KME8", "vehicle_color_name": "New Carbon Black"}` when set and `None` when unset.
  - Test `async_get_config_entry_diagnostics` includes `"color": "black"`, `"color_code": "KME8"`, `"color_name": "New Carbon Black"` in `diag["vehicle"]`.
  - Falsification: breaking `normalize_vehicle_color`, token ordering, 64-char bound, `DATA_CAPS_PROBED_V6` gating, `_timers.closing` guard, or `LepasSessionStatus.extra_state_attributes` immediately fails assertions against real `LepasCoordinator` / `LepasSessionStatus` / `async_get_config_entry_diagnostics` calls.

- [ ] **Step 2: Run test to verify RED**
  - Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_vehicle_color.py -q`

- [ ] **Step 3: Implement constants & `normalize_vehicle_color` in `const.py`**
  - Add `DATA_VEHICLE_COLOR`, `DATA_VEHICLE_COLOR_CODE`, `DATA_VEHICLE_COLOR_NAME`, `DATA_CAPS_PROBED_V6`, `VEHICLE_COLOR_CODE_MAP = {"KME8": "black"}`, and `normalize_vehicle_color` using `re.findall(r"[a-z]+", text.lower())` iterating tokens in appearance order (so `"Silver Black"` deterministically returns `"grey"`).
  - Update `capabilities_from_item` to extract `colorCode` / `colorNameEn` / `colorName` (only `str`, stripped, bounded to 64 chars) and populate `DATA_VEHICLE_COLOR*`.

- [ ] **Step 4: Implement `V6` backfill & attributes in `coordinator.py`, `sensor.py`, `diagnostics.py`**
  - In `coordinator.py`: import new constants, initialize `self.vehicle_color`, `self.vehicle_color_code`, `self.vehicle_color_name` in `__init__`, check `not self.entry.data.get(DATA_CAPS_PROBED_V6)` in `async_ensure_vehicle_identity`, write `DATA_CAPS_PROBED_V6: True` alongside `DATA_CAPS_PROBED_V5: True` in `_fetch_vehicle_identity`. Update `self.vehicle_color*` in memory ONLY for keys present in `info` (never clearing cached keys if absent; even when `nome_in_cache` is True), and call `self.async_update_listeners()` ONLY if color attributes changed AND `not self._timers.closing` (`AB-LEP-010`).
  - In `sensor.py`: verify `_LepasRestoreSensor` (`L491-528`) has no `extra_state_attributes` (merge via `super()` if ever present) and add `extra_state_attributes` on `LepasSessionStatus`.
  - In `diagnostics.py`: expose `color`, `color_code`, `color_name` in `diag["vehicle"]`.

- [ ] **Step 5: Run Python tests to verify GREEN**
  - Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_vehicle_color.py tests/test_native_departure_battery.py tests/test_capabilities_bev.py tests/test_capabilities_scheda.py tests/test_diagnostics.py -q`

---

### Task 2: Lovelace Card Auto-Color Resolution & Editor `"Auto"` Swatch

**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js:59-85,139,350,561,804-830,2272-2335,4240,4487,5336,5536`
- Modify: `tests/lepas_card.test.mjs:991-1042,1505-1534`

**Interfaces:**
- Consumes from Task 1: `attributes.vehicle_color` (`"black" | "grey" | "teal" | "violet" | "white"`), `attributes.vehicle_color_name`, `attributes.vehicle_color_code` on Lepas entities (`collectIntegrationItems` at `L1120-1153` collects all integration entities regardless of `config.entity`, so `sensor.lepas_session_status` is always included in `items`; read attributes safely via `(item.s && item.s.attributes) || item.attributes`).
- Produces in `lepas-card.js`:
  - `resolveCardColor(config, items)` (exposed also in `LepasCard._helpers.resolveCardColor`).

- [ ] **Step 1: Write failing JS tests in `tests/lepas_card.test.mjs`**
  - `resolveHeroImage({}, itemsWithBlackAttr)` (where `sensor.lepas_session_status` has `vehicle_color: "black"`) returns `/lepas_card/lepas-hero-black.png?v=...`.
  - `resolveHeroImage({ color: "auto" }, itemsWithNameOnly)` (only `vehicle_color_name: "New Carbon Black"` or `vehicle_color_code: "KME8"`) returns `/lepas_card/lepas-hero-black.png?v=...`.
  - Substring trap `AB-HA-001` & deterministic token order: `vehicle_color_name: "whiten"` returns `"grey"` (not `"white"`); `"Silver Black"` returns `"grey"` (same order as Python); unknown `vehicle_color*` or non-array `items` falls back to `"grey"`.
  - Multi-entity precedence across `items`: first entity has `vehicle_color_name: "Silver"` (no `vehicle_color`), second entity `sensor.lepas_session_status` has `vehicle_color: "teal"` → 3-pass scan selects `"teal"` (`vehicle_color` pass beats `vehicle_color_name` pass).
  - Explicit manual `cfg.color: "teal"` overrides `vehicle_color: "black"` (`lepas-hero-teal.png` and `.bp-stage[data-car-color="teal"]`).
  - Rendered card with `{}` config and `sensor.lepas_session_status` carrying `vehicle_color: "black"` sets both hero `<img>` `src` to `lepas-hero-black.png` AND `.bp-stage[data-car-color="black"]`, and updates live when `card.hass` changes `vehicle_color` to `"teal"`.
  - `LepasCardEditor`: renders `"auto"` swatch, `_syncValues()` selects `[data-color="auto"]` (and NOT `"grey"`) when `cfg.color` is `undefined`, `""`, or `"auto"`, selects `"grey"` on `"invalid-color"`, and clicking `"auto"` fires `config-changed` with `color` key deleted from `detail.config` (`clearKeys = ["title", "image", "color"]`).
  - Falsification: if `resolveHeroImage` or `.bp-stage` ignores entity `vehicle_color`, falls into `"whiten"` substring matching, uses wrong pass precedence, or `_syncValues()` highlights `"grey"` instead of `"auto"`, tests fail immediately on real DOM output.

- [ ] **Step 2: Run JS test to verify RED**
  - Run: `node --test tests/lepas_card.test.mjs`

- [ ] **Step 3: Implement `resolveCardColor`, editor `"auto"` swatch, and Blueprint/Hero integration in `lepas-card.js`**
  - Add `"auto"` translations (`colors.auto`: `"Auto"` in IT/EN/NL) and `"auto"` swatch button (`data-color="auto"`) before `VALID_COLORS` in `LepasCardEditor._render()` (keeping `VALID_COLORS` and `LepasCard._helpers.COLORS` unchanged!).
  - Update `LepasCardEditor._emitConfig` (`L2273`) to pass `["title", "image", "color"]` as `clearKeys`, and `_handleFieldChange` (`L2280-2283`) so clicking `[data-color="auto"]` emits `{ color: "" }` (deleting `config.color` via `emitEditorConfig`).
  - Update `LepasCardEditor._syncValues()` (`L2299-2306`): if `!cfg.color || String(cfg.color).trim().toLowerCase() === "auto"`, mark `[data-color="auto"]` with `.is-selected` (and NOT `"grey"`); otherwise mark `resolveColor(cfg.color)`.
  - Implement `resolveColorFromText(raw)` using word-boundary tokenization `String(raw).toLowerCase().match(/[a-z]+/g)` (iterating tokens in appearance order — NEVER `indexOf`/`includes`, `AB-HA-001`) reusing `COLOR_ALIASES` (`L59-76`) plus only extra tokens (`silver`, `cyan`, `emerald`, `zwart`, `wit`, `grijs`, `zeegroen`).
  - Implement `resolveCardColor(config, items)` (ES5-safe, no `?.` / `??`): if `cfg.color` is non-empty and `!== "auto"` (lowercased/trimmed), return `resolveColor(cfg.color)`; otherwise run 3 passes over `items` reading `(item.s && item.s.attributes) || item.attributes` (pass 1: `vehicle_color` matching `VALID_COLORS`; pass 2: `vehicle_color_name` via `resolveColorFromText`; pass 3: `vehicle_color_code` uppercase lookup in `{ KME8: "black" }`), falling back to `"grey"`. Never interpolate raw `vehicle_color_name`/`vehicle_color_code` into DOM/HTML/CSS/URLs.
  - Update `resolveHeroImage(config, items)` (`L810-828`) to use `resolveCardColor(cfg, items)`, and update `bpStage` `data-car-color` at both skeleton render (`L4240`, passing `ctx.items`) and live update (`L5336`, passing `vm.items`).

- [ ] **Step 4: Run JS & Python full card tests to verify GREEN**
  - Run: `node --test tests/lepas_card.test.mjs`
  - Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_lovelace_card.py -q`
