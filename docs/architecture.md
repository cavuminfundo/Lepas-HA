# Lepas — Architectural Vision & System Design

> **Target Integration**: Home Assistant Custom Integration (`custom_components/lepas`)  
> **Vehicle Model**: Lepas L8 (Chery Europe platform)  
> **Upstream Companion App**: `com.chery.eu.lepas`  
> **Archetype**: Backend (`python`, `homeassistant`)

---

## 1. High-Level Architecture

The Lepas workspace provides an asynchronous Python API client and Home Assistant custom integration to interact with Chery EU connected vehicle cloud services. It enables real-time telematics ingestion, state monitoring, and remote vehicle control for the Lepas L8.

```
┌────────────────────────────────────────────────────────┐
│                  Home Assistant Core                   │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │             custom_components/lepas              │  │
│  │                                                  │  │
│  │  ┌─────────────┐    ┌─────────────────────────┐  │  │
│  │  │ config_flow │    │ DataUpdateCoordinator   │  │  │
│  │  └──────┬──────┘    └────────────┬────────────┘  │  │
│  │         │                        │               │  │
│  │  ┌──────┴────────────────────────┴────────────┐  │  │
│  │  │ LepasApiClient (api.py)                    │  │  │
│  │  │ - Session reuse (async_get_clientsession)  │  │  │
│  │  │ - Token refresh lock & rate-limiting       │  │  │
│  │  └───────────────────────┬────────────────────┘  │  │
│  │                          │                       │  │
│  │  ┌───────────────────────┴────────────────────┐  │  │
│  │  │ Entities: sensor, binary_sensor, lock,     │  │  │
│  │  │           switch, climate, device_tracker  │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  └──────────────────────────┬───────────────────────┘  │
└─────────────────────────────┼──────────────────────────┘
                              │ HTTPS / REST (JWT Bearer)
                              ▼
┌────────────────────────────────────────────────────────┐
│            Chery EU Cloud Infrastructure               │
│          (com.chery.eu.lepas API Gateway)              │
│                                                        │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │ Auth / OAuth │   │ Telematics   │   │ Remote Cmd │  │
│  │ Token Service│   │ Vehicle State│   │ Execution  │  │
│  └──────────────┘   └──────────────┘   └────────────┘  │
└─────────────────────────────┬──────────────────────────┘
                              │ Cellular / TCU
                              ▼
┌────────────────────────────────────────────────────────┐
│                   Lepas L8 Vehicle                     │
└────────────────────────────────────────────────────────┘
```

---

## 2. Directory Layout & Subsystem Responsibilities

```
Lepas/
├── .agents/
│   ├── AGENTS.md                  ← Agent router, quality gates, and rules
│   └── memory/
│       └── lessons.md             ← Discovered context and telemetry invariants
├── docs/
│   ├── architecture.md            ← System architecture and topology
│   ├── roadmap.md                 ← Development milestones and phases
│   └── code-implementation.md     ← Low-level technical constraints
├── custom_components/
│   └── lepas/
│       ├── __init__.py            ← Entry setup, unload, and coordinator attachment
│       ├── manifest.json          ← Integration metadata, domain, and dependencies
│       ├── const.py               ← Domain string constants and configuration keys
│       ├── config_flow.py         ← User authentication flow and options handler
│       ├── coordinator.py         ← DataUpdateCoordinator managing polling cycles
│       ├── api.py                 ← Pure async Chery EU cloud client
│       ├── diagnostics.py         ← Redacted diagnostics export for debugging
│       ├── sensor.py              ← Numerical entities (battery SoC, range, fuel, odometer)
│       ├── binary_sensor.py       ← Boolean entities (doors, windows, trunk, charging status)
│       ├── device_tracker.py      ← Vehicle GPS coordinate reporting
│       ├── lock.py                ← Remote vehicle door lock and unlock entity
│       ├── switch.py              ← Toggle entities (charging switch, seat heaters)
│       └── climate.py             ← HVAC pre-conditioning and cabin temperature target
├── pyproject.toml                 ← Python packaging and dev dependencies
├── README.md                      ← Workspace overview
└── tests/                         ← Automated pytest suite
```

---

## 3. Subsystem Breakdown

### 3.1 Cloud API Client Layer (`api.py`)
- **Transport**: Uses Home Assistant's managed `aiohttp.ClientSession` via `async_get_clientsession(hass)`.
- **Authentication**: JWT bearer token with automated renewal via dedicated refresh endpoints. Token renewal calls are serialized under an `asyncio.Lock` to avoid token invalidation race conditions.
- **Payload Normalization**: Unpacks raw JSON responses from Chery EU endpoints and maps them to strongly typed internal data structures (`LepasVehicleState`, `LepasBatteryState`, `LepasLocation`).

### 3.2 Data Coordinator (`coordinator.py`)
- Extends `homeassistant.helpers.update_coordinator.DataUpdateCoordinator`.
- **Dynamic Cadence**: Polling cadence adjusts automatically:
  - 30–60 seconds when ignition is active or charging is in progress.
  - 15–30 minutes when parked and stationary, protecting the vehicle's 12V battery from drain.
- **Failure Resilience**: Handles 429 Rate Limit and transient network drops without discarding existing entity state.

### 3.3 Home Assistant Entity Platforms
- **`sensor.py`**:
  - High-Voltage Battery SoC (`%`)
  - Estimated Electric & Fuel Range (`km`)
  - Total Odometer (`km`)
  - Tire Pressures (Front-Left, Front-Right, Rear-Left, Rear-Right in `bar`/`kPa`)
  - 12V Battery Voltage (`V`)
- **`binary_sensor.py`**:
  - Door status (Driver, Passenger, Rear-Left, Rear-Right)
  - Trunk & Hood closure status
  - Charging cable connection status & charging active state
- **`device_tracker.py`**:
  - GPS latitude, longitude, and accuracy from TCU telematics.
- **`lock.py`**:
  - Remote central door lock control with confirmation state.
- **`switch.py`**:
  - Instant charging initiation/pause switch.
  - Cabin pre-conditioning presets.
- **`climate.py`**:
  - Target cabin temperature setting, HVAC power, and front/rear window defrost.

### 3.4 Device Registry Topology
Every vehicle associated with the Chery EU account is mapped to a distinct Home Assistant Device:
- **Identifiers**: `{(DOMAIN, vehicle_vin)}`
- **Manufacturer**: Chery / Lepas
- **Model**: Lepas L8
- **Name**: User-assigned vehicle nickname or "Lepas L8 ({last_4_vin})"
- **Configuration URL**: Chery EU customer portal / account page
