"""Pure scheduling calculations for departure pre-climate and smart charging."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from .const import DEFAULT_BATTERY_CAPACITY_KWH
from .consumption import _safe_float

CHARGE_START_STEP_MINUTES = 15
CHARGE_DURATION_STEP_MINUTES = 15
CHARGE_WINDOW_MODES = ("off", "fixed", "smart_departure")
SMART_AC_EFFICIENCY = 0.90
SMART_AC_CV_MARGIN_MIN = 25
SMART_DC_EFFICIENCY = 0.92
SMART_DC_CV_MARGIN_MIN = 30
SMART_MIN_DURATION_MIN = 30
DEFAULT_HOME_CHARGE_POWER_KW = 2.3
SMART_24H_WINDOW_MAX_MINUTES = 23 * 60 + 45

CHARGE_DAYS_PRESETS: dict[str, list[int]] = {
    "all_days": [1, 2, 3, 4, 5, 6, 7],
    "weekdays": [1, 2, 3, 4, 5],
    "weekend": [6, 7],
    "mon_wed_fri": [1, 3, 5],
    "tue_thu_sat": [2, 4, 6],
}

DEPARTURE_DAY_SLUGS: dict[int, str] = {
    1: "mon",
    2: "tue",
    3: "wed",
    4: "thu",
    5: "fri",
    6: "sat",
    7: "sun",
}

_SLUG_TO_DAY: dict[str, int] = {slug: day for day, slug in DEPARTURE_DAY_SLUGS.items()}
_VALID_DAY_STRINGS: frozenset[str] = frozenset(str(d) for d in range(1, 8))

DEPARTURE_CLIMATE_EXTRAS_COMMANDS: dict[str, str] = {
    "driver_seat_heating": "sedile_guida_caldo",
    "driver_seat_ventilation": "sedile_guida_aria",
    "passenger_seat_heating": "sedile_passeggero_caldo",
    "passenger_seat_ventilation": "sedile_passeggero_aria",
    "rear_left_seat_heating": "sedile_post_sx_caldo",
    "rear_left_seat_ventilation": "sedile_post_sx_aria",
    "rear_right_seat_heating": "sedile_post_dx_caldo",
    "rear_right_seat_ventilation": "sedile_post_dx_aria",
    "rear_window_heating": "defrost_lunotto",
    "windshield_defrost": "defrost_parabrezza",
    "windshield_defog": "disappanna_parabrezza",
    "steering_wheel_heating": "volante_caldo",
}

DEPARTURE_CLIMATE_EXTRAS_FEATURES: dict[str, str] = {
    "driver_seat_heating": "driver_seat_heating",
    "driver_seat_ventilation": "driver_seat_ventilation",
    "passenger_seat_heating": "passenger_seat_heating",
    "passenger_seat_ventilation": "passenger_seat_ventilation",
    "rear_left_seat_heating": "rear_left_seat_heating",
    "rear_left_seat_ventilation": "rear_left_seat_ventilation",
    "rear_right_seat_heating": "rear_right_seat_heating",
    "rear_right_seat_ventilation": "rear_right_seat_ventilation",
    "rear_window_heating": "rear_window_heating",
    "windshield_defrost": "front_windshield_electric",
    "windshield_defog": "front_windshield_defog",
    "steering_wheel_heating": "steering_wheel_heating",
}

DEPARTURE_CLIMATE_EXTRAS_MUTUAL_EXCLUSIONS: dict[str, str] = {
    "driver_seat_heating": "driver_seat_ventilation",
    "driver_seat_ventilation": "driver_seat_heating",
    "passenger_seat_heating": "passenger_seat_ventilation",
    "passenger_seat_ventilation": "passenger_seat_heating",
    "rear_left_seat_heating": "rear_left_seat_ventilation",
    "rear_left_seat_ventilation": "rear_left_seat_heating",
    "rear_right_seat_heating": "rear_right_seat_ventilation",
    "rear_right_seat_ventilation": "rear_right_seat_heating",
}


@dataclass(frozen=True)
class DepartureOccurrence:
    """Next scheduled departure occurrence and its pre-climate start timestamp."""

    source: str
    weekday: int
    departure_at: datetime
    climate_start_at: datetime
    key: str

    @property
    def departure_at_minutes(self) -> int:
        """Departure time in local minutes since midnight."""
        return self.departure_at.hour * 60 + self.departure_at.minute


def shift_minutes(dt: datetime, delta_minutes: int) -> datetime:
    """Shift ``dt`` by ``delta_minutes`` in elapsed time, preserving its tzinfo."""
    if dt.tzinfo is not None:
        return (dt.astimezone(timezone.utc) + timedelta(minutes=delta_minutes)).astimezone(dt.tzinfo)
    return dt + timedelta(minutes=delta_minutes)


def _at_local_time(base_date: date, minutes: int, tzinfo) -> datetime:
    hh, mm = divmod(int(minutes) % 1440, 60)
    return datetime(base_date.year, base_date.month, base_date.day, hh, mm, 0, 0, tzinfo=tzinfo)


def next_quick_departure_at(now: datetime, quick_minutes: int) -> datetime:
    """Return the next local datetime for ``quick_minutes`` (today if ``> now``, else tomorrow)."""
    cand = _at_local_time(now.date(), quick_minutes, now.tzinfo)
    if cand <= now:
        cand = _at_local_time(now.date() + timedelta(days=1), quick_minutes, now.tzinfo)
    return cand


def _build_occurrence(
    source: str, departure_at: datetime, clima_duration_min: int
) -> DepartureOccurrence:
    dur = max(0, int(clima_duration_min))
    return DepartureOccurrence(
        source=source,
        weekday=departure_at.isoweekday(),
        departure_at=departure_at,
        climate_start_at=shift_minutes(departure_at, -dur),
        key=f"{source}:{departure_at.isoformat()}",
    )


def compute_next_occurrence(
    now: datetime,
    weekly: Mapping[int, tuple[bool, int]] | None,
    quick_enabled: bool,
    quick_minutes: int,
    clima_duration_min: int,
) -> DepartureOccurrence | None:
    """Select the earliest upcoming departure across quick and weekly schedules.

    Quick departure takes priority on exact timestamp ties.
    """
    quick_occ: DepartureOccurrence | None = None
    if quick_enabled and 0 <= int(quick_minutes) < 1440:
        quick_dt = next_quick_departure_at(now, int(quick_minutes))
        quick_occ = _build_occurrence("quick", quick_dt, clima_duration_min)

    weekly_occ: DepartureOccurrence | None = None
    if weekly:
        for offset in range(0, 8):
            target_date = now.date() + timedelta(days=offset)
            entry = weekly.get(target_date.isoweekday())
            if not entry:
                continue
            enabled, mins = entry
            if not enabled:
                continue
            mins_int = int(mins)
            if not 0 <= mins_int < 1440:
                continue
            cand = _at_local_time(target_date, mins_int, now.tzinfo)
            if cand > now:
                weekly_occ = _build_occurrence("weekly", cand, clima_duration_min)
                break

    if quick_occ is not None and weekly_occ is not None:
        return quick_occ if quick_occ.departure_at <= weekly_occ.departure_at else weekly_occ
    return quick_occ or weekly_occ


@dataclass(frozen=True)
class SmartChargeEstimate:
    """Estimated charging duration and intermediate energy metrics."""

    duration_minutes: int
    raw_minutes: float
    missing_kwh: float
    fallback_used: bool
    soc_used: float | None
    charge_kind: str


@dataclass(frozen=True)
class DesiredChargePlan:
    """Resolved target charge schedule or bypass/immediate directive."""

    action: str
    reason: str
    start_minutes: int | None
    duration_minutes: int | None
    days: tuple[int, ...] | None
    ref_date: date | None
    target_key: str
    estimated_duration_min: int | None
    soc_used: float | None
    charge_kind: str
    effective_power_kw: float
    power_source: str
    fallback_used: bool
    away_bypass_active: bool
    quick_override_active: bool


def select_charge_departure_occurrence(
    now: datetime,
    weekly: Mapping[int, tuple[bool, int]] | None,
    quick_enabled: bool,
    quick_minutes: int,
    clima_duration_min: int,
) -> tuple[DepartureOccurrence | None, bool]:
    """Return ``(occurrence, quick_override_active)`` with quick taking priority over weekly."""
    if quick_enabled and not isinstance(quick_minutes, bool):
        try:
            q_min = int(quick_minutes)
        except (TypeError, ValueError):
            q_min = -1
        if 0 <= q_min < 1440:
            quick_dt = next_quick_departure_at(now, q_min)
            return (_build_occurrence("quick", quick_dt, clima_duration_min), True)

    weekly_occ = compute_next_occurrence(
        now, weekly, False, quick_minutes, clima_duration_min
    )
    return (weekly_occ, False)


def estimate_smart_charge_plan(
    *,
    soc_pct: float | None,
    degraded_battery: bool,
    capacity_kwh: float,
    power_kw: float,
    charge_kind: str,
    max_duration_hours: int,
    step_minutes: int = CHARGE_DURATION_STEP_MINUTES,
) -> SmartChargeEstimate:
    """Estimate duration in minutes to reach 100% SoC, falling back safely on bad SoC."""
    kind = "dc" if charge_kind == "dc" else "ac"

    if isinstance(max_duration_hours, bool):
        max_hours = 6
    else:
        try:
            max_hours = int(max_duration_hours)
        except (TypeError, ValueError):
            max_hours = 6
    max_dur_min = max(SMART_MIN_DURATION_MIN, min(720, max_hours * 60))

    if isinstance(step_minutes, bool):
        step = CHARGE_DURATION_STEP_MINUTES
    else:
        try:
            step = int(step_minutes)
        except (TypeError, ValueError):
            step = CHARGE_DURATION_STEP_MINUTES
        if step <= 0:
            step = CHARGE_DURATION_STEP_MINUTES

    soc = None if degraded_battery else _safe_float(soc_pct)
    if soc is None or not (0.0 <= soc <= 100.0):
        return SmartChargeEstimate(
            duration_minutes=max_dur_min,
            raw_minutes=float(max_dur_min),
            missing_kwh=0.0,
            fallback_used=True,
            soc_used=None,
            charge_kind=kind,
        )

    cap_raw = _safe_float(capacity_kwh)
    cap = (
        cap_raw
        if (cap_raw is not None and cap_raw > 0.0)
        else DEFAULT_BATTERY_CAPACITY_KWH
    )
    pwr_raw = _safe_float(power_kw)
    pwr = (
        pwr_raw
        if (pwr_raw is not None and pwr_raw > 0.0)
        else DEFAULT_HOME_CHARGE_POWER_KW
    )
    missing_kwh = max(0.0, cap * ((100.0 - soc) / 100.0))

    if soc >= 99.0:
        rounded_min = math.ceil(round(SMART_MIN_DURATION_MIN / step, 9)) * step
        duration_minutes = max(SMART_MIN_DURATION_MIN, min(max_dur_min, rounded_min))
        return SmartChargeEstimate(
            duration_minutes=duration_minutes,
            raw_minutes=float(SMART_MIN_DURATION_MIN),
            missing_kwh=missing_kwh,
            fallback_used=False,
            soc_used=soc,
            charge_kind=kind,
        )

    eta = SMART_DC_EFFICIENCY if kind == "dc" else SMART_AC_EFFICIENCY
    cv_margin = SMART_DC_CV_MARGIN_MIN if kind == "dc" else SMART_AC_CV_MARGIN_MIN
    raw_min = (missing_kwh / (pwr * eta)) * 60.0 + cv_margin
    # Round ratio before ceil so IEEE-754 representation jitter never bumps exact steps.
    rounded_min = math.ceil(round(raw_min / step, 9)) * step
    duration_minutes = max(SMART_MIN_DURATION_MIN, min(max_dur_min, rounded_min))
    return SmartChargeEstimate(
        duration_minutes=duration_minutes,
        raw_minutes=raw_min,
        missing_kwh=missing_kwh,
        fallback_used=False,
        soc_used=soc,
        charge_kind=kind,
    )


def resolve_desired_charge_schedule(
    *,
    now: datetime,
    mode: str,
    at_home: bool | None,
    is_plugged: bool,
    charge_state: int | None,
    charge_start_minutes: int,
    charge_duration_hours: int,
    charge_days: Sequence[int],
    weekly: Mapping[int, tuple[bool, int]] | None,
    quick_enabled: bool,
    quick_minutes: int,
    clima_duration_min: int,
    soc_pct: float | None,
    degraded_battery: bool,
    capacity_kwh: float,
    power_kw: float,
    power_source: str,
    charge_kind: str,
    step_minutes: int = CHARGE_DURATION_STEP_MINUTES,
) -> DesiredChargePlan:
    """Resolve the desired charging schedule from mode, home presence, SoC, and departures."""
    kind = "dc" if charge_kind == "dc" else "ac"
    pwr_raw = _safe_float(power_kw)
    eff_power = (
        pwr_raw
        if (pwr_raw is not None and pwr_raw > 0.0)
        else DEFAULT_HOME_CHARGE_POWER_KW
    )
    pwr_src = (
        power_source
        if power_source in ("learned_ac", "learned_dc", "manual")
        else "manual"
    )
    soc_raw = None if degraded_battery else _safe_float(soc_pct)
    valid_soc = soc_raw if (soc_raw is not None and 0.0 <= soc_raw <= 100.0) else None

    def _plan(
        *,
        action: str,
        reason: str,
        target_key: str,
        start_minutes: int | None = None,
        duration_minutes: int | None = None,
        days: tuple[int, ...] | None = None,
        ref_date: date | None = None,
        estimated_duration_min: int | None = None,
        soc_used: float | None = valid_soc,
        fallback_used: bool = False,
        away_bypass_active: bool = False,
        quick_override_active: bool = False,
    ) -> DesiredChargePlan:
        return DesiredChargePlan(
            action=action,
            reason=reason,
            start_minutes=start_minutes,
            duration_minutes=duration_minutes,
            days=days,
            ref_date=ref_date,
            target_key=target_key,
            estimated_duration_min=estimated_duration_min,
            soc_used=soc_used,
            charge_kind=kind,
            effective_power_kw=eff_power,
            power_source=pwr_src,
            fallback_used=fallback_used,
            away_bypass_active=away_bypass_active,
            quick_override_active=quick_override_active,
        )

    if mode not in ("fixed", "smart_departure"):
        return _plan(action="noop", reason="mode_off", target_key="manual")

    if at_home is None:
        return _plan(action="noop", reason="unknown_location", target_key="manual")

    if at_home is False:
        return _plan(
            action="disable",
            reason="away_bypass",
            target_key="bypass",
            away_bypass_active=True,
        )

    use_smart = mode == "smart_departure"
    occ: DepartureOccurrence | None = None
    quick_override_active = False
    if use_smart or quick_enabled:
        occ, quick_override_active = select_charge_departure_occurrence(
            now, weekly, quick_enabled, quick_minutes, clima_duration_min
        )
        if mode == "fixed" and not quick_override_active:
            occ = None

    if use_smart or quick_override_active:
        if occ is None:
            return _plan(
                action="disable",
                reason="no_departure_24h",
                target_key="immediate",
                quick_override_active=quick_override_active,
            )

        cs_val = _safe_float(charge_state)
        if cs_val == 2.0 or (
            valid_soc is not None and valid_soc >= 99.0 and is_plugged
        ):
            return _plan(
                action="noop",
                reason="already_charged",
                target_key=occ.key,
                quick_override_active=quick_override_active,
            )

        est = estimate_smart_charge_plan(
            soc_pct=soc_pct,
            degraded_battery=degraded_battery,
            capacity_kwh=capacity_kwh,
            power_kw=eff_power,
            charge_kind=kind,
            max_duration_hours=charge_duration_hours,
            step_minutes=step_minutes,
        )
        raw_start = (
            occ.departure_at.hour * 60 + occ.departure_at.minute - est.duration_minutes
        ) % 1440
        floor_delta = raw_start - align_charge_start_minutes(
            raw_start, step=CHARGE_START_STEP_MINUTES
        )
        smart_start_at = shift_minutes(
            occ.departure_at, -(est.duration_minutes + floor_delta)
        )

        if now >= smart_start_at and now < occ.departure_at:
            return _plan(
                action="disable",
                reason="late_plug_in",
                target_key="immediate",
                estimated_duration_min=est.duration_minutes,
                soc_used=est.soc_used,
                fallback_used=est.fallback_used,
                quick_override_active=quick_override_active,
            )

        if (smart_start_at - now) > timedelta(minutes=SMART_24H_WINDOW_MAX_MINUTES):
            return _plan(
                action="disable",
                reason="no_departure_24h",
                target_key="immediate",
                estimated_duration_min=est.duration_minutes,
                soc_used=est.soc_used,
                fallback_used=est.fallback_used,
                quick_override_active=quick_override_active,
            )

        return _plan(
            action="enable",
            reason="quick_override" if quick_override_active else "smart_home",
            start_minutes=smart_start_at.hour * 60 + smart_start_at.minute,
            duration_minutes=est.duration_minutes,
            days=(smart_start_at.isoweekday(),),
            ref_date=smart_start_at.date(),
            target_key=f"{occ.source}:{occ.departure_at.isoformat()}",
            estimated_duration_min=est.duration_minutes,
            soc_used=est.soc_used,
            fallback_used=est.fallback_used,
            quick_override_active=quick_override_active,
        )

    return _plan(
        action="enable",
        reason="fixed_home",
        start_minutes=align_charge_start_minutes(charge_start_minutes),
        duration_minutes=int(charge_duration_hours) * 60,
        days=tuple(int(d) for d in charge_days),
        ref_date=now.date(),
        target_key="fixed",
    )


def compute_charge_window(
    start_minutes: int,
    duration_hours: int | float,
    days: Sequence[int] | None = None,
) -> tuple[str, str, bool]:
    """Compute ``(start_hhmm, end_hhmm, next_day)`` for a scheduled charging window."""
    _ = days
    start = int(start_minutes) % 1440
    dur_min = max(0, int(round(float(duration_hours) * 60)))
    end_total = start + dur_min
    next_day = end_total >= 1440
    end = end_total % 1440
    return (f"{start // 60:02d}:{start % 60:02d}", f"{end // 60:02d}:{end % 60:02d}", next_day)


def align_charge_start_minutes(
    minutes: int, *, step: int = CHARGE_START_STEP_MINUTES
) -> int:
    """Floor ``minutes`` within ``0..1439`` down to the nearest ``step``-minute boundary."""
    if isinstance(minutes, bool):
        raise ValueError(f"Boolean is not a valid minute count: {minutes!r}")
    if isinstance(step, bool) or int(step) <= 0:
        raise ValueError(f"step must be a positive integer: {step!r}")
    step_int = int(step)
    return ((int(minutes) % 1440) // step_int) * step_int


def resolve_tzinfo(hass=None):
    """Resolve local tzinfo from Home Assistant config, or deterministic UTC when absent."""
    if hass is None:
        return timezone.utc
    tz_name = getattr(getattr(hass, "config", None), "time_zone", None)
    try:
        from homeassistant.util import dt as dt_util

        if tz_name:
            return dt_util.get_time_zone(tz_name) or dt_util.DEFAULT_TIME_ZONE or timezone.utc
        return dt_util.DEFAULT_TIME_ZONE or timezone.utc
    except ImportError:
        if tz_name:
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

            try:
                return ZoneInfo(str(tz_name))
            except (ZoneInfoNotFoundError, ValueError):
                return timezone.utc
        return timezone.utc


def compute_charge_start_for_departure(
    departure_minutes: int, duration_hours: int | float
) -> int:
    """Compute aligned charge start time in local minutes from midnight, wrapping across midnight."""
    raw = (int(departure_minutes) - int(round(float(duration_hours) * 60))) % 1440
    return align_charge_start_minutes(raw)


def compute_charge_start_datetime(
    departure_at: datetime, duration_hours: int | float
) -> datetime:
    """Compute aligned local charge start datetime before ``departure_at``."""
    dur_min = int(round(float(duration_hours) * 60))
    raw_start = (departure_at.hour * 60 + departure_at.minute - dur_min) % 1440
    floor_delta = raw_start - align_charge_start_minutes(raw_start)
    return shift_minutes(departure_at, -(dur_min + floor_delta))


def compute_battery_heat_start_for_departure(
    departure_minutes: int, lead_minutes: int = 30
) -> int:
    """Compute battery pack heat start time in local minutes before ``departure_minutes``."""
    return (int(departure_minutes) - int(lead_minutes)) % 1440


def _shift_schedule_days(days: Sequence[int] | None, day_delta: int) -> list[int]:
    if not days:
        return []
    return sorted({((_parse_day_token(d) - 1 + day_delta) % 7) + 1 for d in days})


def local_schedule_to_utc(
    local_minutes: int,
    days: Sequence[int] | None,
    tzinfo,
    *,
    ref_date: date | None = None,
) -> tuple[int, list[int]]:
    """Convert local minutes since midnight and ISO weekdays ``1..7`` to UTC."""
    if isinstance(local_minutes, bool):
        raise ValueError(f"Boolean is not a valid minute count: {local_minutes!r}")
    tz = tzinfo or timezone.utc
    base_date = ref_date if ref_date is not None else datetime.now(tz).date()
    local_dt = _at_local_time(base_date, int(local_minutes), tz)
    utc_dt = local_dt.astimezone(timezone.utc)
    utc_minutes = utc_dt.hour * 60 + utc_dt.minute
    day_delta = (utc_dt.date() - local_dt.date()).days
    return utc_minutes, _shift_schedule_days(days, day_delta)


def utc_schedule_to_local(
    utc_minutes: int,
    days: Sequence[int] | None,
    tzinfo,
    *,
    ref_date: date | None = None,
) -> tuple[int, list[int]]:
    """Convert UTC minutes since midnight and ISO weekdays ``1..7`` to local ``tzinfo``."""
    if isinstance(utc_minutes, bool):
        raise ValueError(f"Boolean is not a valid minute count: {utc_minutes!r}")
    tz = tzinfo or timezone.utc
    base_date = ref_date if ref_date is not None else datetime.now(timezone.utc).date()
    utc_dt = _at_local_time(base_date, int(utc_minutes), timezone.utc)
    local_dt = utc_dt.astimezone(tz)
    local_minutes = local_dt.hour * 60 + local_dt.minute
    day_delta = (local_dt.date() - utc_dt.date()).days
    return local_minutes, _shift_schedule_days(days, day_delta)


def decode_charge_appoint_plan(
    piano: dict, tzinfo, *, ref_date: date | None = None
) -> dict[str, object] | None:
    """Decode ``chargeAppointPlans[0]`` from UTC wire format into local schedule fields."""
    if not isinstance(piano, dict):
        return None

    raw_start = piano.get("startTime")
    utc_min: int | None = None
    local_start: int | None = None
    if raw_start is not None and not isinstance(raw_start, bool):
        try:
            parsed_start = int(raw_start)
        except (TypeError, ValueError):
            parsed_start = -1
        if 0 <= parsed_start < 1440:
            utc_min = parsed_start
            local_start, _ = utc_schedule_to_local(utc_min, None, tzinfo, ref_date=ref_date)

    raw_dur = piano.get("timeConsuming")
    duration_minutes: int | None = None
    if raw_dur is not None and not isinstance(raw_dur, bool):
        try:
            parsed_dur = int(raw_dur)
        except (TypeError, ValueError):
            parsed_dur = -1
        if parsed_dur >= 0:
            duration_minutes = parsed_dur

    raw_days = piano.get("cycleData")
    days: list[int] | None
    if raw_days is None or raw_days == []:
        days = []
    elif isinstance(raw_days, (list, tuple)) and utc_min is not None:
        try:
            _, days = utc_schedule_to_local(utc_min, raw_days, tzinfo, ref_date=ref_date)
        except (ValueError, TypeError):
            days = None
    elif isinstance(raw_days, (list, tuple)) and utc_min is None:
        try:
            days = sorted({_parse_day_token(d) for d in raw_days})
        except (ValueError, TypeError):
            days = None
    else:
        days = None

    if local_start is None and duration_minutes is None and not days:
        return None
    return {
        "start_minutes": local_start,
        "duration_minutes": duration_minutes,
        "days": days,
    }


def normalize_climate_extras(extras: Sequence[str] | object) -> list[str]:
    """Validate, deduplicate, and resolve seat heating/ventilation mutual exclusions."""
    if extras is None:
        return []
    if isinstance(extras, str):
        stripped = extras.strip()
        if not stripped:
            return []
        items: list[object] = [part.strip() for part in stripped.split(",")]
        if any(not part for part in items):
            raise ValueError(f"Empty token in climate extras: {extras!r}")
    elif isinstance(extras, (list, tuple, set)):
        items = list(extras)
    else:
        raise ValueError(f"Unsupported climate extras type: {type(extras).__name__}")

    out: list[str] = []
    for raw in items:
        if not isinstance(raw, str):
            raise ValueError(f"Invalid climate extra token: {raw!r}")
        key = raw.strip()
        if key not in DEPARTURE_CLIMATE_EXTRAS_COMMANDS:
            raise ValueError(f"Unknown departure climate extra: {raw!r}")
        # Last selection wins when heating and ventilation target the same seat.
        opposite = DEPARTURE_CLIMATE_EXTRAS_MUTUAL_EXCLUSIONS.get(key)
        if opposite and opposite in out:
            out.remove(opposite)
        if key not in out:
            out.append(key)
    return out


def preset_for_days(days: Sequence[int] | None) -> str:
    """Return the matching preset key for ``days``, or ``'custom'``."""
    if not days:
        return "custom"
    try:
        norm = parse_days_input(list(days))
    except ValueError:
        return "custom"
    for name, preset_days in CHARGE_DAYS_PRESETS.items():
        if norm == preset_days:
            return name
    return "custom"


def _parse_day_token(token: object) -> int:
    if isinstance(token, bool):
        raise ValueError(f"Boolean is not a valid weekday: {token!r}")
    if isinstance(token, int):
        if 1 <= token <= 7:
            return token
        raise ValueError(f"Weekday integer out of range 1..7: {token!r}")
    if isinstance(token, str):
        cleaned = token.strip().lower()
        if cleaned in _SLUG_TO_DAY:
            return _SLUG_TO_DAY[cleaned]
        if cleaned in _VALID_DAY_STRINGS:
            return int(cleaned)
        raise ValueError(f"Invalid weekday token: {token!r}")
    raise ValueError(f"Unsupported weekday token type: {type(token).__name__}")


def parse_days_input(raw: object) -> list[int]:
    """Parse preset name, CSV string, slug/int, or sequence into sorted ISO weekdays ``1..7``."""
    if isinstance(raw, bool) or raw is None:
        raise ValueError(f"Invalid days input: {raw!r}")
    if isinstance(raw, int):
        return [_parse_day_token(raw)]
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if not normalized:
            raise ValueError("Empty days input")
        if normalized in CHARGE_DAYS_PRESETS:
            return list(CHARGE_DAYS_PRESETS[normalized])
        parts = [part.strip() for part in raw.split(",")]
        if any(not part for part in parts):
            raise ValueError(f"Empty token in CSV days input: {raw!r}")
        return sorted({_parse_day_token(part) for part in parts})
    if isinstance(raw, (list, tuple, set)):
        items = list(raw)
        if not items:
            raise ValueError("Empty days collection")
        return sorted({_parse_day_token(item) for item in items})
    raise ValueError(f"Unsupported days input type: {type(raw).__name__}")
