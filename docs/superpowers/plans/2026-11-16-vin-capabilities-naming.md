# VIN Auto-Learning Capabilities, `unknown` State Fixes & Nomenclature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-configure vehicle entities per-VIN from `vmc/queryVehicleAuthority` (`DATA_CAPS_PROBED_V3`), fix `binary_sensor.lepas_at_home` post-restart state, replace residual `unknown` states on `remaining_charge_time` (`0 min`) and `sunroof_movement_state`/HA diagnostic result sensors (`"In attesa"`/`"Waiting"`), disable `sunshadeState` by default, and align `strings.json` + `translations/{en,it,nl}.json`.

**Architecture:** Read `permessi.leggi()` (`POST /tsp/v1/app/vmc/queryVehicleAuthority`) once per VIN in `config_flow.py` and `coordinator.async_ensure_vehicle_identity` (gated by `DATA_CAPS_PROBED_V3`, fail-open on missing keys/errors), persist a compact `vehicle_features: dict[str, bool]` in `entry.data`, clean up confirmed-`False` entities from the HA entity registry before platform setup, and share position restore from `LepasTracker` into `LepasCoordinator.restore_position()`.

**Tech Stack:** Python 3.12+, Home Assistant Core (`DataUpdateCoordinator`, `RestoreEntity`, `RestoreSensor`, `entity_registry`), `pytest` via `/home/federico/.local/bin/uv run --with pytest pytest` (or `.venv/bin/pytest`), `ruff`.

**Spec:** [2026-11-16-vin-capabilities-naming-design.md](file:///home/federico/Lepas/docs/superpowers/specs/2026-11-16-vin-capabilities-naming-design.md)

## Global Constraints
- `channelId` for Lepas EU MUST stay `"6"` and `LepasConfigFlow.VERSION` MUST stay `2` (`AB-LEP-006`).
- Zero plaintext secrets, VINs, tokens, or coordinates in logs/diagnostics (`AB-LEP-002`).
- Zero concurrent OAuth token refreshes outside `ctx.stato.lock_token` (`AB-LEP-001`, `AB-LEP-004`).
- Fail-open capability gating: missing permission IDs or network errors NEVER hide entities; only explicit `0` disables a feature.
- Preserve all existing English `entity_id`s in Home Assistant (`naming.py` / `CANON_ENTITY_ID`).
- Test runner (Master only): `.venv/bin/pytest -q --tb=short --maxfail=2` and `uv run ruff check custom_components/ tests/`.

---

### Domain Skills & Sub-Agent Roster

| Dominio Coeso | Worker / Tipo | Model | Skill Primaria + Companions | File Assegnati (Contratto End-to-End) |
| :--- | :--- | :--- | :--- | :--- |
| **VIN Capabilities, Registry Cleanup, State Restore & Sensors** | `ha_caps_entities_worker` | `pro` (file `>600L` + `>=3` file interdipendenti) | `python-development`, `ponytail`, `antislop-code` | `custom_components/lepas/const.py`, `custom_components/lepas/__init__.py`, `custom_components/lepas/config_flow.py`, `custom_components/lepas/coordinator.py`, `custom_components/lepas/diagnostics.py`, `custom_components/lepas/device_tracker.py`, `custom_components/lepas/binary_sensor.py`, `custom_components/lepas/sensor.py`, `custom_components/lepas/switch.py`, `custom_components/lepas/cover.py`, `custom_components/lepas/lock.py`, `custom_components/lepas/climate.py`, `custom_components/lepas/number.py`, `custom_components/lepas/button.py`, `tests/test_vin_features.py`, `tests/test_sensors.py` |
| **Translations & Nomenclature Alignment** | `ha_translations_worker` | `flash` (JSON + test locale, file `<600L`, zero overlap) | `python-development`, `ponytail`, `antislop-code` | `custom_components/lepas/strings.json`, `custom_components/lepas/translations/en.json`, `custom_components/lepas/translations/it.json`, `custom_components/lepas/translations/nl.json`, `tests/test_traduzioni_complete.py` |

---

### Blast Radius & StateGraph

- **`direct_files`:** `const.py`, `__init__.py`, `config_flow.py`, `coordinator.py`, `diagnostics.py`, `device_tracker.py`, `binary_sensor.py`, `sensor.py`, `switch.py`, `cover.py`, `lock.py`, `climate.py`, `number.py`, `button.py`, `strings.json`, `translations/{en,it,nl}.json`, `tests/test_vin_features.py`, `tests/test_sensors.py`, `tests/test_traduzioni_complete.py`.
- **`transitively_affected`:** `core/permessi.py` (consumer of `ctx.permessi`), `entity.py` (`LepasEntity` / `in_zona_casa` / `car_zone`), `tests/test_capabilities_scheda.py`, `tests/test_permessi.py`, `tests/test_diagnostics.py`, `tests/test_repo_hygiene.py`.
- **`uncertain`:** Live reload on Home Assistant after `DATA_CAPS_PROBED_V3` backfill (verified post-implementation only upon explicit user consent for deploy + `ha_restart`).
- **`StateGraph`:**
  - `async_ensure_vehicle_identity` (`coordinator.py`):
    - `onSuccess`: persists `DATA_CAPS_PROBED_V3 = True` and `DATA_VEHICLE_FEATURES` via `async_update_entry`, updates `self._ctx.permessi` under existing context object (no `CoreCtx` replacement), removes newly confirmed-`False` entities from `entity_registry`, and calls `async_schedule_reload` once if any feature is `False`.
    - `onFailure`: if `permessi.leggi()` returns `IGNOTO` (`{}`) or network fails, does NOT mark missing keys as `False` (`vehicle_features` empty or omitted), logs at `DEBUG`, never blocks setup or raises.
  - `async_cleanup_disabled_entities` (`__init__.py`):
    - `onSuccess`: iterates only `er.async_entries_for_config_entry(reg, entry.entry_id)`, removes entries whose `(domain, suffix)` maps in `ENTITY_FEATURE_MAP` to a feature explicitly `False` in `entry.data[DATA_VEHICLE_FEATURES]`.
    - `onFailure`: wrapped in `try/except Exception` logging warning without blocking `async_setup_entry`.
  - `LepasCoordinator.restore_position` (`coordinator.py`):
    - `onSuccess`: acquires `self._state_lock`; if `self.position is None and self.data.get("position") is None`, stores `{"lat": lat, "lon": lon}` and emits `self._update({"position": {"lat": lat, "lon": lon}})` (preserving `last_pos_fix = None`).
    - `onFailure`: invalid non-float coordinates ignored safely before lock acquisition; lock always released on scope exit.

---

### Task 1: VIN Features Extraction, Persistence & Diagnostics (`const.py`, `config_flow.py`, `coordinator.py`, `diagnostics.py`)

**Files:**
- Modify: `custom_components/lepas/const.py`
- Modify: `custom_components/lepas/config_flow.py`
- Modify: `custom_components/lepas/coordinator.py`
- Modify: `custom_components/lepas/diagnostics.py`
- Create: `tests/test_vin_features.py`

**Interfaces:**
- Produces in `const.py`:
  - `DATA_CAPS_PROBED_V3 = "caps_probed_v3"`
  - `DATA_VEHICLE_FEATURES = "vehicle_features"`
  - `ENTITY_FEATURE_MAP: dict[tuple[str, str], str]`
  - `features_from_permissions(perms: dict[int, int] | None) -> dict[str, bool]`
- Produces in `coordinator.py`:
  - `LepasCoordinator.feature_enabled(self, feature: str) -> bool`

- [ ] **Step 1: Write failing falsifiable tests in `tests/test_vin_features.py`**

```python
from custom_components.lepas.const import (
    DATA_CAPS_PROBED_V2,
    DATA_CAPS_PROBED_V3,
    DATA_VEHICLE_FEATURES,
    ENTITY_FEATURE_MAP,
    features_from_permissions,
)

def test_features_fail_open_on_empty_or_none():
    assert features_from_permissions(None) == {}
    assert features_from_permissions({}) == {}

def test_features_lepas_l8_real_profile():
    # Real 308-permission pattern: 208/215/220/401/2145-2148 = 0; 207/2045/213/2141-2144/232 = 1
    perms = {
        202: 1, 203: 1, 204: 1, 205: 1, 206: 1, 207: 1, 209: 1, 210: 1,
        213: 1, 214: 1, 232: 1, 2045: 1, 2046: 1,
        2141: 1, 2142: 1, 2143: 1, 2144: 1,
        208: 0, 2081: 0, 2082: 0,
        215: 0, 2151: 0, 20416: 0,
        220: 0, 2201: 0, 2202: 0,
        401: 0, 4011: 0,
        2145: 0, 2146: 0, 2147: 0, 2148: 0,
        20412: 0, 20413: 0, 20414: 0, 20415: 0,
    }
    vf = features_from_permissions(perms)
    assert vf["steering_wheel_heating"] is False
    assert vf["front_windshield_electric"] is False
    assert vf["instant_charging"] is False
    assert vf["alarm"] is False
    assert vf["rear_left_seat_heating"] is False
    assert vf["rear_right_seat_ventilation"] is False
    assert vf["rear_center_seat"] is False
    assert vf["sunroof"] is True
    assert vf["front_windshield_defog"] is True
    assert vf["driver_seat_heating"] is True

def test_features_uk_profile_enables_electric_windshield_and_wheel():
    perms = {208: 1, 2081: 1, 215: 1, 2151: 1, 214: 1, 2145: 1, 401: 1}
    vf = features_from_permissions(perms)
    assert vf["steering_wheel_heating"] is True
    assert vf["front_windshield_electric"] is True
    assert vf["rear_left_seat_heating"] is True
    assert vf["rear_center_seat"] is True
    assert vf["alarm"] is True

def test_features_partial_perms_fail_open():
    # Missing keys are never treated as False
    vf = features_from_permissions({208: 0})
    assert vf == {"steering_wheel_heating": False}
    assert vf.get("alarm", True) is True

async def test_ensure_vehicle_identity_v3_branches(hass, monkeypatch):
    from custom_components.lepas.coordinator import LepasCoordinator
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain="lepas", data={"vin": "VIN123", "caps_probed_v2": True}, entry_id="e1")
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    hass.data.setdefault("lepas", {})["e1"] = coord
    ctx_orig = coord.ctx

    reloads = []
    monkeypatch.setattr(hass.config_entries, "async_schedule_reload", lambda eid: reloads.append(eid))
    monkeypatch.setattr(coord, "_fetch_vehicle_identity", lambda: {"caps_probed_v2": True})
    await coord.async_ensure_vehicle_identity()
    assert not entry.data.get(DATA_CAPS_PROBED_V3)
    assert reloads == []

    coord._probed_permessi = {208: 0, 207: 1}
    monkeypatch.setattr(coord, "_fetch_vehicle_identity", lambda: {DATA_CAPS_PROBED_V3: True, DATA_VEHICLE_FEATURES: {"steering_wheel_heating": False, "sunroof": True}})
    await coord.async_ensure_vehicle_identity()
    assert entry.data.get(DATA_CAPS_PROBED_V3) is True
    assert coord.ctx is ctx_orig
    assert coord.ctx.permessi == {208: 0, 207: 1}
    assert reloads == ["e1"]

def test_v3_marker_distinct_from_v2():
    assert DATA_CAPS_PROBED_V3 != DATA_CAPS_PROBED_V2
```

- [ ] **Step 2: Implement `features_from_permissions`, `ENTITY_FEATURE_MAP`, `DATA_CAPS_PROBED_V3`, `DATA_VEHICLE_FEATURES` in `custom_components/lepas/const.py`**
  Use a table `_FEATURE_RULES: dict[str, tuple[int | None, tuple[int, ...]]]` where `(req_cat, fallback_or_any_ids)` matches Spec §1.2 1:1 via one shared evaluator:
  - If `req_cat is not None`: if `req_cat not in perms`, omit (fail-open); if `perms[req_cat] == 1`, `out[feat] = True`; else (`perms[req_cat] == 0`), `out[feat] = any(perms.get(i) == 1 for i in any_ids)`.
    - Examples: `"front_windshield_electric": (215, (20416,))`, `"rear_window_heating": (232, (20411,))`, `"steering_wheel_heating": (208, ())`, `"instant_charging": (220, ())`, `"scheduled_charging": (213, ())`, `"alarm": (401, ())`, `"sunroof": (207, ())`, `"windows": (206, ())`, `"trunk": (205, ())`, `"locks": (203, ())`, `"find_car": (202, ())`, `"climate": (204, ())`, `"heat_everything": (209, ())`.
  - If `req_cat is None`: collect `vals = [perms[i] for i in any_ids if i in perms]`; if `vals` non-empty, `out[feat] = any(v == 1 for v in vals)` (otherwise omit for fail-open).
    - Examples: `"cool_everything": (None, (210, 204))`, `"front_windshield_defog": (None, (2045,))`, `"air_purification": (None, (2046,))`, `"driver_seat_heating": (None, (2141, 2047))`, `"driver_seat_ventilation": (None, (2143, 2049))`, `"passenger_seat_heating": (None, (2142, 2048))`, `"passenger_seat_ventilation": (None, (2144, 20410))`, `"rear_left_seat_heating": (None, (2145, 20412))`, `"rear_left_seat_ventilation": (None, (2147, 20414))`, `"rear_right_seat_heating": (None, (2146, 20413))`, `"rear_right_seat_ventilation": (None, (2148, 20415))`, `"rear_center_seat": (None, (2145, 2146, 2147, 2148))`.
  - Populate `ENTITY_FEATURE_MAP` mapping every gated `(domain, unique_suffix)` (using the exact `LepasEntity` `unique_suffix`, e.g. `("switch", "steerWheelHeating")`, `("switch", "disappannamento_parabrezza")`, `("switch", "ricarica")`, `("switch", "raffredda_tutto")`, `("switch", "riscalda_tutto")`, `("switch", "antifurto")`, `("button", "cmd_antifurto_on")`, `("sensor", "mSeatHeatingState2")`, `("cover", "tetto")`).

- [ ] **Step 3: Update `coordinator.py`, `config_flow.py`, and `diagnostics.py`**
  - In `coordinator.py`:
    - Add `feature_enabled(self, feature: str) -> bool`: reads `(self.entry.data.get(DATA_VEHICLE_FEATURES) or {}).get(feature, True)`.
    - In `_fetch_vehicle_identity(self)`: call `token, tuid_login = wake._bff_login(ctx)` (returning `(userToken, tUserId)` as in `config_flow.py:127` and `commands.py:1046`), resolve `tuid = wake._valid_tuserid(getattr(self, "tuserid", "")) or wake._valid_tuserid(tuid_login) or wake._resolve_tuserid(ctx)`, guard `if token and tuid:` (`AB-LEP-003`) before calling `perms = permessi.leggi(ctx, token, tuid)`, compute `vf = features_from_permissions(perms)`, set `caps[DATA_CAPS_PROBED_V3] = True` and `caps[DATA_VEHICLE_FEATURES] = vf` when `perms` is non-empty (so transient network errors retry cleanly on next boot), and stash `self._probed_permessi = perms`.
    - In `async_ensure_vehicle_identity(self)`: trigger on `not self.entry.data.get(DATA_CAPS_PROBED_V3)`; after `await self.hass.async_add_executor_job(...)`, guard `if self.entry.entry_id not in self.hass.data.get(DOMAIN, {}): return` (unload race protection) before mutating `entry.data` or scheduling reload; apply `self._ctx.permessi = self._probed_permessi` in-place if probed and `self._ctx is not None`; after `async_update_entry`, if any feature in `info.get(DATA_VEHICLE_FEATURES)` is `False`, call `await async_cleanup_disabled_entities(self.hass, self.entry)` and `self.hass.config_entries.async_schedule_reload(self.entry.entry_id)`.
  - In `config_flow.py`: add helper called inside `_discover` / `hass.async_add_executor_job` (never directly on the event loop, `AB-LEP-004`) to read `capabilities_from_item` + `features_from_permissions` during onboarding when available, fail-open if unavailable.
  - In `diagnostics.py`: add `"vehicle_features": entry.data.get(DATA_VEHICLE_FEATURES)` to `diag["vehicle"]`.

---

### Task 2: Platform Gating, Orphan Registry Cleanup & `sunroof_blind` Disabled Default

**Files:**
- Modify: `custom_components/lepas/__init__.py`
- Modify: `custom_components/lepas/binary_sensor.py`
- Modify: `custom_components/lepas/sensor.py`
- Modify: `custom_components/lepas/switch.py`
- Modify: `custom_components/lepas/cover.py`
- Modify: `custom_components/lepas/lock.py`
- Modify: `custom_components/lepas/climate.py`
- Modify: `custom_components/lepas/number.py`
- Modify: `custom_components/lepas/button.py`
- Modify: `tests/test_vin_features.py`

**Interfaces:**
- Consumes from Task 1: `ENTITY_FEATURE_MAP`, `DATA_VEHICLE_FEATURES`, `LepasCoordinator.feature_enabled(feature)`
- Produces in `__init__.py`: `async_cleanup_disabled_entities(hass: HomeAssistant, entry: ConfigEntry) -> int`

- [ ] **Step 1: Add failing HA integration tests in `tests/test_vin_features.py`**
  - Test with `MockConfigEntry` containing `DATA_VEHICLE_FEATURES = {"steering_wheel_heating": False, "alarm": False, "front_windshield_electric": False, "instant_charging": False, "rear_left_seat_heating": False, "rear_center_seat": False, "sunroof": True}`:
    - Excluded entities (`switch.lepas_steering_wheel_heating`, `switch.lepas_alarm`, `button.lepas_alarm_on`, `button.lepas_alarm_off`, `switch.lepas_windshield_defrost`, `switch.lepas_charging`, `switch.lepas_rear_left_seat_heating`, `sensor.lepas_rear_center_seat_heating`) are NOT in `hass.states`.
    - Enabled entities (`switch.lepas_windshield_defog`, `binary_sensor.lepas_windshield_heating`, `cover.lepas_sunroof`, `switch.lepas_driver_seat_heating`) ARE present.
    - `binary_sensor.lepas_sunroof_blind` in `entity_registry` has `disabled_by == RegistryEntryDisabler.INTEGRATION` (from `entity_registry_enabled_default = False`).
    - Pre-existing registry entry with real HA `unique_id` format `f"{vin}_antifurto"` (no `ID_PREFIX`, matching `entity.py:134`) belonging to `entry.entry_id` is removed by `async_cleanup_disabled_entities` (while entries of another `entry_id` are untouched), plus a suffix alignment test verifying every `(domain, suffix)` in `ENTITY_FEATURE_MAP` matches actual suffixes registered on platforms (`ricarica`, `disappannamento_parabrezza`, `raffredda_tutto`, `riscalda_tutto`, etc.).

- [ ] **Step 2: Implement `async_cleanup_disabled_entities` in `__init__.py` and call before `async_forward_entry_setups`**
  ```python
  async def async_cleanup_disabled_entities(hass: HomeAssistant, entry: ConfigEntry) -> int:
      vf = entry.data.get(DATA_VEHICLE_FEATURES) or {}
      if not isinstance(vf, dict) or not vf:
          return 0
      vin = str(entry.data.get(CONF_VIN, "")).strip().upper()
      if not vin:
          return 0
      reg = er.async_get(hass)
      removed = 0
      p_vin = f"{vin}_"
      p_pref = f"{ID_PREFIX}_{vin}_"
      for ent in list(er.async_entries_for_config_entry(reg, entry.entry_id)):
          uid = ent.unique_id
          if uid.startswith(p_pref):
              suffix = uid[len(p_pref):]
          elif uid.startswith(p_vin):
              suffix = uid[len(p_vin):]
          else:
              continue
          feat = ENTITY_FEATURE_MAP.get((ent.domain, suffix))
          if feat and vf.get(feat) is False:
              reg.async_remove(ent.entity_id)
              removed += 1
      return removed
  ```

- [ ] **Step 3: Gate entity creation across platforms via `coord.feature_enabled(...)` and set `sunshadeState` `entity_registry_enabled_default = False`**
  - Helper strictly in `const.py` (never modifying `entity.py`): `entity_allowed(coord, domain: str, suffix: str) -> bool` using `ENTITY_FEATURE_MAP` + `coord.feature_enabled(feat)` so every platform uses the exact same Single Source of Truth!
  - `binary_sensor.py`: filter `SENSORS` via `entity_allowed(coord, "binary_sensor", s["key"])`; in `LepasBinarySensor.__init__`, if `self._key == "sunshadeState"`, set `self._attr_entity_registry_enabled_default = False`.
  - `sensor.py`: filter `SENSORS` via `entity_allowed(coord, "sensor", s["key"])`.
  - `switch.py`, `cover.py`, `lock.py`, `climate.py`, `number.py`, `button.py`: filter each constructed/candidate entity via `entity_allowed(coord, domain, suffix)` before `add(...)` (and in `switch.py`, do NOT instantiate `LepasTheftAlarmSwitch` or add it to `add(...)` if `not coord.feature_enabled("alarm")`).

---

### Task 3: `at_home` Position Restore, `remaining_charge_time` `0 min`, `"In attesa"` States

**Files:**
- Modify: `custom_components/lepas/coordinator.py`
- Modify: `custom_components/lepas/device_tracker.py`
- Modify: `custom_components/lepas/sensor.py`
- Modify: `tests/test_sensors.py`
- Modify: `tests/test_vin_features.py`

**Interfaces:**
- Produces in `coordinator.py`: `LepasCoordinator.restore_position(self, lat: float, lon: float) -> bool`
- Consumes in `device_tracker.py`: `self.coordinator.restore_position(lat, lon)`

- [ ] **Step 1: Write failing falsifiable tests in `tests/test_sensors.py` and `tests/test_vin_features.py`**
  - Update `tests/test_sensors.py::test_tempo_ricarica_sparisce_a_carica_finita` so after `_A_RIPOSO` (`chargeState="0"`), `hass.states.get(ent).state in ("0", "0.0")`, AND add assertion that when `chargeState="1"` with `remainChargeTime` absent, state is `"unknown"` (not `"0"`).
  - Test `LepasTextSensor` (`sensor.lepas_command_result`, `wake_up_result`, `location_probe_result`) and `sensor.lepas_sunroof_movement_state` start as `"In attesa"` (when `hass.config.language == "it"`) or `"Waiting"` (when `"en"`), then transition to live value when updated.
  - Test `LepasCoordinator.restore_position(lat, lon)` sets `coordinator.data["position"]` only when `position` is `None` (never overwrites a live `1301` position), and makes `binary_sensor.lepas_at_home` resolve `"on"`/`"off"` immediately at startup when `device_tracker.lepas_location` restores coordinates inside `zone.home`.

- [ ] **Step 2: Implement `restore_position` in `coordinator.py` and call it from `device_tracker.py`**
  - In `coordinator.py`:
    ```python
    def restore_position(self, lat: float, lon: float) -> bool:
        import math
        try:
            flat, flon = float(lat), float(lon)
        except (TypeError, ValueError):
            return False
        if not (math.isfinite(flat) and math.isfinite(flon) and -90.0 <= flat <= 90.0 and -180.0 <= flon <= 180.0):
            return False
        geo = {"lat": flat, "lon": flon}
        with self._state_lock:
            if self.position is not None or self.data.get("position") is not None:
                return False
            self.position = dict(geo)
        self._update({"position": geo})
        return True
    ```
  - In `device_tracker.py` (`LepasTracker.async_added_to_hass`):
    ```python
    if self._restored_lat is not None and self._restored_lon is not None:
        self.coordinator.restore_position(self._restored_lat, self._restored_lon)
    ```

- [ ] **Step 3: Implement `0 min` and `"In attesa"`/`"Waiting"` in `sensor.py`**
  - Add helper `_waiting_text(hass: HomeAssistant | None) -> str`:
    ```python
    def _waiting_text(hass: HomeAssistant | None) -> str:
        lang = (getattr(getattr(hass, "config", None), "language", None) or "it").split("-")[0].lower()
        return "In attesa" if lang == "it" else "Waiting"
    ```
  - In `LepasRealtimeSensor.native_value`:
    ```python
    if self._spec.volatile:
        live = self._live_value()
        if live is not None:
            return live
        # _rt() is defined at sensor.py:403
        if self._spec.field == "remainChargeTime" and not _in_ricarica(_rt(self.coordinator, "chargeState")):
            return 0
        return None
    ```
  - In `LepasTextSensor.native_value`:
    ```python
    live = self._live_value()
    return live if live is not None else _waiting_text(self.hass)
    ```
  - In `LepasFieldSensor.native_value`:
    ```python
    @property
    def native_value(self):
        val = super().native_value
        if val is None and self._key == "sunroofMoveState":
            return _waiting_text(self.hass)
        return val
    ```

---

### Task 4: Fix `strings.json` & Align Nomenclature (`strings.json`, `translations/{en,it,nl}.json`)

**Files:**
- Modify: `custom_components/lepas/strings.json`
- Modify: `custom_components/lepas/translations/en.json`
- Modify: `custom_components/lepas/translations/it.json`
- Modify: `custom_components/lepas/translations/nl.json`
- Modify: `tests/test_traduzioni_complete.py`

**Interfaces:**
- Zero key additions/removals; only `"name"` values updated under `"entity"`.

- [ ] **Step 1: Add falsifiable parity test in `tests/test_traduzioni_complete.py`**
  - Assert `strings["entity"] == en["entity"]` (catches any untranslated Italian string left in `strings.json` and any drift between `strings.json` and `en.json`).

- [ ] **Step 2: Update `strings.json`, `translations/en.json`, `translations/it.json`, `translations/nl.json`**
  - `strings.json` & `translations/en.json`:
    - `binary_sensor.at_home.name`: `"At home"`
    - `sensor.home_charging_energy.name`: `"Home charging energy"`
    - `sensor.away_charging_energy.name`: `"Away charging energy"`
    - `switch.windshield_defrost.name`: `"Heated windshield"`
    - `binary_sensor.windshield_heating.name`: `"Windshield defog status"`
    - `binary_sensor.tailgate_moving.name`: `"Trunk moving"`
    - Keep `binary_sensor.charging_cable.name` = `"Charging cable"`, `sensor.hv_battery_voltage.name` = `"HV battery voltage"`, `sensor.hv_battery_current.name` = `"HV battery current"` consistent in both `strings.json` and `en.json`.
  - `translations/it.json`:
    - `switch.windshield_defrost.name`: `"Sbrinamento elettrico parabrezza"`
    - `binary_sensor.windshield_heating.name`: `"Disappannamento parabrezza (stato)"`
    - `binary_sensor.tailgate_moving.name`: `"Baule in movimento"`
    - `binary_sensor.charging_cable.name`: `"Cavo di ricarica"`
    - `sensor.hv_battery_voltage.name`: `"Tensione alta tensione"`
    - `sensor.hv_battery_current.name`: `"Corrente alta tensione"`
  - `translations/nl.json`:
    - Align `switch.windshield_defrost.name` (`"Voorruitverwarming"`), `binary_sensor.windshield_heating.name` (`"Voorruitontwaseming (status)"`), `binary_sensor.tailgate_moving.name` (`"Kofferbak beweegt"`), preserving existing Dutch translations for the rest.

---

### Task 5: Master Verification & Dual-Gate Code Audit
- [ ] Run `.venv/bin/pytest -q --tb=short --maxfail=2`
- [ ] Run `uv run ruff check custom_components/ tests/` and `uv run ruff format --check custom_components/ tests/`
- [ ] Run `python3 /home/federico/skills_library/scripts/local_llm_offload.py --task review-hygiene --files ... --json`
- [ ] Run Sentinel Pass 2 (`Model: 'inherit'`, reuse Stage 2 CID via `send_message`) and record `APPROVED_TREE=$(git write-tree)`
- [ ] Ask user before any deploy to live Home Assistant (`ha_write_file` + `ha_restart`) or Git commit/push/tag (`v1.17.0`).
