# Design Spec — Lepas EU `channelId: "6"` & `ConfigEntry` Migration (v1 → v2)

**Data:** 2026-11-16
**Stato:** Approvato concettualmente (Opzione A) — pronto per pianificazione e Dual-Gate Audit
**Obiettivo:** Eliminare l'errore `A00361` ("User does not exist") su `cpm/checkPassword`, `vmc/queryVehicleAuthority` e `vac/queryAuthRemoteList` allineando il `channelId` Lepas EU al valore reale restituito da `/tsp/v1/app/env/defaultEnv` (`"6"`), migrando automaticamente le `ConfigEntry` esistenti senza richiedere riconfigurazione manuale.

---

## 1. Contesto & Root Cause Empirica
- L'app ufficiale Android Lepas parte con `.env.prod` (`CHANNELID=1`), ma all'avvio invoca `GET /tsp/v1/app/env/defaultEnv` (`CHApiConfig::setCarControlConfig`) che restituisce `channelId: 6`, `country: "1"`, `tenantId: "3000011"`, `domain: "https://tspconsole-eu.cheryinternational.com"`.
- Con `channelId = "1"`, i microservizi `cpm/checkPassword`, `vmc/queryVehicleAuthority` e `vac/queryAuthRemoteList` su `eu-lepas.cheryinternational.com` rispondono `A00361`.
- Test empirico su HA live (`[A00361_RO3]`): chiamando `POST /tsp/v1/app/vmc/queryVehicleAuthority` con `channelId: "6"`, il backend ha risposto `http=200, code=0, d=['permissionList']`.

---

## 2. Architettura della Soluzione (Opzione A — Ponytail / Deterministica)

### 2.1 Aggiornamento Default & Costanti Lepas EU (`"1"` → `"6"`)
Tutti i default di regione Lepas EU puntano a `"6"` da un'unica verità di modulo dove applicabile:
- `custom_components/lepas/const.py`:
  - `DEFAULTS[CONF_CHANNEL_ID] = "6"`
  - `PRESETS[PRESET_LEPAS_EU][CONF_CHANNEL_ID] = "6"`
  - `PRESETS[PRESET_CHERY_EU][CONF_CHANNEL_ID]` resta `"2"` (invariato).
- `custom_components/lepas/coordinator.py`:
  - `LepasCoordinator.__init__`: sostituire il fallback hardcoded `"1"` con `DEFAULTS[CONF_CHANNEL_ID]` (`str(cfg.get(CONF_CHANNEL_ID) or DEFAULTS[CONF_CHANNEL_ID])`).
- `custom_components/lepas/core/context.py`:
  - `DEFAULT_CHANNEL_ID = "6"`.
- `custom_components/lepas/core/lepas_auth.py` & `custom_components/lepas/core/lepas.py`:
  - `CHANNEL_ID = os.environ.get("CHANNEL_ID", "6")` (fallback CLI/diagnostica).

### 2.2 Migrazione `ConfigEntry` (`VERSION = 1 → 2`)
- `custom_components/lepas/config_flow.py`:
  - Incrementare `LepasConfigFlow.VERSION = 2`.
- `custom_components/lepas/__init__.py`:
  - Implementare `async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool`:
    - Se `config_entry.version > 2`: log warning e ritorna `False` (protezione downgrade).
    - Se `config_entry.version == 1`:
      - Copiare `data = dict(config_entry.data)`.
      - Normalizzare `bff = str(data.get(CONF_BFF, DEFAULTS[CONF_BFF])).rstrip("/")`, `tenant = str(data.get(CONF_TENANT_CODE, DEFAULTS[CONF_TENANT_CODE]))`, `channel = str(data.get(CONF_CHANNEL_ID, ""))`.
      - Se l'entry appartiene a Lepas EU (`bff == DEFAULTS[CONF_BFF].rstrip("/")` e `tenant == DEFAULTS[CONF_TENANT_CODE]`) e `channel in ("", "1")`:
        - Impostare `data[CONF_CHANNEL_ID] = PRESETS[PRESET_LEPAS_EU][CONF_CHANNEL_ID]` (`"6"`).
      - Chiamare `hass.config_entries.async_update_entry(config_entry, data=data, version=2)`.
    - Ritornare `True`.
  - **Preservazione casi non-Lepas EU / custom:**
    - Entry `chery_eu` (`tenant="300001"`, `channel="2"`): `channel` non toccato, solo bump a `version=2`.
    - Entry `custom` (es. BFF/tenant diversi o `channel="42"`): `channel` preservato, solo bump a `version=2`.
    - Entry legacy v1 prive di `CONF_BFF` / `CONF_TENANT_CODE` / `CONF_CHANNEL_ID`: ricadono nei default Lepas EU e ricevono `CONF_CHANNEL_ID = "6"`.

### 2.3 Verifica Live Post-Implementazione (su consenso utente)
1. Deploy della modifica su Home Assistant + `ha_restart` (obbligatorio per `AB-LEP-005`, poiché `reload_config_entry` non ricarica `core/*.py`).
2. Verifica passiva automatica allo startup:
   - Avvio migrazione `v1 → v2` e persistenza `channel_id="6"` nella `ConfigEntry`.
   - Sottoscrizione MQTT su `app/6/{tuserid}/account/msgCenter/msg` (`rc=0`).
   - Stato sessione attivo (`sensor.lepas_session_status`).
3. Verifica attiva su consenso esplicito utente:
   - 1 esecuzione reale di `cpm/checkPassword` tramite comando/azione su veicolo per confermare la risoluzione end-to-end di `A00361`.

---

## 3. Vincoli di Sicurezza & Crash Antibodies
- Rispetto integrale di `AB-LEP-001`..`AB-LEP-005`: zero PII nei log, redazione in `diagnostics.py`, nessun riutilizzo `reload_config_entry` al posto di `ha_restart` per test live su `core/*.py`.
- Registrazione di `AB-LEP-006` in `.agents/memory/antibodies/lepas.md` per fissare l'invariante `channelId = "6"` (vs `.env.prod = "1"`) e la migrazione `ConfigEntry` `v1 → v2`.
