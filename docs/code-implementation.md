# Lepas — Low-Level Implementation & Algorithmic Details

> **Component Scope**: `custom_components/lepas` & Async API Client  
> **Platform**: Chery EU (`com.chery.eu.lepas`)

---

## 1. Networking & Session Management

### 1.1 Mandatory Session Reuse
- Under no circumstances should individual classes or functions instantiate `aiohttp.ClientSession()` directly.
- In Home Assistant runtime, obtain the session exclusively from `homeassistant.helpers.aiohttp_client.async_get_clientsession(hass)`.
- When running outside Home Assistant (e.g. standalone CLI or unit tests), accept an injected `aiohttp.ClientSession` in the client constructor:

```python
class LepasApiClient:
    def __init__(self, session: aiohttp.ClientSession, base_url: str) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token_lock = asyncio.Lock()
        self._access_token: str | None = None
        self._refresh_token: str | None = None
```

### 1.2 Non-Blocking Timeouts
- All network calls must pass explicit timeouts (`asyncio.timeout(10.0)` or `aiohttp.ClientTimeout(total=15.0)`).
- Never allow an unbounded network request to freeze the coordinator loop.

---

## 2. Token Refresh Synchronization & Rate Limiting

### 2.1 Serialized Token Refresh Pattern
When an access token expires (HTTP 401 response or client-side expiry check), multiple entities or polling loops may attempt a refresh simultaneously. All callers must acquire an `asyncio.Lock` before refreshing:

```python
async def _ensure_valid_token(self) -> str:
    if self._is_token_valid():
        return self._access_token  # type: ignore[return-value]

    async with self._token_lock:
        # Double-check inside lock to ensure another task did not just complete the refresh
        if self._is_token_valid():
            return self._access_token  # type: ignore[return-value]
        
        await self._refresh_access_token()
        return self._access_token  # type: ignore[return-value]
```

### 2.2 Exponential Backoff with Jitter
- On HTTP 429 (Too Many Requests) or 5xx server errors, the client applies truncated exponential backoff with full jitter:
  $$T_{\text{wait}} = \min(T_{\max}, 2^{\text{attempt}} \cdot \text{base}) \cdot \text{random}(0.5, 1.5)$$
- Standard parameters: `base = 1.0` second, `T_max = 60.0` seconds, `max_retries = 3`.
- If the server provides a `Retry-After` header, respect its integer value up to a hard cap of 120 seconds.

---

## 3. Telematics Polling Strategy & 12V Battery Protection

### 3.1 Adaptive Update Intervals
To prevent draining the vehicle's 12V auxiliary battery by keeping the Telematics Control Unit (TCU) awake:
- **Driving State** (Speed > 0 or ignition ON): Update interval = 30 seconds.
- **Charging State** (Charger connected and active): Update interval = 60 seconds.
- **Parked / Standby State** (Vehicle locked and stationary): Update interval = 15–30 minutes.

### 3.2 State Preservation on Failure
- If a polling cycle fails due to network outage or vehicle asleep (timeout), the coordinator must log a warning and retain the previous valid state.
- Do not set entities to `unavailable` on a single transient failure; mark unavailable only after 3 consecutive failed cycles spanning > 30 minutes.

---

## 4. Diagnostics & Sensitive Data Redaction

### 4.1 Strict Masking Invariants
All diagnostic dumps produced by `diagnostics.py` must redact:
- **Vehicle VIN**: Mask everything except the last 4 characters (`***XXXX`).
- **Auth Tokens**: Strip `access_token`, `refresh_token`, and authorization headers entirely.
- **GPS Coordinates**: Round `latitude` and `longitude` to 2 decimal places or mask them completely in anonymized reports.
- **User Identifiers**: Mask email addresses, phone numbers, and internal Chery user IDs.

```python
TO_REDACT = {
    "access_token",
    "refresh_token",
    "password",
    "authorization",
    "token",
    "phone",
    "email",
    "vin",
    "latitude",
    "longitude",
}
```

---

## 5. Home Assistant Entity Conventions

### 5.1 Unique ID Format
- Unique IDs for entities must follow the deterministic format:
  `{entry.entry_id}_{vin}_{entity_key}`
- Example: `8f7b2a..._LS5...1234_battery_soc`

### 5.2 Device Association
- All entities created for a vehicle must set `device_info`:
```python
@property
def device_info(self) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, self._vin)},
        name=f"Lepas L8 ({self._vin[-4:]})",
        manufacturer="Chery / Lepas",
        model="Lepas L8",
    )
```
