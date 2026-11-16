# Lepas EU `channelId: "6"` & `ConfigEntry` Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aggiornare il `channelId` Lepas EU da `"1"` a `"6"` su tutti i default/preset e migrare le `ConfigEntry` esistenti da `v1` a `v2` per risolvere l'errore `A00361`.

**Architecture:** Modifica deterministica e minima (Ponytail) della configurazione statica (`const.py`, `core/context.py`, `core/lepas_auth.py`, `core/lepas.py`, `coordinator.py`) accoppiata a `LepasConfigFlow.VERSION = 2` e `async_migrate_entry` in `__init__.py` che aggiorna a `"6"` le sole entry Lepas EU con `channel_id` assente o `"1"`, preservando `chery_eu` e `custom`.

**Tech Stack:** Python 3.12+, Home Assistant Core (`2026.2.3`), `pytest`, `pytest-homeassistant-custom-component`, `ruff`.

**Spec:** `docs/superpowers/specs/2026-11-16-channel-id-6-migration-design.md`

## Global Constraints
- `DEFAULTS[CONF_CHANNEL_ID]` e `PRESETS[PRESET_LEPAS_EU][CONF_CHANNEL_ID]` devono essere `"6"`.
- `PRESETS[PRESET_CHERY_EU][CONF_CHANNEL_ID]` deve rimanere `"2"`.
- `LepasConfigFlow.VERSION` deve passare da `1` a `2`.
- `async_migrate_entry` deve proteggere dai downgrade (`version > 2 -> False`) e aggiornare solo entry Lepas EU (`bff` Lepas EU o assente AND `tenant_code == "3000011"` o assente AND `channel_id in ("", "1")`).
- Nessun secret/PII nei log; rispettare `AB-LEP-001`..`AB-LEP-005` e documentare `AB-LEP-006`.
- Test eseguiti solo dal Master via `.venv/bin/pytest -q --tb=short --maxfail=2` e lint con `ruff`.

---

## Domain Skills & Sub-Agent Roster

| Dominio Coeso | Worker / Tipo | Model | Skill Primaria + Companions | File Assegnati (Contratto End-to-End) |
| :--- | :--- | :--- | :--- | :--- |
| **HA Integration, Config Migration & Core Channel Contract** | `ha_lepas_channel_worker` | `'pro'` (file `>600L` + `>=3` file interdipendenti) | `python-pro`, `ponytail`, `antislop-code` | `custom_components/lepas/const.py`, `custom_components/lepas/__init__.py`, `custom_components/lepas/config_flow.py`, `custom_components/lepas/coordinator.py`, `custom_components/lepas/core/context.py`, `custom_components/lepas/core/lepas_auth.py`, `custom_components/lepas/core/lepas.py`, `tests/test_config_flow.py`, `tests/test_context.py`, `.agents/memory/antibodies/lepas.md` |

---

## Blast Radius & StateGraph (`onSuccess` / `onFailure`)

### `BlastRadius`
- `direct_files`:
  - `custom_components/lepas/const.py`
  - `custom_components/lepas/__init__.py`
  - `custom_components/lepas/config_flow.py`
  - `custom_components/lepas/coordinator.py`
  - `custom_components/lepas/core/context.py`
  - `custom_components/lepas/core/lepas_auth.py`
  - `custom_components/lepas/core/lepas.py`
  - `tests/test_config_flow.py`
  - `tests/test_context.py`
  - `.agents/memory/antibodies/lepas.md`
- `transitively_affected`:
  - `custom_components/lepas/core/wake.py` (`_resolve_tuserid`, `_bff_login`, `_regione` leggono `ctx.channel_id`)
  - `custom_components/lepas/core/commands.py` (`_checkpassword` legge `ctx.channel_id`)
  - `custom_components/lepas/core/permessi.py` (`queryVehicleAuthority` legge `ctx.channel_id`)
  - `custom_components/lepas/core/provision.py` (legge `lepas_auth.CHANNEL_ID`)
  - `custom_components/lepas/core/session.py` (`_subenv` propaga `CHANNEL_ID`)
  - `custom_components/lepas/coordinator.py` (`_connect_car` costruisce `client_id = app_{channel_id}_{tuserid}` e topic `app/{channel_id}/{tuserid}/account/msgCenter/msg`)
  - `custom_components/lepas/diagnostics.py` (riporta `coordinator.channel_id`)
  - `tests/test_session.py`, `tests/test_command_routing.py`, `tests/test_hardening.py` (usano `ctx.channel_id` dinamico)
- `uncertain`:
  - Comportamento broker MQTT live su topic `app/6/{tuserid}/account/msgCenter/msg` e risposta live di `cpm/checkPassword` su HA (da verificare post-deploy con `ha_restart` + consenso utente).

### `StateGraph`
- **Migrazione ConfigEntry (`async_migrate_entry`)**:
  - `onSuccess`: aggiorna `entry.data[CONF_CHANNEL_ID]` a `"6"` (solo Lepas EU con `"1"`/assente) e porta `entry.version = 2` via `hass.config_entries.async_update_entry(...)`, ritornando `True`.
  - `onFailure`: se `config_entry.version > 2`, non muta `entry.data`, emette warning e ritorna `False` così HA blocca il setup proteggendo i dati futuri.
- **Deploy & Verifica Live HA (Fase post-test locali, opzionale su consenso)**:
  - `onSuccess`: backup pre-deploy dei file target, sync su HA `/config/custom_components/lepas/`, `ha_restart`, controllo log `rc=0` MQTT + assenza `A00361`.
  - `onFailure`: ripristino immediato dei file di backup e `ha_restart`.

---

### Task 1: Allineamento costanti `channel_id = "6"` e fallback `coordinator`

**Files:**
- Modify: `custom_components/lepas/const.py:231-266`
- Modify: `custom_components/lepas/coordinator.py:293`
- Modify: `custom_components/lepas/core/context.py:48`
- Modify: `custom_components/lepas/core/lepas_auth.py:36`
- Modify: `custom_components/lepas/core/lepas.py:23`
- Test: `tests/test_config_flow.py:372-408`
- Test: `tests/test_context.py:130-147`

**Interfaces:**
- Produces: `DEFAULTS[CONF_CHANNEL_ID] == "6"`, `PRESETS[PRESET_LEPAS_EU][CONF_CHANNEL_ID] == "6"`, `DEFAULT_CHANNEL_ID == "6"`, `CoreCtx().channel_id == "6"`, `lepas_auth.CHANNEL_ID == "6"`, `lepas.CHANNEL_ID == "6"`, `LepasCoordinator.channel_id == "6"` (quando assente in `entry.data`).

- [ ] **Step 1: Aggiornare i test esistenti / scrivere i test in rosso (TDD RED)**

In `tests/test_config_flow.py`: aggiornare `test_domain_and_defaults_lepas`, `test_apply_preset_lepas_eu`, `test_apply_preset_default_fallback` ad aspettarsi `"6"` invece di `"1"` (mantenendo `"2"` per `chery_eu` e `"42"` per `custom`). Nota: `tests/test_config_flow.py` e `tests/test_context.py` importano già `import fixtures as FX` in testa al file (verificare la presenza dell'import prima di usare `FX.*`).
In `tests/test_context.py`: aggiungere un test falsificabile `test_default_channel_id_lepas_eu_e_6(hass)`:
```python
def test_default_channel_id_lepas_eu_e_6(hass):
    """Senza channel_id esplicito nell'entry, CoreCtx e LepasCoordinator usano '6'."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.lepas.const import (
        CONF_EMAIL, CONF_PIN, CONF_TUSERID, CONF_VIN, DOMAIN,
    )
    from custom_components.lepas.coordinator import LepasCoordinator
    from custom_components.lepas.core import lepas, lepas_auth

    assert CoreCtx().channel_id == "6"
    assert lepas_auth.CHANNEL_ID == "6"
    assert lepas.CHANNEL_ID == "6"

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="LZZAAAAAA1B2C3D4E",
        data={
            CONF_VIN: "LZZAAAAAA1B2C3D4E",
            CONF_TUSERID: FX.TUSERID,
            CONF_EMAIL: FX.EMAIL,
            CONF_PIN: "123456",
        },
    )
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    assert coord.channel_id == "6"
    assert coord.ctx.channel_id == "6"
```
**Falsification note:** Fallisce immediatamente se `const.py`, `context.py`, `lepas_auth.py`, `lepas.py` o `coordinator.py` usano ancora `"1"`.

- [ ] **Step 2: Aggiornare i default e fallback a `"6"`**

1. `custom_components/lepas/const.py`:
   - `DEFAULTS[CONF_CHANNEL_ID] = "6"`
   - `PRESETS[PRESET_LEPAS_EU][CONF_CHANNEL_ID] = "6"`
2. `custom_components/lepas/coordinator.py:293`:
   - `self.channel_id = str(cfg.get(CONF_CHANNEL_ID) or DEFAULTS[CONF_CHANNEL_ID])`
3. `custom_components/lepas/core/context.py:48`:
   - `DEFAULT_CHANNEL_ID = "6"`
4. `custom_components/lepas/core/lepas_auth.py:36`:
   - `CHANNEL_ID = os.environ.get("CHANNEL_ID", "6")`
5. `custom_components/lepas/core/lepas.py:23`:
   - `CHANNEL_ID = os.environ.get("CHANNEL_ID", "6")`

---

### Task 2: Migrazione `ConfigEntry` `v1 → v2` (`async_migrate_entry` + `VERSION = 2`)

**Files:**
- Modify: `custom_components/lepas/config_flow.py:190`
- Modify: `custom_components/lepas/__init__.py:11,62-135`
- Test: `tests/test_config_flow.py`

**Interfaces:**
- Consumes: `DEFAULTS`, `PRESETS`, `PRESET_LEPAS_EU`, `CONF_BFF`, `CONF_TENANT_CODE`, `CONF_CHANNEL_ID` from `.const`.
- Produces: `LepasConfigFlow.VERSION == 2` and `async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool`.

- [ ] **Step 1: Scrivere i test di migrazione `ConfigEntry` (TDD RED)**

Aggiungere in `tests/test_config_flow.py` test falsificabili che esercitano `async_migrate_entry` reale su `hass`:
```python
async def test_migrate_entry_v1_lepas_eu_aggiorna_channel_a_6(hass):
    """Entry v1 Lepas EU con channel_id='1' viene migrata a v2 con channel_id='6'."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.lepas import async_migrate_entry
    from custom_components.lepas.const import (
        CONF_BFF, CONF_CHANNEL_ID, CONF_COUNTRY_ID, CONF_TENANT_CODE, CONF_VIN, DOMAIN,
    )

    assert LepasConfigFlow.VERSION == 2
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id=FX.VIN,
        data={
            CONF_VIN: FX.VIN,
            CONF_BFF: "https://eu-lepas.cheryinternational.com/api",
            CONF_TENANT_CODE: "3000011",
            CONF_COUNTRY_ID: "1",
            CONF_CHANNEL_ID: "1",
        },
    )
    entry.add_to_hass(hass)

    ok = await async_migrate_entry(hass, entry)
    assert ok is True
    assert entry.version == 2
    assert entry.data[CONF_CHANNEL_ID] == "6"


async def test_migrate_entry_v1_legacy_senza_campi_regione_imposta_6(hass):
    """Entry v1 storica senza bff/tenant_code/channel_id espliciti riceve channel_id='6'."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.lepas import async_migrate_entry
    from custom_components.lepas.const import CONF_CHANNEL_ID, CONF_VIN, DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id=FX.VIN,
        data={CONF_VIN: FX.VIN},
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is True
    assert entry.version == 2
    assert entry.data[CONF_CHANNEL_ID] == "6"


async def test_migrate_entry_v1_preserva_chery_eu_e_custom(hass):
    """Entry v1 Chery EU ('2') o custom ('42') mantengono il proprio channel_id avanzando a v2."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.lepas import async_migrate_entry
    from custom_components.lepas.const import (
        CONF_BFF, CONF_CHANNEL_ID, CONF_COUNTRY_ID, CONF_TENANT_CODE, CONF_VIN, DOMAIN,
    )

    chery = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id="LZZCHERY000000001",
        data={
            CONF_VIN: "LZZCHERY000000001",
            CONF_BFF: "https://eu-chery.cheryinternational.com/api",
            CONF_TENANT_CODE: "300001",
            CONF_COUNTRY_ID: "2",
            CONF_CHANNEL_ID: "2",
        },
    )
    custom = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id="LZZCUSTOM00000002",
        data={
            CONF_VIN: "LZZCUSTOM00000002",
            CONF_BFF: "https://eu-lepas.cheryinternational.com/api",
            CONF_TENANT_CODE: "3000011",
            CONF_CHANNEL_ID: "42",
        },
    )
    chery.add_to_hass(hass)
    custom.add_to_hass(hass)

    assert await async_migrate_entry(hass, chery) is True
    assert chery.version == 2
    assert chery.data[CONF_CHANNEL_ID] == "2"

    assert await async_migrate_entry(hass, custom) is True
    assert custom.version == 2
    assert custom.data[CONF_CHANNEL_ID] == "42"


async def test_migrate_entry_downgrade_rifiutato(hass):
    """Una entry con version > 2 non viene degradata e ritorna False."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.lepas import async_migrate_entry
    from custom_components.lepas.const import CONF_CHANNEL_ID, CONF_VIN, DOMAIN

    future = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id=FX.VIN,
        data={CONF_VIN: FX.VIN, CONF_CHANNEL_ID: "99"},
    )
    future.add_to_hass(hass)

    assert await async_migrate_entry(hass, future) is False
    assert future.version == 3
    assert future.data[CONF_CHANNEL_ID] == "99"
```
**Falsification note:** Esercitano direttamente `async_migrate_entry` con `MockConfigEntry` reale in `hass`; falliscono se `VERSION != 2`, se la migrazione non aggiorna `entry.data` / `entry.version`, se sovrascrive `chery_eu`/`custom`, o se permette downgrade.

- [ ] **Step 2: Implementare `VERSION = 2` e `async_migrate_entry`**

1. In `custom_components/lepas/config_flow.py:190`:
   `VERSION = 2`
2. In `custom_components/lepas/__init__.py`:
   Importare `CONF_BFF`, `CONF_CHANNEL_ID`, `CONF_TENANT_CODE`, `DEFAULTS`, `PRESET_LEPAS_EU`, `PRESETS` da `.const` e implementare:
```python
async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migra i config entry da versioni precedenti allo schema corrente."""
    if config_entry.version > 2:
        _LOGGER.warning(
            "Lepas: impossibile migrare config entry da versione futura %s",
            config_entry.version,
        )
        return False

    if config_entry.version == 1:
        data = dict(config_entry.data)
        bff = str(data.get(CONF_BFF) or DEFAULTS[CONF_BFF]).rstrip("/")
        tenant = str(data.get(CONF_TENANT_CODE) or DEFAULTS[CONF_TENANT_CODE])
        channel = str(data.get(CONF_CHANNEL_ID) or "")
        is_lepas_eu = (
            bff == DEFAULTS[CONF_BFF].rstrip("/")
            and tenant == DEFAULTS[CONF_TENANT_CODE]
        )
        if is_lepas_eu and channel in ("", "1"):
            new_channel = PRESETS[PRESET_LEPAS_EU][CONF_CHANNEL_ID]
            data[CONF_CHANNEL_ID] = new_channel
            _LOGGER.info(
                "Lepas: config entry migrata a v2 (channel_id %s -> %s)",
                channel or "<default>",
                new_channel,
            )
        hass.config_entries.async_update_entry(config_entry, data=data, version=2)
    return True
```

---

### Task 3: Crash Antibody `AB-LEP-006` e Verifica Suite Locale

**Files:**
- Modify: `.agents/memory/antibodies/lepas.md`

- [ ] **Step 1: Registrare la scheda `AB-LEP-006`**

Aggiungere in `.agents/memory/antibodies/lepas.md` la scheda `AB-LEP-006` che fissa:
- **Root Cause**: L'APK Lepas EU parte con `.env.prod` (`CHANNELID=1`) ma lo sovrascrive all'avvio tramite `/tsp/v1/app/env/defaultEnv` con `channelId="6"`. Usare `"1"` provoca `A00361` su `cpm/checkPassword`, `vmc/queryVehicleAuthority` e `vac/queryAuthRemoteList`.
- **Invariant**: `PRESET_LEPAS_EU`, `DEFAULTS[CONF_CHANNEL_ID]`, `DEFAULT_CHANNEL_ID` e `CHANNEL_ID` devono restare `"6"`, con `LepasConfigFlow.VERSION >= 2` e `async_migrate_entry` per aggiornare le entry `v1` Lepas EU preservando `chery_eu` (`"2"`) e `custom`.
- **onFailure Mandate**: Su ricomparsa di `A00361`, verificare `GET /tsp/v1/app/env/defaultEnv` e `entry.data[CONF_CHANNEL_ID]` prima di toccare il flow PIN/lockout.
- **Forbidden Regex**: `PRESET_LEPAS_EU[^}]*CONF_CHANNEL_ID:\s*["']1["']`

- [ ] **Step 2: Eseguire `pytest` e `ruff` (eseguito dal Master Agent)**
- `.venv/bin/pytest -q --tb=short --maxfail=2`
- `/home/federico/.local/bin/uv run ruff check custom_components/ tests/`
- `/home/federico/.local/bin/uv run ruff format --check custom_components/ tests/`

---

### Task 4 (Post-Verifica Locale, previo consenso esplicito): Verifica Live su Home Assistant
- Sync su HA `/config/custom_components/lepas/` + `ha_restart` (`mcp_home-assistant` / `AB-LEP-005`).
- Controllo log e stato `sensor.lepas_session_status`, MQTT `app/6/{tuserid}/account/msgCenter/msg`, `vmc/queryVehicleAuthority` / `vac/queryAuthRemoteList`.
- Su esplicita conferma utente: 1 test reale di `cpm/checkPassword` tramite comando/azione su veicolo per validazione end-to-end.
