# Lepas Lessons Learned & Operational Knowledge Base

> **Metadata**:
> - **Workspace:** Lepas (`custom_components/lepas`)
> - **Target Vehicle:** Lepas L8 (Chery Europe platform)
> - **Companion App ID:** `com.chery.eu.lepas`
> - **Cloud Ecosystem:** Chery EU Connected Cloud Services
> - **Initialized:** 2026-10-23

---

## 2026-10-23 — Initial Platform Discovery & Scaffolding

### 1. Chery EU Cloud Ecosystem & App Identity (`com.chery.eu.lepas`)
- **Regional Isolation**: The European Chery connected vehicle infrastructure (`com.chery.eu.lepas`) is hosted on EU-compliant regional gateways, physically and logically isolated from Chinese (APAC) Chery endpoints. Endpoints, cryptographic sign keys, and auth flows must not be conflated with non-EU Chery apps.
- **TLS & Certificate Pinning**: Production Android releases of `com.chery.eu.lepas` enforce TLS pinning via OkHttp NetworkSecurityConfig. Traffic interception during reverse engineering requires Frida-based unpinning or custom CA injection into user certificate stores on rooted test environments.

### 2. Authentication Lifecycle & Refresh Serialization
- **Token Dualism**: The platform issues short-lived JWT access tokens accompanied by longer-lived refresh tokens.
- **Race Condition Guard**: Token refresh operations must be strictly serialized behind an `asyncio.Lock` in the API client. Simultaneous coordinator polls or user command dispatches during token expiration must await the same refresh task rather than triggering duplicate concurrent refresh requests that invalidate previous tokens.

### 3. Auxiliary 12V Battery Drain Prevention
- **Wake vs. Deep Sleep**: Actively polling vehicle telematics wakes the vehicle's telematics control unit (TCU) from low-power sleep mode, placing continuous drain on the auxiliary 12V battery.
- **Adaptive Polling**: Polling frequency must be dynamically adjusted:
  - Active (vehicle driving, ignition ON, or actively charging): 30–60 seconds.
  - Stationary / Parked / Sleep: 15–30 minutes, or rely on push notifications / cloud cache timestamps when available.
  - Never trigger active vehicle wake commands on routine coordinator update cycles.

### 4. PII & Sensitive Telemetry Redaction
- **VIN Handling**: The Vehicle Identification Number (VIN) is sensitive PII and a critical authorization identifier. All VINs must be redacted in diagnostics outputs (displaying only the last 4 characters, e.g., `***1234`) and excluded from debug logs.
- **Geographic Data**: GPS coordinates (`latitude`, `longitude`) must be treated as sensitive user location data and masked in public diagnostics payloads.

## 2026-10-23 — Entity Prefix Alignment & Registry Migration

### 5. `ID_PREFIX = "lepas"` Alignment and Registry Migration
- **Root Cause & Hazard**: When establishing the domain as `lepas`, changing `ID_PREFIX` in `naming.py` ensures all newly instantiated entities use `{platform}.lepas_{english_key}`. However, Home Assistant stores entity mappings in the Entity Registry (`er.EntityRegistry`) keyed by `unique_id`; without an active migration step, existing installations retain legacy `entity_id` values, while new installations receive the rebranded names, causing documentation divergence and breaking user automations.
- **Prefix Traversal**: In `_async_migrate_entity_ids` (`custom_components/lepas/__init__.py`), the migration loop normalizes entity IDs under `f"{DOMAIN}_"` (`lepas_`) when extracting `old_key` to map against `ENGLISH_KEYS`. This guarantees clean migration whether an entity originated with Italian legacy names or under an earlier transitional scheme.
- **Collision & History Guard**: Renaming via `reg.async_update_entity(voce.entity_id, new_entity_id=nuovo)` preserves recorder history and long-term statistics. If `nuovo` already exists in `reg.entities`, the migration skips the rename with a warning rather than failing silently, preventing recorder history corruption.

## 2026-10-23: HACS Direct Repository Download & GitHub Remote Alignment

1. **Removed zip_release/filename from hacs.json**: Updated the `hacs.json` file to remove the `zip_release/filename` entry. This change allows HACS to download the `custom_components/lepas` directly from the branch or tags on the `cavuminfundo/Lepas-HA` repository, eliminating the need for a zip release asset.

2. **Use `uv run --no-project --with-requirements requirements_test.txt pytest`**: Modified the command to use `uv run --no-project --with-requirements requirements_test.txt pytest` to avoid issues with the hatchling wheel build failure and the untracked `uv.lock` file creation.