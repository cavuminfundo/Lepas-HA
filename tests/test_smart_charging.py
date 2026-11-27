"""Pure unit tests for smart charging estimation and schedule resolution."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from custom_components.lepas.scheduler import (
    CHARGE_DURATION_STEP_MINUTES,
    CHARGE_WINDOW_MODES,
    DEFAULT_HOME_CHARGE_POWER_KW,
    SMART_24H_WINDOW_MAX_MINUTES,
    SMART_AC_CV_MARGIN_MIN,
    SMART_AC_EFFICIENCY,
    SMART_DC_CV_MARGIN_MIN,
    SMART_DC_EFFICIENCY,
    SMART_MIN_DURATION_MIN,
    DesiredChargePlan,
    SmartChargeEstimate,
    estimate_smart_charge_plan,
    local_schedule_to_utc,
    resolve_desired_charge_schedule,
    select_charge_departure_occurrence,
)


def test_smart_charging_constants_match_contract():
    assert CHARGE_DURATION_STEP_MINUTES == 15
    assert CHARGE_WINDOW_MODES == ("off", "fixed", "smart_departure")
    assert SMART_AC_EFFICIENCY == 0.90
    assert SMART_AC_CV_MARGIN_MIN == 25
    assert SMART_DC_EFFICIENCY == 0.92
    assert SMART_DC_CV_MARGIN_MIN == 30
    assert SMART_MIN_DURATION_MIN == 30
    assert DEFAULT_HOME_CHARGE_POWER_KW == 2.3
    assert SMART_24H_WINDOW_MAX_MINUTES == 23 * 60 + 45


def test_estimate_ac_and_dc_durations():
    ac_80 = estimate_smart_charge_plan(
        soc_pct=80.0,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=2.3,
        charge_kind="ac",
        max_duration_hours=10,
    )
    assert isinstance(ac_80, SmartChargeEstimate)
    assert ac_80.missing_kwh == pytest.approx(3.68)
    assert ac_80.raw_minutes == pytest.approx(131.6667, abs=0.01)
    assert ac_80.duration_minutes == 135
    assert ac_80.fallback_used is False
    assert ac_80.soc_used == 80.0
    assert ac_80.charge_kind == "ac"

    ac_50 = estimate_smart_charge_plan(
        soc_pct=50.0,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=2.3,
        charge_kind="ac",
        max_duration_hours=10,
    )
    assert ac_50.duration_minutes == 300

    ac_10_uncapped = estimate_smart_charge_plan(
        soc_pct=10.0,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=2.3,
        charge_kind="ac",
        max_duration_hours=10,
    )
    assert ac_10_uncapped.raw_minutes == pytest.approx(505.0, abs=0.01)
    assert ac_10_uncapped.duration_minutes == 510

    ac_10_capped = estimate_smart_charge_plan(
        soc_pct=10.0,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=2.3,
        charge_kind="ac",
        max_duration_hours=6,
    )
    assert ac_10_capped.duration_minutes == 360

    ac_99 = estimate_smart_charge_plan(
        soc_pct=99.0,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=2.3,
        charge_kind="ac",
        max_duration_hours=6,
    )
    assert ac_99.duration_minutes == 30
    assert ac_99.fallback_used is False
    assert ac_99.soc_used == 99.0

    ac_99_hour_step = estimate_smart_charge_plan(
        soc_pct=99.0,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=2.3,
        charge_kind="ac",
        max_duration_hours=6,
        step_minutes=60,
    )
    assert ac_99_hour_step.duration_minutes == 60
    assert ac_99_hour_step.fallback_used is False

    ac_min_clamp = estimate_smart_charge_plan(
        soc_pct=98.5,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=40.0,
        charge_kind="ac",
        max_duration_hours=6,
    )
    assert ac_min_clamp.duration_minutes == 30

    dc_80 = estimate_smart_charge_plan(
        soc_pct=80.0,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=24.0,
        charge_kind="dc",
        max_duration_hours=6,
    )
    assert dc_80.raw_minutes == pytest.approx(40.0, abs=0.01)
    assert dc_80.duration_minutes == 45
    assert dc_80.charge_kind == "dc"

    dc_50 = estimate_smart_charge_plan(
        soc_pct=50.0,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=24.0,
        charge_kind="dc",
        max_duration_hours=6,
    )
    assert dc_50.raw_minutes == pytest.approx(55.0, abs=0.01)
    assert dc_50.duration_minutes == 60

    dc_10 = estimate_smart_charge_plan(
        soc_pct=10.0,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=24.0,
        charge_kind="dc",
        max_duration_hours=6,
    )
    assert dc_10.raw_minutes == pytest.approx(75.0, abs=0.01)
    assert dc_10.duration_minutes == 75

    dc_99 = estimate_smart_charge_plan(
        soc_pct=99.5,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=24.0,
        charge_kind="dc",
        max_duration_hours=6,
    )
    assert dc_99.duration_minutes == 30
    assert dc_99.fallback_used is False

    ac_zero_soc = estimate_smart_charge_plan(
        soc_pct=0.0,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=2.3,
        charge_kind="ac",
        max_duration_hours=12,
    )
    assert ac_zero_soc.fallback_used is False
    assert ac_zero_soc.soc_used == 0.0
    assert ac_zero_soc.missing_kwh == pytest.approx(18.4)
    assert ac_zero_soc.duration_minutes == 570


def test_estimate_fallback_on_missing_or_degraded_soc():
    for bad_soc in (None, -5.0, 101.0, True, float("nan"), float("inf")):
        est = estimate_smart_charge_plan(
            soc_pct=bad_soc,  # type: ignore[arg-type]
            degraded_battery=False,
            capacity_kwh=18.4,
            power_kw=2.3,
            charge_kind="ac",
            max_duration_hours=6,
        )
        assert est.fallback_used is True
        assert est.soc_used is None
        assert est.duration_minutes == 360

    degraded = estimate_smart_charge_plan(
        soc_pct=50.0,
        degraded_battery=True,
        capacity_kwh=18.4,
        power_kw=2.3,
        charge_kind="ac",
        max_duration_hours=6,
    )
    assert degraded.fallback_used is True
    assert degraded.soc_used is None
    assert degraded.duration_minutes == 360

    clamped_high = estimate_smart_charge_plan(
        soc_pct=None,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=2.3,
        charge_kind="ac",
        max_duration_hours=15,
    )
    assert clamped_high.duration_minutes == 720

    clamped_low = estimate_smart_charge_plan(
        soc_pct=None,
        degraded_battery=False,
        capacity_kwh=18.4,
        power_kw=2.3,
        charge_kind="ac",
        max_duration_hours=0,
    )
    assert clamped_low.duration_minutes == 30


def test_select_charge_departure_quick_override_even_if_later():
    tz = ZoneInfo("Europe/Rome")
    now = datetime(2026, 11, 26, 20, 0, tzinfo=tz)  # Thursday
    weekly = {5: (True, 8 * 60)}  # Friday 08:00

    occ, override_active = select_charge_departure_occurrence(
        now, weekly, quick_enabled=True, quick_minutes=10 * 60, clima_duration_min=15
    )
    assert override_active is True
    assert occ is not None
    assert occ.source == "quick"
    assert occ.departure_at == datetime(2026, 11, 27, 10, 0, tzinfo=tz)

    occ_w, override_w = select_charge_departure_occurrence(
        now, weekly, quick_enabled=False, quick_minutes=10 * 60, clima_duration_min=15
    )
    assert override_w is False
    assert occ_w is not None
    assert occ_w.source == "weekly"
    assert occ_w.departure_at == datetime(2026, 11, 27, 8, 0, tzinfo=tz)

    occ_none, override_none = select_charge_departure_occurrence(
        now, None, quick_enabled=False, quick_minutes=10 * 60, clima_duration_min=15
    )
    assert occ_none is None
    assert override_none is False


def _resolve_base(**overrides) -> DesiredChargePlan:
    tz = ZoneInfo("Europe/Rome")
    params = {
        "now": datetime(2026, 11, 26, 20, 0, tzinfo=tz),
        "mode": "smart_departure",
        "at_home": True,
        "is_plugged": True,
        "charge_state": 0,
        "charge_start_minutes": 23 * 60 + 5,
        "charge_duration_hours": 6,
        "charge_days": [1, 3, 5],
        "weekly": {5: (True, 8 * 60)},
        "quick_enabled": False,
        "quick_minutes": 10 * 60,
        "clima_duration_min": 15,
        "soc_pct": 80.0,
        "degraded_battery": False,
        "capacity_kwh": 18.4,
        "power_kw": 2.3,
        "power_source": "learned_ac",
        "charge_kind": "ac",
    }
    params.update(overrides)
    return resolve_desired_charge_schedule(**params)


def test_resolve_desired_charge_schedule_all_branches():
    p_off = _resolve_base(mode="off", at_home=False, quick_enabled=True)
    assert p_off.action == "noop"
    assert p_off.reason == "mode_off"

    p_unknown = _resolve_base(at_home=None)
    assert p_unknown.action == "noop"
    assert p_unknown.reason == "unknown_location"

    p_away = _resolve_base(at_home=False)
    assert p_away.action == "disable"
    assert p_away.reason == "away_bypass"
    assert p_away.away_bypass_active is True

    p_fixed = _resolve_base(mode="fixed")
    assert p_fixed.action == "enable"
    assert p_fixed.reason == "fixed_home"
    assert p_fixed.start_minutes == 23 * 60
    assert p_fixed.duration_minutes == 360
    assert p_fixed.days == (1, 3, 5)
    assert p_fixed.target_key == "fixed"
    assert p_fixed.quick_override_active is False

    p_fixed_quick = _resolve_base(mode="fixed", quick_enabled=True)
    assert p_fixed_quick.action == "enable"
    assert p_fixed_quick.reason == "quick_override"
    assert p_fixed_quick.quick_override_active is True
    # 10:00 - 135m = 07:45 (465m)
    assert p_fixed_quick.start_minutes == 7 * 60 + 45
    assert p_fixed_quick.duration_minutes == 135
    assert p_fixed_quick.target_key.startswith("quick:")

    p_smart_quick = _resolve_base(mode="smart_departure", quick_enabled=True)
    assert p_smart_quick.action == "enable"
    assert p_smart_quick.reason == "quick_override"
    assert p_smart_quick.quick_override_active is True
    assert p_smart_quick.start_minutes == 7 * 60 + 45

    p_smart_weekly = _resolve_base(mode="smart_departure", quick_enabled=False)
    assert p_smart_weekly.action == "enable"
    assert p_smart_weekly.reason == "smart_home"
    assert p_smart_weekly.quick_override_active is False
    # 08:00 - 135m = 05:45 (345m)
    assert p_smart_weekly.start_minutes == 5 * 60 + 45
    assert p_smart_weekly.duration_minutes == 135
    assert p_smart_weekly.days == (5,)
    assert p_smart_weekly.ref_date == date(2026, 11, 27)
    assert p_smart_weekly.target_key.startswith("weekly:")
    assert p_smart_weekly.power_source == "learned_ac"
    assert p_smart_weekly.effective_power_kw == 2.3

    p_no_dep = _resolve_base(weekly=None, quick_enabled=False)
    assert p_no_dep.action == "disable"
    assert p_no_dep.reason == "no_departure_24h"

    tz = ZoneInfo("Europe/Rome")
    # Thursday 20:00 -> Monday 08:00 (smart_start Monday 05:45 -> > 23h45m away)
    p_far = _resolve_base(
        now=datetime(2026, 11, 26, 20, 0, tzinfo=tz),
        weekly={1: (True, 8 * 60)},
    )
    assert p_far.action == "disable"
    assert p_far.reason == "no_departure_24h"

    # Boundary: smart_start at 2026-11-27 19:45, now at 2026-11-26 20:00 -> exactly 23h45m -> allowed!
    p_boundary_ok = _resolve_base(
        now=datetime(2026, 11, 26, 20, 0, tzinfo=tz),
        weekly={5: (True, 22 * 60)},  # 22:00 - 135m = 19:45 (delta == 23h45m)
    )
    assert p_boundary_ok.action == "enable"
    assert p_boundary_ok.reason == "smart_home"

    # 1 minute past 23h45m -> disable
    p_boundary_over = _resolve_base(
        now=datetime(2026, 11, 26, 19, 59, tzinfo=tz),
        weekly={5: (True, 22 * 60)},
    )
    assert p_boundary_over.action == "disable"
    assert p_boundary_over.reason == "no_departure_24h"

    # Late plug-in: smart_start 05:45, departure 08:00, plugged at 06:30
    p_late = _resolve_base(now=datetime(2026, 11, 27, 6, 30, tzinfo=tz))
    assert p_late.action == "disable"
    assert p_late.reason == "late_plug_in"

    # Already charged: charge_state == 2 or (soc >= 99 and is_plugged)
    p_done_cs = _resolve_base(charge_state=2, soc_pct=80.0)
    assert p_done_cs.action == "noop"
    assert p_done_cs.reason == "already_charged"

    p_done_soc = _resolve_base(charge_state=0, soc_pct=99.5, is_plugged=True)
    assert p_done_soc.action == "noop"
    assert p_done_soc.reason == "already_charged"

    # Degraded 99.5% must NOT suppress scheduling as already_charged
    p_degraded = _resolve_base(
        charge_state=0,
        soc_pct=99.5,
        degraded_battery=True,
        is_plugged=True,
    )
    assert p_degraded.action == "enable"
    assert p_degraded.fallback_used is True
    assert p_degraded.duration_minutes == 360


def test_smart_start_midnight_and_dst_alignment():
    tz = ZoneInfo("Europe/Rome")
    # Midnight wrap with 15-min floor alignment: departure Fri 00:20, dur=135m -> raw 22:05 -> floor 22:00 Thu
    p_midnight = _resolve_base(
        now=datetime(2026, 11, 26, 18, 0, tzinfo=tz),
        weekly={5: (True, 20)},
        soc_pct=80.0,
    )
    assert p_midnight.action == "enable"
    assert p_midnight.start_minutes == 22 * 60
    assert p_midnight.start_minutes % 15 == 0
    assert p_midnight.duration_minutes == 135
    assert p_midnight.ref_date == date(2026, 11, 26)
    assert p_midnight.days == (4,)

    # Spring-forward DST (2026-03-29 Europe/Rome skips 02:00->03:00):
    # Sun 07:00 CEST (05:00 UTC), soc=50% -> 300m (5h) -> 00:00 UTC = Sun 01:00 CET
    p_spring = _resolve_base(
        now=datetime(2026, 3, 28, 21, 0, tzinfo=tz),
        weekly={7: (True, 7 * 60)},
        soc_pct=50.0,
    )
    assert p_spring.action == "enable"
    assert p_spring.start_minutes == 60
    assert p_spring.start_minutes % 15 == 0
    assert p_spring.ref_date == date(2026, 3, 29)
    assert p_spring.days == (7,)
    utc_min, utc_days = local_schedule_to_utc(
        p_spring.start_minutes, p_spring.days, tz, ref_date=p_spring.ref_date
    )
    assert utc_min == 0
    assert utc_days == [7]

    # Fall-back DST (2026-10-25 Europe/Rome repeats 02:00->03:00):
    # Sun 08:00 CET (07:00 UTC), soc=50% -> 300m (5h) -> 02:00 UTC = Sun 03:00 CET (non-ambiguous)
    p_fall = _resolve_base(
        now=datetime(2026, 10, 24, 21, 0, tzinfo=tz),
        weekly={7: (True, 8 * 60)},
        soc_pct=50.0,
    )
    assert p_fall.action == "enable"
    assert p_fall.start_minutes == 3 * 60
    assert p_fall.start_minutes % 15 == 0
    assert p_fall.ref_date == date(2026, 10, 25)
    assert p_fall.days == (7,)
    utc_fall_min, utc_fall_days = local_schedule_to_utc(
        p_fall.start_minutes, p_fall.days, tz, ref_date=p_fall.ref_date
    )
    assert utc_fall_min == 120
    assert utc_fall_days == [7]
