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

## Phase 1: Chery EU / `com.chery.eu.lepas` API Discovery & Auth Flow
- [ ] Decompilation and static traffic analysis of `com.chery.eu.lepas` APK package:
  - Identify base API domains and regional EU gateway endpoints.
  - Extract cryptographic signing keys, headers, and request signature algorithms (HMAC / timestamp / nonce).
  - Map network security configuration and TLS pinning parameters.
- [ ] Authentication and Session Reverse Engineering:
  - Document user credential login exchange (phone/email + password + SMS/MFA if present).
  - Document token issuance format (JWT access token + refresh token rotation mechanism).
  - Characterize session expiry intervals and refresh request schema.
- [ ] Endpoint and Telemetry Schema Mapping:
  - Vehicle status querying: battery SoC, remaining electric/fuel range, odometer, tire pressure.
  - State boundaries: door locks, windows, trunk/hood closures, charging state.
  - Remote control commands: lock, unlock, climate start/stop, defrost, seat heating, charging toggle.
  - GPS tracking telemetry schema.

---

## Phase 2: Async Python API Client & Unit Tests
- [ ] Standalone asynchronous Python client (`custom_components/lepas/api.py` or separate package):
  - Session injection accepting standard `aiohttp.ClientSession`.
  - Serialized token refresh mechanism guarded by `asyncio.Lock`.
  - Exponential backoff with jitter on HTTP 429 and transient 5xx server responses.
  - Strong typed data models for telematics states using Python standard `dataclasses`.
- [ ] Unit Test Suite (`tests/`):
  - Mocked HTTP fixtures for authentication success, expired token renewal, and invalid credential handling.
  - Serialization tests verifying no parallel refresh calls are emitted.
  - Error translation tests mapping HTTP status codes to domain-specific exceptions.

---

## Phase 3: Home Assistant Custom Integration MVP & HACS Packaging
- [ ] Integration Core Setup:
  - `manifest.json` with domain `lepas`, requirements, and code owners.
  - `config_flow.py` supporting user login, MFA/challenge handling, and multi-vehicle selection.
  - `__init__.py` handling `async_setup_entry`, `async_unload_entry`, and platform forwarding.
  - `coordinator.py` implementing adaptive polling intervals (driving/charging vs. sleeping).
- [ ] Entity Platform Implementations:
  - `sensor.py`: SoC, range, odometer, tire pressures.
  - `binary_sensor.py`: Doors, trunk, charging connection status.
  - `device_tracker.py`: Real-time vehicle GPS location.
  - `lock.py`: Remote door lock and unlock control.
  - `switch.py`: Charging control switch.
  - `climate.py`: Cabin HVAC pre-conditioning.
- [ ] Security & HACS Compliance:
  - `diagnostics.py` implementing strict VIN and token masking.
  - HACS validation (`hacs.json`) and branding asset preparation for Home Assistant Brands.
