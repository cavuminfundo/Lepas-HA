# Architectural Design Specification: Lepas L8 Chery Connect Integration (Option A)

> **Document ID**: `SPEC-2026-10-23-LEPAS-CHERY-CONNECT`  
> **Status**: Approved (Option A — Multi-Tenant Native Integration)  
> **Target Package**: `custom_components/omoda9` (`omoda9-ha` / Chery Connect)  
> **Target Vehicle Platform**: Lepas L8 (Chery Europe, `com.chery.eu.lepas`)

---

## 1. Architectural Vision & Upstream Compatibility

### 1.1 Multi-Tenant Core Architecture (Option A)
Chery International operates a single, centralized backend platform (code-named `"legend"`) across Europe. Rather than deploying disparate backends for each corporate subsidiary, the European infrastructure serves **Omoda**, **Jaecoo**, **Chery**, and **Lepas** from common cloud gateways.

Under **Option A**, the Lepas L8 is supported natively inside `custom_components/omoda9` (branded in Home Assistant as *"Chery Connect"*). This design choice avoids fork divergence, eliminates duplicated protocol maintenance, and guarantees that any telemetry or command enhancements immediately benefit all Chery International brands.

### 1.2 Shared Infrastructure vs. Tenant Isolation
The architectural division between shared infrastructure and tenant-specific configuration is strictly partitioned:

| Component / Layer | Shared Across Brands (Europe) | Tenant-Specific (Brand / Region) |
|---|---|---|
| **Mutual-TLS MQTT Broker** | `tspemqx-app-eu.cheryinternational.com:8083` | No (Shared across all EU brands) |
| **mTLS Client Certificates** | `ca.pem`, `client.pem`, `client.key`, `eu_prd_cheryinternational.cer` | No (Same root CA and issued device certs) |
| **TSP Console Host** | `https://tspconsole-eu.cheryinternational.com` | No (Shared TSP control plane) |
| **MQTT App Password Seed** | `CAR_SEED = "fa89db3abe8045919d70c6ed3cc65bc5"` | No (Common algorithmic hash derivation) |
| **BFF API Gateway URL** | No | **Brand Dependent** (`CONF_BFF`) |
| **Tenant Code** | No | **Brand Dependent** (`CONF_TENANT_CODE`) |
| **Channel ID** | No | **Brand Dependent** (`CONF_CHANNEL_ID`) |
| **Country ID** | No | **Brand Dependent** (`CONF_COUNTRY_ID`) |

### 1.3 Zero Fork Divergence
Because `custom_components/omoda9` was already designed with regional preset selectors (`CONF_PRESET`), integrating Lepas requires **zero modifications to the core engine** (`core/session.py`, `core/commands.py`, `core/routing.py`, `coordinator.py`, or entity platforms). It only requires registering the verified tenant parameters in the preset registry and exposing the brand in UI selection schemas.

---

## 2. Verified Parameters for `PRESET_LEPAS_EU`

Static analysis and reverse-engineering of the official Lepas Europe companion application (`com.chery.eu.lepas`) confirmed the following regional gateway parameters:

- **BFF Gateway URL (`CONF_BFF`)**: `https://eu-lepas.cheryinternational.com/api`
- **Tenant Code (`CONF_TENANT_CODE`)**: `3000011`
- **Channel ID (`CONF_CHANNEL_ID`)**: `1`
- **Country ID (`CONF_COUNTRY_ID`)**: `1`

### Preset Comparison Matrix

```
┌────────────────────────┬──────────────────────────────────────────────┬─────────────┬────────────┬────────────┐
│ Preset Constant        │ BFF Gateway Endpoint                         │ Tenant Code │ Channel ID │ Country ID │
├────────────────────────┼──────────────────────────────────────────────┼─────────────┼────────────┼────────────┤
│ PRESET_OMODA_JAECOO_EU │ https://legend-oj.omodaauto.nl/api           │ 300006      │ 1          │ 1          │
│ PRESET_CHERY_EU        │ https://eu-chery.cheryinternational.com/api  │ 300001      │ 2          │ 2          │
│ PRESET_LEPAS_EU        │ https://eu-lepas.cheryinternational.com/api  │ 3000011     │ 1          │ 1          │
│ PRESET_CUSTOM          │ (User Defined)                               │ (User)      │ (User)     │ (User)     │
└────────────────────────┴──────────────────────────────────────────────┴─────────────┴────────────┴────────────┘
```

---

## 3. Planned Code Modifications

### 3.1 Constants Definition (`custom_components/omoda9/const.py`)
1. Declare preset identifier:
   ```python
   PRESET_LEPAS_EU = "lepas_eu"
   ```
2. Extend `PRESETS` dictionary:
   ```python
   PRESETS = {
       PRESET_OMODA_JAECOO_EU: {
           CONF_BFF: "https://legend-oj.omodaauto.nl/api",
           CONF_TENANT_CODE: "300006",
           CONF_CHANNEL_ID: "1",
           CONF_COUNTRY_ID: "1",
       },
       PRESET_CHERY_EU: {
           CONF_BFF: "https://eu-chery.cheryinternational.com/api",
           CONF_TENANT_CODE: "300001",
           CONF_CHANNEL_ID: "2",
           CONF_COUNTRY_ID: "2",
       },
       PRESET_LEPAS_EU: {
           CONF_BFF: "https://eu-lepas.cheryinternational.com/api",
           CONF_TENANT_CODE: "3000011",
           CONF_CHANNEL_ID: "1",
           CONF_COUNTRY_ID: "1",
       },
   }
   ```

### 3.2 Configuration Flow (`custom_components/omoda9/config_flow.py`)
1. Import `PRESET_LEPAS_EU` from `.const`.
2. Update the `SelectSelectorConfig` dropdown in `_region_fields()`:
   ```python
   SelectOptionDict(value=PRESET_OMODA_JAECOO_EU, label="Omoda / Jaecoo — Europe"),
   SelectOptionDict(value=PRESET_CHERY_EU, label="Chery — Europe"),
   SelectOptionDict(value=PRESET_LEPAS_EU, label="Lepas — Europe"),
   SelectOptionDict(value=PRESET_CUSTOM, label="Custom / other region (use the fields below)"),
   ```
3. Verify that `_apply_preset()` cleanly resolves `PRESET_LEPAS_EU` into `data` and removes `CONF_PRESET` prior to storing the entry.

### 3.3 Localization & String Resources
Update `custom_components/omoda9/strings.json` and its localized counterparts (`translations/en.json`, `translations/it.json`, `translations/nl.json`):
1. **Preset Descriptions**:
   - English (`en.json` & `strings.json`):
     `"Omoda/Jaecoo (Europe), Chery (Europe) and Lepas (Europe) fill in everything automatically. Choose Custom to set the BFF endpoint, tenant code, country/channel IDs, MQTT host and certs by hand for any other region or brand."`
   - Italian (`it.json`):
     `"Omoda/Jaecoo (Europa), Chery (Europa) e Lepas (Europa) compilano tutto in automatico. Scegli Personalizzato per impostare a mano l'endpoint BFF, codice tenant, ID paese/canale, host MQTT e certificati per qualunque altra regione o marchio."`
   - Dutch (`nl.json`):
     `"Omoda/Jaecoo (Europa), Chery (Europa) en Lepas (Europa) vullen alles automatisch in. Kies Aangepast om het BFF-eindpunt, tenantcode, land-/kanaal-ID's, MQTT-host en certificaten handmatig in te stellen voor elke andere regio of merk."`
2. **Account Sign-in Descriptions**: Update mentions of *"Omoda/Jaecoo account"* to include Lepas where appropriate.

---

## 4. TDD Test Strategy

The changes will be guarded by automated regression and contract tests:

### 4.1 Config Flow Tests (`tests/test_config_flow.py`)
- **`test_preset_lepas_eu_resolution`**:
  - Instantiate the config flow step (`login_email` or `login_password`) with `preset="lepas_eu"`.
  - Assert that `_apply_preset` populates:
    * `CONF_BFF == "https://eu-lepas.cheryinternational.com/api"`
    * `CONF_TENANT_CODE == "3000011"`
    * `CONF_CHANNEL_ID == "1"`
    * `CONF_COUNTRY_ID == "1"`
  - Assert that `CONF_PRESET` is cleanly excised from the resulting `entry.data`.

### 4.2 Routing & Command Integrity (`tests/test_routing.py` & `tests/test_command_routing.py`)
- Verify that `routing.classifica()` and `commands` correctly handle responses under the Lepas tenant context.
- Ensure that tenant code headers (`TENANT-CODE: 3000011`) are appropriately forwarded to `CoreCtx` during session initialization.

### 4.3 Translation Completeness (`tests/test_traduzioni_complete.py`)
- Execute key coverage validation across `strings.json`, `translations/en.json`, `translations/it.json`, and `translations/nl.json`.
- Confirm that every field rendered by `_region_fields()` has a 100% matched translation entry in all supported languages.

---

## 5. Credential Security & Secrets Isolation

1. **Transient Password Policy (ROPC)**:
   - When users authenticate using username/password, the password is used strictly in-memory during `login_with_password` to mint the initial OAuth token pair.
   - The password is NEVER written to Home Assistant storage (`entry.data` or `entry.options`).
2. **Token Rotation & Concurrency Locking**:
   - Access tokens are short-lived JWTs renewed via refresh tokens.
   - All token refresh operations are serialized via `asyncio.Lock` in `core/session.py` to prevent token invalidation races.
3. **Anti-Lockout Protection (`core/pin_lockout.py`)**:
   - Consecutive incorrect PIN inputs trigger exponential backoff and a hard local lockout before Chery's server-side lockout threshold is breached.
4. **Diagnostics Redaction (`diagnostics.py` & `diag.py`)**:
   - Vehicle VIN is masked to display only the last 4 characters (`***XXXX`).
   - All tokens, coordinates, passwords, and PII are stripped prior to diagnostic export.
