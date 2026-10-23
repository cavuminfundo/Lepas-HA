# Architectural Design Specification: Lepas Connect Home Assistant Integration

> **Document ID**: `SPEC-2026-10-23-LEPAS-CHERY-CONNECT`  
> **Status**: Approved (Final Rebranded Native Architecture)  
> **Target Integration Directory**: `custom_components/lepas`  
> **Integration Domain**: `lepas` (`Lepas Connect`)  
> **Target Vehicle Platform**: Lepas L8 / Chery Europe (`com.chery.eu.lepas`)

---

## 1. Architectural Vision & Systemic Rebranding

### 1.1 From Upstream Fork to Dedicated Lepas Integration
The integration is derived from the battle-tested Chery Connect codebase, systematically established as a first-class, standalone Home Assistant custom component for **Lepas**:
- **Package Path**: `custom_components/lepas/`
- **Domain Identifier**: `DOMAIN = "lepas"`
- **Component Display Name**: `"Lepas Connect"`
- **Integration Manifest (`custom_components/lepas/manifest.json`)**:
  - `domain`: `"lepas"`
  - `name`: `"Lepas Connect"`
  - `documentation`: `"https://github.com/chery-connect-ha/lepas-ha"`
  - `issue_tracker`: `"https://github.com/chery-connect-ha/lepas-ha/issues"`
  - `codeowners`: `["@Caslinovich"]`
  - `requirements`: `["paho-mqtt>=2.0", "pycryptodome>=3.17", "numpy>=1.21"]`
  - `dependencies`: `["http"]`
  - `after_dependencies`: `["recorder"]`
  - `version`: `"1.15.0"`
- **HACS Manifest (`hacs.json`)**: Updated to `"Lepas Connect"`, pointing to `custom_components/lepas`.

### 1.2 Class, Module, and Frontend Rebranding Matrix
All identifiers, module paths, and class names are harmonized under the `Lepas` namespace:

| Upstream / Legacy Construct | Rebranded Lepas Construct | Purpose / Responsibilities |
|---|---|---|
| Legacy component directory | `custom_components/lepas/` | Root component directory |
| Legacy config flow | `LepasConfigFlow` | Authentication and setup flow |
| Legacy options flow | `LepasOptionsFlow` | Options and telematics poll reconfiguration |
| Legacy coordinator | `LepasCoordinator` | Vehicle polling and telemetry update coordinator |
| Legacy entity | `LepasEntity` | Base entity class with device linkage |
| Legacy optimistic mixin | `LepasOptimisticMixin` | Actuator optimistic state coordinator |
| Legacy login | `core/login_lepas.py` | Cloud login endpoints and OTP validation |
| Legacy client | `core/lepas.py` | Core MQTT client and frame orchestrator |
| Legacy auth | `core/lepas_auth.py` | Token management and crypto signature handler |
| `lovelace/chery-card.js` | `lovelace/lepas-card.js` | Dedicated Lovelace UI card |
| `services.yaml` | `services.yaml` | Domain-scoped services under `lepas.*` |

---

## 2. Dynamic Vehicle Auto-Discovery (Zero Static Presets)

### 2.1 YAGNI & Ponytail Ladder Enforcement
In accordance with the **Ponytail Ladder**, we explicitly reject maintaining a static hardcoded table or dictionary of vehicle models/trims. Static model registries create maintenance debt, require constant component updates for new factory releases, and risk drifting from actual vehicle specifications.

### 2.2 100% Dynamic Discovery Pipeline
All vehicle identification and capability parameters are discovered dynamically at runtime:
1. **Cloud Identity Discovery (`_discover` / `queryList`)**:
   - `seriesName`: Vehicle series returned by Chery Cloud (e.g. `"Lepas"`).
   - `modelName`: Precise vehicle model (e.g. `"L8"`).
   - `vehicleName`: User-assigned nickname from the companion app profile.
   - `powerType`: Fuel/propulsion type (`0` = BEV, other = PHEV/ICE).
   - `minTemperature`, `maxTemperature`, `temperatureStepLength`, `isHaveLoAndHi`, `loValue`, `hiValue`: Exact HVAC capabilities declared by the vehicle firmware.
   - `maxAirDuration`: Permitted remote climate durations declared by the TCU.
2. **Realtime Telemetry Ingestion (T-Box `5A02` Protocol)**:
   - High-voltage battery SoC, electric range, fuel level, odometer, tire pressure, and lock/window/door states are parsed directly from live CAN-bus frames relayed through MQTT.
3. **Single Generic Fallback**:
   - In `naming.py` and `coordinator.py`, `DEFAULT_VEHICLE_NAME` is set strictly to:
     ```python
     DEFAULT_VEHICLE_NAME = "Lepas"
     ```
   - When a vehicle is first added or if the cloud is offline before the first `queryList` returns, the device is named `"Lepas ({last_4_vin})"`. It is dynamically enriched to the specific model (e.g., `"Lepas L8"`) immediately upon receiving cloud metadata.

---

## 3. Default Configuration & Preset Alignment

### 3.1 Default Constants (`custom_components/lepas/const.py`)
Because this repository is dedicated to Lepas, the default target region and gateway parameters point directly to **Lepas Europe**:

```python
CONF_BFF = "bff"
CONF_TSP_HOST = "tsp_host"
CONF_CAR_MQTT_HOST = "car_mqtt_host"
CONF_CAR_MQTT_PORT = "car_mqtt_port"
CONF_CHANNEL_ID = "channel_id"
CONF_TENANT_CODE = "tenant_code"
CONF_COUNTRY_ID = "country_id"

CONF_PRESET = "preset"
PRESET_LEPAS_EU = "lepas_eu"
PRESET_CHERY_EU = "chery_eu"
PRESET_CUSTOM = "custom"
DEFAULT_PRESET = PRESET_LEPAS_EU

DEFAULTS = {
    CONF_BFF: "https://eu-lepas.cheryinternational.com/api",
    CONF_TSP_HOST: "https://tspconsole-eu.cheryinternational.com",
    CONF_CAR_MQTT_HOST: "tspemqx-app-eu.cheryinternational.com",
    CONF_CAR_MQTT_PORT: 8083,
    CONF_CHANNEL_ID: "1",
    CONF_TENANT_CODE: "3000011",
    CONF_COUNTRY_ID: "1",
}

PRESETS = {
    PRESET_LEPAS_EU: {
        CONF_BFF: "https://eu-lepas.cheryinternational.com/api",
        CONF_TENANT_CODE: "3000011",
        CONF_CHANNEL_ID: "1",
        CONF_COUNTRY_ID: "1",
    },
    PRESET_CHERY_EU: {
        CONF_BFF: "https://eu-chery.cheryinternational.com/api",
        CONF_TENANT_CODE: "300001",
        CONF_CHANNEL_ID: "2",
        CONF_COUNTRY_ID: "2",
    },
}
```

### 3.2 Config Flow Fix in `async_step_login_password`
In the upstream codebase, `_apply_preset` was executed in `async_step_login_email` and `async_step_login_phone`, but was missing in `async_step_login_password`. 

In `custom_components/lepas/config_flow.py`, `self._apply_preset(self._data)` is strictly invoked in `async_step_login_password` before authenticating via ROPC:
```python
async def async_step_login_password(self, user_input=None):
    if user_input is not None:
        self._data = dict(user_input)
        self._apply_preset(self._data)
        # Authentication proceeds with resolved Lepas BFF and tenant code...
```
This guarantees that:
1. `CONF_BFF`, `CONF_TENANT_CODE`, `CONF_CHANNEL_ID`, and `CONF_COUNTRY_ID` are properly injected when logging in with password.
2. `CONF_PRESET` is cleanly popped from `self._data` and never leaks into `entry.data`.

---

## 4. Localization & User Experience

### 4.1 Form Dropdown Options
In `_region_fields()` of `config_flow.py`, the dropdown prioritizes Lepas:
```python
SelectOptionDict(value=PRESET_LEPAS_EU, label="Lepas — Europe (default)"),
SelectOptionDict(value=PRESET_CHERY_EU, label="Chery — Europe"),
SelectOptionDict(value=PRESET_CUSTOM, label="Custom / other region (use fields below)"),
```

### 4.2 Language Consistency
- `strings.json` and `translations/{en,it,nl}.json` are fully updated:
  - Integration name: `"Lepas Connect"`.
  - Step descriptions and guides refer to `"Lepas account"` as the primary platform, while retaining guidance for multi-tenant accounts.
  - Zero missing keys between `strings.json` and any translation file (`test_traduzioni_complete.py` compliance).

---

## 5. TDD Verification & Quality Gates

The test suite in `tests/` is fully ported to target `custom_components.lepas`:
1. **`tests/test_config_flow.py`**:
   - `test_default_preset_is_lepas_eu`: Confirms `DEFAULT_PRESET == "lepas_eu"` and matches `DEFAULTS`.
   - `test_config_flow_password_applies_preset`: Confirms `login_password` step applies `PRESET_LEPAS_EU` parameters and strips `CONF_PRESET`.
   - `test_config_flow_email_applies_preset`: Confirms email login configures Lepas endpoints out of the box.
2. **`tests/test_routing.py` & `tests/test_command_routing.py`**:
   - Validates that command dispatching and response code classification operate under `DOMAIN = "lepas"`.
3. **`tests/test_traduzioni_complete.py`**:
   - Asserts 100% key parity across `strings.json`, `en.json`, `it.json`, `nl.json`.
   - Asserts every field rendered by `_region_fields` has an explicit label in all three languages.
4. **`tests/test_architecture.py` & `test_repo_hygiene.py`**:
   - Validates that no stale legacy module imports linger inside `custom_components/lepas`.

---

## 6. Security, Anti-Lockout, and Secrets Management

1. **Transient Password Handling**: Passwords supplied in `login_password` exist solely in memory during the initial token minting call; they are NEVER written to disk or stored in `entry.data`.
2. **Serialized Token Renewal**: Token refreshes are synchronized behind an `asyncio.Lock` in `core/session.py`.
3. **Anti-Lockout Protection (`core/pin_lockout.py`)**: Local counter tracking prevents exceeding the 5-attempt PIN threshold on Chery servers.
4. **Diagnostics Sanitization**: `diagnostics.py` masks VINs to `***XXXX` and scrubs tokens, passwords, and GPS coordinates.
