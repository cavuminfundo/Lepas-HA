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
- **Regional Isolation**: The European Chery connected vehicle infrastructure (`com.chery.eu.lepas`) is hosted on EU-compliant regional gateways, physically and logically isolated from Chinese (APAC) Chery endpoints. Endpoints, cryptographic sign keys, and auth flows must not be conflated with non-EU Chery/Omoda apps.
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
