## Dual-Gate Audit Matrix

| Stage | Ruolo | Model | Conversation ID | Verdetto |
| :--- | :--- | :--- | :--- | :--- |
| Stage 1 | Domain & Archaeology Pre-Audit | `flash` | `32a24aad-ff5a-4364-a46e-f946c54a6ed6` | `NEEDS_CHANGES` (3 rilievi corretti su `plan_draft.md`) |
| Stage 2 | Six-Pillars Sentinel Control Gate | `inherit` | `63d26400-c547-48c3-a938-9f7979db9316` | `REJECTED` → **`APPROVED`** (7/7 difetti risolti e riverificati) |

---

# Long-Term Consumption Sensors (EV / Hybrid) & Card Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 6 persistent long-term consumption sensors split between EV (`kWh/100 km`) and Hybrid (`L/100 km`) across `100 km`, `1000 km`, and `From Start` windows, a `From Start` reset button, configurable HV battery capacity (`18.4 kWh` default), and a compact Consumption section in `lepas-card.js` Overview tab.

**Architecture:** A pure Python `ConsumptionTracker` module (`custom_components/lepas/consumption.py`) maintains per-mode FIFO segment queues (capped at `1000.0 km` each) and cumulative `from_start` totals. `LepasCoordinator` integrates valid `/asr/manager/realtime` frames under a dedicated `threading.Lock` (`_consumption_lock`, never nested with `_state_lock` or `_hv_lock`), persisting state via `homeassistant.helpers.storage.Store` (`lepas.<entry_id>.consumption`) with debounced saves and explicit unload flush. Six `SensorEntity` instances (`sensor.py`), one `ButtonEntity` (`button.py`), one `LepasOptionsFlow` field (`config_flow.py`), 4-language translations, and an Overview Consumption panel in `lepas-card.js` expose the data end-to-end.

**Tech Stack:** Python 3.12, Home Assistant Core (`Store`, `SensorEntity`, `ButtonEntity`, `OptionsFlow`), `pytest`, `ruff`, Vanilla JS Shadow DOM Web Component (`lepas-card.js`), Node test runner (`tests/lepas_card.test.mjs`).

**Spec:** `docs/superpowers/specs/2026-11-19-consumption-sensors-design.md`

---

## Global Constraints

- `ID_PREFIX = "lepas"` and `unique_id = f"{coordinator.vin}_{unique_suffix}"` (AB-LEP-002).
- Never nest `self._consumption_lock` with `self._state_lock` or `self._hv_lock` (AB-LEP-007 / AB-LEP-014).
- All `Store` async I/O (`async_load`, `async_delay_save`, `async_save`) MUST run on the Home Assistant event loop, never inside an executor thread or `async_stop()`.
- Hide the 3 `hybrid_*` sensors automatically when `coordinator.is_pure_electric()` is `True`, and hide the Hybrid row in `lepas-card.js` when hybrid sensors are absent.
- Keep all 4 translation files (`strings.json`, `translations/en.json`, `translations/it.json`, `translations/nl.json`) leaf-key synchronized (`tests/test_traduzioni_complete.py`), and update `tests/test_entity_count.py` (`sensor: 49`, `button: 16`, `TOTALE_ATTESO = 141`).
- No PII (VIN, coordinates, tokens) in consumption `Store` snapshots or logs (AB-LEP-002).

---

## Blast Radius & StateGraph

### BlastRadius
- **direct_files**:
  - Create: `custom_components/lepas/consumption.py`
  - Create: `tests/test_consumption.py`
  - Modify: `custom_components/lepas/const.py`
  - Modify: `custom_components/lepas/config_flow.py`
  - Modify: `custom_components/lepas/coordinator.py`
  - Modify: `custom_components/lepas/__init__.py`
  - Modify: `custom_components/lepas/sensor.py`
  - Modify: `custom_components/lepas/button.py`
  - Modify: `custom_components/lepas/strings.json`
  - Modify: `custom_components/lepas/translations/en.json`
  - Modify: `custom_components/lepas/translations/it.json`
  - Modify: `custom_components/lepas/translations/nl.json`
  - Modify: `tests/test_entity_count.py`
  - Modify: `custom_components/lepas/lovelace/lepas-card.js`
  - Modify: `tests/lepas_card.test.mjs`
- **transitively_affected**:
  - `tests/test_traduzioni_complete.py` (validates leaf key parity across `strings.json` and `translations/{en,it,nl}.json`)
  - `tests/test_translation_key_declared.py` (validates `translation_key` uniqueness and `lepas_` object_id prefix)
  - `tests/test_capabilities_bev.py` (checks entity omission on confirmed BEV `powerType == 0`)
  - `tests/test_lovelace_card.py` (validates `lepas-card.js` serving/manifest alignment)
- **uncertain**:
  - Live behavior of `oilSurplus` integer quantization (`1 L` steps) over short hybrid segments: mitigated by `MIN_SAMPLE_KM_HYBRID = 10.0`.
  - Whether `Store` file exists yet on existing entries: handled gracefully (`async_load()` returning `None` initializes empty `ConsumptionTracker`).

### StateGraph (`onSuccess:` / `onFailure:`)
1. **Startup `Store.async_load()` in `LepasCoordinator.async_start()` (`__init__.py:307` before `async_forward_entry_setups` at `__init__.py:318`)**:
   - `onSuccess`: hydrate `self._consumption_tracker` under `self._consumption_lock` before `async_forward_entry_setups` mounts entities.
   - `onFailure` (corrupt JSON / OSError): log `WARNING` (no PII), keep fresh `ConsumptionTracker()` so integration boot never fails.
2. **Sample ingestion in `LepasCoordinator._on_probe_data(data)` (executor thread)**:
   - Acquire `self._consumption_lock` (`with self._consumption_lock:` — no nested locks, `try/finally` via context manager guarantees release) after `_state_lock` is released.
   - `onSuccess` (`changed=True`): schedule `self.hass.loop.call_soon_threadsafe(self._schedule_consumption_save)` wrapped in `if not self._timers.closing:` + `try/except RuntimeError`.
   - `onFailure` (malformed numeric telemetry): `_safe_float` returns `None`, `ingest()` returns `False` without mutating baselines or raising.
3. **Unload flush in `async_unload_entry()` AFTER `coordinator.async_stop()` (`__init__.py:566`)**:
   - Execute `await coordinator.async_flush_consumption()` **after** `await hass.async_add_executor_job(coordinator.async_stop)` so `_timers.closing` is `True` and paho/timers are already stopped (prevents any in-flight `_on_probe_data` from scheduling `async_delay_save` after flush).
   - `onSuccess`: calls `await self._consumption_store.async_save(snapshot)` on the HA event loop if store is initialized.
   - `onFailure`: log `WARNING` and still return `ok` so integration unload never hangs.
4. **Reset action (`button.lepas_reset_consumption_from_start`)**:
   - Acquire `self._consumption_lock`, call `reset_from_start()`, release lock, persist via `await self._consumption_store.async_save(snapshot)` (`onFailure`: log warning), then `if not self._timers.closing: self.async_update_listeners()` (`AB-LEP-010`).
5. **Lovelace Card Overview (`lepas-card.js`)**:
   - `onSuccess`: renders `Consumi medi` with `50 km`, `100 km`, `1000 km`, `Da inizio` cells carrying `data-e="<entity_id>"` for `hass-more-info`; hides Hybrid row when no hybrid entities exist (BEV).
   - `onFailure` (missing/unknown sensor state): cell displays `"—"` without throwing in `_applyBindingsInner`.

### Test Falsification Mandate
- Every test in `tests/test_consumption.py` exercises the real `ConsumptionTracker`, `LepasCoordinator._on_probe_data`, `LepasConsumptionSensor`, `LepasActionButton`, and `LepasOptionsFlow` without mocking the function under test. Breaking refuel filtering, recharge filtering, degraded-frame rejection, `MAX_STEP_GAP_KM`, proportional window trimming, `Store` serialization, or BEV suppression immediately fails assertions.
- Every test in `tests/lepas_card.test.mjs` renders the real `LepasCard` custom element against `makeFullHass()` and asserts rendered DOM values, BEV hiding, language switching (`it`/`en`/`nl`), and `hass-more-info` event dispatch on click.

---

## Domain Skills & Sub-Agent Roster

1. **Domain 1 — Backend Consumption Engine, Coordinator, Entities & Translations (`consumption_backend_worker`)**:
   - **Model**: `pro` (Round 1 — touches `>600L` files `coordinator.py` / `sensor.py`, `>=3` interdependent files, and `threading.Lock` + `Store` lifecycle).
   - **Skills**: `clean-code` (primary) + `ponytail` + `antislop-code` (companions from `lookup.py`).
   - **Crash Antibodies**: `AB-LEP-002`, `AB-LEP-007`, `AB-LEP-010`, `AB-LEP-014`.
   - **Files**: `custom_components/lepas/consumption.py`, `custom_components/lepas/const.py`, `custom_components/lepas/config_flow.py`, `custom_components/lepas/coordinator.py`, `custom_components/lepas/__init__.py`, `custom_components/lepas/sensor.py`, `custom_components/lepas/button.py`, `custom_components/lepas/strings.json`, `custom_components/lepas/translations/{en,it,nl}.json`, `tests/test_consumption.py`, `tests/test_entity_count.py`.
2. **Domain 2 — Lovelace Card Consumption Overview (`consumption_card_worker`)**:
   - **Model**: `pro` (Round 1 — modifies `>600L` `lepas-card.js` 4233L).
   - **Skills**: `frontend-ui-engineering` (primary) + `antislop-ui` + `antislop-code` (companions from `lookup.py`).
   - **Crash Antibodies**: `AB-LEP-008`, `AB-LEP-014`.
   - **Files**: `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`.

---

## Tasks

### Task 1: Pure Consumption Engine (`consumption.py`) & Unit Tests

**Files:**
- Create: `custom_components/lepas/consumption.py`
- Create: `tests/test_consumption.py`

**Interfaces:**
- Produces:
  - `DEFAULT_BATTERY_CAPACITY_KWH = 18.4`
  - `WINDOW_100_KM = 100.0`, `WINDOW_1000_KM = 1000.0`, `MAX_STEP_GAP_KM = 50.0`
  - `MIN_SAMPLE_KM_EV = 5.0`, `MIN_SAMPLE_KM_HYBRID = 10.0`
  - `is_degraded_battery_frame(rt: dict | None) -> bool`
  - `ConsumptionTracker`:
    - `ingest(odometer: float | None, soc_pct: float | None, fuel_l: float | None, *, engine_on: bool, charging_or_plugged: bool, degraded_battery: bool, battery_capacity_kwh: float) -> bool`
    - `window_stats(mode: str, target_km: float | None) -> dict[str, Any]`
    - `reset_from_start() -> None`
    - `to_dict() -> dict[str, Any]` / `classmethod from_dict(cls, raw: dict | None) -> ConsumptionTracker`

- [ ] **Step 1: Write failing unit tests in `tests/test_consumption.py`**

```python
import pytest
from custom_components.lepas.consumption import (
    ConsumptionTracker,
    DEFAULT_BATTERY_CAPACITY_KWH,
    is_degraded_battery_frame,
)


def test_ev_and_hybrid_split_and_refuel_recharge_filtering():
    t = ConsumptionTracker()
    assert t.ingest(1000.0, 80.0, 30.0, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=18.4) is True
    assert t.ingest(1010.0, 70.0, 30.0, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=18.4) is True
    ev_100 = t.window_stats("ev", 100.0)
    assert ev_100["sampled_km"] == pytest.approx(10.0)
    assert ev_100["value"] == pytest.approx(18.4, rel=1e-3)

    assert t.ingest(1010.0, 90.0, 30.0, engine_on=False, charging_or_plugged=True, degraded_battery=False, battery_capacity_kwh=18.4) is True
    assert t.ingest(1010.0, 90.0, 45.0, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=18.4) is True

    assert t.ingest(1035.0, 85.0, 43.0, engine_on=True, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=18.4) is True
    hyb_100 = t.window_stats("hev", 100.0)
    assert hyb_100["sampled_km"] == pytest.approx(25.0)
    assert hyb_100["value"] == pytest.approx(8.0, rel=1e-3)
    assert hyb_100["electric_kwh_100km"] == pytest.approx(3.68, rel=1e-3)


def test_minimum_thresholds_gap_guard_degraded_and_window_trim():
    t = ConsumptionTracker()
    t.ingest(100.0, 80.0, 20.0, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=20.0)
    t.ingest(104.0, 76.0, 20.0, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=20.0)
    assert t.window_stats("ev", 100.0)["value"] is None
    assert t.ingest(108.0, 97.0, 20.0, engine_on=False, charging_or_plugged=False, degraded_battery=True, battery_capacity_kwh=20.0) is False
    assert t.ingest(200.0, 50.0, 15.0, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=20.0) is True
    assert t.window_stats("ev", 100.0)["sampled_km"] == pytest.approx(4.0)

    t2 = ConsumptionTracker()
    t2.ingest(1000.0, 90.0, 20.0, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=100.0)
    t2.ingest(1030.0, 87.0, 20.0, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=100.0)
    t2.ingest(1060.0, 84.0, 20.0, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=100.0)
    t2.ingest(1090.0, 78.0, 20.0, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=100.0)
    t2.ingest(1120.0, 72.0, 20.0, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=100.0)
    assert t2.window_stats("ev", 100.0)["value"] == pytest.approx(16.0, rel=1e-3)
    assert t2.window_stats("ev", None)["value"] == pytest.approx(15.0, rel=1e-3)

    t2.reset_from_start()
    assert t2.window_stats("ev", None)["value"] is None
    assert t2.window_stats("ev", 100.0)["value"] == pytest.approx(16.0, rel=1e-3)

    restored = ConsumptionTracker.from_dict(t2.to_dict())
    assert restored.window_stats("ev", 100.0)["value"] == pytest.approx(16.0, rel=1e-3)
    assert is_degraded_battery_frame({"pureElectricRange": 0, "dumpEnergy": 97}) is True


def test_bev_none_fuel_parked_idle_and_negative_odo_anomaly():
    t = ConsumptionTracker()
    assert t.ingest(100.0, 80.0, None, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=50.0) is True
    assert t.ingest(100.0, 80.0, None, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=50.0) is False
    assert t.ingest(120.0, 72.0, None, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=50.0) is True
    assert t.window_stats("ev", 100.0)["value"] == pytest.approx(20.0, rel=1e-3)
    assert t.ingest(90.0, 70.0, None, engine_on=False, charging_or_plugged=False, degraded_battery=False, battery_capacity_kwh=50.0) is True
    assert t.window_stats("ev", 100.0)["sampled_km"] == pytest.approx(20.0)
    assert t.window_stats("ev", 100.0)["value"] == pytest.approx(20.0, rel=1e-3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_consumption.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.lepas.consumption'`

- [ ] **Step 3: Implement `custom_components/lepas/consumption.py`**

Implement `is_degraded_battery_frame`, constants, and `ConsumptionTracker` with proportional window slicing (`_slice_window`), queue cap at `WINDOW_1000_KM`, refuel/recharge guards, `reset_from_start()`, and `to_dict()` / `from_dict()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_consumption.py -q`
Expected: PASS

---

### Task 2: Constants & Options Flow (`const.py`, `config_flow.py`)

**Files:**
- Modify: `custom_components/lepas/const.py`
- Modify: `custom_components/lepas/config_flow.py:567-592`
- Modify: `tests/test_consumption.py`

**Interfaces:**
- Consumes: `DEFAULT_BATTERY_CAPACITY_KWH` from `.consumption` (single source of truth, re-exported in `const.py`)
- Produces:
  - `CONF_BATTERY_CAPACITY_KWH = "battery_capacity_kwh"` in `const.py`
  - `LepasOptionsFlow` includes `CONF_BATTERY_CAPACITY_KWH` (`vol.Coerce(float)`, `vol.Range(min=5.0, max=150.0)`).

- [ ] **Step 1: Add failing test for `LepasOptionsFlow` battery capacity option in `tests/test_consumption.py`**

```python
async def test_options_flow_persists_battery_capacity(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.lepas.const import DOMAIN, CONF_BATTERY_CAPACITY_KWH, DEFAULT_BATTERY_CAPACITY_KWH

    entry = MockConfigEntry(domain=DOMAIN, data={"vin": "TESTVIN"}, options={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    result2 = await hass.config_entries.options.async_configure(
        result["step_id"],
        user_input={
            "poll_normal_min": 60,
            "poll_charging_min": 30,
            "vehicle_name": "Lepas L8",
            CONF_BATTERY_CAPACITY_KWH: 19.2,
        },
    )
    assert result2["type"] == "create_entry"
    assert result2["data"][CONF_BATTERY_CAPACITY_KWH] == pytest.approx(19.2)
    assert DEFAULT_BATTERY_CAPACITY_KWH == 18.4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_consumption.py::test_options_flow_persists_battery_capacity -q`
Expected: FAIL (`ImportError` on `CONF_BATTERY_CAPACITY_KWH`)

- [ ] **Step 3: Add `CONF_BATTERY_CAPACITY_KWH` / `DEFAULT_BATTERY_CAPACITY_KWH` in `const.py` and add field to `LepasOptionsFlow` in `config_flow.py`**

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_consumption.py -q`
Expected: PASS

---

### Task 3: Coordinator Persistence & Ingestion (`coordinator.py`, `__init__.py`)

**Files:**
- Modify: `custom_components/lepas/coordinator.py:30-55, 336-505, 583-590, 2835-2860`
- Modify: `custom_components/lepas/__init__.py:306-320, 553-574`
- Modify: `tests/test_consumption.py`

**Interfaces:**
- Consumes: `ConsumptionTracker`, `CONF_BATTERY_CAPACITY_KWH`, `DEFAULT_BATTERY_CAPACITY_KWH`, `is_degraded_battery_frame`
- Produces on `LepasCoordinator`:
  - `async_load_consumption() -> None` (called in `async_start()` at `__init__.py:307` before `async_forward_entry_setups` at `__init__.py:318`)
  - `async_flush_consumption() -> None` (called in `async_unload_entry()` **after** `await hass.async_add_executor_job(coordinator.async_stop)` at `__init__.py:566`)
  - `consumption_stats(mode: str, target_km: float | None) -> dict[str, Any]`
  - `async_reset_consumption_from_start() -> None` (guards `self.async_update_listeners()` with `if not self._timers.closing:`)
  - `_ingest_consumption(rt: dict, fields: dict) -> None` (called from `_on_probe_data` outside `_state_lock` / `_hv_lock`)

- [ ] **Step 1: Write failing coordinator ingestion & unload flush test in `tests/test_consumption.py`**

```python
async def test_coordinator_ingests_realtime_and_persists_store(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.lepas.const import DOMAIN, CONF_VIN, CONF_BATTERY_CAPACITY_KWH
    from custom_components.lepas.coordinator import LepasCoordinator

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_VIN: "VINCONS01"},
        options={CONF_BATTERY_CAPACITY_KWH: 20.0},
    )
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    await coord.async_load_consumption()

    coord._on_probe_data({"odometer": 500, "dumpEnergy": 80, "oilSurplus": 30, "pureElectricRange": 100, "engineState": 0, "chargeState": 0, "chargeGunState": 0})
    coord._on_probe_data({"odometer": 510, "dumpEnergy": 70, "oilSurplus": 30, "pureElectricRange": 85, "engineState": 0, "chargeState": 0, "chargeGunState": 0})
    stats = coord.consumption_stats("ev", 100.0)
    assert stats["value"] == pytest.approx(20.0, rel=1e-3)

    await coord.async_flush_consumption()
    coord2 = LepasCoordinator(hass, entry)
    await coord2.async_load_consumption()
    assert coord2.consumption_stats("ev", 100.0)["value"] == pytest.approx(20.0, rel=1e-3)

    await coord2.async_reset_consumption_from_start()
    assert coord2.consumption_stats("ev", None)["value"] is None
    assert coord2.consumption_stats("ev", 100.0)["value"] == pytest.approx(20.0, rel=1e-3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_consumption.py::test_coordinator_ingests_realtime_and_persists_store -q`
Expected: FAIL (`AttributeError: 'LepasCoordinator' object has no attribute 'async_load_consumption'`)

- [ ] **Step 3: Implement `Store` lifecycle, `_consumption_lock`, `_ingest_consumption`, `consumption_stats`, `async_reset_consumption_from_start`, and `async_flush_consumption` in `coordinator.py` and `__init__.py`**

Note: In `sensor.py`, replace duplicate `_frame_batteria_degradato` body with call/import to `is_degraded_battery_frame` from `.consumption` (keeping `_frame_batteria_degradato` alias if tests import it).

- [ ] **Step 4: Run test to verify it passes**

Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_consumption.py -q`
Expected: PASS

---

### Task 4: HA Sensors, Reset Button, Translations & Entity Count (`sensor.py`, `button.py`, `strings.json`, `translations/*.json`, `tests/test_entity_count.py`)

**Files:**
- Modify: `custom_components/lepas/sensor.py:145-169, 432-479, 700-740`
- Modify: `custom_components/lepas/button.py:19-65, 86-105`
- Modify: `custom_components/lepas/strings.json`
- Modify: `custom_components/lepas/translations/en.json`
- Modify: `custom_components/lepas/translations/it.json`
- Modify: `custom_components/lepas/translations/nl.json`
- Modify: `tests/test_entity_count.py:36-175` (update `ATTESO` + `TOTALE_ATTESO` and verify Level 1/2 counts)
- Modify: `tests/test_consumption.py`

**Interfaces:**
- Consumes: `LepasCoordinator.consumption_stats`, `LepasCoordinator.async_reset_consumption_from_start`, `LepasCoordinator.is_pure_electric`, `entity_allowed`
- `LepasConsumptionSensor(LepasEntity, SensorEntity)`:
  - `_attr_state_class = SensorStateClass.MEASUREMENT`, `_attr_suggested_display_precision = 2`
  - Units: `"kWh/100 km"` for EV, `"L/100 km"` for Hybrid
  - `extra_state_attributes`: always exposes `sampled_km`, `window_target_km`, `progress_pct`, `energy_kwh`, `fuel_l`; on Hybrid sensors also exposes `electric_consumption_kwh_100km` mapped from `stats["electric_kwh_100km"]`.
- `LepasActionButton` in `button.py`:
  - Add `"reset_consumption_from_start": "mdi:restart"` to `_ICONS`, gate setup with `entity_allowed(coord, "button", "reset_consumption_from_start")`, `EntityCategory.CONFIG`, `object_id=f"{ID_PREFIX}_reset_consumption_from_start"`, `translation_key="reset_consumption_from_start"`.
- Produces entities:
  - `sensor.lepas_ev_consumption_100km`
  - `sensor.lepas_ev_consumption_1000km`
  - `sensor.lepas_ev_consumption_from_start`
  - `sensor.lepas_hybrid_consumption_100km` (non-BEV only)
  - `sensor.lepas_hybrid_consumption_1000km` (non-BEV only)
  - `sensor.lepas_hybrid_consumption_from_start` (non-BEV only)
  - `button.lepas_reset_consumption_from_start`

- [ ] **Step 1: Write failing HA entity, attributes, button press & BEV suppression tests in `tests/test_consumption.py`**

```python
async def test_consumption_sensors_and_reset_button_entities(hass, integrazione_avviata):
    from custom_components.lepas.const import DOMAIN

    coord = next(iter(hass.data[DOMAIN].values()))
    coord._on_probe_data({"odometer": 1000, "dumpEnergy": 80, "oilSurplus": 30, "pureElectricRange": 100, "engineState": 0, "chargeState": 0, "chargeGunState": 0})
    coord._on_probe_data({"odometer": 1010, "dumpEnergy": 70, "oilSurplus": 30, "pureElectricRange": 85, "engineState": 0, "chargeState": 0, "chargeGunState": 0})
    coord._on_probe_data({"odometer": 1030, "dumpEnergy": 65, "oilSurplus": 28, "pureElectricRange": 80, "engineState": 1, "chargeState": 0, "chargeGunState": 0})
    await hass.async_block_till_done()

    ev_100 = hass.states.get("sensor.lepas_ev_consumption_100km")
    assert ev_100 is not None and float(ev_100.state) == pytest.approx(18.4, rel=1e-2)
    assert ev_100.attributes["unit_of_measurement"] == "kWh/100 km"
    assert ev_100.attributes["state_class"] == "measurement"
    assert ev_100.attributes["sampled_km"] == pytest.approx(10.0)

    hyb_100 = hass.states.get("sensor.lepas_hybrid_consumption_100km")
    assert hyb_100 is not None and float(hyb_100.state) == pytest.approx(10.0, rel=1e-2)
    assert hyb_100.attributes["unit_of_measurement"] == "L/100 km"
    assert "electric_consumption_kwh_100km" in hyb_100.attributes

    await hass.services.async_call("button", "press", {"entity_id": "button.lepas_reset_consumption_from_start"}, blocking=True)
    assert hass.states.get("sensor.lepas_ev_consumption_from_start").state == "unknown"
    assert hass.states.get("sensor.lepas_hybrid_consumption_from_start").state == "unknown"
    assert float(hass.states.get("sensor.lepas_ev_consumption_100km").state) == pytest.approx(18.4, rel=1e-2)


async def test_bev_hides_hybrid_consumption_sensors(hass):
    from unittest.mock import patch
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.lepas.const import DOMAIN, CONF_VIN, DATA_POWER_TYPE

    entry = MockConfigEntry(domain=DOMAIN, version=2, data={CONF_VIN: "VINBEV01", DATA_POWER_TYPE: 0})
    entry.add_to_hass(hass)
    with patch("custom_components.lepas.coordinator.LepasCoordinator._connect_car"), \
         patch("custom_components.lepas.coordinator.LepasCoordinator.async_provision_certs", return_value=(True, "ok")), \
         patch("custom_components.lepas.coordinator.LepasCoordinator.async_check_session"):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert hass.states.get("sensor.lepas_ev_consumption_100km") is not None
    assert hass.states.get("button.lepas_reset_consumption_from_start") is not None
    for hyb in ("100km", "1000km", "from_start"):
        assert hass.states.get(f"sensor.lepas_hybrid_consumption_{hyb}") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_consumption.py::test_consumption_sensors_and_reset_button_entities -q`
Expected: FAIL (`AssertionError: Missing entity sensor.lepas_ev_consumption_100km`)

- [ ] **Step 3: Implement `LepasConsumptionSensor` in `sensor.py`, reset button in `button.py`, translations in all 4 JSON files, and update `tests/test_entity_count.py`**

- [ ] **Step 4: Run backend test suite & ruff**

Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_consumption.py tests/test_entity_count.py tests/test_traduzioni_complete.py tests/test_translation_key_declared.py tests/test_capabilities_bev.py -q`
Expected: PASS

---

### Task 5: Lovelace Card Consumption Overview Integration (`lepas-card.js`, `tests/lepas_card.test.mjs`)

**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js` (`I18N`, `buildStyles`, `render`, `_buildSkeletonHtml`, `_applyBindingsInner`)
- Modify: `tests/lepas_card.test.mjs`

**Interfaces:**
- Consumes entity IDs:
  - EV: `average_energy_consumption` (`50 km`), `ev_consumption_100km`, `ev_consumption_1000km`, `ev_consumption_from_start`
  - Hybrid: `average_fuel_consumption` (`50 km`), `hybrid_consumption_100km`, `hybrid_consumption_1000km`, `hybrid_consumption_from_start`
- Produces: Overview `.surface` section (`consSection`) with EV row (`kWh/100 km`) and Hybrid row (`L/100 km`, hidden when all hybrid entities are absent), each cell carrying `data-e="<entity_id>"` so click/Enter dispatches `hass-more-info`.

- [ ] **Step 1: Add failing card tests in `tests/lepas_card.test.mjs`**

Test that:
1. Rendering `lepas-card` on Overview shows `50 km`, `100 km`, `1000 km`, and `Da inizio` / `From start` values for both EV and Hybrid.
2. Clicking a consumption cell dispatches `hass-more-info` with that exact `entityId`.
3. On a BEV (no hybrid sensors in `hass.states`), the Hybrid consumption row is hidden while the EV row remains visible.

- [ ] **Step 2: Run JS test to verify it fails**

Run: `node --test tests/lepas_card.test.mjs`
Expected: FAIL (missing consumption section/cells)

- [ ] **Step 3: Implement I18N (`it`, `en`, `nl`), compact CSS grid, entity mapping, skeleton, and binding updates in `lepas-card.js`**

- [ ] **Step 4: Run JS tests and full Python test suite + ruff**

Run: `node --test tests/lepas_card.test.mjs && /home/federico/.local/bin/uv run --with pytest pytest -q --tb=short --maxfail=2`
Expected: PASS

---

### Task 6: Release Sync (Only at Final Commit/Push if Requested)
- Keep `manifest.json`, `pyproject.toml`, `lepas-card.js` `?v=` and `CHANGELOG.md` aligned per `.agents/AGENTS.md` §5 if creating a release commit/push.
