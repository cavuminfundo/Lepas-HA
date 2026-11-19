"""Tests for ECU reason optimism cancellation and car-in-use detection."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fixtures as FX
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.climate import HVACMode

from custom_components.lepas.binary_sensor import LepasRealtimeBinary
from custom_components.lepas.climate import LepasClimate
from custom_components.lepas.const import CONF_VIN, DOMAIN
from custom_components.lepas.coordinator import LepasCoordinator
from custom_components.lepas.switch import LepasComfortSwitch
from custom_components.lepas.timers import HV_POLL


def make_entry(entry_id: str = "car_in_use_entry") -> MockConfigEntry:
    """Create a synthetic Lepas ConfigEntry for coordinator unit tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=f"Lepas ({FX.VIN})",
        unique_id=FX.VIN,
        data={
            CONF_VIN: FX.VIN,
            "tuserid": FX.TUSERID,
            "email": FX.EMAIL,
            "pin": FX.PIN,
        },
        entry_id=entry_id,
    )


def _make_coord(hass, *, poll_enabled: bool = False) -> LepasCoordinator:
    entry = make_entry()
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    coord.poll_enabled = poll_enabled
    return coord


def _make_seat_pair(coord, hass) -> tuple[LepasComfortSwitch, LepasComfortSwitch]:
    sw_heat = LepasComfortSwitch(
        coord,
        "Lepas Sedile guida riscaldato",
        "driver_seat_heating",
        "dSeatHeatingState",
        "sedile_guida_caldo",
        "sedile_guida_caldo_off",
        "mdi:car-seat-heater",
    )
    sw_vent = LepasComfortSwitch(
        coord,
        "Lepas Sedile guida ventilato",
        "driver_seat_ventilation",
        "dSeatVentilateState",
        "sedile_guida_aria",
        "sedile_guida_aria_off",
        "mdi:car-seat-cooler",
    )
    sw_heat._exclusive = sw_vent
    sw_vent._exclusive = sw_heat
    sw_heat.hass = hass
    sw_vent.hass = hass
    sw_heat.async_write_ha_state = lambda: None
    sw_vent.async_write_ha_state = lambda: None
    return sw_heat, sw_vent


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

    sw_heat, sw_vent = _make_seat_pair(coord, hass)

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


async def test_seat_heating_rejection_reverse_update_order_and_cmd_rejected_other(hass) -> None:
    coord = _make_coord(hass)
    coord._fields["dSeatHeatingState"] = "0"
    coord.data = {**coord.data, "fields": {"dSeatHeatingState": "0"}, "last_seen": "t0"}
    coord.async_send_command = AsyncMock(return_value="ok")

    sw_heat, sw_vent = _make_seat_pair(coord, hass)
    await sw_heat.async_turn_on()
    assert sw_vent._opt_value is False

    coord._apply_update({
        "last_seen": "t1",
        "msg_fields": {},
        "cmd_rejected_fields": frozenset(),
        "cmd_rejected_other": True,
    })
    # Reverse listener order: twin updates before rejected switch
    sw_vent._handle_coordinator_update()
    sw_heat._handle_coordinator_update()

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


def test_car_in_use_door_open_during_hv_latches(hass) -> None:
    coord = _make_coord(hass)
    coord._on_probe_data({
        "hVoltageState": "1",
        "engineState": "0",
        "vehicleSpeed": "0",
        "chargeGunState": "0",
        "frontHVACState": "1",
        "doorLock": "1",
        "frontLeftDoor": "1",
    })
    assert coord.is_car_in_use() is True


def test_car_in_use_attribute_exposed_on_hv_binary_and_climate(hass) -> None:
    coord = _make_coord(hass)
    coord._on_probe_data({
        "hVoltageState": "1",
        "engineState": "1",
        "vehicleSpeed": "0",
        "chargeGunState": "0",
        "frontHVACState": "0",
    })
    hv_ent = LepasRealtimeBinary(
        coord, "Alta tensione attiva", "alta_tensione", "hVoltageState", BinarySensorDeviceClass.RUNNING
    )
    tyre_ent = LepasRealtimeBinary(
        coord, "Avviso gomma ant. SX", "avviso_gomma_ant_sx", "lFrontTyreCall", BinarySensorDeviceClass.PROBLEM
    )
    cli_ent = LepasClimate(coord)
    assert hv_ent.extra_state_attributes == {"car_in_use": True}
    assert tyre_ent.extra_state_attributes is None
    assert cli_ent.extra_state_attributes == {"car_in_use": True}


async def test_hv_followup_cb_respects_poll_busy_and_rearms(hass) -> None:
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
    coord = _make_coord(hass, poll_enabled=False)
    coord.async_probe = AsyncMock()
    coord.data = {
        **coord.data,
        "realtime": {"hVoltageState": "1", "frontHVACState": "1", "vehicleSpeed": "0", "chargeGunState": "0"},
        "fields": {"dSeatHeatingState": "0"},
        "last_seen": "t0",
    }
    coord._fields["dSeatHeatingState"] = "0"
    coord.async_send_command = AsyncMock(return_value="ok")

    sw_heat, sw_vent = _make_seat_pair(coord, hass)

    await sw_heat.async_turn_on()
    assert sw_heat.is_on is True
    assert sw_vent._opt_value is False

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
    try:
        coord._on_car_message(None, None, SimpleNamespace(payload=payload))
        await hass.async_block_till_done()
        sw_heat._handle_coordinator_update()
        sw_vent._handle_coordinator_update()

        assert sw_heat.is_on is False
        assert sw_heat._opt_value is None
        assert sw_vent._opt_value is None
        assert coord.is_car_in_use() is True
    finally:
        coord._timers.close()


async def test_on_car_message_5a02_engine_1_not_masked_by_stale_realtime_and_odo_latch(hass) -> None:
    coord = _make_coord(hass, poll_enabled=False)
    coord.async_probe = AsyncMock()
    coord.data = {
        **coord.data,
        "realtime": {
            "hVoltageState": "1",
            "engineState": "0",
            "frontHVACState": "1",
            "vehicleSpeed": "0",
            "chargeGunState": "0",
            "odometer": "593",
        },
    }
    assert coord.is_car_in_use() is False

    # 5A02 reports engineState=1 while realtime is stale (engineState=0) -> msg_fields must win
    payload = json.dumps({"content": {"serviceType": "5A02", "data": {"engineState": "1"}}}).encode("utf-8")
    try:
        coord._on_car_message(None, None, SimpleNamespace(payload=payload))
        await hass.async_block_till_done()
        assert coord.is_car_in_use() is True

        # Reset with HV=0, then verify latch on odometer increase alone during HV=1 + pre-climate
        coord._on_probe_data({"hVoltageState": "0", "engineState": "0", "vehicleSpeed": "0"})
        assert coord.is_car_in_use() is False
        coord._on_probe_data({
            "hVoltageState": "1",
            "engineState": "0",
            "vehicleSpeed": "0",
            "frontHVACState": "1",
            "odometer": "593",
        })
        assert coord.is_car_in_use() is False
        coord._on_probe_data({
            "hVoltageState": "1",
            "engineState": "0",
            "vehicleSpeed": "0",
            "frontHVACState": "1",
            "odometer": "594",
        })
        assert coord.is_car_in_use() is True
    finally:
        coord._timers.close()


def test_car_in_use_clears_when_plugged_in_after_drive(hass) -> None:
    coord = _make_coord(hass)

    # 1. Driving latches car_in_use=True with start odometer 616
    coord._on_probe_data({
        "hVoltageState": "1",
        "engineState": "0",
        "vehicleSpeed": "57",
        "chargeGunState": "0",
        "frontHVACState": "1",
        "odometer": "616",
    })
    assert coord.is_car_in_use() is True

    # 2. Parked, door opened at 636 km -> still in use
    coord._on_probe_data({
        "hVoltageState": "1",
        "engineState": "0",
        "vehicleSpeed": "0",
        "chargeGunState": "0",
        "frontLeftDoor": "1",
        "odometer": "636",
    })
    assert coord.is_car_in_use() is True

    # 3. Doors closed and cable plugged in while hVoltageState stays 1 -> NOT in use
    coord._on_probe_data({
        "hVoltageState": "1",
        "engineState": "0",
        "vehicleSpeed": "0",
        "chargeGunState": "1",
        "frontLeftDoor": "0",
        "frontHVACState": "0",
        "odometer": "636",
    })
    assert coord.is_car_in_use() is False

    # 4. Subsequent remote pre-climate after unplugging at same 636 km stays NOT in use
    coord._on_probe_data({
        "hVoltageState": "1",
        "engineState": "0",
        "vehicleSpeed": "0",
        "chargeGunState": "0",
        "frontHVACState": "1",
        "odometer": "636",
    })
    assert coord.is_car_in_use() is False



async def test_climate_optimism_clears_on_rejected_climate_and_preserves_0_95(hass) -> None:
    coord = _make_coord(hass)
    coord.async_probe = AsyncMock()
    coord.data = {**coord.data, "fields": {"frontHVACState": "0"}, "last_seen": "t0"}
    coord.async_send_command = AsyncMock(return_value="ok")

    cli = LepasClimate(coord)
    cli.hass = hass
    cli.async_write_ha_state = lambda: None

    await cli.async_turn_on()
    assert cli.hvac_mode == HVACMode.HEAT_COOL

    try:
        # MQTT push [0:95] alone -> preserves climate optimism
        ack_ok = json.dumps({
            "content": {"serviceType": "110F", "data": {"result": "1", "reason": [{"modelId": "0", "code": "95"}]}}
        }).encode("utf-8")
        coord._on_car_message(None, None, SimpleNamespace(payload=ack_ok))
        await hass.async_block_till_done()
        cli._handle_coordinator_update()
        assert cli._opt_on is True

        # MQTT push with explicit module 0 error + result "0" -> clears climate optimism
        ack_fail = json.dumps({
            "content": {
                "serviceType": "110F",
                "data": {"result": "0", "reason": [{"modelId": "0", "code": "8"}, {"modelId": "4", "code": "95"}]},
            }
        }).encode("utf-8")
        coord._on_car_message(None, None, SimpleNamespace(payload=ack_fail))
        await hass.async_block_till_done()
        cli._handle_coordinator_update()
        assert cli._opt_on is None
        assert cli.hvac_mode == HVACMode.OFF
    finally:
        coord._timers.close()


async def test_schedule_probe_on_loop_guards_and_rollback(hass, monkeypatch) -> None:
    coord = _make_coord(hass, poll_enabled=True)
    coord.async_probe = AsyncMock()
    coord._last_msg_ts = time.time()

    try:
        # Busy guard skips probe
        coord._poll_busy = True
        coord._schedule_probe_on_loop()
        await hass.async_block_till_done()
        coord.async_probe.assert_not_awaited()
        coord._poll_busy = False

        # Rollback _poll_busy when task creation fails
        def _boom(_coro):
            _coro.close()
            raise RuntimeError("loop broken")

        with monkeypatch.context() as mp:
            mp.setattr(hass, "async_create_task", _boom)
            with pytest.raises(RuntimeError, match="loop broken"):
                coord._schedule_probe_on_loop()
            assert coord._poll_busy is False

        # Rejection push schedules guarded probe when poll_enabled=True
        payload = json.dumps({
            "content": {
                "serviceType": "110F",
                "data": {"result": "1", "reason": [{"modelId": "4", "code": "95"}]},
            }
        }).encode("utf-8")
        coord._on_car_message(None, None, SimpleNamespace(payload=payload))
        await hass.async_block_till_done()
        coord.async_probe.assert_awaited_once_with(force=True)
        assert coord._poll_busy is False
    finally:
        coord._timers.close()
