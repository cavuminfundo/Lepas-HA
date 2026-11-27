"""Test del motore scheduler, feature gating V4, coordinazione partenze/ricarica e teardown."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

import fixtures as FX
from custom_components.lepas.const import (
    CONF_VIN,
    DATA_CAPS_PROBED_V3,
    DATA_CAPS_PROBED_V4,
    DATA_VEHICLE_FEATURES,
    DOMAIN,
    ENTITY_FEATURE_MAP,
    PLATFORMS,
    entity_allowed,
    features_from_permissions,
)
from custom_components.lepas.coordinator import LepasCoordinator
from custom_components.lepas.core.commands import duration_params_for_command
from custom_components.lepas.scheduler import (
    CHARGE_DAYS_PRESETS,
    DEPARTURE_DAY_SLUGS,
    DepartureOccurrence,
    compute_charge_start_for_departure,
    compute_charge_window,
    compute_next_occurrence,
    parse_days_input,
    preset_for_days,
)
from custom_components.lepas.timers import DEPARTURE_TICK


def _make_coord(hass, *, data: dict | None = None, entry_id: str = "sched_entry") -> LepasCoordinator:
    base = {
        CONF_VIN: FX.VIN,
        "tuserid": FX.TUSERID,
        "email": FX.EMAIL,
        "pin": FX.PIN,
    }
    if data:
        base.update(data)
    entry = MockConfigEntry(domain=DOMAIN, data=base, entry_id=entry_id)
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry_id] = coord
    return coord


# ───────────────────────────── scheduler.py ─────────────────────────────

def test_presets_and_day_slugs():
    assert CHARGE_DAYS_PRESETS == {
        "all_days": [1, 2, 3, 4, 5, 6, 7],
        "weekdays": [1, 2, 3, 4, 5],
        "weekend": [6, 7],
        "mon_wed_fri": [1, 3, 5],
        "tue_thu_sat": [2, 4, 6],
    }
    assert DEPARTURE_DAY_SLUGS == {
        1: "mon",
        2: "tue",
        3: "wed",
        4: "thu",
        5: "fri",
        6: "sat",
        7: "sun",
    }


def test_compute_next_occurrence_none_when_disabled():
    now = datetime(2026, 11, 16, 8, 0, tzinfo=timezone.utc)  # Monday
    weekly = {d: (False, 420) for d in range(1, 8)}
    assert compute_next_occurrence(now, weekly, False, 1080, 15) is None


def test_compute_next_occurrence_weekly_today_and_inside_window():
    tz = ZoneInfo("Europe/Rome")
    weekly = {d: (d == 1, 420) for d in range(1, 8)}  # Monday 07:00

    # Before climate window
    occ = compute_next_occurrence(datetime(2026, 11, 16, 6, 30, tzinfo=tz), weekly, False, 1080, 15)
    assert isinstance(occ, DepartureOccurrence)
    assert occ.source == "weekly"
    assert occ.weekday == 1
    assert occ.departure_at == datetime(2026, 11, 16, 7, 0, tzinfo=tz)
    assert occ.climate_start_at == datetime(2026, 11, 16, 6, 45, tzinfo=tz)
    assert occ.departure_at_minutes == 420
    assert occ.key

    # Inside [06:45, 07:00) still picks today's 07:00
    occ_in = compute_next_occurrence(datetime(2026, 11, 16, 6, 59, tzinfo=tz), weekly, False, 1080, 15)
    assert occ_in is not None
    assert occ_in.departure_at == datetime(2026, 11, 16, 7, 0, tzinfo=tz)


def test_compute_next_occurrence_weekly_rollover_on_le_now():
    tz = timezone.utc
    weekly = {d: (d == 1, 420) for d in range(1, 8)}  # Monday 07:00 only

    # Exactly at 07:00 -> rolls to next Monday
    occ_eq = compute_next_occurrence(datetime(2026, 11, 16, 7, 0, tzinfo=tz), weekly, False, 1080, 15)
    assert occ_eq is not None
    assert occ_eq.departure_at == datetime(2026, 11, 23, 7, 0, tzinfo=tz)

    # After 07:00 -> rolls to next Monday
    occ_after = compute_next_occurrence(datetime(2026, 11, 16, 7, 1, tzinfo=tz), weekly, False, 1080, 15)
    assert occ_after is not None
    assert occ_after.departure_at == datetime(2026, 11, 23, 7, 0, tzinfo=tz)


def test_compute_next_occurrence_quick_rollover_and_tie_priority():
    tz = timezone.utc
    weekly = {d: (d == 1, 18 * 60) for d in range(1, 8)}  # Monday 18:00

    # Exact tie at Monday 18:00 -> quick has priority
    occ_tie = compute_next_occurrence(datetime(2026, 11, 16, 17, 0, tzinfo=tz), weekly, True, 18 * 60, 15)
    assert occ_tie is not None
    assert occ_tie.source == "quick"
    assert occ_tie.departure_at == datetime(2026, 11, 16, 18, 0, tzinfo=tz)

    # Weekly earlier (07:00) than quick (18:00) -> weekly wins
    weekly_early = {d: (d == 1, 7 * 60) for d in range(1, 8)}
    occ_early = compute_next_occurrence(datetime(2026, 11, 16, 6, 0, tzinfo=tz), weekly_early, True, 18 * 60, 15)
    assert occ_early is not None
    assert occ_early.source == "weekly"
    assert occ_early.departure_at == datetime(2026, 11, 16, 7, 0, tzinfo=tz)

    # Quick <= now -> rolls to tomorrow
    occ_next_day = compute_next_occurrence(
        datetime(2026, 11, 16, 18, 0, tzinfo=tz),
        {d: (False, 420) for d in range(1, 8)},
        True,
        18 * 60,
        15,
    )
    assert occ_next_day is not None
    assert occ_next_day.source == "quick"
    assert occ_next_day.departure_at == datetime(2026, 11, 17, 18, 0, tzinfo=tz)
    assert occ_next_day.weekday == 2


def test_compute_charge_window_and_start_for_departure():
    assert compute_charge_window(8 * 60, 6, [1, 2, 3, 4, 5]) == ("08:00", "14:00", False)
    assert compute_charge_window(23 * 60, 6, [1, 2, 3, 4, 5, 6, 7]) == ("23:00", "05:00", True)
    assert compute_charge_window(18 * 60, 6, [1, 2, 3, 4, 5, 6, 7]) == ("18:00", "00:00", True)

    assert compute_charge_start_for_departure(7 * 60, 6) == 60
    assert compute_charge_start_for_departure(5 * 60, 6) == 23 * 60  # midnight wrap
    assert compute_charge_start_for_departure(0, 6) == 18 * 60
    assert compute_charge_start_for_departure(8 * 60, 8) == 0


def test_preset_for_days_and_parse_days_input():
    assert preset_for_days([1, 2, 3, 4, 5, 6, 7]) == "all_days"
    assert preset_for_days([5, 3, 1, 2, 4]) == "weekdays"
    assert preset_for_days([6, 7]) == "weekend"
    assert preset_for_days([1, 3, 5]) == "mon_wed_fri"
    assert preset_for_days([2, 4, 6]) == "tue_thu_sat"
    assert preset_for_days([1, 4]) == "custom"

    # Valid inputs
    assert parse_days_input("all_days") == [1, 2, 3, 4, 5, 6, 7]
    assert parse_days_input("WEEKDAYS") == [1, 2, 3, 4, 5]
    assert parse_days_input("mon,wed,fri") == [1, 3, 5]
    assert parse_days_input("5, 1, 3") == [1, 3, 5]
    assert parse_days_input("sun,1") == [1, 7]
    assert parse_days_input(4) == [4]
    assert parse_days_input(["tue", 6, "tue"]) == [2, 6]

    # Reject booleans, empty, out-of-range, non-exact substrings
    for bad in (
        True,
        False,
        [True],
        [1, False],
        None,
        "",
        "   ",
        [],
        0,
        8,
        "0",
        "8",
        "1,,2",
        "1,",
        "weekday",
        "all",
        "custom",
        "monday",
        "sunflower",
        "1.5",
        1.5,
        "+1",
        "01",
        {"days": [1]},
    ):
        with pytest.raises(ValueError):
            parse_days_input(bad)


# ───────────────────────────── const.py ─────────────────────────────

def test_const_platforms_v4_permissions_and_entity_feature_map(hass):
    assert "select" in PLATFORMS
    assert DATA_CAPS_PROBED_V4 == "caps_probed_v4"

    vf = features_from_permissions({213: 1, 2131: 0, 2132: 1})
    assert vf["scheduled_charging"] is True
    assert vf["scheduled_charging_custom_days"] is False

    # Absent 2131 -> fail-open
    vf_absent = features_from_permissions({213: 1})
    assert "scheduled_charging_custom_days" not in vf_absent

    expected_map = {
        ("select", "charge_days"): "scheduled_charging",
        ("button", "apply_charging_schedule"): "scheduled_charging",
        ("switch", "sync_charge_to_departure"): "scheduled_charging",
        ("sensor", "scheduled_charging_window"): "scheduled_charging",
        ("select", "departure_climate_mode"): "climate",
    }
    for pair, feat in expected_map.items():
        assert ENTITY_FEATURE_MAP[pair] == feat

    coord_enabled = _make_coord(hass, data={DATA_VEHICLE_FEATURES: {"scheduled_charging": True, "climate": True}}, entry_id="e_on")
    assert coord_enabled.feature_enabled("scheduled_charging_custom_days") is True
    for domain, suffix in expected_map:
        assert entity_allowed(coord_enabled, domain, suffix) is True

    coord_disabled = _make_coord(hass, data={DATA_VEHICLE_FEATURES: {"scheduled_charging": False, "climate": False}}, entry_id="e_off")
    for domain, suffix in expected_map:
        assert entity_allowed(coord_disabled, domain, suffix) is False


# ───────────────────────────── coordinator.py ─────────────────────────────

def test_coordinator_scheduler_defaults(hass):
    coord = _make_coord(hass)
    assert coord.clima_duration == 15
    assert coord.departure_preclimate_duration == 15
    assert coord._sched_opt_seq == 0
    assert coord._scheduled_opt == {}
    assert coord.charge_duration_hours == 6
    assert coord.charge_start_minutes == 480
    assert coord.charge_days == [1, 2, 3, 4, 5, 6, 7]
    assert coord.climate_target_temp == 21.0
    assert coord.quick_departure_enabled is False
    assert coord.quick_departure_minutes == 1080
    assert coord.departure_weekly == {d: (False, 420) for d in range(1, 8)}
    assert coord.departure_climate_mode == "at_home"
    assert coord.sync_charge_to_departure is False
    assert coord._probed_permessi is None
    assert coord._departure_busy is False
    assert coord._quick_target_at is None
    assert coord._fired_climate_key is None
    assert coord._attempted_climate_key is None
    assert coord._last_synced_charge_sig is None
    assert coord._last_attempted_charge_sig is None


async def test_preclimate_window_and_deduplication(hass, monkeypatch):
    coord = _make_coord(hass)
    tz = timezone.utc
    coord.departure_weekly[1] = (True, 7 * 60)  # Monday 07:00
    coord.clima_duration = 15
    coord.climate_target_temp = 22.5
    coord.departure_climate_mode = "anywhere"

    sent: list[tuple[str, dict | None]] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", fake_send)

    # Before window
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 44, tzinfo=tz))
    assert sent == []

    # Inside [06:45, 07:00)
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 45, tzinfo=tz))
    assert sent == [("clima_on", {"temperature": "22.5", "times": "15"})]
    assert coord._fired_climate_key is not None

    # Deduplicated on subsequent tick in same window
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 50, tzinfo=tz))
    assert len(sent) == 1

    # At exact departure_at (07:00) rolls over -> does not fire
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 7, 0, tzinfo=tz))
    assert len(sent) == 1


async def test_preclimate_at_home_guard_and_engine_speed_off(hass, monkeypatch):
    hass.config.latitude, hass.config.longitude = 45.0, 9.0
    assert await async_setup_component(hass, "zone", {})
    await hass.async_block_till_done()

    tz = timezone.utc
    tick_time = datetime(2026, 11, 16, 6, 50, tzinfo=tz)  # Mon inside [06:45, 07:00)
    sent: list[tuple[str, dict | None]] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    # 1. at_home + away -> skipped
    c1 = _make_coord(hass, entry_id="c_away")
    c1.departure_weekly[1] = (True, 7 * 60)
    c1.departure_climate_mode = "at_home"
    c1.position = {"lat": 46.5, "lon": 11.5}
    monkeypatch.setattr(c1, "async_send_command", fake_send)
    await c1._departure_tick_cb(_now=tick_time)
    assert sent == []
    assert c1._fired_climate_key is not None

    # 2. at_home + no position -> skipped
    c2 = _make_coord(hass, entry_id="c_nopos")
    c2.departure_weekly[1] = (True, 7 * 60)
    c2.departure_climate_mode = "at_home"
    c2.position = None
    monkeypatch.setattr(c2, "async_send_command", fake_send)
    await c2._departure_tick_cb(_now=tick_time)
    assert sent == []

    # 3. at_home + at home + engineState active -> skipped
    c3 = _make_coord(hass, entry_id="c_eng")
    c3.departure_weekly[1] = (True, 7 * 60)
    c3.departure_climate_mode = "at_home"
    c3.position = {"lat": 45.0, "lon": 9.0}
    c3.data["realtime"] = {"engineState": "1", "vehicleSpeed": "0"}
    monkeypatch.setattr(c3, "async_send_command", fake_send)
    await c3._departure_tick_cb(_now=tick_time)
    assert sent == []

    # 4. at_home + at home + vehicleSpeed > 0 -> skipped
    c3.data["realtime"] = {"engineState": "0", "vehicleSpeed": "15"}
    await c3._departure_tick_cb(_now=tick_time)
    assert sent == []

    # 5. off mode -> skipped even at home & parked
    c3.data["realtime"] = {"engineState": "0", "vehicleSpeed": "0"}
    c3.departure_climate_mode = "off"
    await c3._departure_tick_cb(_now=tick_time)
    assert sent == []

    # 6. at_home + at home + parked -> sends!
    c3.departure_climate_mode = "at_home"
    await c3._departure_tick_cb(_now=tick_time)
    assert len(sent) == 1

    # 7. at_home when zone.home does NOT exist -> no restriction even with pos=None
    hass.states.async_remove("zone.home")
    c4 = _make_coord(hass, entry_id="c_nozone")
    c4.departure_weekly[1] = (True, 7 * 60)
    c4.departure_climate_mode = "at_home"
    c4.position = None
    monkeypatch.setattr(c4, "async_send_command", fake_send)
    await c4._departure_tick_cb(_now=tick_time)
    assert len(sent) == 2


async def test_preclimate_quick_resets_immediately_on_success(hass, monkeypatch):
    tz = timezone.utc
    coord = _make_coord(hass)
    coord.departure_climate_mode = "anywhere"
    sent: list[str] = []

    async def ok_send(key: str, params: dict | None = None) -> str:
        sent.append(key)
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", ok_send)
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 17, 45, tzinfo=tz))
    await coord.async_set_quick_departure(18 * 60, enabled=True)

    hits: list[int] = []
    unsub = coord.async_add_listener(lambda: hits.append(1))
    try:
        await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 17, 50, tzinfo=tz))
        assert sent == ["clima_on"]
        assert coord._fired_climate_key is not None
        assert coord.quick_departure_enabled is False
        assert coord._quick_target_at is None
        assert len(hits) >= 1
    finally:
        unsub()


async def test_preclimate_failure_anti_storm_and_quick_reset_and_anti_rollover(hass, monkeypatch):
    tz = timezone.utc
    coord = _make_coord(hass)
    coord.departure_climate_mode = "anywhere"
    calls = 0

    async def failing_send(key: str, params: dict | None = None) -> str:
        nonlocal calls
        calls += 1
        raise HomeAssistantError("network fail")

    monkeypatch.setattr(coord, "async_send_command", failing_send)

    # Activate quick departure for 18:00 when now is 17:50
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 17, 50, tzinfo=tz))
    await coord.async_set_quick_departure(18 * 60, enabled=True)
    assert coord.quick_departure_enabled is True
    assert coord._quick_target_at == datetime(2026, 11, 16, 18, 0, tzinfo=tz)

    # Tick inside window -> attempts once, fails, sets _attempted_climate_key, resets quick immediately
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 17, 50, tzinfo=tz))
    assert calls == 1
    assert coord._attempted_climate_key is not None
    assert coord._fired_climate_key is None
    assert coord.quick_departure_enabled is False
    assert coord._quick_target_at is None

    # No retry storm if quick is re-enabled at same target or weekly has same key
    coord.departure_weekly[1] = (True, 18 * 60)
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 17, 51, tzinfo=tz))
    assert calls == 2  # different source key (weekly vs quick)
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 17, 52, tzinfo=tz))
    assert calls == 2  # no retry storm on same weekly key

    # Anti-rollover: climate_mode == "off" and now >= _quick_target_at resets quick_departure_enabled
    coord.departure_climate_mode = "off"
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 17, 40, tzinfo=tz))
    await coord.async_set_quick_departure(18 * 60, enabled=True)
    assert coord.quick_departure_enabled is True
    assert coord._quick_target_at == datetime(2026, 11, 16, 18, 0, tzinfo=tz)

    listener_hits = []
    unsub = coord.async_add_listener(lambda: listener_hits.append(1))
    try:
        await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 18, 1, tzinfo=tz))
        assert coord.quick_departure_enabled is False
        assert coord._quick_target_at is None
        assert len(listener_hits) >= 1
    finally:
        unsub()


def _set_home(hass, coord: LepasCoordinator, *, plugged: bool = False) -> None:
    hass.states.async_set("zone.home", "zoning", {"latitude": 45.0, "longitude": 9.0, "radius": 100})
    coord.position = {"lat": 45.0, "lon": 9.0}
    if plugged:
        coord.data = dict(coord.data or {})
        rt = dict(coord.data.get("realtime") or {})
        rt["chargeGunState"] = "1"
        coord.data["realtime"] = rt


async def test_charge_sync_quick_immediate_and_notify_schedule_changed(hass, monkeypatch):
    tz = timezone.utc
    hass.config.time_zone = "UTC"
    coord = _make_coord(hass)
    _set_home(hass, coord)
    coord.charge_duration_hours = 6
    sent: list[tuple[str, dict | None]] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", fake_send)
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 10, 0, tzinfo=tz))

    listener_hits = []
    unsub = coord.async_add_listener(lambda: listener_hits.append(coord.charge_start_minutes))
    try:
        # async_set_quick_departure with sync_charging=True sends immediately
        await coord.async_set_quick_departure(18 * 60, enabled=True, sync_charging=True)
        assert coord.charge_start_minutes == 12 * 60
        assert listener_hits[-1] == 12 * 60
        assert len(sent) == 1
        assert sent[0][0] == "ricarica_prog_on"
        assert sent[0][1]["chargeAppointPlans"][0]["startTime"] == 12 * 60
        assert sent[0][1]["chargeAppointPlans"][0]["timeConsuming"] == 360

        # Calling notify_schedule_changed(sync_charge=True) with same state is deduplicated
        coord.notify_schedule_changed(sync_charge=True)
        await hass.async_block_till_done(wait_background_tasks=True)
        assert len(sent) == 1

        # Changing quick time triggers immediate background sync
        coord.quick_departure_minutes = 19 * 60
        coord.notify_schedule_changed(sync_charge=True)
        await hass.async_block_till_done(wait_background_tasks=True)
        assert coord.charge_start_minutes == 13 * 60
        assert len(sent) == 2
        assert sent[1][1]["chargeAppointPlans"][0]["startTime"] == 13 * 60
    finally:
        unsub()


async def test_charge_sync_weekly_window_dedup_failure_and_2131_fallback(hass, monkeypatch):
    tz = timezone.utc
    hass.config.time_zone = "UTC"
    coord = _make_coord(
        hass,
        data={DATA_VEHICLE_FEATURES: {"scheduled_charging": True, "scheduled_charging_custom_days": True}},
        entry_id="w_custom",
    )
    _set_home(hass, coord, plugged=True)
    coord.departure_weekly[2] = (True, 7 * 60)  # Tuesday 07:00
    coord.charge_duration_hours = 6             # T_charge_start = Tuesday 01:00 (min=60)
    coord.sync_charge_to_departure = True
    coord.departure_climate_mode = "off"

    sent: list[tuple[str, dict | None]] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", fake_send)

    # Monday 23:59 -> T_charge_start - 61 min -> updates charge_start_minutes locally, does NOT send
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 23, 59, tzinfo=tz))
    assert coord.charge_start_minutes == 60
    assert sent == []

    # Tuesday 00:00 -> T_charge_start - 60 min -> sends once with custom cycleData=[2]
    await coord._departure_tick_cb(_now=datetime(2026, 11, 17, 0, 0, tzinfo=tz))
    assert len(sent) == 1
    assert sent[0][1]["chargeAppointPlans"][0]["cycleData"] == [2]
    assert sent[0][1]["chargeAppointPlans"][0]["startTime"] == 60

    # Tuesday 00:05 -> deduplicated
    await coord._departure_tick_cb(_now=datetime(2026, 11, 17, 0, 5, tzinfo=tz))
    assert len(sent) == 1

    # Tuesday 06:30 -> still < T_dep (07:00), deduplicated; if fresh sig, syncs immediately
    coord._last_synced_charge_sig = None
    await coord._departure_tick_cb(_now=datetime(2026, 11, 17, 6, 30, tzinfo=tz))
    assert len(sent) == 2

    # Tuesday 07:00 -> T_dep passed, rolls to next Tuesday (>24h -> Phase 2 sends ricarica_prog_off)
    coord._last_synced_charge_sig = None
    await coord._departure_tick_cb(_now=datetime(2026, 11, 17, 7, 0, tzinfo=tz))
    assert len(sent) == 3
    assert sent[2][0] == "ricarica_prog_off"
    assert sent[2][1]["mainSwitch"] == 0

    # Failure anti-storm + 2131=0 fallback to [1..7]
    coord2 = _make_coord(
        hass,
        data={DATA_VEHICLE_FEATURES: {"scheduled_charging": True, "scheduled_charging_custom_days": False}},
        entry_id="w_2131",
    )
    _set_home(hass, coord2, plugged=True)
    coord2.departure_weekly[2] = (True, 7 * 60)
    coord2.charge_duration_hours = 6
    coord2.sync_charge_to_departure = True
    coord2.departure_climate_mode = "off"

    fail_calls: list[dict | None] = []

    async def failing_send(key: str, params: dict | None = None) -> str:
        fail_calls.append(params)
        raise HomeAssistantError("cmd rejected")

    monkeypatch.setattr(coord2, "async_send_command", failing_send)
    await coord2._departure_tick_cb(_now=datetime(2026, 11, 17, 0, 10, tzinfo=tz))
    assert len(fail_calls) == 1
    assert fail_calls[0]["chargeAppointPlans"][0]["cycleData"] == [1, 2, 3, 4, 5, 6, 7]
    assert coord2._last_attempted_charge_sig is not None

    # Next tick does not retry storm
    await coord2._departure_tick_cb(_now=datetime(2026, 11, 17, 0, 11, tzinfo=tz))
    assert len(fail_calls) == 1

    # Manual override ignores _last_attempted_charge_sig and _last_synced_charge_sig
    ok_calls: list[dict | None] = []

    async def ok_send(key: str, params: dict | None = None) -> str:
        ok_calls.append(params)
        return "ok"

    monkeypatch.setattr(coord2, "async_send_command", ok_send)
    await coord2.async_apply_charging_schedule(start_minutes=60, duration_hours=6, days=[2])
    assert len(ok_calls) == 1
    assert ok_calls[0]["chargeAppointPlans"][0]["cycleData"] == [1, 2, 3, 4, 5, 6, 7]  # 2131=0 fallback
    assert coord2._last_synced_charge_sig is not None
    assert coord2._last_attempted_charge_sig is None

    # Calling manual override again still sends (ignores _last_synced_charge_sig)
    await coord2.async_apply_charging_schedule(start_minutes=60, duration_hours=6, days=[2])
    assert len(ok_calls) == 2


async def test_v4_backfill_probes_once_when_perms_empty_and_persists_v4(hass, cloud, monkeypatch):
    cloud.on(
        "/tsp/v1/app/vmc/queryList",
        data=[{"vin": FX.VIN, "nickname": "Lepas L8", "fullName": "LEPAS L8"}],
    )
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", data={"permissionList": []})

    coord = _make_coord(
        hass,
        data={
            "vehicle_name": "Lepas L8",
            DATA_CAPS_PROBED_V3: True,
        },
        entry_id="v4_empty",
    )
    await coord.async_ensure_vehicle_identity()
    assert coord.entry.data.get(DATA_CAPS_PROBED_V4) is True
    assert cloud.count("/tsp/v1/app/vmc/queryList") == 1

    # Subsequent call must NOT re-probe
    await coord.async_ensure_vehicle_identity()
    assert cloud.count("/tsp/v1/app/vmc/queryList") == 1


async def test_v4_backfill_populates_custom_days_feature_from_v3_entry(hass, cloud):
    cloud.on(
        "/tsp/v1/app/vmc/queryList",
        data=[{"vin": FX.VIN, "nickname": "Lepas L8", "fullName": "LEPAS L8"}],
    )
    cloud.on(
        "/tsp/v1/app/vmc/queryVehicleAuthority",
        data={
            "permissionList": [
                {"id": 213, "state": 1},
                {"id": 2131, "state": 0},
                {"id": 2132, "state": 1},
            ]
        },
    )

    coord = _make_coord(
        hass,
        data={"vehicle_name": "Lepas L8", DATA_CAPS_PROBED_V3: True},
        entry_id="v4_perms",
    )
    await coord.async_ensure_vehicle_identity()
    assert coord.entry.data.get(DATA_CAPS_PROBED_V4) is True
    assert coord.feature_enabled("scheduled_charging") is True
    assert coord.feature_enabled("scheduled_charging_custom_days") is False
    assert coord.effective_charge_days([1, 3, 5]) == [1, 2, 3, 4, 5, 6, 7]


async def test_teardown_closing_guards_and_busy_released_in_finally(hass, monkeypatch):
    coord = _make_coord(hass)
    coord.async_start_departure_scheduler()
    assert coord._timers.is_armed(DEPARTURE_TICK)

    # Simulate closing mid-await inside _departure_tick_cb
    coord.departure_weekly[1] = (True, 7 * 60)
    coord.departure_climate_mode = "anywhere"
    tz = timezone.utc

    async def closing_send(key: str, params: dict | None = None) -> str:
        coord._timers.close()
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", closing_send)
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 50, tzinfo=tz))
    assert coord._timers.closing is True
    assert coord._departure_busy is False
    assert coord._fired_climate_key is None  # aborted after await when closing

    # Entry check when already closing
    calls = 0

    async def count_send(key: str, params: dict | None = None) -> str:
        nonlocal calls
        calls += 1
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", count_send)
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 51, tzinfo=tz))
    assert calls == 0

    # Closing mid-await during charge sync aborts updating _last_synced_charge_sig and releases busy
    coord_sync = _make_coord(hass, entry_id="close_sync")
    coord_sync.departure_climate_mode = "off"
    coord_sync.sync_charge_to_departure = True
    coord_sync.departure_weekly[1] = (True, 7 * 60)

    async def closing_charge_send(key: str, params: dict | None = None) -> str:
        coord_sync._timers.close()
        return "ok"

    monkeypatch.setattr(coord_sync, "async_send_command", closing_charge_send)
    await coord_sync._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 50, tzinfo=tz))
    assert coord_sync._departure_busy is False
    assert coord_sync._last_synced_charge_sig is None

    # Exception inside tick still releases _departure_busy via finally
    coord_err = _make_coord(hass, entry_id="err_busy")
    monkeypatch.setattr(coord_err, "next_departure_occurrence", lambda _now: (_ for _ in ()).throw(RuntimeError("boom")))
    with pytest.raises(RuntimeError, match="boom"):
        await coord_err._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 50, tzinfo=tz))
    assert coord_err._departure_busy is False

    # async_stop cancels timers and closes TimerRegistry
    coord2 = _make_coord(hass, entry_id="stop_entry")
    coord2.async_start_departure_scheduler()
    assert coord2._timers.is_armed(DEPARTURE_TICK)
    coord2.async_stop()
    assert coord2._timers.closing is True
    assert not coord2._timers.is_armed(DEPARTURE_TICK)


def test_duration_params_for_command():
    assert duration_params_for_command("sedile_guida_caldo", 10) == {"times": "10"}
    assert duration_params_for_command("defrost_parabrezza", 5) == {"times": "5"}
    assert duration_params_for_command("clima_riscalda_on", 10) == {"duration": "10"}
    assert duration_params_for_command("clima_raffredda_on", 5) == {"duration": "5"}
    assert duration_params_for_command("volante_caldo", 10) is None
    assert duration_params_for_command("unknown_cmd", 10) is None


def test_entity_feature_map_departure_preclimate_duration(hass):
    assert ENTITY_FEATURE_MAP[("number", "partenza_preclima_durata")] == "climate"
    coord_on = _make_coord(
        hass, data={DATA_VEHICLE_FEATURES: {"climate": True}}, entry_id="dep_dur_on"
    )
    coord_off = _make_coord(
        hass, data={DATA_VEHICLE_FEATURES: {"climate": False}}, entry_id="dep_dur_off"
    )
    assert entity_allowed(coord_on, "number", "partenza_preclima_durata") is True
    assert entity_allowed(coord_off, "number", "partenza_preclima_durata") is False


async def test_departure_preclimate_duration_decoupled_from_clima_duration(hass, monkeypatch):
    tz = timezone.utc
    coord = _make_coord(hass, entry_id="decoupled_dur")
    coord.departure_weekly[1] = (True, 7 * 60)
    coord.departure_climate_mode = "anywhere"
    coord.departure_preclimate_duration = 10
    coord.clima_duration = 5
    coord.departure_climate_extras = ["driver_seat_heating", "steering_wheel_heating"]

    occ = coord.next_departure_occurrence(datetime(2026, 11, 16, 6, 30, tzinfo=tz))
    assert occ is not None
    assert occ.climate_start_at == datetime(2026, 11, 16, 6, 50, tzinfo=tz)

    sent: list[tuple[str, dict | None]] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    monkeypatch.setattr(coord, "async_send_command", fake_send)
    # 06:54 was inside 15-min window only for old coupling, already inside 10-min window at 06:50;
    # verify 06:48 (inside 15m, outside 10m) does NOT trigger when departure_preclimate_duration=10.
    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 48, tzinfo=tz))
    assert sent == []

    await coord._departure_tick_cb(_now=datetime(2026, 11, 16, 6, 50, tzinfo=tz))
    assert sent == [
        ("clima_on", {"temperature": "21.0", "times": "10"}),
        ("sedile_guida_caldo", {"times": "10"}),
        ("volante_caldo", None),
    ]
