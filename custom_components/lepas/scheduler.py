"""Pure scheduling calculations for departure pre-climate and smart charging."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

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


def compute_charge_start_for_departure(
    departure_minutes: int, duration_hours: int | float
) -> int:
    """Compute charge start time in local minutes from midnight, wrapping across midnight."""
    return (int(departure_minutes) - int(round(float(duration_hours) * 60))) % 1440


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
