"""Tests for native departure scheduling, battery pack heat, climate extras & services."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import fixtures as FX
import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

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

    assert commands.CMD_MAP["partenza_prog_on"]["endpoint"] == "travelAppointControl"
    assert commands.CMD_MAP["partenza_prog_on"]["body"]["mainSwitcher"] == "1"
    assert commands.CMD_MAP["partenza_prog_off"]["endpoint"] == "travelAppointControl"
    assert commands.CMD_MAP["partenza_prog_off"]["body"]["mainSwitcher"] == "0"
    assert commands.CMD_MAP["partenza_prog_off"]["body"]["appointmentTravelSetVOS"][0]["travelWeekday"] == ""

    assert commands.CMD_MAP["battery_heat_on"]["endpoint"] == "batteryPackHeat"
    assert commands.CMD_MAP["battery_heat_on"]["body"]["switchState"] == "1"
    assert commands.CMD_MAP["battery_heat_off"]["endpoint"] == "batteryPackHeat"
    assert commands.CMD_MAP["battery_heat_off"]["body"] == {"switchState": "0", "startTime": "0"}


def test_query_travel_appoint_and_battery_pack_heat(core, cloud, ctx):
    commands = core["commands"]

    # Primary endpoint succeeds
    cloud.on(
        "/asc/vehicleControl/travelAppointQuery",
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

    # Fallback endpoint when primary fails
    cloud.on("/asc/vehicleControl/travelAppointQuery", raises=TimeoutError("timeout"))
    cloud.on(
        "/asd/travelAppointManage/travelAppointQuery",
        code="000000",
        data=[{"id": 555, "switcher": "1", "travelTime": "360", "travelWeekday": "1,3,5"}],
    )
    res_fb = commands.query_travel_appoint(ctx)
    assert isinstance(res_fb, dict)
    assert res_fb["appointmentTravelSetVOS"][0]["id"] == 555

    # Error code -> None
    cloud.on("/asd/travelAppointManage/travelAppointQuery", code="A00084", data={})
    assert commands.query_travel_appoint(ctx) is None

    # Battery pack heat query
    cloud.on(
        "/asc/vehicleControl/queryBatteryPackHeat",
        code="000000",
        data={"switchState": "1", "startTime": "390"},
    )
    bh = commands.query_battery_pack_heat(ctx)
    assert bh == {"switchState": "1", "startTime": "390"}

    cloud.on("/asc/vehicleControl/queryBatteryPackHeat", raises=RuntimeError("boom"))
    assert commands.query_battery_pack_heat(ctx) is None


# ───────────────────────────── 4. Permissions & V5 Backfill ─────────────────────────────


def test_permessi_travel_and_battery_tables_and_csv_giorni(core):
    P = core["permessi"]
    commands = core["commands"]

    assert P.CATEGORIA["travelAppointControl"] == 212
    assert P.CATEGORIA["batteryPackHeat"] == 216
    assert P.CICLO["travelAppointControl"] == (2121, 2122, "travelWeekday")

    # CSV parsing
    body_csv = {
        "mainSwitcher": "1",
        "appointmentTravelSetVOS": [{"planId": 1, "switcher": "1", "travelTime": "305", "travelWeekday": "1,3,5"}],
    }
    assert P._giorni(body_csv, "travelWeekday") == [1, 3, 5]
    assert P.ciclo_non_autorizzato("travelAppointControl", body_csv, {212: 1, 2121: 0, 2122: 1}) is not None
    assert P.ciclo_non_autorizzato("travelAppointControl", body_csv, {212: 1, 2121: 1, 2122: 0}) is None

    # All 7 days CSV triggers 2122 check
    body_all = {"appointmentTravelSetVOS": [{"travelWeekday": "1,2,3,4,5,6,7"}]}
    assert P.ciclo_non_autorizzato("travelAppointControl", body_all, {212: 1, 2121: 1, 2122: 0}) is not None

    # Empty "" on partenza_prog_off is non-blocking
    off_body = dict(commands.CMD_MAP["partenza_prog_off"]["body"])
    assert P._giorni(off_body, "travelWeekday") is None
    assert P.ciclo_non_autorizzato("travelAppointControl", off_body, {212: 1, 2121: 0, 2122: 0}) is None


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
    vo = sent[0][1]["appointmentTravelSetVOS"][0]
    assert sent[0][1]["mainSwitcher"] == "1"
    assert vo["id"] == 777123
    assert vo["planId"] == 1
    assert vo["switcher"] == "1"
    assert vo["travelTime"] == "360"
    assert vo["travelWeekday"] == "1,3,5"

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
    vo2 = sent[1][1]["appointmentTravelSetVOS"][0]
    assert "id" not in vo2
    assert vo2["travelTime"] == str(23 * 60 + 30)
    assert vo2["travelWeekday"] == "1,2,3,4,5,6,7"

    # No active departure -> partenza_prog_off
    for d in range(1, 8):
        coord.departure_weekly[d] = (False, 420)
    await coord.async_apply_departure_schedule()
    assert sent[2][0] == "partenza_prog_off"
    assert sent[2][1]["mainSwitcher"] == "0"
    assert sent[2][1]["appointmentTravelSetVOS"][0]["switcher"] == "0"
    assert sent[2][1]["appointmentTravelSetVOS"][0]["travelWeekday"] == ""


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
    assert [s[0] for s in sent[3:]] == ["partenza_prog_off", "battery_heat_off"]
    assert sent[-1][1] == {"switchState": "0", "startTime": "0"}

    # Now verify departure_climate_mode == "off" expires cleanly to weekly restore!
    sent.clear()
    coord.departure_climate_mode = "off"
    coord.departure_weekly[2] = (True, 7 * 60)  # Tuesday 07:00
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 17, 40, tzinfo=tz))
    await coord.async_set_quick_departure(18 * 60, True)
    assert sent[0][0] == "partenza_prog_on"
    assert sent[0][1]["appointmentTravelSetVOS"][0]["travelWeekday"] == "1"

    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 18, 1, tzinfo=tz))
    assert coord.quick_departure_enabled is False
    assert coord._quick_target_at is None
    assert coord._quick_native_until is None
    # Restored to Tuesday 07:00 native & 06:30 battery heat
    assert sent[-2][0] == "partenza_prog_on"
    assert sent[-2][1]["appointmentTravelSetVOS"][0]["travelWeekday"] == "2"
    assert sent[-2][1]["appointmentTravelSetVOS"][0]["travelTime"] == str(7 * 60)
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

    monkeypatch.setattr(coord, "async_send_command", fake_send)
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
        "/asc/vehicleControl/travelAppointQuery",
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
    assert sent[0][1]["appointmentTravelSetVOS"][0]["id"] == 445566

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
