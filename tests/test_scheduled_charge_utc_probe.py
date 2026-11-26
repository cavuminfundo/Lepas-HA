"""Falsifiable tests for Phase 1: scheduled charging UTC alignment, 15m floor, CMD_PROBE, deferred 2132 warning, and appointmentChargeState guard."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
import logging
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache

import fixtures as FX
from custom_components.lepas import coordinator as coord_mod
from custom_components.lepas import scheduler as sched_mod
from custom_components.lepas.const import (
    CHARGE_PROBE_COMMANDS,
    CONF_PIN,
    CONF_TUSERID,
    CONF_VIN,
    DATA_CAPS_PROBED_V5,
    DOMAIN,
)
from custom_components.lepas.core import commands as CMD
from custom_components.lepas.scheduler import (
    CHARGE_START_STEP_MINUTES,
    align_charge_start_minutes,
    compute_charge_start_datetime,
    compute_charge_start_for_departure,
    decode_charge_appoint_plan,
    resolve_tzinfo,
)
from custom_components.lepas.sensor import LepasScheduledChargingWindowSensor
from custom_components.lepas.switch import LepasScheduledChargeSwitch
from custom_components.lepas.timers import CMD_PROBE


class _FixedWinterDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        base = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
        return base.astimezone(tz) if tz is not None else base.replace(tzinfo=None)


def _patch_io(monkeypatch) -> list[tuple[str, dict | None]]:
    sent: list[tuple[str, dict | None]] = []

    async def fake_send(self, key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    async def no_backfill(self) -> None:
        return None

    monkeypatch.setattr(coord_mod.LepasCoordinator, "_provision_certs", lambda self: (True, "ok"))
    monkeypatch.setattr(coord_mod.LepasCoordinator, "_connect_car", lambda self: None)
    monkeypatch.setattr(coord_mod.LepasCoordinator, "async_start_keepalive", lambda self: None)
    monkeypatch.setattr(coord_mod.LepasCoordinator, "async_start_telemetry_poll", lambda self: None)
    monkeypatch.setattr(coord_mod.LepasCoordinator, "async_start_drive_watch", lambda self: None)
    monkeypatch.setattr(coord_mod.LepasCoordinator, "async_ensure_vehicle_identity", no_backfill)
    monkeypatch.setattr(coord_mod.LepasCoordinator, "async_send_command", fake_send)
    return sent


async def _setup_entry(hass: HomeAssistant, *, entry_id: str = "phase1_entry") -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Lepas ({FX.VIN})",
        unique_id=FX.VIN,
        data={
            CONF_VIN: FX.VIN,
            CONF_TUSERID: FX.TUSERID,
            "email": FX.EMAIL,
            CONF_PIN: FX.PIN,
            DATA_CAPS_PROBED_V5: True,
        },
        entry_id=entry_id,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def test_charge_plan_cet_cest_and_midnight_rollover(hass: HomeAssistant, monkeypatch) -> None:
    assert CHARGE_START_STEP_MINUTES == 15
    assert align_charge_start_minutes(320) == 315
    assert align_charge_start_minutes(0) == 0
    assert align_charge_start_minutes(1439) == 1425
    assert compute_charge_start_for_departure(7 * 60 + 20, 2) == 315

    for bad_min in (True, False):
        with pytest.raises(ValueError):
            align_charge_start_minutes(bad_min)
    for bad_step in (0, -15, True):
        with pytest.raises(ValueError):
            align_charge_start_minutes(320, step=bad_step)

    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_VIN: FX.VIN, CONF_TUSERID: FX.TUSERID, "email": FX.EMAIL, CONF_PIN: FX.PIN},
        entry_id="cet_cest_coord",
    )
    entry.add_to_hass(hass)
    coord = coord_mod.LepasCoordinator(hass, entry)

    # CET (UTC+1): 05:20 local -> 05:15 local -> 04:15 UTC (255)
    cet_date = date(2026, 11, 16)
    plan_cet = coord.build_charge_appoint_plan(
        local_start_minutes=320,
        duration_hours=6,
        local_days=[1, 2, 3],
        switch_status=1,
        ref_date=cet_date,
    )
    assert plan_cet == {
        "cycleData": [1, 2, 3],
        "startTime": 255,
        "switchStatus": 1,
        "timeConsuming": 360,
    }

    # Midnight rollover in CET: 00:15 local [1] -> 23:15 UTC (1395) [7]
    plan_midnight = coord.build_charge_appoint_plan(
        local_start_minutes=15,
        duration_hours=6,
        local_days=[1],
        switch_status=1,
        ref_date=cet_date,
    )
    assert plan_midnight["startTime"] == 1395
    assert plan_midnight["cycleData"] == [7]

    decoded_midnight = decode_charge_appoint_plan(plan_midnight, rome, ref_date=cet_date)
    assert decoded_midnight == {"start_minutes": 15, "duration_minutes": 360, "days": [1]}

    # CEST (UTC+2): 05:20 local -> 05:15 local -> 03:15 UTC (195)
    cest_date = date(2026, 7, 15)
    plan_cest = coord.build_charge_appoint_plan(
        local_start_minutes=320,
        duration_hours=6,
        local_days=[1],
        switch_status=1,
        ref_date=cest_date,
    )
    assert plan_cest["startTime"] == 195
    assert decode_charge_appoint_plan(plan_cest, rome, ref_date=cest_date) == {
        "start_minutes": 315,
        "duration_minutes": 360,
        "days": [1],
    }

    # Boolean rejection in decode_charge_appoint_plan
    assert decode_charge_appoint_plan(
        {"startTime": True, "timeConsuming": False, "cycleData": [1]}, rome, ref_date=cet_date
    ) == {"start_minutes": None, "duration_minutes": None, "days": [1]}
    assert decode_charge_appoint_plan({"startTime": True, "timeConsuming": False}, rome) is None

    # Dirty cycleData preserves orario_sull_auto on switch and returns None in _synced_with_car
    monkeypatch.setattr(sched_mod, "datetime", _FixedWinterDatetime)
    coord.data = {
        "fields": {
            "chargeAppointPlans": [
                {"startTime": "1395", "timeConsuming": "360", "cycleData": [1]}
            ]
        }
    }
    sw = LepasScheduledChargeSwitch.__new__(LepasScheduledChargeSwitch)
    sw.coordinator = coord
    sw.hass = hass

    coord.data["fields"]["chargeAppointPlans"] = [
        {"startTime": "255", "timeConsuming": "360", "cycleData": ["bad_day"]}
    ]
    attrs_dirty = sw.extra_state_attributes
    assert attrs_dirty is not None
    assert attrs_dirty["orario_sull_auto"] == "05:15"
    assert "giorni_sull_auto" not in attrs_dirty

    sensor = LepasScheduledChargingWindowSensor.__new__(LepasScheduledChargingWindowSensor)
    sensor.coordinator = coord
    sensor.hass = hass
    assert sensor._synced_with_car(315, 6, [1, 2, 3]) is None

    # Empty cycleData == [] yields False (not None) in _synced_with_car
    coord.data["fields"]["chargeAppointPlans"] = [
        {"startTime": "255", "timeConsuming": "360", "cycleData": []}
    ]
    assert sensor._synced_with_car(315, 6, [1, 2, 3]) is False

    # Midnight rollover plan matches _synced_with_car() is True
    coord.charge_start_minutes = 15
    coord.charge_duration_hours = 6
    coord.charge_days = [1]
    coord.data["fields"]["chargeAppointPlans"] = [plan_midnight]
    assert sensor._synced_with_car(15, 6, [1]) is True

    # compute_charge_start_datetime alignment
    dep_dt = datetime(2026, 11, 17, 7, 20, tzinfo=rome)
    assert compute_charge_start_datetime(dep_dt, 2) == datetime(2026, 11, 17, 5, 15, tzinfo=rome)


async def test_charge_time_entity_and_service_apply_false_floor_15m(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    sent = _patch_io(monkeypatch)
    mock_restore_cache(
        hass,
        [
            State("time.lepas_charge_start_time", "05:20:00"),
            State("time.lepas_departure_fri_time", "13:20:00"),
        ],
    )
    entry = await _setup_entry(hass, entry_id="floor_time_entry")
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        assert coord.charge_start_minutes == 315
        assert hass.states.get("time.lepas_charge_start_time").state == "05:15:00"
        assert hass.states.get("time.lepas_departure_fri_time").state == "13:20:00"
        assert coord.departure_weekly[5][1] == 13 * 60 + 20

        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_charge_start_time", "time": "06:44:00"},
            blocking=True,
        )
        assert coord.charge_start_minutes == 390
        assert hass.states.get("time.lepas_charge_start_time").state == "06:30:00"

        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_departure_fri_time", "time": "13:20:00"},
            blocking=True,
        )
        assert coord.departure_weekly[5][1] == 13 * 60 + 20
        assert hass.states.get("time.lepas_departure_fri_time").state == "13:20:00"

        await hass.services.async_call(
            DOMAIN,
            "set_charging_schedule",
            {"start_time": "05:20", "apply": False},
            blocking=True,
        )
        assert coord.charge_start_minutes == 315
        assert hass.states.get("time.lepas_charge_start_time").state == "05:15:00"
        assert sent == []
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


def test_stub_coordinator_plan_parity(monkeypatch) -> None:
    monkeypatch.setattr(sched_mod, "datetime", _FixedWinterDatetime)

    class CoordFinto:
        charge_start_minutes = 320
        charge_duration_hours = 6

        def effective_charge_days(self):
            return [1]

    assert resolve_tzinfo(None) == timezone.utc

    sw = LepasScheduledChargeSwitch.__new__(LepasScheduledChargeSwitch)
    sw.coordinator = CoordFinto()
    assert sw._plan(1) == {
        "cycleData": [1],
        "startTime": 315,
        "switchStatus": 1,
        "timeConsuming": 360,
    }

    CoordFinto.charge_start_minutes = 20
    sw.coordinator.hass = SimpleNamespace(config=SimpleNamespace(time_zone="Europe/Rome"))
    assert sw._plan(1) == {
        "cycleData": [7],
        "startTime": 1395,
        "switchStatus": 1,
        "timeConsuming": 360,
    }


async def test_charge_commands_arm_cmd_probe_in_timer_registry(
    hass: HomeAssistant, integrazione_avviata, cloud, monkeypatch
) -> None:
    coord = hass.data[DOMAIN][integrazione_avviata.entry_id]
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0)
    monkeypatch.setattr(coord, "async_probe", AsyncMock())
    cloud.on(
        "/tsp/v1/app/vmc/queryVehicleAuthority",
        {
            "code": "000000",
            "data": {
                "permissionList": [
                    {"id": 213, "state": 1},
                    {"id": 2132, "state": 1},
                    {"id": 220, "state": 1},
                    {"id": 204, "state": 1},
                    {"id": 2041, "state": 1},
                ]
            },
        },
    )
    cloud.on("/asc/vehicleControl/", code="A00079")

    assert CHARGE_PROBE_COMMANDS == frozenset({
        "ricarica_prog_on",
        "ricarica_prog_off",
        "ricarica_start",
        "ricarica_stop",
    })

    coord.poll_enabled = True
    for cmd_key in ("ricarica_prog_on", "ricarica_prog_off", "ricarica_start", "ricarica_stop"):
        coord._timers.cancel(CMD_PROBE)
        await coord.async_send_command(cmd_key)
        await hass.async_block_till_done()
        assert coord._timers.is_armed(CMD_PROBE), f"{cmd_key} must arm CMD_PROBE"

    # AB-LEP-018: clima_on must NEVER arm CMD_PROBE
    coord._timers.cancel(CMD_PROBE)
    await coord.async_send_command("clima_on")
    await hass.async_block_till_done()
    assert not coord._timers.is_armed(CMD_PROBE)

    # Disabled poll_enabled must never arm CMD_PROBE
    coord.poll_enabled = False
    await coord.async_send_command("ricarica_prog_on")
    await hass.async_block_till_done()
    assert not coord._timers.is_armed(CMD_PROBE)

    # CommandError must never arm CMD_PROBE
    coord.poll_enabled = True
    cloud.on("/asc/vehicleControl/chargeAppointControl", code="A00084")
    with pytest.raises(CMD.CommandError):
        await coord.async_send_command("ricarica_prog_on")
    await hass.async_block_till_done()
    assert not coord._timers.is_armed(CMD_PROBE)


async def test_cmd_probe_65s_does_not_clear_scheduled_charge_optimism(
    hass: HomeAssistant, integrazione_avviata, cloud, monkeypatch
) -> None:
    coord = hass.data[DOMAIN][integrazione_avviata.entry_id]
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0)
    cloud.on("/asc/vehicleControl/", code="A00079")
    coord._on_car_message(
        None,
        None,
        SimpleNamespace(
            payload=json.dumps(
                FX.telemetry_5a02(chargeAppointPlans="[{'switchStatus': '0', 'startTime': '255'}]")
            ).encode("utf-8"),
            topic="app/1/test/account/msgCenter/msg",
        ),
    )
    await hass.async_block_till_done()
    assert hass.states.get("switch.lepas_scheduled_charging").state == "off"

    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.lepas_scheduled_charging"},
        blocking=True,
    )
    sw = next(
        e
        for e in hass.data["entity_components"]["switch"].entities
        if isinstance(e, LepasScheduledChargeSwitch)
    )
    assert sw._opt_value is True
    assert sw.is_on is True
    assert hass.states.get("switch.lepas_scheduled_charging").state == "on"

    # Past 60s probe settle ceiling, realtime probe without chargeAppointPlans must NOT clear optimism
    sw._opt_at = time.monotonic() - 65
    coord._on_probe_data({"chargeState": "0", "chargingPower": "0"})
    await hass.async_block_till_done()
    assert sw._opt_value is True
    assert sw.is_on is True
    assert hass.states.get("switch.lepas_scheduled_charging").state == "on"

    # Real 5A02 chargeAppointPlans clears optimism
    coord._on_car_message(
        None,
        None,
        SimpleNamespace(
            payload=json.dumps(
                FX.telemetry_5a02(chargeAppointPlans="[{'switchStatus': '0', 'startTime': '255'}]")
            ).encode("utf-8"),
            topic="app/1/test/account/msgCenter/msg",
        ),
    )
    await hass.async_block_till_done()
    assert sw._opt_value is None
    assert hass.states.get("switch.lepas_scheduled_charging").state == "off"


async def test_ciclo_warning_deferred_and_single_on_retry(
    hass: HomeAssistant, integrazione_avviata, cloud, ctx, monkeypatch, caplog
) -> None:
    coord = hass.data[DOMAIN][integrazione_avviata.entry_id]
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0)
    perms_2132_denied = {
        "code": "000000",
        "data": {
            "permissionList": [
                {"id": 213, "state": 1},
                {"id": 2131, "state": 0},
                {"id": 2132, "state": 0},
            ]
        },
    }
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", perms_2132_denied)
    plan_params = {
        "mainSwitch": 1,
        "chargeAppointPlans": [
            {"cycleData": [1, 2, 3, 4, 5, 6, 7], "startTime": 255, "switchStatus": 1, "timeConsuming": 360}
        ],
    }

    # (a) Accepted with A00079 -> zero avvisa, clean cmd_status, DEBUG log without PII
    coord.ctx.permessi = None
    cloud.on("/asc/vehicleControl/chargeAppointControl", code="A00079")
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger="custom_components.lepas.core.commands"):
        await coord.async_send_command("ricarica_prog_on", plan_params)
    await hass.async_block_till_done()

    assert coord._note_cmd == []
    assert "non autorizza" not in coord.data["cmd_status"]
    assert "A00079" in coord.data["cmd_status"]
    debug_msgs = [
        r.getMessage()
        for r in caplog.records
        if r.levelno == logging.DEBUG and r.name == "custom_components.lepas.core.commands"
    ]
    assert any("non autorizza il ciclo" in m and "A00079" in m for m in debug_msgs)
    for rec in caplog.records:
        msg = rec.getMessage()
        assert FX.VIN not in msg
        assert FX.ACCESS_TOKEN not in msg
        assert FX.USER_TOKEN not in msg
        assert FX.TUSERID not in msg

    # (b) attempt==1 (riconia_taskid A00089) -> attempt==2 (A00084): avvisa called once before emit(out)
    ctx.permessi = {213: 1, 2131: 0, 2132: 0}
    seq_core = iter(["A00089", "A00084"])
    cloud.on(
        "/asc/vehicleControl/chargeAppointControl",
        response=lambda _p, _b: {"code": next(seq_core)},
    )
    events: list[tuple[str, str]] = []
    with pytest.raises(CMD.CommandError):
        CMD.send(
            ctx,
            "ricarica_prog_on",
            emit=lambda m: events.append(("emit", m)),
            params=plan_params,
            avvisa=lambda m: events.append(("avvisa", m)),
        )
    avvisa_events = [idx for idx, (kind, _msg) in enumerate(events) if kind == "avvisa"]
    assert len(avvisa_events) == 1
    assert avvisa_events[0] == len(events) - 2
    assert events[-1][0] == "emit"
    assert "A00084" in events[-1][1]
    assert "non autorizza il ciclo" in events[avvisa_events[0]][1]

    # End-to-end through coordinator populates cmd_status with A00084 + single cycle warning
    coord.ctx.permessi = {213: 1, 2131: 0, 2132: 0}
    seq_coord = iter(["A00089", "A00084"])
    cloud.on(
        "/asc/vehicleControl/chargeAppointControl",
        response=lambda _p, _b: {"code": next(seq_coord)},
    )
    with pytest.raises(CMD.CommandError):
        await coord.async_send_command("ricarica_prog_on", plan_params)
    await hass.async_block_till_done()
    assert len(coord._note_cmd) == 1
    assert "A00084" in coord.data["cmd_status"]
    assert "non autorizza il ciclo" in coord.data["cmd_status"]


async def test_scheduled_charge_switch_ignores_realtime_appointment_charge_state(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    mock_restore_cache(hass, [State("switch.lepas_scheduled_charging", "on")])
    entry = await _setup_entry(hass, entry_id="ignore_rt_appt_state")
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        assert hass.states.get("switch.lepas_scheduled_charging").state == "on"

        for val in ("0", "1", "2"):
            coord._on_probe_data({"appointmentChargeState": val})
            await hass.async_block_till_done()
            assert hass.states.get("switch.lepas_scheduled_charging").state == "on"

        coord._update(
            {"fields": {"chargeAppointPlans": [{"switchStatus": "0", "startTime": "255"}]}}
        )
        await hass.async_block_till_done()
        assert hass.states.get("switch.lepas_scheduled_charging").state == "off"
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
