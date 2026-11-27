"""Integration tests for smart charging coordination, debounce, away bypass, and diagnostics."""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import fixtures as FX
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.lepas.const import CONF_VIN, DOMAIN
from custom_components.lepas.coordinator import LepasCoordinator
from custom_components.lepas.diagnostics import async_get_config_entry_diagnostics
from custom_components.lepas.timers import CHARGE_PLUGIN_DEBOUNCE

HOME_LAT = 45.070312
HOME_LON = 7.686856
AWAY_LAT = 45.550000
AWAY_LON = 9.200000


def _set_home_zone(hass: HomeAssistant) -> None:
    hass.states.async_set(
        "zone.home",
        "0",
        {"latitude": HOME_LAT, "longitude": HOME_LON, "radius": 200},
    )


def _make_coord(
    hass: HomeAssistant,
    monkeypatch,
    *,
    entry_id: str = "smart_charge_entry",
) -> tuple[MockConfigEntry, LepasCoordinator, list[tuple[str, dict | None]]]:
    _set_home_zone(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_VIN: FX.VIN,
            "tuserid": FX.TUSERID,
            "email": FX.EMAIL,
            "pin": FX.PIN,
        },
        entry_id=entry_id,
    )
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry_id] = coord

    sent: list[tuple[str, dict | None]] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    async def noop_probe(force: bool = False) -> None:
        return None

    monkeypatch.setattr(coord, "async_send_command", fake_send)
    monkeypatch.setattr(coord, "async_probe", noop_probe)
    monkeypatch.setattr(coord._charging_store, "async_delay_save", lambda _fn, _d: None)
    return entry, coord, sent


def _mqtt_msg(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(
        payload=json.dumps(payload).encode("utf-8"),
        topic=f"app/6/{FX.TUSERID}/account/msgCenter/msg",
    )


def _send_5a02(coord: LepasCoordinator, **overrides) -> None:
    coord._on_car_message(None, None, _mqtt_msg(FX.telemetry_5a02(**overrides)))


def _send_1301(coord: LepasCoordinator, lat: float, lon: float) -> None:
    coord._on_car_message(None, None, _mqtt_msg(FX.position_1301(lat=lat, lon=lon)))


async def test_plugin_home_debounce_20s_and_cancel_on_unplug(
    hass: HomeAssistant, freezer, monkeypatch
) -> None:
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    now_local = datetime(2026, 11, 16, 22, 0, tzinfo=rome)  # Monday CET
    freezer.move_to(now_local)

    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="debounce_home")
    coord.set_charge_window_mode("smart_departure", sync_charge=False)
    coord.departure_weekly[2] = (True, 7 * 60)  # Tuesday 07:00 CET
    coord.charge_duration_hours = 6
    coord.home_charge_power = 2.3
    coord.home_charge_power_auto = False

    _send_1301(coord, HOME_LAT, HOME_LON)
    _send_5a02(coord, chargeGunState="0", chargeState="0", dumpEnergy="50")
    await hass.async_block_till_done()
    assert sent == []

    # Plug in at home -> arms 20s debounce without immediate send
    _send_5a02(coord, chargeGunState="1", chargeState="0", dumpEnergy="50")
    await hass.async_block_till_done()
    assert coord._timers.is_armed(CHARGE_PLUGIN_DEBOUNCE)
    assert sent == []

    # Unplug before 20s -> cancels debounce, firing past 20s sends nothing
    freezer.tick(timedelta(seconds=10))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    _send_5a02(coord, chargeGunState="0", chargeState="0", dumpEnergy="50")
    await hass.async_block_till_done()
    assert not coord._timers.is_armed(CHARGE_PLUGIN_DEBOUNCE)

    freezer.tick(timedelta(seconds=25))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert sent == []

    # Plug in again and let 20s expire -> sends smart window in UTC aligned to 15m
    _send_5a02(coord, chargeGunState="1", chargeState="0", dumpEnergy="50")
    await hass.async_block_till_done()
    assert coord._timers.is_armed(CHARGE_PLUGIN_DEBOUNCE)

    freezer.tick(timedelta(seconds=21))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(sent) == 1
    cmd_key, body = sent[0]
    assert cmd_key == "ricarica_prog_on"
    assert body is not None
    assert body["mainSwitch"] == 1
    plan = body["chargeAppointPlans"][0]
    # 50% missing of 18.4 kWh = 9.2 kWh at 2.3*0.90 kW + 25m = 291.7m -> ceil 15m = 300m
    # 07:00 CET - 300m = 02:00 CET = 01:00 UTC (60m)
    assert plan["startTime"] == 60
    assert plan["startTime"] % 15 == 0
    assert plan["timeConsuming"] == 300
    assert plan["switchStatus"] == 1
    coord.async_stop()


async def test_return_home_after_away_bypass_with_active_charging_state_1(
    hass: HomeAssistant, freezer, monkeypatch
) -> None:
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    now_local = datetime(2026, 11, 16, 21, 30, tzinfo=rome)
    freezer.move_to(now_local)

    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="return_after_bypass")
    coord.set_charge_window_mode("fixed", sync_charge=False)
    coord.charge_start_minutes = 23 * 60
    coord.charge_duration_hours = 6
    coord.charge_days = [1, 2, 3, 4, 5, 6, 7]

    # Car parked away with schedule active -> away_bypass disables schedule
    _send_1301(coord, AWAY_LAT, AWAY_LON)
    _send_5a02(
        coord,
        engineState="1",
        hVoltageState="1",
        chargeGunState="0",
        chargeAppointPlans="[{'switchStatus': '1', 'startTime': '1320'}]",
    )
    await hass.async_block_till_done()
    _send_5a02(
        coord,
        engineState="0",
        hVoltageState="0",
        chargeGunState="0",
        chargeAppointPlans="[{'switchStatus': '1', 'startTime': '1320'}]",
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(sent) == 1
    assert sent[0][0] == "ricarica_prog_off"
    sent.clear()

    # Drive back home, arrive unplugged, then plug in while car starts charging immediately (chargeState=1)
    _send_1301(coord, HOME_LAT, HOME_LON)
    _send_5a02(
        coord,
        engineState="0",
        hVoltageState="0",
        chargeGunState="0",
        chargeState="0",
        chargeAppointPlans="[{'switchStatus': '0', 'startTime': '1320'}]",
    )
    await hass.async_block_till_done()

    _send_5a02(
        coord,
        chargeGunState="1",
        chargeState="1",
        dumpEnergy="60",
        chargeAppointPlans="[{'switchStatus': '0', 'startTime': '1320'}]",
    )
    await hass.async_block_till_done()
    assert coord._timers.is_armed(CHARGE_PLUGIN_DEBOUNCE)

    freezer.tick(timedelta(seconds=21))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(sent) == 1
    assert sent[0][0] == "ricarica_prog_on"
    assert sent[0][1]["chargeAppointPlans"][0]["switchStatus"] == 1

    # Subsequent SoC bump during chargeState=1 must not re-send
    _send_5a02(
        coord,
        chargeGunState="1",
        chargeState="1",
        dumpEnergy="62",
        chargeAppointPlans="[{'switchStatus': '1', 'startTime': '1320'}]",
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(sent) == 1
    coord.async_stop()


async def test_no_retrigger_while_charging_already_scheduled(
    hass: HomeAssistant, monkeypatch
) -> None:
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    now_local = datetime(2026, 11, 16, 23, 0, tzinfo=rome)
    monkeypatch.setattr(dt_util, "now", lambda: now_local)
    monkeypatch.setattr(dt_util, "utcnow", lambda: now_local.astimezone(UTC))

    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="no_retrigger")
    coord.set_charge_window_mode("smart_departure", sync_charge=False)
    coord.departure_weekly[2] = (True, 7 * 60)
    coord.charge_duration_hours = 6

    _send_1301(coord, HOME_LAT, HOME_LON)
    coord._on_probe_data(
        {
            "chargeGunState": "1",
            "chargeState": "1",
            "dumpEnergy": "80",
            "chargingPower": "2.3",
            "pureElectricRange": "50",
        }
    )
    _send_5a02(
        coord,
        chargeGunState="1",
        chargeState="1",
        dumpEnergy="80",
        chargeAppointPlans="[{'switchStatus': '1', 'startTime': '240'}]",
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert sent == []

    for soc in ("81", "82"):
        _send_5a02(
            coord,
            chargeGunState="1",
            chargeState="1",
            dumpEnergy=soc,
            chargeAppointPlans="[{'switchStatus': '1', 'startTime': '240'}]",
        )
        coord._on_probe_data(
            {
                "chargeGunState": "1",
                "chargeState": "1",
                "dumpEnergy": soc,
                "chargingPower": "2.3",
                "pureElectricRange": "52",
            }
        )
        await coord._departure_tick_cb(_now=now_local)
        await hass.async_block_till_done(wait_background_tasks=True)

    assert sent == []
    coord.async_stop()


async def test_away_bypass_on_park_and_plugin_never_while_car_in_use(
    hass: HomeAssistant, monkeypatch
) -> None:
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    now_local = datetime(2026, 11, 16, 14, 0, tzinfo=rome)
    monkeypatch.setattr(dt_util, "now", lambda: now_local)
    monkeypatch.setattr(dt_util, "utcnow", lambda: now_local.astimezone(UTC))

    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="away_bypass")
    coord.set_charge_window_mode("fixed", sync_charge=False)
    coord.charge_start_minutes = 23 * 60
    coord.charge_duration_hours = 6
    coord.charge_days = [1, 2, 3, 4, 5, 6, 7]

    _send_1301(coord, AWAY_LAT, AWAY_LON)
    # Driving -> car_in_use == True: never sends ricarica_prog_off
    _send_5a02(
        coord,
        engineState="1",
        hVoltageState="1",
        chargeGunState="0",
        chargeAppointPlans="[{'switchStatus': '1', 'startTime': '1320'}]",
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coord.car_in_use is True
    coord.notify_schedule_changed(sync_charge=True)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert sent == []

    # Park away -> car_in_use True -> False sends ricarica_prog_off with non-None payload
    _send_5a02(
        coord,
        engineState="0",
        hVoltageState="0",
        chargeGunState="0",
        chargeAppointPlans="[{'switchStatus': '1', 'startTime': '1320'}]",
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coord.car_in_use is False
    assert len(sent) == 1
    cmd_key, body = sent[0]
    assert cmd_key == "ricarica_prog_off"
    assert body is not None
    assert body["mainSwitch"] == 0
    off_plan = body["chargeAppointPlans"][0]
    assert off_plan["switchStatus"] == 0
    assert off_plan["startTime"] % 15 == 0
    assert len(off_plan["cycleData"]) > 0
    assert off_plan["timeConsuming"] > 0
    assert not coord._timers.is_armed(CHARGE_PLUGIN_DEBOUNCE)

    # Plug in away after schedule was somehow enabled -> sends ricarica_prog_off without debounce
    sent.clear()
    coord._last_synced_charge_sig = ("enable", 23 * 60, 360, (1, 2, 3, 4, 5, 6, 7), "fixed")
    _send_5a02(
        coord,
        engineState="0",
        chargeGunState="1",
        chargeAppointPlans="[{'switchStatus': '1', 'startTime': '1320'}]",
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    assert not coord._timers.is_armed(CHARGE_PLUGIN_DEBOUNCE)
    assert len(sent) == 1
    assert sent[0][0] == "ricarica_prog_off"
    coord.async_stop()


async def test_fixed_mode_quick_override_preserves_charge_start_minutes(
    hass: HomeAssistant, monkeypatch
) -> None:
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    now_local = datetime(2026, 11, 16, 22, 0, tzinfo=rome)
    monkeypatch.setattr(dt_util, "now", lambda: now_local)
    monkeypatch.setattr(dt_util, "utcnow", lambda: now_local.astimezone(UTC))

    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="fixed_quick_override")
    coord.set_charge_window_mode("fixed", sync_charge=False)
    coord.charge_start_minutes = 23 * 60
    coord.charge_duration_hours = 6
    coord.charge_days = [1, 2, 3, 4, 5, 6, 7]
    coord.home_charge_power = 2.3
    coord.home_charge_power_auto = False

    _send_1301(coord, HOME_LAT, HOME_LON)
    coord._on_probe_data(
        {
            "chargeGunState": "1",
            "chargeState": "0",
            "dumpEnergy": "80",
            "pureElectricRange": "50",
        }
    )
    await hass.async_block_till_done()

    # Enable quick departure 07:00 -> smart override sent, charge_start_minutes preserved at 23:00
    await coord.async_set_quick_departure(7 * 60, enabled=True)
    assert coord.charge_start_minutes == 23 * 60
    assert len(sent) == 1
    assert sent[0][0] == "ricarica_prog_on"
    # 20% of 18.4 kWh = 3.68 kWh / (2.3 * 0.9) * 60 + 25 = 131.67m -> 135m
    # 07:00 CET - 135m = 04:45 CET = 03:45 UTC (225m)
    assert sent[0][1]["chargeAppointPlans"][0]["startTime"] == 225
    assert sent[0][1]["chargeAppointPlans"][0]["timeConsuming"] == 135

    # Quick departure expires while plugged at home -> restores fixed 23:00 CET (22:00 UTC = 1320)
    sent.clear()
    expired_at = datetime(2026, 11, 17, 7, 1, tzinfo=rome)
    monkeypatch.setattr(dt_util, "now", lambda: expired_at)
    await coord._departure_tick_cb(_now=expired_at)
    assert coord.quick_departure_enabled is False
    assert coord.charge_start_minutes == 23 * 60
    assert len(sent) == 1
    assert sent[0][0] == "ricarica_prog_on"
    assert sent[0][1]["chargeAppointPlans"][0]["startTime"] == 22 * 60
    assert sent[0][1]["chargeAppointPlans"][0]["timeConsuming"] == 360

    # Re-enable quick departure (11:00 -> smart start 08:45 > 08:00), then unplug before expiration -> clears sig with zero cloud call
    t2 = datetime(2026, 11, 17, 8, 0, tzinfo=rome)
    monkeypatch.setattr(dt_util, "now", lambda: t2)
    await coord.async_set_quick_departure(11 * 60, enabled=True)
    assert isinstance(coord._last_synced_charge_sig, tuple)
    assert str(coord._last_synced_charge_sig[4]).startswith("quick:")

    coord._on_probe_data(
        {
            "chargeGunState": "0",
            "chargeState": "0",
            "dumpEnergy": "80",
            "pureElectricRange": "50",
        }
    )
    await hass.async_block_till_done()
    sent.clear()

    t2_expired = datetime(2026, 11, 17, 11, 1, tzinfo=rome)
    monkeypatch.setattr(dt_util, "now", lambda: t2_expired)
    await coord._departure_tick_cb(_now=t2_expired)
    assert coord.quick_departure_enabled is False
    assert coord._last_synced_charge_sig is None
    assert coord.charge_start_minutes == 23 * 60
    assert sent == []
    coord.async_stop()


async def test_tick_safety_net_requires_plugged_and_resets_attempted_on_new_plugin(
    hass: HomeAssistant, freezer, monkeypatch
) -> None:
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    # Tuesday 01:30 CET: inside [02:00 - 60m, 07:00) for smart_start 02:00 CET
    now_local = datetime(2026, 11, 17, 1, 30, tzinfo=rome)
    freezer.move_to(now_local)

    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="tick_safety_net")
    coord.set_charge_window_mode("smart_departure", sync_charge=False)
    coord.departure_weekly[2] = (True, 7 * 60)
    coord.charge_duration_hours = 6
    coord.home_charge_power = 2.3
    coord.home_charge_power_auto = False

    _send_1301(coord, HOME_LAT, HOME_LON)
    coord._on_probe_data(
        {
            "chargeGunState": "0",
            "chargeState": "0",
            "dumpEnergy": "50",
            "pureElectricRange": "40",
        }
    )
    await hass.async_block_till_done()

    # Unplugged at home -> tick safety net sends nothing (AB-LEP-001)
    await coord._departure_tick_cb(_now=now_local)
    assert sent == []

    # Plugged in + failing send -> sets _last_attempted_charge_sig and avoids 60s storm
    coord._on_probe_data(
        {
            "chargeGunState": "1",
            "chargeState": "0",
            "dumpEnergy": "50",
            "pureElectricRange": "40",
        }
    )
    await hass.async_block_till_done()
    coord._timers.cancel(CHARGE_PLUGIN_DEBOUNCE)

    fail_count = 0

    async def failing_send(key: str, params: dict | None = None) -> str:
        nonlocal fail_count
        fail_count += 1
        raise HomeAssistantError("cloud timeout")

    monkeypatch.setattr(coord, "async_send_command", failing_send)
    await coord._departure_tick_cb(_now=now_local)
    assert fail_count == 1
    assert coord._last_attempted_charge_sig is not None

    await coord._departure_tick_cb(_now=now_local + timedelta(minutes=1))
    assert fail_count == 1

    # Unplug then new plug-in resets _last_attempted_charge_sig and retries after 20s
    _send_5a02(coord, chargeGunState="0", chargeState="0", dumpEnergy="50")
    await hass.async_block_till_done()

    async def ok_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", ok_send)
    _send_5a02(coord, chargeGunState="1", chargeState="0", dumpEnergy="50")
    await hass.async_block_till_done()
    assert coord._last_attempted_charge_sig is None

    freezer.tick(timedelta(seconds=21))
    async_fire_time_changed(hass)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(sent) == 1
    assert sent[0][0] == "ricarica_prog_on"

    # No deadlock on _departure_lock across async_set_quick_departure and _departure_tick_cb
    await asyncio.wait_for(
        coord.async_set_quick_departure(9 * 60, enabled=True),
        timeout=1.0,
    )
    await asyncio.wait_for(
        coord._departure_tick_cb(_now=now_local + timedelta(minutes=2)),
        timeout=1.0,
    )
    coord.async_stop()


async def test_diagnostics_smart_charging_redacted_no_pii(
    hass: HomeAssistant, monkeypatch
) -> None:
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    now_local = datetime(2026, 11, 16, 22, 0, tzinfo=rome)
    monkeypatch.setattr(dt_util, "now", lambda: now_local)
    monkeypatch.setattr(dt_util, "utcnow", lambda: now_local.astimezone(UTC))

    entry, coord, _sent = _make_coord(hass, monkeypatch, entry_id="diag_smart_charge")
    coord.set_charge_window_mode("smart_departure", sync_charge=False)
    coord.home_charge_power_auto = True
    coord.home_charge_power = 3.7
    coord.departure_weekly[2] = (True, 7 * 60)

    # Seed learned AC session
    with coord._charging_lock:
        for i in range(4):
            coord._charging_tracker.ingest(
                1000.0 + i * 120.0,
                "2026-11-16",
                power_kw=3.4,
                charge_state="1",
                plugged=True,
                soc_pct=40.0 + i,
                odometer=100.0,
                in_home_zone=True,
                degraded_battery=False,
                fast_charging=False,
            )
        coord._charging_tracker.ingest(
            1600.0,
            "2026-11-16",
            power_kw=0.0,
            charge_state="0",
            plugged=False,
            soc_pct=45.0,
            odometer=100.0,
            in_home_zone=True,
            degraded_battery=False,
            fast_charging=False,
        )

    _send_1301(coord, HOME_LAT, HOME_LON)
    await hass.async_block_till_done()
    plan = coord.evaluate_charge_plan(now_local)
    assert plan.reason == "smart_home"

    diag = await async_get_config_entry_diagnostics(hass, entry)
    sc = diag["smart_charging"]
    assert sc == {
        "window_mode": "smart_departure",
        "home_charge_power_auto": True,
        "home_charge_power_kw": 3.7,
        "learned_ac_kw": 3.4,
        "learned_dc_kw": None,
        "home_ac_sessions": 1,
        "home_dc_sessions": 0,
        "last_plan_reason": "smart_home",
    }

    blob = json.dumps(diag, default=str)
    for secret in (FX.VIN, FX.EMAIL, FX.PIN, str(HOME_LAT), str(HOME_LON)):
        assert secret not in blob
    coord.async_stop()


async def test_mode_validation_restore_legacy_sync_and_dc_plan(
    hass: HomeAssistant, monkeypatch
) -> None:
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    now_local = datetime(2026, 11, 16, 22, 0, tzinfo=rome)
    monkeypatch.setattr(dt_util, "now", lambda: now_local)
    monkeypatch.setattr(dt_util, "utcnow", lambda: now_local.astimezone(UTC))

    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="mode_restore_dc")

    with pytest.raises(ValueError):
        coord.set_charge_window_mode("solar")
    with pytest.raises(ValueError):
        coord.build_charge_appoint_plan(local_start_minutes=60, local_days=[1])

    # Legacy sync_charge_to_departure setter preserves "off" when False
    assert coord.charge_window_mode == "off"
    coord.sync_charge_to_departure = False
    assert coord.charge_window_mode == "off"
    coord.sync_charge_to_departure = True
    assert coord.charge_window_mode == "smart_departure"
    coord.sync_charge_to_departure = False
    assert coord.charge_window_mode == "fixed"

    # from_restore=True notifies listeners without sending cloud commands
    hits: list[str] = []
    unsub = coord.async_add_listener(lambda: hits.append(coord.charge_window_mode))
    try:
        _send_1301(coord, HOME_LAT, HOME_LON)
        await hass.async_block_till_done()
        coord.set_charge_window_mode("smart_departure", from_restore=True)
        await hass.async_block_till_done(wait_background_tasks=True)
        assert coord._charge_window_mode_restored is True
        assert hits[-1] == "smart_departure"
        assert sent == []
    finally:
        unsub()

    # fastChargingGunStatus=1 -> DC classification + no_departure_24h disables active schedule
    _send_5a02(
        coord,
        chargeGunState="0",
        fastChargingGunStatus="1",
        dumpEnergy="50",
        chargeAppointPlans="[{'switchStatus': '1', 'startTime': '60'}]",
    )
    await hass.async_block_till_done()
    plan = coord.evaluate_charge_plan(now_local)
    assert plan.charge_kind == "dc"
    assert plan.action == "disable"
    assert plan.reason == "no_departure_24h"

    coord._last_attempted_charge_sig = ("enable", 60, 360, (1, 2, 3, 4, 5, 6, 7), "fixed")
    await coord.async_apply_charging_schedule(start_minutes=60, duration_hours=6, days=[1, 2, 3, 4, 5, 6, 7])
    assert coord._last_attempted_charge_sig is None
    assert coord._last_synced_charge_sig == ("enable", 60, 360, (1, 2, 3, 4, 5, 6, 7), "manual")
    coord.async_stop()


async def test_departure_tick_ui_sig_notifications_and_dedup(
    hass: HomeAssistant, monkeypatch
) -> None:
    """_departure_tick_cb notifies real listeners on UI state changes without duplicates."""
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    current_now = [datetime(2026, 11, 16, 23, 58, tzinfo=rome)]
    monkeypatch.setattr(dt_util, "now", lambda: current_now[0])
    monkeypatch.setattr(dt_util, "utcnow", lambda: current_now[0].astimezone(UTC))

    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="tick_ui_sig")
    coord.departure_climate_mode = "off"
    coord.departure_weekly[3] = (True, 7 * 60)  # Wednesday 07:00 CET
    coord.charge_duration_hours = 6
    coord.home_charge_power = 2.3
    coord.home_charge_power_auto = False
    # Align charge_start_minutes to 02:00 CET so no_departure_24h -> smart_home
    # proves tick_ui_sig drives the UI update even without charge_start_minutes change.
    coord.charge_start_minutes = 2 * 60
    coord.set_charge_window_mode("smart_departure", sync_charge=False)

    _send_1301(coord, HOME_LAT, HOME_LON)
    _send_5a02(coord, chargeGunState="0", chargeState="0", dumpEnergy="50")
    await hass.async_block_till_done()
    sent.clear()

    hits: list[tuple[str | None, str | None, str | None]] = []

    def _on_update() -> None:
        plan = coord._last_desired_charge_plan
        occ = coord.next_departure_occurrence(current_now[0])
        hits.append(
            (
                plan.action if plan is not None else None,
                plan.reason if plan is not None else None,
                occ.key if occ is not None else None,
            )
        )

    unsub = coord.async_add_listener(_on_update)
    try:
        # Initial tick seeds _last_tick_ui_sig without spurious notification
        await coord._departure_tick_cb(_now=current_now[0])
        assert hits == []

        # (a) Stable tick emits no redundant notification
        current_now[0] = datetime(2026, 11, 16, 23, 59, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert hits == []

        # (b) Midnight rollover (now.date() change) notifies once
        current_now[0] = datetime(2026, 11, 17, 0, 0, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert len(hits) == 1
        assert hits[-1][:2] == ("disable", "no_departure_24h")

        current_now[0] = datetime(2026, 11, 17, 0, 1, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert len(hits) == 1

        # (c) Transition no_departure_24h -> smart_home (smart_start 02:00 CET Wed)
        current_now[0] = datetime(2026, 11, 17, 2, 14, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert len(hits) == 1

        current_now[0] = datetime(2026, 11, 17, 2, 15, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert len(hits) == 2
        assert hits[-1][:2] == ("enable", "smart_home")

        # Midnight rollover into Wednesday notifies once
        current_now[0] = datetime(2026, 11, 18, 1, 59, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert len(hits) == 3
        assert hits[-1][:2] == ("enable", "smart_home")

        # (d) Transition smart_home -> late_plug_in at 02:00 CET while unplugged
        current_now[0] = datetime(2026, 11, 18, 2, 0, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert len(hits) == 4
        assert hits[-1][:2] == ("disable", "late_plug_in")

        current_now[0] = datetime(2026, 11, 18, 6, 59, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert len(hits) == 4

        # (e) Occurrence expiration at 07:00 CET with departure_climate_mode="off" notifies once
        prev_occ_key = hits[-1][2]
        current_now[0] = datetime(2026, 11, 18, 7, 0, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert len(hits) == 5
        assert hits[-1][:2] == ("disable", "no_departure_24h")
        assert hits[-1][2] != prev_occ_key

        # Also verify occ expiration notifies when charge_window_mode="off" (only occ.key changes)
        coord.set_charge_window_mode("off", sync_charge=False)
        coord.departure_weekly[3] = (False, 7 * 60)
        coord.departure_weekly[4] = (True, 9 * 60)
        coord._last_tick_ui_sig = None
        hits.clear()

        current_now[0] = datetime(2026, 11, 19, 8, 59, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert hits == []

        current_now[0] = datetime(2026, 11, 19, 9, 0, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert len(hits) == 1
        assert hits[-1][:2] == ("noop", "mode_off")

        # Verify Sentinel #5 dedup: when charge_start_minutes mutates during smart_home transition,
        # listener is notified once (not twice).
        coord.departure_weekly[4] = (False, 9 * 60)
        coord.departure_weekly[5] = (True, 7 * 60)  # Friday 07:00 CET
        coord.charge_start_minutes = 8 * 60
        coord.set_charge_window_mode("smart_departure", sync_charge=False)
        coord._last_tick_ui_sig = None
        hits.clear()

        current_now[0] = datetime(2026, 11, 19, 2, 14, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert hits == []

        current_now[0] = datetime(2026, 11, 19, 2, 15, tzinfo=rome)
        await coord._departure_tick_cb(_now=current_now[0])
        assert len(hits) == 1
        assert hits[-1][:2] == ("enable", "smart_home")
        assert coord.charge_start_minutes == 2 * 60

        assert sent == []
    finally:
        unsub()
        coord.async_stop()
