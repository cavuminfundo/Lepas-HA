"""Tests for native departure scheduling, battery pack heat, climate extras & services."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import date, datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import fixtures as FX
import pytest
from homeassistant.core import State
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache

from custom_components.lepas.const import (
    COMMANDS_AS_RICH_ENTITY,
    CONF_PIN,
    CONF_TUSERID,
    CONF_VIN,
    DATA_CAPS_PROBED_V4,
    DATA_CAPS_PROBED_V5,
    DATA_VEHICLE_FEATURES,
    DOMAIN,
    features_from_permissions,
)
from custom_components.lepas.coordinator import LepasCoordinator
from custom_components.lepas.scheduler import (
    DEPARTURE_CLIMATE_EXTRAS_COMMANDS,
    DEPARTURE_CLIMATE_EXTRAS_FEATURES,
    DEPARTURE_CLIMATE_EXTRAS_MUTUAL_EXCLUSIONS,
    compute_battery_heat_start_for_departure,
    local_schedule_to_utc,
    normalize_climate_extras,
    utc_schedule_to_local,
)


def _make_coord(
    hass,
    *,
    data: dict | None = None,
    entry_id: str = "native_dep_entry",
) -> LepasCoordinator:
    base = {
        CONF_VIN: FX.VIN,
        CONF_TUSERID: FX.TUSERID,
        "email": FX.EMAIL,
        CONF_PIN: FX.PIN,
    }
    if data:
        base.update(data)
    entry = MockConfigEntry(domain=DOMAIN, data=base, entry_id=entry_id)
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry_id] = coord
    return coord


# ───────────────────────────── 1. Timezone & Pure Math ─────────────────────────────


def test_local_utc_schedule_conversion_cet_cest_and_rollover():
    rome = ZoneInfo("Europe/Rome")
    winter = date(2026, 11, 16)  # CET (UTC+1)
    summer = date(2026, 7, 15)   # CEST (UTC+2)

    # 06:05 CET -> 05:05 UTC (305), same weekdays
    assert local_schedule_to_utc(6 * 60 + 5, [1, 2, 3, 4, 5], rome, ref_date=winter) == (
        305,
        [1, 2, 3, 4, 5],
    )
    assert utc_schedule_to_local(305, [1, 2, 3, 4, 5], rome, ref_date=winter) == (
        365,
        [1, 2, 3, 4, 5],
    )

    # 07:05 CEST -> 05:05 UTC (305)
    assert local_schedule_to_utc(7 * 60 + 5, [1, 5], rome, ref_date=summer) == (305, [1, 5])
    assert utc_schedule_to_local(305, [1, 5], rome, ref_date=summer) == (425, [1, 5])

    # Midnight weekday rollover: 00:30 CET Mon [1] -> 23:30 UTC (1410) Sun [7] and back
    utc_min, utc_days = local_schedule_to_utc(30, [1], rome, ref_date=winter)
    assert (utc_min, utc_days) == (23 * 60 + 30, [7])
    assert utc_schedule_to_local(utc_min, utc_days, rome, ref_date=date(2026, 11, 15)) == (30, [1])

    # Negative UTC offset forward rollover: 22:00 EST Sun [7] -> 03:00 UTC Mon [1]
    ny = ZoneInfo("America/New_York")
    ny_utc_min, ny_utc_days = local_schedule_to_utc(22 * 60, [7], ny, ref_date=date(2026, 11, 15))
    assert (ny_utc_min, ny_utc_days) == (3 * 60, [1])
    assert utc_schedule_to_local(ny_utc_min, ny_utc_days, ny, ref_date=date(2026, 11, 16)) == (
        22 * 60,
        [7],
    )

    # None / empty days
    assert local_schedule_to_utc(420, None, rome, ref_date=winter) == (360, [])
    assert utc_schedule_to_local(360, None, rome, ref_date=winter) == (420, [])


def test_compute_battery_heat_start_for_departure():
    assert compute_battery_heat_start_for_departure(7 * 60 + 30) == 7 * 60
    assert compute_battery_heat_start_for_departure(30) == 0
    assert compute_battery_heat_start_for_departure(15) == 23 * 60 + 45
    assert compute_battery_heat_start_for_departure(0, lead_minutes=30) == 23 * 60 + 30


# ───────────────────────────── 2. Climate Extras Normalization ─────────────────────────────


def test_climate_extras_mappings_and_normalization():
    assert DEPARTURE_CLIMATE_EXTRAS_FEATURES["windshield_defrost"] == "front_windshield_electric"
    assert DEPARTURE_CLIMATE_EXTRAS_FEATURES["windshield_defog"] == "front_windshield_defog"
    assert DEPARTURE_CLIMATE_EXTRAS_FEATURES["steering_wheel_heating"] == "steering_wheel_heating"
    assert DEPARTURE_CLIMATE_EXTRAS_COMMANDS["windshield_defrost"] == "defrost_parabrezza"
    assert DEPARTURE_CLIMATE_EXTRAS_COMMANDS["windshield_defog"] == "disappanna_parabrezza"
    assert DEPARTURE_CLIMATE_EXTRAS_MUTUAL_EXCLUSIONS["driver_seat_heating"] == "driver_seat_ventilation"
    assert DEPARTURE_CLIMATE_EXTRAS_MUTUAL_EXCLUSIONS["driver_seat_ventilation"] == "driver_seat_heating"

    # Deduplication preserves order
    assert normalize_climate_extras(
        ["steering_wheel_heating", "windshield_defog", "steering_wheel_heating"]
    ) == ["steering_wheel_heating", "windshield_defog"]

    # Mutual exclusion: last writer wins
    assert normalize_climate_extras(
        ["driver_seat_heating", "windshield_defog", "driver_seat_ventilation"]
    ) == ["windshield_defog", "driver_seat_ventilation"]
    assert normalize_climate_extras(
        ["rear_right_seat_ventilation", "rear_right_seat_heating"]
    ) == ["rear_right_seat_heating"]

    # Empty / None
    assert normalize_climate_extras(None) == []
    assert normalize_climate_extras([]) == []

    # Rejects unknown keys or non-string/invalid types
    for bad in (["unknown_extra"], [123], [True], 42, True, ["driver_seat_heating", "bad"]):
        with pytest.raises(ValueError):
            normalize_climate_extras(bad)


# ───────────────────────────── 3. Commands & Read-Only Queries ─────────────────────────────


def test_commands_catalog_and_rich_entity_gating(core):
    commands = core["commands"]

    for key in ("partenza_prog_on", "partenza_prog_off", "battery_heat_on", "battery_heat_off"):
        assert key in commands.CMD_MAP
        assert key in COMMANDS_AS_RICH_ENTITY

    assert commands.CMD_MAP["partenza_prog_on"]["endpoint"] == "appointmentTravel"
    assert commands.CMD_MAP["partenza_prog_on"]["body"]["mainSwitcher"] == "1"
    assert commands.CMD_MAP["partenza_prog_on"]["body"]["appointmentTravelAOS"][0]["travelWeekday"] == ["1", "2", "3", "4", "5"]
    assert commands.CMD_MAP["partenza_prog_off"]["endpoint"] == "appointmentTravel"
    assert commands.CMD_MAP["partenza_prog_off"]["body"]["mainSwitcher"] == "0"
    assert commands.CMD_MAP["partenza_prog_off"]["body"]["appointmentTravelAOS"][0]["travelWeekday"] == ["1", "2", "3", "4", "5"]

    assert commands.CMD_MAP["battery_heat_on"]["endpoint"] == "batteryPackHeat"
    assert commands.CMD_MAP["battery_heat_on"]["body"]["switchState"] == "1"
    assert commands.CMD_MAP["battery_heat_off"]["endpoint"] == "batteryPackHeat"
    assert commands.CMD_MAP["battery_heat_off"]["body"] == {"switchState": "0", "startTime": "0"}


def test_query_travel_appoint_and_battery_pack_heat(core, cloud, ctx):
    commands = core["commands"]

    # Primary endpoint succeeds
    cloud.on(
        "/asd/travelManage/travelQuery",
        code="000000",
        data={
            "mainSwitcher": "1",
            "appointmentTravelSetVOS": [
                {"id": 98765, "planId": 1, "switcher": "1", "travelTime": "305", "travelWeekday": "1,2,3,4,5"}
            ],
        },
    )
    res = commands.query_travel_appoint(ctx)
    assert isinstance(res, dict)
    assert res["appointmentTravelSetVOS"][0]["id"] == 98765

    # List payload normalization
    cloud.on(
        "/asd/travelManage/travelQuery",
        code="000000",
        data=[{"id": 555, "switcher": "1", "travelTime": "360", "travelWeekday": "1,3,5"}],
    )
    res_list = commands.query_travel_appoint(ctx)
    assert isinstance(res_list, dict)
    assert res_list["appointmentTravelSetVOS"][0]["id"] == 555

    # Error code -> None
    cloud.on("/asd/travelManage/travelQuery", code="A00084", data={})
    assert commands.query_travel_appoint(ctx) is None

    # Battery pack heat query
    cloud.on(
        "/asd/travelManage/queryBatteryPackHeat",
        code="000000",
        data={"switchState": "1", "startTime": "390"},
    )
    bh = commands.query_battery_pack_heat(ctx)
    assert bh == {"switchState": "1", "startTime": "390"}

    cloud.on("/asd/travelManage/queryBatteryPackHeat", raises=RuntimeError("boom"))
    assert commands.query_battery_pack_heat(ctx) is None


# ───────────────────────────── 4. Permissions & V5 Backfill ─────────────────────────────


def test_permessi_travel_and_battery_tables_and_csv_giorni(core):
    P = core["permessi"]
    commands = core["commands"]

    assert P.CATEGORIA["appointmentTravel"] == 212
    assert P.CATEGORIA["batteryPackHeat"] == 216
    assert P.CICLO["appointmentTravel"] == (2121, 2122, "travelWeekday")

    # List[str] weekday parsing (appointmentTravelAOS schema)
    body_aos = {
        "mainSwitcher": "1",
        "appointmentTravelAOS": [{"planId": 1, "switcher": "1", "travelTime": "305", "travelWeekday": ["1", "3", "5"]}],
    }
    assert P._giorni(body_aos, "travelWeekday") == ["1", "3", "5"]
    assert P.ciclo_non_autorizzato("appointmentTravel", body_aos, {212: 1, 2121: 0, 2122: 1}) is not None
    assert P.ciclo_non_autorizzato("appointmentTravel", body_aos, {212: 1, 2121: 1, 2122: 0}) is None

    # All 7 days list triggers 2122 check
    body_all = {"appointmentTravelAOS": [{"travelWeekday": ["1", "2", "3", "4", "5", "6", "7"]}]}
    assert P.ciclo_non_autorizzato("appointmentTravel", body_all, {212: 1, 2121: 1, 2122: 0}) is not None

    # Disabling (mainSwitcher == "0") sends non-empty travelWeekday list (API rejects "") and never warns on cycle
    off_body = dict(commands.CMD_MAP["partenza_prog_off"]["body"])
    assert P._giorni(off_body, "travelWeekday") == ["1", "2", "3", "4", "5"]
    assert P.ciclo_non_autorizzato("appointmentTravel", off_body, {212: 1, 2121: 0, 2122: 0}) is None


async def test_v5_backfill_and_feature_rules_and_effective_departure_days(hass, cloud):
    assert DATA_CAPS_PROBED_V5 == "caps_probed_v5"
    vf = features_from_permissions({212: 1, 2121: 0, 216: 0})
    assert vf["scheduled_departure_control"] is True
    assert vf["scheduled_departure_custom_days"] is False
    assert vf["battery_pack_heat"] is False

    # V4 entry re-probes once for V5
    cloud.on(
        "/tsp/v1/app/vmc/queryList",
        data=[{"vin": FX.VIN, "nickname": "Lepas L8", "fullName": "LEPAS L8"}],
    )
    cloud.on(
        "/tsp/v1/app/vmc/queryVehicleAuthority",
        data={
            "permissionList": [
                {"id": 212, "state": 1},
                {"id": 2121, "state": 0},
                {"id": 2122, "state": 1},
                {"id": 216, "state": 0},
            ]
        },
    )
    coord = _make_coord(
        hass,
        data={"vehicle_name": "Lepas L8", DATA_CAPS_PROBED_V4: True},
        entry_id="v5_backfill",
    )
    await coord.async_ensure_vehicle_identity()
    assert coord.entry.data.get(DATA_CAPS_PROBED_V5) is True
    assert cloud.count("/tsp/v1/app/vmc/queryList") == 1
    assert coord.feature_enabled("scheduled_departure_control") is True
    assert coord.feature_enabled("scheduled_departure_custom_days") is False
    assert coord.feature_enabled("battery_pack_heat") is False
    assert coord.effective_departure_days([1, 3, 5]) == [1, 2, 3, 4, 5, 6, 7]

    # Subsequent call does NOT re-probe
    await coord.async_ensure_vehicle_identity()
    assert cloud.count("/tsp/v1/app/vmc/queryList") == 1


# ───────────────────────────── 5. Preclimate Dynamic Extras ─────────────────────────────


async def test_preclimate_sends_allowed_extras_skips_forbidden_and_survives_partial_failure(
    hass, monkeypatch, caplog
):
    tz = timezone.utc
    coord = _make_coord(
        hass,
        data={
            DATA_VEHICLE_FEATURES: {
                "front_windshield_electric": False,
                "front_windshield_defog": True,
                "steering_wheel_heating": True,
                "driver_seat_heating": True,
                "rear_window_heating": True,
            }
        },
        entry_id="extras_entry",
    )
    coord.departure_climate_mode = "anywhere"
    coord.departure_weekly[1] = (True, 7 * 60)

    allowed = coord.allowed_departure_climate_extras()
    assert "windshield_defrost" not in allowed
    assert "windshield_defog" in allowed
    assert "steering_wheel_heating" in allowed

    # async_set_departure_climate_extras normalizes & drops disallowed
    saved = await coord.async_set_departure_climate_extras(
        ["windshield_defrost", "windshield_defog", "steering_wheel_heating", "driver_seat_heating"]
    )
    assert saved == ["windshield_defog", "steering_wheel_heating", "driver_seat_heating"]

    # Force a forbidden key directly to verify _maybe_trigger_preclimate filters too
    coord.departure_climate_extras = [
        "windshield_defrost",
        "windshield_defog",
        "steering_wheel_heating",
        "rear_window_heating",
    ]
    sent: list[str] = []

    async def send_with_one_failure(key: str, params: dict | None = None) -> str:
        sent.append(key)
        if key == "volante_caldo":
            raise HomeAssistantError(f"partial failure on {FX.VIN}")
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", send_with_one_failure)

    with caplog.at_level(logging.WARNING):
        await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 50, tzinfo=tz))

    assert sent == ["clima_on", "disappanna_parabrezza", "volante_caldo", "defrost_lunotto"]
    assert "defrost_parabrezza" not in sent
    assert coord._fired_climate_key is not None
    # No plaintext VIN in warning log
    assert not any(FX.VIN in rec.getMessage() for rec in caplog.records)


# ───────────────────────────── 6. Native Departure Sync & Quick Expiry ─────────────────────────────


async def test_native_departure_sync_weekly_grouping_server_id_and_off(hass, monkeypatch):
    rome = ZoneInfo("Europe/Rome")
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 6, 0, tzinfo=rome))
    hass.config.time_zone = "Europe/Rome"

    coord = _make_coord(
        hass,
        data={
            DATA_VEHICLE_FEATURES: {
                "scheduled_departure_control": True,
                "scheduled_departure_custom_days": True,
            }
        },
        entry_id="native_sync",
    )
    coord.data["realtime"] = {"appointmentTravelSetVOS": [{"id": 777123, "travelTime": 305}]}
    # Mon, Wed, Fri at 07:00 CET (420 -> 06:00 UTC = 360); Tue at 08:00 CET (different time)
    coord.departure_weekly[1] = (True, 7 * 60)
    coord.departure_weekly[2] = (True, 8 * 60)
    coord.departure_weekly[3] = (True, 7 * 60)
    coord.departure_weekly[5] = (True, 7 * 60)

    sent: list[tuple[str, dict | None]] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", fake_send)

    await coord.async_apply_departure_schedule()
    assert len(sent) == 1
    assert sent[0][0] == "partenza_prog_on"
    vo = sent[0][1]["appointmentTravelAOS"][0]
    assert "appointmentTravelSetVOS" not in sent[0][1]
    assert sent[0][1]["mainSwitcher"] == "1"
    assert vo["id"] == 777123
    assert vo["planId"] == 1
    assert vo["switcher"] == "1"
    assert vo["travelTime"] == "360"
    assert vo["travelWeekday"] == ["1", "3", "5"]

    # With 2121 == 0 -> fallback to 1,2,3,4,5,6,7
    coord2 = _make_coord(
        hass,
        data={
            DATA_VEHICLE_FEATURES: {
                "scheduled_departure_control": True,
                "scheduled_departure_custom_days": False,
            }
        },
        entry_id="native_2121_0",
    )
    coord2.departure_weekly[1] = (True, 30)  # 00:30 CET Mon -> 23:30 UTC Sun
    monkeypatch.setattr(coord2, "async_send_command", fake_send)
    await coord2.async_apply_departure_schedule()
    vo2 = sent[1][1]["appointmentTravelAOS"][0]
    assert "id" not in vo2
    assert vo2["travelTime"] == str(23 * 60 + 30)
    assert vo2["travelWeekday"] == ["1", "2", "3", "4", "5", "6", "7"]

    # No active departure -> partenza_prog_off (non-empty travelWeekday + preserved travelTime)
    # and refreshes realtime from travelQuery (clearing stale appointmentTravelSetVOS on mainSwitcher=0)
    async def fake_query():
        return {"mainSwitcher": 0}

    monkeypatch.setattr(coord, "async_query_travel_appoint", fake_query)
    for d in range(1, 8):
        coord.departure_weekly[d] = (False, 420)
    await coord.async_apply_departure_schedule()
    assert sent[2][0] == "partenza_prog_off"
    assert sent[2][1]["mainSwitcher"] == "0"
    assert sent[2][1]["appointmentTravelAOS"][0]["switcher"] == "0"
    assert sent[2][1]["appointmentTravelAOS"][0]["travelTime"] == "305"
    assert sent[2][1]["appointmentTravelAOS"][0]["travelWeekday"] == ["1"]
    assert coord.data["realtime"]["mainSwitcher"] == 0
    assert "appointmentTravelSetVOS" not in coord.data["realtime"]


async def test_quick_departure_hold_across_preclimate_and_expiry_in_all_modes(hass, monkeypatch):
    tz = timezone.utc
    coord = _make_coord(hass, entry_id="quick_hold")
    coord.native_departure_sync = True
    coord.sync_battery_heat_to_departure = True
    coord.departure_climate_mode = "anywhere"
    coord.clima_duration = 15

    sent: list[tuple[str, dict | None]] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", fake_send)

    # Set quick departure for 18:00 when now is 17:40
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 17, 40, tzinfo=tz))
    await coord.async_set_quick_departure(18 * 60, True)
    assert [s[0] for s in sent] == ["partenza_prog_on", "battery_heat_on"]
    assert sent[1][1] == {"switchState": "1", "startTime": str(17 * 60 + 30)}
    # sync_charge was NOT touched
    assert coord.sync_charge_to_departure is False

    # Tick at 17:50 (inside preclimate window): triggers clima_on, holds native/battery until 18:00
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 17, 50, tzinfo=tz))
    assert [s[0] for s in sent] == ["partenza_prog_on", "battery_heat_on", "clima_on"]
    assert coord.quick_departure_enabled is False
    assert coord._quick_native_until == datetime(2026, 11, 16, 18, 0, tzinfo=tz)

    # Tick at 17:55 still holds quick (no premature off)
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 17, 55, tzinfo=tz))
    assert len(sent) == 3

    # Tick at 18:00 expires _quick_native_until and sends partenza_prog_off + battery_heat_off
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 18, 0, tzinfo=tz))
    assert coord._quick_native_until is None
    assert coord.native_departure_sync is False
    assert [s[0] for s in sent[3:]] == ["partenza_prog_off", "battery_heat_off"]
    assert sent[-1][1] == {"switchState": "0", "startTime": "0"}

    # Now verify departure_climate_mode == "off" expires cleanly to weekly restore!
    sent.clear()
    coord.native_departure_sync = True
    coord.departure_climate_mode = "off"
    coord.departure_weekly[2] = (True, 7 * 60)  # Tuesday 07:00
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 17, 40, tzinfo=tz))
    await coord.async_set_quick_departure(18 * 60, True)
    assert sent[0][0] == "partenza_prog_on"
    assert sent[0][1]["appointmentTravelAOS"][0]["travelWeekday"] == ["1"]

    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 18, 1, tzinfo=tz))
    assert coord.quick_departure_enabled is False
    assert coord._quick_target_at is None
    assert coord._quick_native_until is None
    # Restored to Tuesday 07:00 native & 06:30 battery heat
    assert sent[-2][0] == "partenza_prog_on"
    assert sent[-2][1]["appointmentTravelAOS"][0]["travelWeekday"] == ["2"]
    assert sent[-2][1]["appointmentTravelAOS"][0]["travelTime"] == str(7 * 60)
    assert sent[-1][0] == "battery_heat_on"
    assert sent[-1][1]["startTime"] == str(6 * 60 + 30)


async def test_notify_schedule_changed_isolation_and_stale_quick_hold_cleanup(hass, monkeypatch):
    tz = timezone.utc
    coord = _make_coord(hass, entry_id="isolation")
    coord.native_departure_sync = True
    coord.sync_battery_heat_to_departure = True
    coord.sync_charge_to_departure = True
    coord.departure_weekly[1] = (True, 7 * 60)
    coord._quick_native_until = datetime(2026, 11, 16, 18, 0, tzinfo=tz)

    sent: list[str] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append(key)
        return "ok"

    async def fast_settle() -> None:
        return None

    async def fake_query() -> None:
        return None

    monkeypatch.setattr(coord, "async_send_command", fake_send)
    monkeypatch.setattr(coord, "_settle_after_command", fast_settle)
    monkeypatch.setattr(coord, "async_query_travel_appoint", fake_query)
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 5, 0, tzinfo=tz))

    # Boot restore: all sync flags default False -> clears stale hold, sends NO commands
    coord.notify_schedule_changed()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coord._quick_native_until is None
    assert sent == []

    # Native toggle only -> syncs ONLY travelAppointControl (NOT charge, NOT battery)
    coord.notify_schedule_changed(sync_native=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert sent == ["partenza_prog_on"]

    # Battery toggle only -> syncs ONLY batteryPackHeat
    coord.notify_schedule_changed(sync_battery=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert sent == ["partenza_prog_on", "battery_heat_on"]


async def test_read_only_queries_never_called_in_tick_or_passive_poll(hass, monkeypatch):
    from custom_components.lepas.core import commands as CMD

    called: list[str] = []
    monkeypatch.setattr(CMD, "query_travel_appoint", lambda ctx: called.append("travel") or None)
    monkeypatch.setattr(CMD, "query_battery_pack_heat", lambda ctx: called.append("battery") or None)

    coord = _make_coord(hass, entry_id="no_poll_query")
    coord.native_departure_sync = True
    coord.sync_battery_heat_to_departure = True
    # Already synced in OFF state so the idle tick does not emit a write command
    coord._last_synced_native_dep_sig = ("0", 0, ())

    async def fake_send(key: str, params: dict | None = None) -> str:
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", fake_send)
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 0, tzinfo=timezone.utc))

    # Simulate passive poll when car is online
    async def fake_probe(force: bool = False) -> None:
        coord._online = True

    monkeypatch.setattr(coord, "async_probe", fake_probe)
    await coord._do_poll_cycle()

    assert called == []


# ───────────────────────────── 7. HA Services ─────────────────────────────


async def test_new_services_and_apply_native(hass, cloud, monkeypatch):
    sent: list[tuple[str, dict | None]] = []

    async def fake_send(self, key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    async def no_backfill(self) -> None:
        return None

    monkeypatch.setattr(LepasCoordinator, "_provision_certs", lambda self: (True, "ok"))
    monkeypatch.setattr(LepasCoordinator, "_connect_car", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_keepalive", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_telemetry_poll", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_drive_watch", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_ensure_vehicle_identity", no_backfill)
    monkeypatch.setattr(LepasCoordinator, "async_send_command", fake_send)

    tz = timezone.utc
    hass.config.time_zone = "UTC"
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 6, 0, tzinfo=tz))

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
            DATA_VEHICLE_FEATURES: {
                "steering_wheel_heating": True,
                "front_windshield_electric": False,
                "battery_pack_heat": True,
                "scheduled_departure_control": True,
            },
        },
        entry_id="svc_entry",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        assert hass.services.has_service(DOMAIN, "set_departure_climate_extras")
        assert hass.services.has_service(DOMAIN, "set_battery_pack_heat")

        # Positional async_set_quick_departure(480, True) works
        await coord.async_set_quick_departure(480, True)
        assert coord.quick_departure_minutes == 480
        assert coord.quick_departure_enabled is True

        # set_quick_departure with apply_native=True forces travelAppointControl even when sync is OFF
        assert coord.native_departure_sync is False
        await hass.services.async_call(
            DOMAIN,
            "set_quick_departure",
            {"time": "08:30", "enabled": True, "apply_native": True},
            blocking=True,
        )
        assert any(k == "partenza_prog_on" for k, _ in sent)

        # set_departure_climate_extras
        await hass.services.async_call(
            DOMAIN,
            "set_departure_climate_extras",
            {"extras": ["steering_wheel_heating", "windshield_defrost"]},
            blocking=True,
        )
        assert coord.departure_climate_extras == ["steering_wheel_heating"]

        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN,
                "set_departure_climate_extras",
                {"extras": ["not_a_valid_extra"]},
                blocking=True,
            )

        # set_battery_pack_heat
        sent.clear()
        await hass.services.async_call(
            DOMAIN,
            "set_battery_pack_heat",
            {"enabled": True, "time": "06:45", "sync_to_departure": False},
            blocking=True,
        )
        assert coord.battery_heat_enabled is True
        assert coord.battery_heat_minutes == 6 * 60 + 45
        assert sent == [("battery_heat_on", {"switchState": "1", "startTime": str(6 * 60 + 45)})]

        await hass.services.async_call(
            DOMAIN,
            "set_battery_pack_heat",
            {"enabled": False},
            blocking=True,
        )
        assert coord.battery_heat_enabled is False
        assert sent[-1] == ("battery_heat_off", {"switchState": "0", "startTime": "0"})

        # Updating time alone while disabled updates local time without sending command
        sent.clear()
        await hass.services.async_call(
            DOMAIN,
            "set_battery_pack_heat",
            {"time": "05:15"},
            blocking=True,
        )
        assert coord.battery_heat_minutes == 5 * 60 + 15
        assert sent == []
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, "set_departure_climate_extras")
    assert not hass.services.has_service(DOMAIN, "set_battery_pack_heat")


async def test_query_caching_and_closing_guards(hass, cloud, monkeypatch):
    cloud.on(
        "/asd/travelManage/travelQuery",
        code="000000",
        data={"appointmentTravelSetVOS": [{"id": 445566, "travelTime": "360", "travelWeekday": "1,2"}]},
    )
    coord = _make_coord(hass, entry_id="query_cache")
    coord.departure_weekly[1] = (True, 7 * 60)
    hass.config.time_zone = "UTC"
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 6, 0, tzinfo=timezone.utc))

    q = await coord.async_query_travel_appoint()
    assert q is not None

    sent: list[tuple[str, dict | None]] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", fake_send)
    await coord.async_apply_departure_schedule()
    assert sent[0][1]["appointmentTravelAOS"][0]["id"] == 445566

    # Closing mid-await aborts battery sync and extra loop cleanly
    coord.sync_battery_heat_to_departure = True
    coord.departure_climate_mode = "anywhere"
    coord.departure_climate_extras = ["steering_wheel_heating", "rear_window_heating"]

    async def closing_send(key: str, params: dict | None = None) -> str:
        if key == "volante_caldo":
            coord._timers.close()
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", closing_send)
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 50, tzinfo=timezone.utc))
    assert coord._timers.closing is True
    assert coord._departure_busy is False
    assert coord._last_synced_battery_sig is None


def test_appointment_travel_endpoint_and_http_error_raises(core, cloud, ctx, monkeypatch):
    import io
    import json
    import urllib.error
    import urllib.request

    commands = core["commands"]
    monkeypatch.setattr(commands, "get_taskid", lambda *a, **kw: ("tid_test", "env"))
    monkeypatch.setattr(core["wake"], "_bff_login", lambda c: ("tok_test", "uid_test"))
    ctx.permessi = {212: 1, 2121: 1, 2122: 0}

    cloud.on("/asc/vehicleControl/appointmentTravel", code="000000", data={})
    res = commands.send(
        ctx,
        "partenza_prog_off",
        params={"mainSwitcher": "0", "appointmentTravelAOS": [{"planId": 1, "switcher": "0", "travelTime": "420", "travelWeekday": ["1"]}]},
    )
    assert "HTTP 200" in res
    assert cloud.count("/asc/vehicleControl/appointmentTravel") == 1

    # HTTP >= 400 without Chery `code` MUST raise CommandError (no silent success)
    def fake_urlopen_404(req, timeout=None):
        url = req.full_url
        err_body = json.dumps({"status": 404, "error": "Not Found", "path": url}).encode()
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(err_body))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen_404)
    with pytest.raises(commands.CommandError, match="HTTP 404"):
        commands.send(ctx, "partenza_prog_off")


def test_tsp_sign_and_permessi_appointment_travel_aos_list(core):
    tsp_sign = core["tsp_sign"]
    permessi = core["permessi"]
    body = {
        "mainSwitcher": "1",
        "appointmentTravelAOS": [
            {"planId": 1, "switcher": "1", "travelTime": "420", "travelWeekday": ["1", "3", "5"]},
        ],
    }
    signed = tsp_sign.sign_body(body, 1731974400000)
    assert isinstance(signed.get("sign"), str) and signed["sign"]
    assert signed["appId"] == tsp_sign.APP_ID
    assert signed["appointmentTravelAOS"][0]["travelWeekday"] == ["1", "3", "5"]
    assert tsp_sign._flatten_value(body["appointmentTravelAOS"]) == (
        "planId=1&switcher=1&travelTime=420&travelWeekday=135"
    )
    assert permessi.ciclo_non_autorizzato("appointmentTravel", body, {212: 1, 2121: 0, 2122: 1}) is not None
    assert permessi.ciclo_non_autorizzato("appointmentTravel", body, {212: 1, 2121: 1, 2122: 0}) is None


async def test_on_probe_data_preserves_travel_appoint_when_omitted(hass):
    coord = _make_coord(hass, entry_id="probe_preserve_travel")
    cached_vos = [{"planId": 1, "switcher": "1", "travelTime": "420", "travelWeekday": ["1", "3"]}]
    coord._apply_update(
        {
            "realtime": {
                "soc": 80,
                "mainSwitcher": 1,
                "appointmentTravelSetVOS": cached_vos,
            }
        }
    )

    # Probe omitting both keys must preserve existing travel appointment state/attributes
    coord._on_probe_data({"soc": 81})
    await hass.async_block_till_done()
    rt = coord.data["realtime"]
    assert rt["soc"] == 81
    assert rt["mainSwitcher"] == 1
    assert rt["appointmentTravelSetVOS"] == cached_vos

    # Probe explicitly reporting mainSwitcher=0 clears stale appointmentTravelSetVOS when absent
    coord._on_probe_data({"soc": 82, "mainSwitcher": 0})
    await hass.async_block_till_done()
    rt2 = coord.data["realtime"]
    assert rt2["mainSwitcher"] == 0
    assert "appointmentTravelSetVOS" not in rt2


async def test_apply_departure_schedule_schedules_post_settle_refresh(hass, monkeypatch):
    coord = _make_coord(hass, entry_id="post_settle_travel")
    coord.departure_weekly[1] = (True, 420)

    calls: list[str] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        calls.append(f"send:{key}")
        return "ok"

    async def fake_settle() -> None:
        calls.append("settle")

    async def fake_query() -> dict:
        calls.append("query")
        if "settle" in calls:
            return {
                "mainSwitcher": 1,
                "appointmentTravelSetVOS": [{"planId": 1, "switcher": "1", "travelTime": "360", "travelWeekday": ["1"]}],
            }
        return {"mainSwitcher": 0}

    monkeypatch.setattr(coord, "async_send_command", fake_send)
    monkeypatch.setattr(coord, "_settle_after_command", fake_settle)
    monkeypatch.setattr(coord, "async_query_travel_appoint", fake_query)

    await coord.async_apply_departure_schedule()
    await hass.async_block_till_done(wait_background_tasks=True)

    assert calls == ["send:partenza_prog_on", "query", "settle", "query"]
    assert coord.data["realtime"]["mainSwitcher"] == 1
    assert coord.data["realtime"]["appointmentTravelSetVOS"][0]["travelWeekday"] == ["1"]


# ───────────────────────────── 8. Full-Plan Dirty Tracking, Disable & Lock ─────────────────────────────


def _patch_entry_io(monkeypatch, sent: list[tuple[str, dict | None]], travel_resp: dict | None = None) -> None:
    async def fake_send(self, key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    async def no_backfill(self) -> None:
        return None

    async def fast_settle(self) -> None:
        return None

    async def fake_query(self) -> dict | None:
        return travel_resp

    monkeypatch.setattr(LepasCoordinator, "_provision_certs", lambda self: (True, "ok"))
    monkeypatch.setattr(LepasCoordinator, "_connect_car", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_keepalive", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_telemetry_poll", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_drive_watch", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_ensure_vehicle_identity", no_backfill)
    monkeypatch.setattr(LepasCoordinator, "async_send_command", fake_send)
    monkeypatch.setattr(LepasCoordinator, "_settle_after_command", fast_settle)
    monkeypatch.setattr(LepasCoordinator, "async_query_travel_appoint", fake_query)


async def test_full_plan_dirty_tracking_friday_edit_while_thursday_synced(hass, cloud, monkeypatch):
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 19, 10, 0, tzinfo=rome))

    sent: list[tuple[str, dict | None]] = []
    # Thu 13:25 CET == 12:25 UTC (745 min) on [4]
    travel_resp = {
        "mainSwitcher": 1,
        "appointmentTravelSetVOS": [
            {"planId": 1, "switcher": "1", "travelTime": "745", "travelDate": [4]}
        ],
    }
    _patch_entry_io(monkeypatch, sent, travel_resp=travel_resp)

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
            DATA_VEHICLE_FEATURES: {
                "scheduled_departure_control": True,
                "scheduled_departure_custom_days": True,
            },
        },
        entry_id="dirty_plan_entry",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        coord.departure_weekly[4] = (True, 13 * 60 + 25)
        coord.departure_weekly[5] = (True, 6 * 60)
        coord.departure_weekly[6] = (True, 6 * 60)

        await coord.async_apply_departure_schedule()
        await hass.async_block_till_done(wait_background_tasks=True)

        assert coord.native_departure_sync is True
        assert coord.has_pending_departure_changes() is False
        dp = hass.states.get("sensor.lepas_scheduled_departure")
        assert dp.attributes["synced_with_ha"] is True
        assert dp.attributes["has_pending_changes"] is False
        assert dp.attributes["applied_schedule_sig"] == coord.departure_schedule_signature()

        # Editing Friday time and toggling Sunday stays local (0 TSP commands) and dirties full-plan sig
        sent.clear()
        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_departure_fri_time", "time": "07:30:00"},
            blocking=True,
        )
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_departure_sun_enabled"},
            blocking=True,
        )
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_departure_sun_enabled"},
            blocking=True,
        )
        await hass.async_block_till_done(wait_background_tasks=True)

        assert sent == []
        assert coord.has_pending_departure_changes() is True
        dp_dirty = hass.states.get("sensor.lepas_scheduled_departure")
        assert dp_dirty.attributes["synced_with_ha"] is True
        assert dp_dirty.attributes["has_pending_changes"] is True

        # Editing an inactive weekday's time does NOT dirty the signature
        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_departure_fri_time", "time": "06:00:00"},
            blocking=True,
        )
        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_departure_sun_time", "time": "09:15:00"},
            blocking=True,
        )
        assert coord.has_pending_departure_changes() is False

        # When HA has no active schedule and official app already disabled the car -> False
        for d in range(1, 8):
            coord.departure_weekly[d] = (False, 420)
        assert coord.has_pending_departure_changes() is True  # car still active
        coord._apply_update({"realtime": {"mainSwitcher": 0}})
        assert coord.has_pending_departure_changes() is False
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_tick_auto_advance_thursday_to_friday_saturday_and_draft_guard(hass, monkeypatch):
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 19, 10, 0, tzinfo=rome))

    coord = _make_coord(
        hass,
        data={
            DATA_VEHICLE_FEATURES: {
                "scheduled_departure_control": True,
                "scheduled_departure_custom_days": True,
            }
        },
        entry_id="tick_advance",
    )
    coord.departure_climate_mode = "off"
    coord.departure_weekly[4] = (True, 13 * 60 + 25)
    coord.departure_weekly[5] = (True, 6 * 60)
    coord.departure_weekly[6] = (True, 6 * 60)

    sent: list[tuple[str, dict | None]] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    async def fast_settle() -> None:
        return None

    async def fake_query() -> dict:
        if len(sent) >= 2:
            return {
                "mainSwitcher": 1,
                "appointmentTravelSetVOS": [
                    {"planId": 1, "switcher": "1", "travelTime": "300", "travelDate": [5, 6]}
                ],
            }
        return {
            "mainSwitcher": 1,
            "appointmentTravelSetVOS": [
                {"planId": 1, "switcher": "1", "travelTime": "745", "travelDate": [4]}
            ],
        }

    monkeypatch.setattr(coord, "async_send_command", fake_send)
    monkeypatch.setattr(coord, "_settle_after_command", fast_settle)
    monkeypatch.setattr(coord, "async_query_travel_appoint", fake_query)

    await coord.async_apply_departure_schedule()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(sent) == 1
    assert coord.native_departure_sync is True

    # Advance past Thu 13:25 CET -> auto-advances to Fri & Sat 06:00 CET (05:00 UTC = 300)
    await coord._departure_tick_cb(_now=datetime(2026, 11, 19, 13, 26, tzinfo=rome))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(sent) == 2
    assert sent[1][0] == "partenza_prog_on"
    vo = sent[1][1]["appointmentTravelAOS"][0]
    assert vo["travelTime"] == "300"
    assert vo["travelWeekday"] == ["5", "6"]
    assert coord.data["realtime"]["appointmentTravelSetVOS"][0]["travelTime"] == "300"

    # Unapplied weekly draft (e.g. Friday time changed or all days toggled OFF) must NOT be pushed by tick
    coord.departure_weekly[5] = (True, 7 * 60 + 30)
    await coord._departure_tick_cb(_now=datetime(2026, 11, 19, 13, 27, tzinfo=rome))
    assert len(sent) == 2

    for d in range(1, 8):
        coord.departure_weekly[d] = (False, 420)
    await coord._departure_tick_cb(_now=datetime(2026, 11, 19, 13, 28, tzinfo=rome))
    assert len(sent) == 2


async def test_disable_departure_schedule_success_and_fail_closed(hass, monkeypatch):
    tz = timezone.utc
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 6, 0, tzinfo=tz))
    coord = _make_coord(hass, entry_id="disable_dep")
    coord.departure_weekly[1] = (True, 7 * 60)
    coord.departure_weekly[5] = (True, 8 * 60 + 15)
    coord.quick_departure_enabled = True
    coord.quick_departure_minutes = 18 * 60
    coord.native_departure_sync = True
    coord.sync_battery_heat_to_departure = True
    coord.battery_heat_enabled = True
    coord._applied_schedule_sig = coord.departure_schedule_signature()

    async def fail_send(key: str, params: dict | None = None) -> str:
        raise HomeAssistantError("vehicle unreachable")

    monkeypatch.setattr(coord, "async_send_command", fail_send)
    with pytest.raises(HomeAssistantError):
        await coord.async_disable_departure_schedule()

    # Fail-closed: HA state and signature preserved on command error
    assert coord.departure_weekly[1] == (True, 7 * 60)
    assert coord.departure_weekly[5] == (True, 8 * 60 + 15)
    assert coord.quick_departure_enabled is True
    assert coord.native_departure_sync is True
    assert coord._applied_schedule_sig is not None

    sent: list[tuple[str, dict | None]] = []

    async def ok_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    async def fast_settle() -> None:
        return None

    async def fake_query() -> dict:
        return {"mainSwitcher": 0}

    monkeypatch.setattr(coord, "async_send_command", ok_send)
    monkeypatch.setattr(coord, "_settle_after_command", fast_settle)
    monkeypatch.setattr(coord, "async_query_travel_appoint", fake_query)

    await coord.async_disable_departure_schedule()
    await hass.async_block_till_done(wait_background_tasks=True)

    assert [k for k, _ in sent] == ["partenza_prog_off", "battery_heat_off"]
    for d in range(1, 8):
        assert coord.departure_weekly[d][0] is False
    assert coord.departure_weekly[1][1] == 7 * 60
    assert coord.departure_weekly[5][1] == 8 * 60 + 15
    assert coord.quick_departure_enabled is False
    assert coord.native_departure_sync is False
    assert coord._applied_schedule_sig is None
    assert coord._last_synced_native_dep_sig is None
    assert coord._last_attempted_native_dep_sig is None
    assert coord._quick_applied_native is False
    assert coord.battery_heat_enabled is False
    assert coord.data["realtime"]["mainSwitcher"] == 0
    assert coord.has_pending_departure_changes() is False


async def test_quick_departure_service_apply_native_preserves_manual_sync_and_expiry(hass, monkeypatch):
    tz = timezone.utc
    coord = _make_coord(hass, entry_id="quick_apply_native")
    coord.departure_climate_mode = "off"

    sent: list[tuple[str, dict | None]] = []
    fail_next = False

    async def fake_send(key: str, params: dict | None = None) -> str:
        if fail_next:
            raise HomeAssistantError("transient failure")
        sent.append((key, params))
        return "ok"

    async def fast_settle() -> None:
        return None

    async def fake_query() -> dict:
        return {"mainSwitcher": 0}

    monkeypatch.setattr(coord, "async_send_command", fake_send)
    monkeypatch.setattr(coord, "_settle_after_command", fast_settle)
    monkeypatch.setattr(coord, "async_query_travel_appoint", fake_query)
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 17, 40, tzinfo=tz))

    # 1) apply_native=True with native_departure_sync=False preserves manual sync=False and arms _quick_applied_native
    await coord.async_set_quick_departure(18 * 60, True, apply_native=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coord.native_departure_sync is False
    assert coord._quick_applied_native is True
    assert coord._applied_schedule_sig == coord.departure_schedule_signature()
    assert [k for k, _ in sent] == ["partenza_prog_on"]

    # 2) Expiry send failure keeps _quick_applied_native for retry on next tick
    fail_next = True
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 18, 0, tzinfo=tz))
    assert coord.quick_departure_enabled is False
    assert coord._quick_applied_native is True
    assert len(sent) == 1

    fail_next = False
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 18, 1, tzinfo=tz))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert [k for k, _ in sent] == ["partenza_prog_on", "partenza_prog_off"]
    assert coord._quick_applied_native is False
    assert coord._applied_schedule_sig is None
    assert coord.native_departure_sync is False

    # 3) Expiry with dirty unapplied weekly draft (occ is not None) clears _quick_applied_native without leaking draft
    sent.clear()
    coord.departure_weekly[1] = (True, 7 * 60)
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 17, 40, tzinfo=tz))
    await coord.async_apply_departure_schedule()
    await hass.async_block_till_done(wait_background_tasks=True)
    coord.native_departure_sync = False
    await coord.async_set_quick_departure(18 * 60, True, apply_native=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coord._quick_applied_native is True
    coord.departure_weekly[5] = (True, 8 * 60)  # unapplied weekly draft edited after quick apply

    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 18, 0, tzinfo=tz))
    assert coord._quick_applied_native is False
    assert [k for k, _ in sent] == ["partenza_prog_on", "partenza_prog_on"]
    assert coord.has_pending_departure_changes() is True

    # 4) apply_native=None with native_departure_sync=True updates _applied_schedule_sig only when weekly is clean
    sent.clear()
    for d in range(1, 8):
        coord.departure_weekly[d] = (False, 420)
    coord.departure_weekly[1] = (True, 7 * 60)
    await coord.async_apply_departure_schedule()
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coord.native_departure_sync is True

    await coord.async_set_quick_departure(18 * 60, True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coord._applied_schedule_sig == coord.departure_schedule_signature()
    assert coord.has_pending_departure_changes() is False

    coord.departure_weekly[5] = (True, 8 * 60)
    prev_sig = coord._applied_schedule_sig
    await coord.async_set_quick_departure(18 * 60 + 30, True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coord._applied_schedule_sig == prev_sig
    assert coord.has_pending_departure_changes() is True


async def test_departure_lock_prevents_tick_race_during_disable(hass, monkeypatch):
    tz = timezone.utc
    coord = _make_coord(hass, entry_id="lock_race")
    coord.quick_departure_enabled = True
    coord.quick_departure_minutes = 18 * 60
    coord._quick_target_at = datetime(2026, 11, 16, 18, 0, tzinfo=tz)
    coord.native_departure_sync = True

    entered = asyncio.Event()
    release = asyncio.Event()
    sent: list[str] = []

    async def slow_send(key: str, params: dict | None = None) -> str:
        sent.append(key)
        entered.set()
        await release.wait()
        return "ok"

    async def fast_settle() -> None:
        return None

    async def fake_query() -> dict:
        return {"mainSwitcher": 0}

    monkeypatch.setattr(coord, "async_send_command", slow_send)
    monkeypatch.setattr(coord, "_settle_after_command", fast_settle)
    monkeypatch.setattr(coord, "async_query_travel_appoint", fake_query)

    disable_task = asyncio.create_task(coord.async_disable_departure_schedule())
    await entered.wait()

    # Concurrent tick while _departure_lock is held must return immediately without sending or mutating
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 18, 1, tzinfo=tz))
    assert sent == ["partenza_prog_off"]
    assert coord.quick_departure_enabled is True

    release.set()
    await disable_task
    await hass.async_block_till_done(wait_background_tasks=True)
    assert sent == ["partenza_prog_off"]
    assert coord.quick_departure_enabled is False
    assert coord.native_departure_sync is False


async def test_departure_plan_sensor_exposes_and_restores_applied_sig(hass, cloud, monkeypatch):
    tz = timezone.utc
    hass.config.time_zone = "UTC"
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 6, 0, tzinfo=tz))

    applied_sig = (
        '{"q":[false,null],"w":[[1,true,420],[2,false,null],[3,false,null],'
        '[4,false,null],[5,false,null],[6,false,null],[7,false,null]]}'
    )
    mock_restore_cache(
        hass,
        [
            State("switch.lepas_departure_mon_enabled", "on"),
            State("time.lepas_departure_mon_time", "07:00:00"),
            State(
                "sensor.lepas_scheduled_departure",
                "07:00",
                {"applied_schedule_sig": applied_sig},
            ),
        ],
    )
    sent: list[tuple[str, dict | None]] = []
    _patch_entry_io(monkeypatch, sent)

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
            DATA_VEHICLE_FEATURES: {"scheduled_departure_control": True},
        },
        entry_id="restore_sig_entry",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        # Before any realtime payload arrives, attributes expose restored sig & clean dirty flag
        assert coord._applied_schedule_sig == applied_sig
        assert coord.departure_schedule_signature() == applied_sig
        dp = hass.states.get("sensor.lepas_scheduled_departure")
        assert dp.attributes["applied_schedule_sig"] == applied_sig
        assert dp.attributes["has_pending_changes"] is False

        # Modifying local time sets has_pending_changes=True immediately even without realtime
        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_departure_mon_time", "time": "07:30:00"},
            blocking=True,
        )
        dp_after = hass.states.get("sensor.lepas_scheduled_departure")
        assert dp_after.attributes["has_pending_changes"] is True
        assert dp_after.attributes["applied_schedule_sig"] == applied_sig
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_disable_departure_schedule_service_registered_and_unregistered(hass, cloud, monkeypatch):
    tz = timezone.utc
    hass.config.time_zone = "UTC"
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 6, 0, tzinfo=tz))

    sent: list[tuple[str, dict | None]] = []
    _patch_entry_io(monkeypatch, sent, travel_resp={"mainSwitcher": 0})

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
            DATA_VEHICLE_FEATURES: {"scheduled_departure_control": True},
        },
        entry_id="disable_svc_entry",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        assert hass.services.has_service(DOMAIN, "disable_departure_schedule")
        coord.departure_weekly[1] = (True, 7 * 60)
        coord.native_departure_sync = True
        coord._applied_schedule_sig = coord.departure_schedule_signature()
        coord.async_update_listeners()
        await hass.async_block_till_done()

        await hass.services.async_call(
            DOMAIN,
            "disable_departure_schedule",
            {"entry_id": entry.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done(wait_background_tasks=True)

        assert [k for k, _ in sent] == ["partenza_prog_off"]
        assert hass.states.get("switch.lepas_departure_mon_enabled").state == "off"
        assert hass.states.get("switch.lepas_native_departure_sync").state == "off"
        assert coord._applied_schedule_sig is None
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, "disable_departure_schedule")


async def test_manual_comfort_and_macro_duration_propagation(hass, cloud, monkeypatch):
    from custom_components.lepas import coordinator as coord_mod, switch as switch_mod
    from custom_components.lepas.core import commands as CMD

    sent: list[tuple[str, dict | None]] = []
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0)
    monkeypatch.setattr(switch_mod, "MACRO_WAKE_WAIT", 0)
    monkeypatch.setattr(switch_mod, "MACRO_WAKE_WAIT_AWAKE", 0)
    monkeypatch.setattr(LepasCoordinator, "_provision_certs", lambda self: (True, "ok"))
    monkeypatch.setattr(LepasCoordinator, "_connect_car", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_keepalive", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_telemetry_poll", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_drive_watch", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_ensure_vehicle_identity", lambda self: asyncio.sleep(0))
    monkeypatch.setattr(
        CMD,
        "send",
        lambda _ctx, key, **kw: sent.append((key, kw.get("params"))) or "ok",
    )

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
        entry_id="manual_comfort_dur",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        coord.clima_duration = 5
        coord.departure_preclimate_duration = 10
        coord._last_msg_ts = time.time()

        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_driver_seat_heating"},
            blocking=True,
        )
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_steering_wheel_heating"},
            blocking=True,
        )
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_heat_everything"},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert sent == [
            ("sedile_guida_caldo", {"times": "5"}),
            ("volante_caldo", None),
            ("clima_riscalda_on", {"duration": "5"}),
        ]

        macro = next(
            e
            for e in hass.data["entity_components"]["switch"].entities
            if e.entity_id == "switch.lepas_heat_everything"
        )
        resto = macro._resto_scadenza()
        assert resto is not None
        assert 300 < resto <= (5 * 60 + 60)

        sent.clear()
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_heat_everything"},
            blocking=True,
        )
        await hass.async_block_till_done()
        assert sent == [("clima_riscalda_off", None)]
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_scheduled_comfort_optimistic_sync_rollback_probe_and_rejection_log(
    hass, cloud, monkeypatch, caplog
):
    from unittest.mock import AsyncMock

    from custom_components.lepas import coordinator as coord_mod
    from custom_components.lepas.const import PROBE_MQTT_GRACE_S
    from custom_components.lepas.core import commands as CMD
    from custom_components.lepas.timers import CMD_PROBE

    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0)
    monkeypatch.setattr(LepasCoordinator, "_provision_certs", lambda self: (True, "ok"))
    monkeypatch.setattr(LepasCoordinator, "_connect_car", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_keepalive", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_telemetry_poll", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_drive_watch", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_ensure_vehicle_identity", lambda self: asyncio.sleep(0))

    sent_cmd: list[tuple[str, dict | None]] = []
    monkeypatch.setattr(
        CMD,
        "send",
        lambda _ctx, key, **kw: sent_cmd.append((key, kw.get("params"))) or "ok",
    )

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
        entry_id="sched_comfort_sync",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coord = hass.data[DOMAIN][entry.entry_id]
    monkeypatch.setattr(coord, "async_probe", AsyncMock())

    def _sw(entity_id: str):
        return next(
            e
            for e in hass.data["entity_components"]["switch"].entities
            if e.entity_id == entity_id
        )

    def _deliver(payload: dict) -> None:
        msg = SimpleNamespace(
            payload=json.dumps(payload).encode("utf-8"),
            topic="app/1/test/account/msgCenter/msg",
        )
        coord._on_car_message(None, None, msg)

    try:
        coord.poll_enabled = True
        sw_heat = _sw("switch.lepas_driver_seat_heating")
        sw_vent = _sw("switch.lepas_driver_seat_ventilation")

        # Initial vehicle telemetry: heating OFF, ventilation ON, HVAC ON
        _deliver(FX.telemetry_5a02(dSeatHeatingState="0", dSeatVentilateState="1", frontHVACState="1"))
        await hass.async_block_till_done()
        assert hass.states.get("switch.lepas_driver_seat_heating").state == "off"
        assert hass.states.get("switch.lepas_driver_seat_ventilation").state == "on"

        # 1) In-flight optimistic activation + Exception rollback of self and _exclusive
        tz = timezone.utc
        coord.departure_climate_mode = "anywhere"
        coord.departure_weekly[1] = (True, 7 * 60)
        coord.departure_preclimate_duration = 10
        coord.departure_climate_extras = ["driver_seat_heating", "steering_wheel_heating"]

        entered = asyncio.Event()
        release = asyncio.Event()
        orig_send = coord.async_send_command

        async def paused_fail_send(key: str, params: dict | None = None) -> str:
            if key == "sedile_guida_caldo":
                entered.set()
                await release.wait()
                raise HomeAssistantError("send failed")
            return await orig_send(key, params)

        monkeypatch.setattr(coord, "async_send_command", paused_fail_send)
        tick_task = asyncio.create_task(
            coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 50, tzinfo=tz))
        )
        await entered.wait()
        assert sw_heat.is_on is True
        assert sw_heat._opt_value is True
        assert sw_vent._opt_value is False
        assert hass.states.get("switch.lepas_driver_seat_heating").state == "on"
        assert hass.states.get("switch.lepas_driver_seat_ventilation").state == "off"

        release.set()
        await tick_task
        await hass.async_block_till_done()
        assert sw_heat._opt_value is None
        assert sw_vent._opt_value is None
        assert hass.states.get("switch.lepas_driver_seat_heating").state == "off"
        assert hass.states.get("switch.lepas_driver_seat_ventilation").state == "on"
        assert "sedile_guida_caldo" not in (coord.data.get("scheduled_opt") or {})

        # 2) CancelledError rollback cleans scheduled_opt and both switches, then re-raises
        coord._fired_climate_key = None
        coord._attempted_climate_key = None
        entered.clear()
        release.clear()
        tick_cancel = asyncio.create_task(
            coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 50, tzinfo=tz))
        )
        await entered.wait()
        assert sw_heat._opt_value is True
        assert sw_vent._opt_value is False
        tick_cancel.cancel()
        with pytest.raises(asyncio.CancelledError):
            await tick_cancel
        await hass.async_block_till_done()
        assert sw_heat._opt_value is None
        assert sw_vent._opt_value is None
        assert "sedile_guida_caldo" not in (coord.data.get("scheduled_opt") or {})
        assert coord._timers.closing is False

        # 3) Real async_send_command arms CMD_PROBE on comfort extra, NOT clima_on
        assert coord._timers.is_armed(CMD_PROBE)  # armed by steering_wheel_heating continuing after failure
        coord._timers.cancel(CMD_PROBE)
        monkeypatch.setattr(coord, "async_send_command", orig_send)
        await coord.async_send_command("clima_on")
        await hass.async_block_till_done()
        assert not coord._timers.is_armed(CMD_PROBE)

        await coord.async_send_command("sedile_guida_caldo", {"times": "10"})
        await hass.async_block_till_done()
        assert coord._timers.is_armed(CMD_PROBE)

        # 4) Scheduled success followed by MQTT reason [4:95] rolls back both switches & logs WARNING (no VIN)
        coord.departure_climate_extras = ["driver_seat_heating"]
        coord._fired_climate_key = None
        coord._attempted_climate_key = None
        await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 50, tzinfo=tz))
        await hass.async_block_till_done()
        assert sw_heat._opt_value is True
        assert sw_vent._opt_value is False

        caplog.clear()
        with caplog.at_level(logging.WARNING):
            _deliver({
                "content": {
                    "serviceType": "110F",
                    "data": {
                        "result": "1",
                        "seq": "1",
                        "reason": [{"modelId": "4", "code": "95"}],
                    },
                }
            })
            await hass.async_block_till_done()

        assert sw_heat._opt_value is None
        assert sw_vent._opt_value is None
        assert hass.states.get("switch.lepas_driver_seat_heating").state == "off"
        assert hass.states.get("switch.lepas_driver_seat_ventilation").state == "on"
        warn_msgs = [
            rec.getMessage() for rec in caplog.records if rec.levelno == logging.WARNING
        ]
        assert any("comando rifiutato dall'auto (sedile_guida_caldo)" in m for m in warn_msgs)
        assert not any(FX.VIN in rec.getMessage() for rec in caplog.records)

        # 5) Past PROBE_MQTT_GRACE_S (15s) inside awake_window (300s): comfort settles, HVAC stays protected
        coord._fired_climate_key = None
        coord._attempted_climate_key = None
        await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 50, tzinfo=tz))
        await hass.async_block_till_done()
        assert sw_heat._opt_value is True

        with coord._state_lock:
            coord._last_msg_ts = time.time() - (PROBE_MQTT_GRACE_S + 5)
        coord._on_probe_data({"dSeatHeatingState": "1", "dSeatVentilateState": "0", "frontHVACState": "0"})
        await hass.async_block_till_done()

        assert coord.data["fields"]["dSeatHeatingState"] == "1"
        assert "dSeatHeatingState" in coord.data["probe_changed_fields"]
        assert sw_heat._opt_value is None
        assert hass.states.get("switch.lepas_driver_seat_heating").state == "on"
        assert coord.data["fields"]["frontHVACState"] == "1"
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
