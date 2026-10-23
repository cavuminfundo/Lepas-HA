# Lepas — Project Roadmap & Milestones

> **Target Platform**: Lepas L8 (`com.chery.eu.lepas` / Chery EU)  
> **Target Integration**: Home Assistant Custom Integration (`custom_components/lepas`)

---

## Phase 0: Workspace Scaffolding & Golden Rules (✅ Completed)
- [x] Initial repository structure and workspace doctor verification (`workspace_doctor.py`).
- [x] VCS exclusions: `.gitignore` and `.stignore` configured for virtualenvs, caches, secrets, and APK captures.
- [x] Archetype classification: `backend` (`python`, `homeassistant`) registered via `pyproject.toml`.
- [x] Agent router configuration: `.agents/AGENTS.md` with Ponytail Ladder, Antislop, Zero Secrets, and SDD rules.
- [x] Lessons learned repository initialized: `.agents/memory/lessons.md` with Chery EU context.
- [x] Comprehensive architectural and implementation specifications.

---

## Phase 1: Chery EU / `com.chery.eu.lepas` API Discovery & Auth Flow (✅ Completed)
- [x] Decompilation and static traffic analysis of `com.chery.eu.lepas` APK package:
  - Base API domain and regional EU gateway endpoints identified (`https://eu-lepas.cheryinternational.com/api`, Tenant `3000011`, Channel `1`, Country `1`).
  - Cryptographic signing keys, TSP console host, and mTLS client certificate bundle mapped.
  - Network security configuration and TLS pinning parameters verified.
- [x] Authentication and Session Reverse Engineering:
  - Documented login exchange (Email OTP, SMS OTP, and Username/Password via ROPC).
  - Token issuance format (JWT access token + refresh token rotation mechanism).
  - Session expiry intervals and serialized refresh request schema.
- [x] Endpoint and Telemetry Schema Mapping:
  - Vehicle status querying: battery SoC, remaining electric/fuel range, odometer, tire pressure.
  - State boundaries: door locks, windows, trunk/hood closures, charging state.
  - Remote control commands: lock, unlock, climate start/stop, defrost, seat heating, charging toggle.
  - GPS tracking telemetry schema.

---

## Phase 2: Async Python API Client & Unit Tests (✅ Completed)
- [x] Asynchronous Python client implementation (`custom_components/lepas/core/`):
  - Session injection accepting standard `aiohttp.ClientSession`.
  - Serialized token refresh mechanism guarded by `asyncio.Lock` in `session.py`.
  - Exponential backoff with jitter on HTTP 429 and transient 5xx server responses.
  - Strong typed data models for telematics states using Python standard `dataclasses`.
- [x] Unit Test Suite (`tests/`):
  - Mocked HTTP fixtures for authentication success, expired token renewal, and invalid credential handling.
  - Serialization tests verifying no parallel refresh calls are emitted.
  - Error translation tests mapping HTTP status codes to domain-specific exceptions.

---

## Phase 3: Home Assistant Custom Integration & Rebranding (✅ Completed)
- [x] Systemic Rebranding to `custom_components/lepas`:
  - `DOMAIN = "lepas"` and integration named `"Lepas Connect"`.
  - Complete rename of all classes (`LepasConfigFlow`, `LepasOptionsFlow`, `LepasCoordinator`, `LepasEntity`, `LepasOptimisticMixin`).
  - Core modules restructured: `core/login_lepas.py`, `core/lepas.py`, `core/lepas_auth.py`, `lovelace/lepas-card.js`.
- [x] Native Defaults & Preset Configuration:
  - `DEFAULT_PRESET = PRESET_LEPAS_EU` with `DEFAULTS` pointing to Lepas Europe endpoints.
  - Config flow fix: `self._apply_preset(self._data)` wired in `async_step_login_password`.
- [x] Entity Migration & Prefix Normalization:
  - `ID_PREFIX = "lepas"` established as default.
  - Support for prefix normalization in `_async_migrate_entity_ids` and `entity.py` to prevent orphaned entities across upgrades.
- [x] Entity Platform Implementations:
  - `sensor.py`: SoC, range, odometer, tire pressures.
  - `binary_sensor.py`: Doors, trunk, charging connection status.
  - `device_tracker.py`: Real-time vehicle GPS location.
  - `lock.py`: Remote door lock and unlock control.
  - `switch.py`: Charging control switch, seat/wheel heaters.
  - `climate.py`: Cabin HVAC pre-conditioning.
- [x] Quality Gates & Packaging:
  - Full test suite passing 100% (730/730 tests passed).
  - HACS compliance manifest (`hacs.json`).
  - Diagnostics with strict VIN and token masking.

---

## Phase 4: Field Testing & Live Vehicle Validation (Current Focus)
- [ ] Field verification with live Lepas L8 vehicle account.
- [ ] Live telemetry push monitoring and CAN-bus parameter calibration.
