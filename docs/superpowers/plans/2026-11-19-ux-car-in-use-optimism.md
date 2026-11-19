# UX Partenze, Rilevamento "Auto in uso", Annullamento Ottimismo su `reason` & Badge Clima (`v1.25.0`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Risolvere il blocco dello stato ottimistico su rifiuto centralina (`reason`), rilevare quando la vettura è in uso (`is_car_in_use()`) inibendo i controlli comfort in tab Clima, mostrare l'esito comandi (`cmdResultBadge`) anche nella tab Clima, e applicare l'Opzione 1 UX Partenze (`Prossima partenza` + `Su auto`) in `v1.25.0`.

**Architecture:** `LepasCoordinator` mappa i `modelId` di rifiuto `reason` ai campi telemetrici (`REASON_FIELD_MAP`, preservando `_solo_clima` / `0:95`) e mantiene un latch di sessione HV (`_hv_session_in_use`) in `_evaluate_car_in_use()`, esposto tramite `is_car_in_use()` sugli attributi `car_in_use` di `binary_sensor.lepas_high_voltage_active` e `climate.lepas_climate` (zero nuove entità HA). `LepasOptimisticMixin`, `LepasComfortSwitch` e `LepasClimate` annullano istantaneamente lo stato ottimistico alla ricezione di un rifiuto `reason` pertinente. Nel frontend `LepasCard` (`lepas-card.js`), la tab Clima mostra il banner "Auto in uso", disabilita i comandi comfort quando `car_in_use === true`, e sincronizza `cmdResultBadge` insieme alla Plancia; la sezione Partenze implementa l'Opzione 1 (`Prossima partenza` + `Su auto` con stati verde/ambra/spenta).

**Tech Stack:** Python >=3.12, Home Assistant `DataUpdateCoordinator`, `ClimateEntity`, `BinarySensorEntity`, `SwitchEntity`, JavaScript ES5 Web Component (`LepasCard`), `pytest`, `node --test`, `ruff`, `uv`.

**Spec:** [docs/superpowers/specs/2026-11-19-ux-car-in-use-optimism-design.md](file:///home/federico/Lepas/docs/superpowers/specs/2026-11-19-ux-car-in-use-optimism-design.md)

## Global Constraints
- Zero nuove entità HA (`tests/test_entity_count.py` invariato); `car_in_use` è esposto come attributo su `binary_sensor.lepas_high_voltage_active` e `climate.lepas_climate`.
- Preservare `_solo_clima(reason)` (`0:95` o solo `modelId == "0"`): non deve MAI annullare l'ottimismo né segnalare rifiuto comfort.
- Nessun acquisimento di `self._state_lock` dentro `_handle_coordinator_update` e nessuna chiamata a `_auto_e_sveglia()` dentro `with self._state_lock:` (`AB-LEP-007`).
- Rispetto Battery Guard (`AB-LEP-001`): non svegliare l'auto se `poll_enabled` è `False`; `_hv_followup_cb` rispetta `self._poll_busy` senza sovrapporsi a `_drive_watch_cb`.
- `lepas-card.js` resta ES5 puro (zero `?.`, zero `??`, zero `import`/`export` top-level), rispetta `allowlist` e escaping XSS (`self._h(...)`), usa `.hidden` + attributo `hidden` e ignora click su bottoni `disabled`.
- Versioning sincronizzato a `1.25.0` (`manifest.json`, `pyproject.toml`, `lepas-card.js`, `tests/test_lovelace_card.py`, `CHANGELOG.md` bilingue IT/EN).

---

## Dual-Gate Audit Matrix (Pre-Execution)

| Gate | Sub-Agent Role | Model | Conversation ID | Verdict | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Stage 1 | Domain & Archaeology Pre-Audit | `flash` | `1ba316a4-51a2-4164-a877-f0195632aee9` | `FAIL -> Fixed` | Risolti in spec & piano: (1) `self._hv_lock = threading.Lock()` su `_evaluate_car_in_use`, (2) precedenza `msg_fields > rt > fields` in `_on_car_message` così `realtime` stantio non maschera `5A02`, (3) `@callback _schedule_probe_on_loop` sul loop HA per `_poll_busy`/`closing`, (4) scope `hasPending`/`isSynced` + reset `.is-emerald`/`.is-amber` + disabilitazione post-`_applyBtnState` in `lepas-card.js`, (5) test falsificabili aggiunti per `is_armed(HV_POLL)`, `_on_car_message` end-to-end, `LepasClimate` rejection e `odometer` latch |
| Stage 2 | Six-Pillars Sentinel Control Gate | `inherit` | `7852790e-a8c6-44bf-92b7-e269d3eff7b2` | `REJECTED -> Fixed` | Risolti in spec & piano prima dell'esecuzione: (1) `btn.disabled` non sticky (`climateToggleBtn` = `_pendingKeys.has("climate_toggle") || carInUse`, altri controlli comfort = `carInUse`, più test `true → false` su stessa card), (2) `is_car_in_use()` legge `self._hv_session_in_use` sotto `self._hv_lock`, (3) rimozione esplicita override `nextDepText` `!haHasActiveDep && carActive`, (4) `self._poll_busy = True` impostato sincronamente in `@callback _schedule_probe_on_loop` |

---

### Domain Skills & Sub-Agent Roster

| Dominio Coeso | Skill Primaria & Companions (`lookup.py`) | Sub-Agente / Modello | File Assegnati (Contratto End-to-End) |
| :--- | :--- | :--- | :--- |
| **Backend Coordinator, Ottimismo & Attributi HV/Clima** | `python-pro` + `ponytail` + `antislop-code` | `lepas_backend_worker` (`Model: 'pro'`, `coordinator.py` >600L + `switch.py` >600L + contratto stato distribuito/lock) | `custom_components/lepas/coordinator.py`, `custom_components/lepas/entity.py`, `custom_components/lepas/switch.py`, `custom_components/lepas/climate.py`, `custom_components/lepas/binary_sensor.py`, `tests/test_car_in_use_optimism.py` |
| **Frontend Lovelace Card (Tab Clima, UX Partenze) & Release 1.25.0** | `frontend-api-integration-patterns` (`antislop-ui` + `ponytail` + `antislop-code`) | `lepas_card_worker` (`Model: 'flash'` o `'pro'`: file `lepas-card.js` >600L → `'pro'` per policy file >600L) | `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`, `custom_components/lepas/manifest.json`, `pyproject.toml`, `CHANGELOG.md` |

> **Nota Model Routing:** Poiché `lepas-card.js` supera 600 righe (`4018L`), per regola esplicita (`file >600L → Model: 'pro' dal Round 1`) anche `lepas_card_worker` verrà invocato con `Model: 'pro'`, oppure con scope focalizzato sulle sole sezioni target. Impostiamo entrambi i worker di Round 1 a `Model: 'pro'` in worktree/workspace controllato (file disgiunti, zero sovrapposizioni).

---

## Blast Radius & StateGraph

### `BlastRadius` (da CodeGraph & `--task archaeology`)
- `direct_files`:
  - `custom_components/lepas/coordinator.py` (`REASON_FIELD_MAP`, `__init__`, `_evaluate_car_in_use`, `is_car_in_use`, `_on_car_message`, `_on_probe_data`, `_hv_followup_cb`, `_extract_rejected_fields`)
  - `custom_components/lepas/entity.py` (`LepasOptimisticMixin._verita_arrivata`, `_rifiuto_arrivato`, `_handle_coordinator_update`)
  - `custom_components/lepas/switch.py` (`LepasComfortSwitch._handle_coordinator_update`)
  - `custom_components/lepas/climate.py` (`LepasClimate._handle_coordinator_update`, `extra_state_attributes`)
  - `custom_components/lepas/binary_sensor.py` (`LepasRealtimeBinary.extra_state_attributes`)
  - `custom_components/lepas/lovelace/lepas-card.js` (`CARD_VERSION`, `HERO_IMAGES`, `I18N`, `buildStyles`, `_renderInner`, `_applyBindingsInner`, `_handleClick`)
  - `tests/test_car_in_use_optimism.py` (nuova suite backend mirata), `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`
  - Release metadata `1.25.0`: `custom_components/lepas/manifest.json`, `pyproject.toml`, `CHANGELOG.md`
- `transitively_affected`:
  - `custom_components/lepas/lock.py`, `custom_components/lepas/cover.py` (ereditano `LepasOptimisticMixin` e hanno `_opt_keys` validi — ricevono automaticamente l'annullamento su `cmd_rejected_fields`/`cmd_rejected_other` senza modifiche)
  - `tests/test_entity_count.py` (deve continuare a passare invariato)
  - `tests/test_scheduler.py`, `tests/test_native_departure_battery.py` (interagiscono con `LepasCoordinator.data` e `lepas-card.js` departure attrs)
- `uncertain`:
  - Comportamento su vettura reale di `modelId` diversi da `0,4,5,6,8,9,10,11,13` (es. `15,16` su sbrinamenti/volante): coperti via `cmd_rejected_other = True` solo quando `not _solo_clima(reason)` e `result not in ("1", "2", "5")` oppure `mid != "0"`.

### `StateGraph` (`onSuccess:` / `onFailure:` & Concurrency)
1. **Conferma MQTT con `reason` (`_on_car_message` in thread paho → `_apply_update` sul loop):**
   - `onSuccess` (nessun `reason`, oppure `_solo_clima(reason)` è `True`, es. `[0:95]`): `cmd_rejected_fields = frozenset()`, `cmd_rejected_other = False`. L'ottimismo resta attivo fino a `msg_fields` o `OPT_MAX_S`.
   - `onFailure` (`reason` presente e `not _solo_clima(reason)`, es. `[0:95, 4:95]`):
     - Estrae `rejected_fields` da `REASON_FIELD_MAP` + `rejected_other` per `mid not in ("0", *REASON_FIELD_MAP)`.
     - Aggiorna `_evaluate_car_in_use((self.data or {}).get("realtime"), fields_copy, msg_fields=msg_fields, comfort_rejected=True)` sotto `self._hv_lock` (precedenza `msg_fields > rt > fields`) così se `hVoltageState == 1`, `_hv_session_in_use` fa latch immediato a `True`.
     - Emette `patch` con `last_seen`, `cmd_rejected_fields`, `cmd_rejected_other`, `car_in_use`.
     - Chiama `self.hass.loop.call_soon_threadsafe(self._schedule_probe_on_loop)`: sul loop HA, `@callback _schedule_probe_on_loop` verifica `self._timers.closing`, `self.poll_enabled` e `self._poll_busy`, imposta `self._poll_busy = True` sincronamente prima di `self.hass.async_create_task(self._run_guarded_probe())` (rollback su eccezione di creazione task, rilascio in `finally: self._poll_busy = False` dentro `_run_guarded_probe`) per aggiornare subito `hVoltageState` / `vehicleSpeed` / `frontHVACState`.
2. **Sonda realtime (`_on_probe_data` in thread executor):**
   - Acquisisce `self._state_lock` solo per copiare/aggiornare `self._fields` e `self.position` (mai `_auto_e_sveglia()` dentro il lock).
   - Chiama `_evaluate_car_in_use(rt_copy, fields_copy)` (sotto `self._hv_lock`, precedenza `rt > fields`) e imposta `patch["car_in_use"]`.
   - Se `hVoltageState == 0 and engineState == 0 and vehicleSpeed <= 0`: azzera `_hv_session_in_use = False` e `_hv_session_start_odo = None` (`onSuccess` uscita da sessione HV).
3. **Follow-up HV (`_hv_followup_cb`):**
   - Controlla `if self._timers.closing or not self.poll_enabled: return`.
   - Se `self._poll_busy`: riarma `self._arm_hv_followup()` senza lanciare una seconda `async_probe` concorrente.
   - Altrimenti imposta `self._poll_busy = True` con `try ... finally: self._poll_busy = False` ed esegue `await self.async_probe(force=True)`.
4. **Entità ottimistiche (`entity.py`, `switch.py`, `climate.py`):**
   - `onRejection`: `_verita_arrivata()` ritorna `True` quando `last_seen != _opt_anchor` e (`_opt_keys` interseca `cmd_rejected_fields` o `cmd_rejected_other`). `LepasComfortSwitch` azzera anche `_exclusive._opt_value` se condivideva `_opt_anchor`.
   - `onTimeout`/`onNormal`: invariato (`OPT_MAX_S` / `msg_fields`).
5. **Frontend `lepas-card.js`:**
   - Quando `carInUse === true`, i bottoni comfort in tab Clima hanno `disabled = true` + `aria-disabled="true"` e `_triggerAction` ritorna subito se `actionEl && actionEl.disabled`.
   - `onCarInUseFalse`: rimuove `disabled` e nasconde `carInUseBanner`.

### `Test Falsification Mandate`
- Se `LepasOptimisticMixin._verita_arrivata` ignorasse `cmd_rejected_fields`, il test `test_seat_heating_optimism_clears_immediately_on_4_95_reason` troverebbe `sw.is_on is True` dopo il push `[0:95, 4:95]` e **fallirebbe**.
- Se `REASON_FIELD_MAP` includesse `"0"` per `[0:95]` solo, il test `test_solo_clima_0_95_preserves_climate_optimism` troverebbe `climate.hvac_mode == OFF` prematuramente e **fallirebbe**.
- Se `LepasComfortSwitch` non azzerasse `_exclusive` su rifiuto, il test di mutua esclusione troverebbe `vent_sw._opt_value is False` residuo invece di `None` e **fallirebbe**.
- Se `is_car_in_use()` non usasse il latch di sessione HV, il test con auto ferma al semaforo (`speed=0`, `engineState=0`, `hvac=1` dopo marcia precedente `speed=57`) restituirebbe `False` e **fallirebbe**; viceversa se `doorLock=1` da solo attivasse il latch, il test di pre-clima in garage privato sbloccato restituirebbe `True` e **fallirebbe**.
- Se `lepas-card.js` usasse `querySelector` invece di `querySelectorAll` su `[data-bind="cmdResultBadge"]`, il test JSDOM sul badge nella tab Clima troverebbe il badge nascosto/vuoto e **fallirebbe**.
- Se `lepas-card.js` non disabilitasse o non bloccasse il click con `car_in_use: true`, i test JSDOM su `seat`/`macro`/`defrost`/`climate_toggle` eseguirebbero `callService` e **fallirebbero**.

---

### Task 1: Backend — Ottimismo su `reason`, `is_car_in_use()`, HV Polling & Attributi (`coordinator.py`, `entity.py`, `switch.py`, `climate.py`, `binary_sensor.py`)

**Files:**
- Modify: `custom_components/lepas/coordinator.py:190-206`, `440-462`, `1890-1985`, `2524-2692`
- Modify: `custom_components/lepas/entity.py:237-256`
- Modify: `custom_components/lepas/switch.py:195-214`
- Modify: `custom_components/lepas/climate.py:144-168`
- Modify: `custom_components/lepas/binary_sensor.py:136-154`
- Create: `tests/test_car_in_use_optimism.py`

**Interfaces:**
- Produces on `LepasCoordinator`:
  - `REASON_FIELD_MAP: dict[str, tuple[str, ...]]` (module constant)
  - `is_car_in_use(self) -> bool`
  - `self.data["cmd_rejected_fields"]: frozenset[str]`
  - `self.data["cmd_rejected_other"]: bool`
  - `self.data["car_in_use"]: bool`
- Produces on `LepasRealtimeBinary` (`hVoltageState`) and `LepasClimate`:
  - `extra_state_attributes` includes `"car_in_use": bool`

- [ ] **Step 1: Scrivere i test Python falsificabili in `tests/test_car_in_use_optimism.py` (RED)**

```python
"""Tests for ECU reason optimism cancellation and car-in-use detection."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from homeassistant.components.climate import HVACMode

from custom_components.lepas.binary_sensor import LepasRealtimeBinary
from custom_components.lepas.climate import LepasClimate
from custom_components.lepas.coordinator import LepasCoordinator
from custom_components.lepas.switch import LepasComfortSwitch
from tests.conftest import make_entry


def _make_coord(hass, *, poll_enabled: bool = False) -> LepasCoordinator:
    coord = LepasCoordinator(hass, make_entry())
    coord.poll_enabled = poll_enabled
    return coord


def test_extract_rejected_fields_preserves_solo_clima_and_maps_seat_reason() -> None:
    assert LepasCoordinator._extract_rejected_fields(
        [{"modelId": "0", "code": "95"}], result="1"
    ) == (frozenset(), False)
    fields, other = LepasCoordinator._extract_rejected_fields(
        [{"modelId": "0", "code": "95"}, {"modelId": "4", "code": "95"}], result="1"
    )
    assert fields == frozenset({"dSeatHeatingState"})
    assert other is False
    fields_m, other_m = LepasCoordinator._extract_rejected_fields(
        [{"modelId": "15", "code": "1"}], result="0"
    )
    assert fields_m == frozenset()
    assert other_m is True


async def test_seat_heating_optimism_clears_immediately_on_4_95_reason(hass) -> None:
    coord = _make_coord(hass)
    coord._fields["dSeatHeatingState"] = "0"
    coord.data = {**coord.data, "fields": {"dSeatHeatingState": "0"}, "last_seen": "t0"}
    coord.async_send_command = AsyncMock(return_value="ok")

    sw_heat = LepasComfortSwitch(
        coord, "Lepas Sedile guida riscaldato", "driver_seat_heating",
        "dSeatHeatingState", "sedile_guida_caldo", "sedile_guida_caldo_off", "mdi:car-seat-heater",
    )
    sw_vent = LepasComfortSwitch(
        coord, "Lepas Sedile guida ventilato", "driver_seat_ventilation",
        "dSeatVentilateState", "sedile_guida_aria", "sedile_guida_aria_off", "mdi:car-seat-cooler",
    )
    sw_heat._exclusive = sw_vent
    sw_vent._exclusive = sw_heat
    sw_heat.hass = hass
    sw_vent.hass = hass
    sw_heat.async_write_ha_state = lambda: None
    sw_vent.async_write_ha_state = lambda: None

    await sw_heat.async_turn_on()
    assert sw_heat.is_on is True
    assert sw_vent._opt_value is False

    # Simulate MQTT confirmation 1.4s later: result + reason [0:95, 4:95], NO dSeatHeatingState in msg_fields
    coord._apply_update({
        "last_seen": "t1",
        "msg_fields": {},
        "cmd_rejected_fields": frozenset({"dSeatHeatingState"}),
        "cmd_rejected_other": False,
        "cmd_status": "Eseguito solo in parte ⚠️ — sedile guida riscaldato (codici 0:95, 4:95)",
    })
    sw_heat._handle_coordinator_update()
    sw_vent._handle_coordinator_update()

    assert sw_heat.is_on is False
    assert sw_heat._opt_value is None
    assert sw_vent._opt_value is None


async def test_solo_clima_0_95_preserves_climate_optimism(hass) -> None:
    coord = _make_coord(hass)
    coord.data = {**coord.data, "fields": {"frontHVACState": "0"}, "last_seen": "t0"}
    coord.async_send_command = AsyncMock(return_value="ok")

    cli = LepasClimate(coord)
    cli.hass = hass
    cli.async_write_ha_state = lambda: None

    await cli.async_turn_on()
    assert cli.hvac_mode == HVACMode.HEAT_COOL

    coord._apply_update({
        "last_seen": "t1",
        "msg_fields": {},
        "cmd_rejected_fields": frozenset(),
        "cmd_rejected_other": False,
    })
    cli._handle_coordinator_update()
    assert cli.hvac_mode == HVACMode.HEAT_COOL
    assert cli._opt_on is True


def test_car_in_use_distinguishes_preclimate_garage_vs_driving_and_red_light_latch(hass) -> None:
    coord = _make_coord(hass)

    # 1. Parked, remote pre-climate ON in private unlocked garage -> NOT in use
    coord._on_probe_data({
        "hVoltageState": "1",
        "engineState": "0",
        "vehicleSpeed": "0",
        "chargeGunState": "0",
        "frontHVACState": "1",
        "doorLock": "1",
        "frontLeftDoor": "0",
        "odometer": "593",
    })
    assert coord.is_car_in_use() is False

    # 2. Charging unattended -> NOT in use
    coord._on_probe_data({
        "hVoltageState": "1",
        "engineState": "0",
        "vehicleSpeed": "0",
        "chargeGunState": "1",
        "frontHVACState": "0",
        "odometer": "593",
    })
    assert coord.is_car_in_use() is False

    # 3. Driving at 57 km/h -> IN USE (latched for HV session)
    coord._on_probe_data({
        "hVoltageState": "1",
        "engineState": "0",
        "vehicleSpeed": "57",
        "chargeGunState": "0",
        "frontHVACState": "1",
        "odometer": "594",
    })
    assert coord.is_car_in_use() is True

    # 4. Stopped at red light (speed=0, engine=0, hvac=1) -> STILL IN USE due to HV latch
    coord._on_probe_data({
        "hVoltageState": "1",
        "engineState": "0",
        "vehicleSpeed": "0",
        "chargeGunState": "0",
        "frontHVACState": "1",
        "odometer": "594",
    })
    assert coord.is_car_in_use() is True

    # 5. Parked and HV turned off -> resets latch
    coord._on_probe_data({
        "hVoltageState": "0",
        "engineState": "0",
        "vehicleSpeed": "0",
        "chargeGunState": "0",
        "frontHVACState": "0",
        "odometer": "596",
    })
    assert coord.is_car_in_use() is False


def test_car_in_use_attribute_exposed_on_hv_binary_and_climate(hass) -> None:
    from homeassistant.components.binary_sensor import BinarySensorDeviceClass

    coord = _make_coord(hass)
    coord._on_probe_data({
        "hVoltageState": "1",
        "engineState": "1",
        "vehicleSpeed": "0",
        "chargeGunState": "0",
        "frontHVACState": "0",
    })
    hv_ent = LepasRealtimeBinary(coord, "Alta tensione attiva", "alta_tensione", "hVoltageState", BinarySensorDeviceClass.RUNNING)
    cli_ent = LepasClimate(coord)
    assert hv_ent.extra_state_attributes == {"car_in_use": True}
    assert cli_ent.extra_state_attributes == {"car_in_use": True}


async def test_hv_followup_cb_respects_poll_busy_and_rearms(hass) -> None:
    from custom_components.lepas.timers import HV_POLL

    coord = _make_coord(hass, poll_enabled=True)
    coord._poll_busy = True
    coord.data = {**coord.data, "realtime": {"hVoltageState": "1"}}
    coord.async_probe = AsyncMock()
    try:
        await coord._hv_followup_cb(datetime.now(timezone.utc))
        coord.async_probe.assert_not_awaited()
        assert coord._timers.is_armed(HV_POLL) is True
    finally:
        coord._timers.close()


async def test_on_car_message_reason_4_95_end_to_end_clears_switch_and_latches_car_in_use(hass) -> None:
    import json
    from types import SimpleNamespace

    coord = _make_coord(hass, poll_enabled=False)
    coord.data = {
        **coord.data,
        "realtime": {"hVoltageState": "1", "frontHVACState": "1", "vehicleSpeed": "0", "chargeGunState": "0"},
        "fields": {"dSeatHeatingState": "0"},
        "last_seen": "t0",
    }
    coord._fields["dSeatHeatingState"] = "0"
    coord.async_send_command = AsyncMock(return_value="ok")

    sw_heat = LepasComfortSwitch(
        coord, "Lepas Sedile guida riscaldato", "driver_seat_heating",
        "dSeatHeatingState", "sedile_guida_caldo", "sedile_guida_caldo_off", "mdi:car-seat-heater",
    )
    sw_vent = LepasComfortSwitch(
        coord, "Lepas Sedile guida ventilato", "driver_seat_ventilation",
        "dSeatVentilateState", "sedile_guida_aria", "sedile_guida_aria_off", "mdi:car-seat-cooler",
    )
    sw_heat._exclusive = sw_vent
    sw_vent._exclusive = sw_heat
    sw_heat.hass = hass
    sw_vent.hass = hass
    sw_heat.async_write_ha_state = lambda: None
    sw_vent.async_write_ha_state = lambda: None

    await sw_heat.async_turn_on()
    assert sw_heat.is_on is True
    assert sw_vent._opt_value is False

    # Cattura patch emessi dal thread paho tramite call_soon_threadsafe
    payload = json.dumps({
        "content": {
            "serviceType": "110F",
            "data": {
                "result": "1",
                "seq": "42",
                "reason": [{"modelId": "0", "code": "95"}, {"modelId": "4", "code": "95"}],
            },
        }
    }).encode("utf-8")
    coord._on_car_message(None, None, SimpleNamespace(payload=payload))
    await hass.async_block_till_done()
    sw_heat._handle_coordinator_update()
    sw_vent._handle_coordinator_update()

    assert sw_heat.is_on is False
    assert sw_heat._opt_value is None
    assert sw_vent._opt_value is None
    assert coord.is_car_in_use() is True


async def test_on_car_message_5a02_engine_1_not_masked_by_stale_realtime_and_odo_latch(hass) -> None:
    import json
    from types import SimpleNamespace

    coord = _make_coord(hass, poll_enabled=False)
    coord.data = {
        **coord.data,
        "realtime": {"hVoltageState": "1", "engineState": "0", "frontHVACState": "1", "vehicleSpeed": "0", "chargeGunState": "0", "odometer": "593"},
    }
    assert coord.is_car_in_use() is False

    # 5A02 porta engineState=1 mentre realtime è stantio (engineState=0) -> deve vincere msg_fields
    payload = json.dumps({"content": {"serviceType": "5A02", "data": {"engineState": "1"}}}).encode("utf-8")
    coord._on_car_message(None, None, SimpleNamespace(payload=payload))
    await hass.async_block_till_done()
    assert coord.is_car_in_use() is True

    # Reset con HV=0, poi verifica latch su solo incremento odometer durante HV=1 + pre-clima
    coord._on_probe_data({"hVoltageState": "0", "engineState": "0", "vehicleSpeed": "0"})
    assert coord.is_car_in_use() is False
    coord._on_probe_data({"hVoltageState": "1", "engineState": "0", "vehicleSpeed": "0", "frontHVACState": "1", "odometer": "593"})
    assert coord.is_car_in_use() is False
    coord._on_probe_data({"hVoltageState": "1", "engineState": "0", "vehicleSpeed": "0", "frontHVACState": "1", "odometer": "594"})
    assert coord.is_car_in_use() is True


async def test_climate_optimism_clears_on_rejected_climate_and_preserves_0_95(hass) -> None:
    import json
    from types import SimpleNamespace

    coord = _make_coord(hass)
    coord.data = {**coord.data, "fields": {"frontHVACState": "0"}, "last_seen": "t0"}
    coord.async_send_command = AsyncMock(return_value="ok")

    cli = LepasClimate(coord)
    cli.hass = hass
    cli.async_write_ha_state = lambda: None

    await cli.async_turn_on()
    assert cli.hvac_mode == HVACMode.HEAT_COOL

    # Push MQTT [0:95] solo -> preserva ottimismo clima
    ack_ok = json.dumps({"content": {"serviceType": "110F", "data": {"result": "1", "reason": [{"modelId": "0", "code": "95"}]}}}).encode("utf-8")
    coord._on_car_message(None, None, SimpleNamespace(payload=ack_ok))
    await hass.async_block_till_done()
    cli._handle_coordinator_update()
    assert cli._opt_on is True

    # Push MQTT con errore esplicito modulo 0 + result "0" -> annulla ottimismo clima
    ack_fail = json.dumps({"content": {"serviceType": "110F", "data": {"result": "0", "reason": [{"modelId": "0", "code": "8"}, {"modelId": "4", "code": "95"}]}}}).encode("utf-8")
    coord._on_car_message(None, None, SimpleNamespace(payload=ack_fail))
    await hass.async_block_till_done()
    cli._handle_coordinator_update()
    assert cli._opt_on is None
    assert cli.hvac_mode == HVACMode.OFF
```

- [ ] **Step 2: Eseguire pytest sui nuovi test per confermare RED**

Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_car_in_use_optimism.py -q --tb=short`
Expected: FAIL (`AttributeError: type object 'LepasCoordinator' has no attribute '_extract_rejected_fields'`, `is_car_in_use` missing, etc.).

- [ ] **Step 3: Implementare i cambiamenti in `coordinator.py`, `entity.py`, `switch.py`, `climate.py`, `binary_sensor.py`**

1. **`custom_components/lepas/coordinator.py`**:
   - Subito dopo `REASON_MODULI` (L193-203), aggiungere `REASON_FIELD_MAP`:
     ```python
     REASON_FIELD_MAP: dict[str, tuple[str, ...]] = {
         "4": ("dSeatHeatingState",),
         "5": ("pSeatHeatingState", "lSeatHeatingState2", "rSeatHeatingState2"),
         "6": ("pSeatHeatingState", "lSeatHeatingState2", "rSeatHeatingState2"),
         "8": ("pSeatHeatingState", "lSeatHeatingState2", "rSeatHeatingState2"),
         "9": ("dSeatVentilateState",),
         "10": ("pSeatVentilateState", "lSeatVentilateState2", "rSeatVentilateState2"),
         "11": ("pSeatVentilateState", "lSeatVentilateState2", "rSeatVentilateState2"),
         "13": ("pSeatVentilateState", "lSeatVentilateState2", "rSeatVentilateState2"),
     }
     ```
   - In `__init__` (L402-460): aggiungere `"cmd_rejected_fields": frozenset()`, `"cmd_rejected_other": False`, `"car_in_use": False` a `self.data`, e inizializzare `self._hv_lock: threading.Lock = threading.Lock()`, `self._hv_session_in_use: bool = False` e `self._hv_session_start_odo: float | None = None`.
   - Aggiungere `@staticmethod def _extract_rejected_fields(reason, result: str = "") -> tuple[frozenset[str], bool]`:
     - Se `not reason` o `LepasCoordinator._solo_clima(reason)`: ritorna `(frozenset(), False)`.
     - Se `not isinstance(reason, (list, tuple))` o `not all(isinstance(v, dict) for v in reason)`: ritorna `(frozenset(), True)`.
     - Raccoglie `fields: set[str]`, `other = False`. Per ogni `voce`: `mid = str(voce.get("modelId", ""))`, `code = str(voce.get("code", ""))`.
       - Se `mid in REASON_FIELD_MAP`: `fields.update(REASON_FIELD_MAP[mid])`
       - Elif `mid == "0"`: se `code != "95"` e `str(result).strip() not in ("1", "2", "5", "")`: `fields.add("frontHVACState")`
       - Else: `other = True`
     - Ritorna `(frozenset(fields), other)`.
   - Aggiungere `_evaluate_car_in_use(self, rt: dict | None, fields: dict | None, *, msg_fields: dict | None = None, comfort_rejected: bool = False) -> bool` (usando `with self._hv_lock:` esclusivamente intorno a lettura/mutazione di `_hv_session_in_use` e `_hv_session_start_odo`, precedenza `msg_fields > rt > fields` quando `msg_fields` è passato da `_on_car_message` e `rt > fields` da `_on_probe_data`, latch su `eng_on`, `speed_pos`, `not plugged and not hvac_on`, porta aperta, incremento `odometer > _hv_session_start_odo`, `comfort_rejected`; reset quando `hv_on is False and not eng_on and not speed_pos`) e `is_car_in_use(self) -> bool` (che legge `bool(self._hv_session_in_use)` sotto `with self._hv_lock:` in modo sincrono e deterministico).
   - Aggiungere `@callback def _schedule_probe_on_loop(self) -> None` e `async def _run_guarded_probe(self) -> None` che eseguono la verifica di `self._timers.closing`, `self.poll_enabled`, `self._poll_busy` sul loop HA; `_schedule_probe_on_loop` imposta `self._poll_busy = True` sincronamente prima di `self.hass.async_create_task(self._run_guarded_probe())` (rollback in `except`, rilascio in `finally: self._poll_busy = False` dentro `_run_guarded_probe`).
   - In `_on_car_message` (L1926-1978):
     - Impostare `patch["cmd_rejected_fields"] = frozenset()` e `patch["cmd_rejected_other"] = False` di default.
     - Se `is_confirmation`: calcolare `rej_fields, rej_other = self._extract_rejected_fields(data.get("reason"), str(data.get("result", "")))`; assegnarli a `patch`; valutare `patch["car_in_use"] = self._evaluate_car_in_use((self.data or {}).get("realtime"), fields_copy, msg_fields=msg_fields, comfort_rejected=bool(rej_fields or rej_other))`.
     - Se `not is_confirmation`: valutare `patch["car_in_use"] = self._evaluate_car_in_use((self.data or {}).get("realtime"), fields_copy, msg_fields=msg_fields)`.
     - Se `is_confirmation and (rej_fields or rej_other)`: chiamare `self.hass.loop.call_soon_threadsafe(self._schedule_probe_on_loop)`.
   - In `_on_probe_data` (L2686-2691): calcolare `patch["car_in_use"] = self._evaluate_car_in_use(rt_copy, fields_copy)`.
   - In `_hv_followup_cb` (L2600-2603):
     ```python
     async def _hv_followup_cb(self, _now) -> None:
         self._timers.cancel(HV_POLL)
         if self._timers.closing or not self.poll_enabled:
             return
         if self._poll_busy:
             self._arm_hv_followup()
             return
         self._poll_busy = True
         try:
             await self.async_probe(force=True)
         except Exception as err:  # noqa: BLE001
             _LOGGER.debug("[hv-followup] lettura realtime non riuscita: %s", err)
         finally:
             self._poll_busy = False
     ```

2. **`custom_components/lepas/entity.py`**:
   - In `LepasOptimisticMixin`: aggiungere `_rifiuto_arrivato(self) -> bool` che controlla `last_seen != self._opt_anchor` e `(any(k in (data.get("cmd_rejected_fields") or ()) for k in self._opt_keys) or bool(data.get("cmd_rejected_other")))` quando `self._opt_keys` è non vuoto; chiamare `self._rifiuto_arrivato()` dentro `_verita_arrivata()`.

3. **`custom_components/lepas/switch.py`**:
   - In `LepasComfortSwitch`: aggiungere `_handle_coordinator_update(self) -> None` che prima di `super()._handle_coordinator_update()` controlla se `self._opt_value is not None` e `self._rifiuto_arrivato()`, salva `anchor = self._opt_anchor`, lascia `super()._handle_coordinator_update()` azzerare `self`, e se `_exclusive` aveva `_opt_value is not None` e `_opt_anchor == anchor` chiama `self._exclusive._clear_optimistic()` (e `async_write_ha_state` se montato). (Nota `AB-LEP-007`: nessun uso di `_state_lock`.)

4. **`custom_components/lepas/climate.py`**:
   - In `LepasClimate`: aggiungere `@property def extra_state_attributes(self) -> dict[str, object] | None` che espone `{"car_in_use": bool(fn())}` se `callable(getattr(self.coordinator, "is_car_in_use", None))`.
   - In `_handle_coordinator_update` (L152-161): azzerare `_opt_on`/`_opt_anchor`/`_opt_at` anche quando `last_seen != self._opt_anchor` e (`CAMPO_CLIMA in (data.get("cmd_rejected_fields") or ())` or `bool(data.get("cmd_rejected_other"))`).

5. **`custom_components/lepas/binary_sensor.py`**:
   - In `LepasRealtimeBinary`: aggiungere `@property def extra_state_attributes(self) -> dict[str, object] | None`: se `self._field == "hVoltageState"`, ritorna `{"car_in_use": bool(fn())}` (se `is_car_in_use` callable), altrimenti `None`.

- [ ] **Step 4: Eseguire pytest sui test nuovi + regressione backend**

Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_car_in_use_optimism.py tests/test_entity_count.py -q --tb=short`
Expected: PASS.

---

### Task 2: Frontend `lepas-card.js` — Tab Clima (`carInUseBanner`, controlli disabilitati, `cmdResultBadge`) & UX Partenze Opzione 1 + Release `v1.25.0`

**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js:1-92`, `130-638`, `1065-1135`, `1720-1730`, `1930-1946`, `2170-2245`, `2785-2870`, `2962-2968`, `3476-3555`, `3733-3847`
- Modify: `tests/lepas_card.test.mjs`
- Modify: `tests/test_lovelace_card.py`
- Modify: `custom_components/lepas/manifest.json`
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes from HA entities:
  - `climate.lepas_climate.attributes.car_in_use` (`boolean`)
  - `binary_sensor.lepas_high_voltage_active.attributes.car_in_use` (`boolean`)
  - `sensor.lepas_next_departure.state` / `attributes`
  - `sensor.lepas_scheduled_departure.attributes` (`attiva`, `orario`, `giorni`, `has_pending_changes`, `synced_with_ha`)
  - `sensor.lepas_command_result` (`cmdResultBadge`)
- Produces in DOM (`LepasCard`):
  - `[data-bind="carInUseBanner"]` in `panel[data-panel="climate"]`
  - `[data-bind="cmdResultBadge"]` presente sia in `panel[data-panel="overview"]` sia in `panel[data-panel="climate"]`
  - Controlli comfort tab Clima disabilitati (`disabled = true`) quando `carInUse === true`
  - Riga 1 partenze: `t.nextDeparture` (`Prossima partenza` / `Next departure` / `Volgend vertrek`)
  - Riga 2 partenze: `t.onCar` (`Su auto` / `On car` / `In auto`) con stato `Sincronizzata` (`.is-emerald`) / `Da applicare (auto: ...)` (`.is-amber`) / `Disattivata`

- [ ] **Step 1: Scrivere/aggiornare i test JS in `tests/lepas_card.test.mjs` (RED)**

1. Aggiornare i test partenze esistenti in `tests/lepas_card.test.mjs` (`L1786-L1856` e `L2410-L2451`, previa verifica `grep` su `departureStatus`/`carDeparturePlan`/`noScheduledDeparture`/`nextDepText`/`schedDepText`) al nuovo contratto Opzione 1 (`Prossima partenza` + `Su auto` con `Sincronizzata` / `Da applicare (auto: ...)` / `Disattivata`) e aggiornare `requiredKeys` i18n (`onCar`, `syncedDep`, `toApplyCarPrefix`, `carWord`, `carOff`, `depDisabled`, `carInUseBanner`, mantenendo comunque le chiavi legacy in `I18N`).
2. Aggiungere nuovo test `v1.25.0`:
   - `test("v1.25.0 Climate tab car_in_use banner + disabled comfort controls + cmdResultBadge sync in Climate tab")`:
     - Con `climate.lepas_climate` avente `car_in_use: true` (e test separato via `binary_sensor.lepas_high_voltage_active` con `car_in_use: true`): verifica `carInUseBanner` visibile (`hidden === false`), tutti i bottoni comfort in `[data-panel="climate"]` (`climateToggleBtn`, `temp_down`, `temp_up`, `climate_duration`, `coolAllBtn`, `heatAllBtn`, `[data-defrost-btn]`, `[data-seat-btn]`) con `disabled === true`, classe `is-car-in-use` presente e `data-in-use-label` valorizzato sui bottoni larghi (`climateToggleBtn`, macro, defrost), click ignorato (0 `callService`).
     - Sulla **stessa** istanza renderizzata, aggiorna `card.hass` con `car_in_use: false`: verifica banner nascosto (`hidden === true`), tutti i bottoni comfort riabilitati (`disabled === false`, classe `is-car-in-use` rimossa) e nuovamente cliccabili.
     - Verifica che `sensor.lepas_command_result` aggiornato (es. `"Eseguito solo in parte ⚠️ — sedile guida riscaldato"`) popoli **entrambi** i `[data-bind="cmdResultBadge"]` (Plancia e Clima) con classe `.is-coral` e testo non vuoto.
   - `test("v1.25.0 Departure UX Option 1: Prossima partenza + Su auto states (Sincronizzata / Da applicare / Disattivata)")`:
     - Caso sincronizzato (`attiva: true`, `has_pending_changes: false`, `synced_with_ha: true`): riga 1 = `"Oggi 13:25 (clima 13:10)"`, riga 2 = `"Sincronizzata"` con classe `.is-emerald` (senza ripetere l'orario).
     - Caso pending con auto attiva (`attiva: true`, `orario: "06:35"`, `has_pending_changes: true`, `synced_with_ha: false`): riga 2 = `"Da applicare (auto: 06:35)"` con classe `.is-amber`.
     - Caso pending con auto spenta (`attiva: false`, `has_pending_changes: true`): riga 2 = `"Da applicare (auto: spenta)"` con classe `.is-amber`.
     - Caso tutto spento (`attiva: false`, `has_pending_changes: false`, `synced_with_ha: true`): riga 1 = `"Disattivata"`, riga 2 = `"Disattivata"`.

- [ ] **Step 2: Eseguire `node --test tests/lepas_card.test.mjs` per confermare RED**

Run: `node --test tests/lepas_card.test.mjs`
Expected: FAIL sui nuovi test e su `CARD_VERSION` / `v1.25.0`.

- [ ] **Step 3: Implementare le modifiche in `lepas-card.js` e aggiornare versioning `1.25.0`**

1. In `custom_components/lepas/lovelace/lepas-card.js`:
   - Versione `1.25.0` in commento header, `CARD_VERSION`, `HERO_IMAGES`, `DEFAULT_HERO`, `LepasCardEditor` placeholder.
   - `I18N` (`it`, `en`, `nl`): aggiungere `carInUseBanner`, `inUseShort` (`"Auto in uso"` / `"Car in use"` / `"In gebruik"`), `onCar`, `syncedDep`, `toApplyCarPrefix`, `carWord`, `carOff`, `depDisabled`.
   - `buildStyles()`: separare `.ctrl-btn:disabled` (`opacity: 0.55; cursor: not-allowed;`), `.chip-btn:disabled` (`opacity: 0.55; cursor: not-allowed; position: relative; overflow: hidden;`), `.ctrl-btn.is-pending` (`opacity: 0.58; cursor: wait;`); aggiungere `.ctrl-btn.is-car-in-use::after` / `.chip-btn.is-car-in-use::after` (velo scuro `rgba(17, 19, 23, 0.72)` con icona stop `⊘` centrata e `attr(data-in-use-label)` sui bottoni larghi con `data-in-use-label`), `.info-banner` / `.info-banner.is-amber`, `.climate-meta-bar`, `.dep-summary-row .info-val.is-emerald`, `.dep-summary-row .info-val.is-amber`.
   - `_handleClick` & `_triggerAction`: ignorare se `actionEl.disabled` (o `target.closest("button:disabled")`).
   - `_renderInner`:
     - Cercare `var hvActive = this._findDomain(items, "binary_sensor", "high_voltage_active", "rt_alta_tensione");` e includerlo nel VM.
     - In `climateHtml`: aggiungere in testa `<div class="info-banner is-amber hidden" role="status" data-bind="carInUseBanner" hidden></div>` + `<div class="climate-meta-bar hidden" data-bind="climateCmdBar"><span class="badge hidden" data-bind="cmdResultBadge"></span></div>`.
     - In `depSummaryHtml`: Riga 1 usa `t.nextDeparture` (`Prossima partenza`), Riga 2 usa `t.onCar` (`Su auto`).
   - `_applyBindingsInner`:
     - `cmdResultBadge`: aggiornare tutti gli elementi trovati via `root.querySelectorAll('[data-bind="cmdResultBadge"]')` e sincronizzare `climateCmdBar` (`classList.toggle("hidden", !outcome)`).
     - `carInUse`: `Boolean((vm.climate && vm.climate.s && vm.climate.s.attributes && vm.climate.s.attributes.car_in_use === true) || (vm.hvActive && vm.hvActive.s && vm.hvActive.s.attributes && vm.hvActive.s.attributes.car_in_use === true))`. Aggiornare `carInUseBanner` (`textContent = t.carInUseBanner`, `hidden = !carInUse`, `.hidden`). Nella sezione Climate details: su `climateToggleBtn` (gestito prima da `_applyBtnState`) impostare `btn.disabled = this._pendingKeys.has("climate_toggle") || carInUse`, mentre su tutti gli altri bottoni comfort in `[data-panel="climate"]` (`temp_down`, `temp_up`, `[data-action-id="climate_duration"]`, `coolAllBtn`, `heatAllBtn`, `[data-defrost-btn]`, `[data-seat-btn]`) impostare direttamente `btn.disabled = carInUse`; su tutti questi bottoni impostare `btn.classList.toggle("is-car-in-use", carInUse)`, `btn.setAttribute("aria-disabled", btn.disabled ? "true" : "false")`, e `data-in-use-label` (`t.inUseShort`) sui bottoni larghi (`climateToggleBtn`, `coolAllBtn`, `heatAllBtn`, `[data-defrost-btn]`) quando `carInUse` è `true` (rimuovendolo quando è `false`).
     - Sezione Partenze (`nextDepText` + `schedDepText`): in `nextDepText` (L3737-L3746) rimuovere il ramo `else if (!haHasActiveDep && carActive) { nextDepEl.textContent = t.departureActive; }` lasciando solo `_dead` → `"—"` altrimenti `vm.nextDep.s.state`; dichiarare `hasPending` e `isSynced` **prima** di `if (schedDepTxt && vm.schedDep)` (subito dopo `carActive`), rimuovere sempre entrambe `.is-emerald` e `.is-amber` prima di impostare lo stato del ramo corrente, ordinando i rami come Spec §2.3.2 (`_dead` → `carActive && hasPending === false && isSynced === true` [`.is-emerald`] → `hasPending === true || isSynced === false` [`.is-amber`, gestendo anche fallback `sdRawAttrs.orario` assente] → `hasPending === null && carActive` → `t.depDisabled`).
2. Aggiornare `custom_components/lepas/manifest.json` (`1.25.0`), `pyproject.toml` (`1.25.0`), `tests/test_lovelace_card.py` (check `1.25.0`), `CHANGELOG.md` (`## v1.25.0 — 2026-11-19` bilingue IT/EN).

- [ ] **Step 4: Eseguire test JS + Python card + full suite + ruff**

Run:
- `node --test tests/lepas_card.test.mjs`
- `/home/federico/.local/bin/uv run --with pytest pytest -q --tb=short --maxfail=2`
- `/home/federico/.local/bin/uv run ruff check custom_components/ tests/`
- `/home/federico/.local/bin/uv run ruff format --check custom_components/ tests/`
Expected: PASS su tutti i controlli, zero violazioni ES5 (`?.` / `??`).
