"""Pure Python charging energy statistics tracker with hybrid integration."""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from typing import Any

from .const import CHARGE_ENERGY_MAX_GAP, DEFAULT_BATTERY_CAPACITY_KWH
from .consumption import _safe_float

DAILY_HISTORY_LIMIT = 30
MONTHLY_HISTORY_LIMIT = 12
MIN_VALID_SOC_STEP_PCT = 0.5
MAX_SOC_JUMP_PCT = 100.0
DC_POWER_THRESHOLD_KW = 11.0
CC_MIN_POWER_KW = 0.5
CC_AC_MAX_POWER_KW = 15.0
CC_DC_MAX_POWER_KW = 120.0
CC_AC_SOC_MAX_PCT = 85.0
CC_DC_SOC_MAX_PCT = 75.0
CC_MIN_SAMPLES = 3
CC_MAX_SAMPLES = 120
CC_EMA_OLD_WEIGHT = 0.7
CC_EMA_NEW_WEIGHT = 0.3
DEFAULT_MANUAL_HOME_POWER_KW = 2.3

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")
_YEAR_RE = re.compile(r"^\d{4}$")


def classify_charge_kind(fast_charging: bool | None, power_kw: float | None) -> str:
    """Classify connector type as 'dc' or 'ac' from fast-charging flag or power."""
    if fast_charging is True:
        return "dc"
    pwr = _safe_float(power_kw)
    if pwr is not None and pwr > DC_POWER_THRESHOLD_KW:
        return "dc"
    return "ac"


def select_effective_home_power(
    *,
    auto_enabled: bool,
    manual_kw: float,
    charge_kind: str,
    learned_ac_kw: float | None,
    learned_dc_kw: float | None,
) -> tuple[float, str]:
    """Select effective home power in kW and its source ('learned_ac', 'learned_dc', 'manual')."""
    man_raw = _safe_float(manual_kw)
    manual = (
        man_raw
        if (man_raw is not None and man_raw > 0.0)
        else DEFAULT_MANUAL_HOME_POWER_KW
    )
    if not auto_enabled:
        return (manual, "manual")
    if charge_kind == "dc":
        dc_kw = _safe_float(learned_dc_kw)
        if dc_kw is not None and dc_kw > 0.0:
            return (dc_kw, "learned_dc")
        return (manual, "manual")
    ac_kw = _safe_float(learned_ac_kw)
    if ac_kw is not None and ac_kw > 0.0:
        return (ac_kw, "learned_ac")
    return (manual, "manual")


def _is_charging_state(charge_state: object) -> bool:
    if isinstance(charge_state, bool):
        return charge_state
    val = _safe_float(charge_state)
    return val == 1.0 if val is not None else False


def compute_charge_delta_kwh(
    prev_ts: float | None,
    prev_power_kw: float,
    prev_soc_pct: float | None,
    prev_odo_km: float | None,
    prev_charging: bool,
    *,
    now_ts: float,
    power_kw: float,
    soc_pct: float | None,
    odo_km: float | None,
    charging: bool,
    plugged: bool,
    degraded_battery: bool,
    battery_capacity_kwh: float,
    max_gap_s: float = CHARGE_ENERGY_MAX_GAP,
) -> tuple[float, bool]:
    """Compute charged kWh delta via trapezoidal integration or >max_gap_s SoC delta."""
    if degraded_battery:
        return (0.0, False)

    cur_odo = _safe_float(odo_km)
    p_odo = _safe_float(prev_odo_km)
    if (
        cur_odo is not None
        and cur_odo >= 0.0
        and p_odo is not None
        and p_odo >= 0.0
        and cur_odo > p_odo + 0.1
    ):
        return (0.0, True)

    cap = _safe_float(battery_capacity_kwh)
    if cap is None or cap <= 0.0:
        return (0.0, False)

    cur_ts = _safe_float(now_ts)
    p_ts = _safe_float(prev_ts)
    if cur_ts is None or p_ts is None:
        return (0.0, False)

    dt_s = cur_ts - p_ts
    if dt_s <= 0.0:
        return (0.0, False)

    cur_pwr = _safe_float(power_kw)
    p_pwr = _safe_float(prev_power_kw)
    gap = _safe_float(max_gap_s)
    if gap is None or gap <= 0.0:
        gap = float(CHARGE_ENERGY_MAX_GAP)

    if dt_s <= gap:
        if (
            charging
            and prev_charging
            and cur_pwr is not None
            and cur_pwr > 0.0
            and p_pwr is not None
            and p_pwr > 0.0
        ):
            return (0.5 * (p_pwr + cur_pwr) * (dt_s / 3600.0), False)
        return (0.0, False)

    cur_soc = _safe_float(soc_pct)
    p_soc = _safe_float(prev_soc_pct)
    if (
        (prev_charging or charging or plugged)
        and cur_soc is not None
        and 0.0 <= cur_soc <= 100.0
        and p_soc is not None
        and 0.0 <= p_soc <= 100.0
    ):
        delta_soc = cur_soc - p_soc
        if MIN_VALID_SOC_STEP_PCT <= delta_soc <= MAX_SOC_JUMP_PCT:
            return ((delta_soc / 100.0) * cap, False)
    return (0.0, False)


@dataclass
class _Bucket:
    """Energy and session accumulator for a period or history slot."""

    total_kwh: float = 0.0
    home_kwh: float = 0.0
    away_kwh: float = 0.0
    sessions_count: int = 0

    def add_energy(self, delta_kwh: float, in_home_zone: bool | None) -> None:
        self.total_kwh += delta_kwh
        if in_home_zone is True:
            self.home_kwh += delta_kwh
        elif in_home_zone is False:
            self.away_kwh += delta_kwh

    def reset(self) -> None:
        self.total_kwh = 0.0
        self.home_kwh = 0.0
        self.away_kwh = 0.0
        self.sessions_count = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_kwh": self.total_kwh,
            "home_kwh": self.home_kwh,
            "away_kwh": self.away_kwh,
            "sessions_count": self.sessions_count,
        }

    def to_rounded_dict(self) -> dict[str, Any]:
        return {
            "total_kwh": round(self.total_kwh, 3),
            "home_kwh": round(self.home_kwh, 3),
            "away_kwh": round(self.away_kwh, 3),
            "sessions_count": self.sessions_count,
        }

    @classmethod
    def from_dict(cls, raw: object) -> _Bucket:
        bucket = cls()
        if not isinstance(raw, dict):
            return bucket
        for attr in ("total_kwh", "home_kwh", "away_kwh"):
            val = _safe_float(raw.get(attr))
            if val is not None and val >= 0.0:
                setattr(bucket, attr, val)
        sc = raw.get("sessions_count")
        if not isinstance(sc, bool) and isinstance(sc, (int, float)):
            sc_f = _safe_float(sc)
            if sc_f is not None and sc_f >= 0.0 and float(int(sc_f)) == sc_f:
                bucket.sessions_count = int(sc_f)
        return bucket


class ChargingStatsTracker:
    """Tracks periodic charging energy (today/month/year/from_start) and history."""

    def __init__(self) -> None:
        self._today_key: str | None = None
        self._month_key: str | None = None
        self._year_key: str | None = None
        self._today: _Bucket = _Bucket()
        self._month: _Bucket = _Bucket()
        self._year: _Bucket = _Bucket()
        self._from_start: _Bucket = _Bucket()
        self._daily_history: dict[str, _Bucket] = {}
        self._monthly_history: dict[str, _Bucket] = {}
        self._prev_ts: float | None = None
        self._prev_power_kw: float = 0.0
        self._prev_soc_pct: float | None = None
        self._prev_odo_km: float | None = None
        self._prev_charging: bool = False
        self._session_active: bool = False
        self._session_counted: bool = False
        self._home_learned_ac_kw: float | None = None
        self._home_learned_dc_kw: float | None = None
        self._home_ac_sessions: int = 0
        self._home_dc_sessions: int = 0
        self._cc_kind: str | None = None
        self._cc_samples: list[float] = []

    def _flush_cc_learning(self) -> bool:
        """Finalize buffered CC home power samples into the learned AC/DC EMA profile."""
        if len(self._cc_samples) < CC_MIN_SAMPLES or self._cc_kind not in ("ac", "dc"):
            self._cc_samples.clear()
            self._cc_kind = None
            return False
        med = float(statistics.median(self._cc_samples))
        if self._cc_kind == "dc":
            old = self._home_learned_dc_kw
            self._home_learned_dc_kw = (
                round(med, 2)
                if old is None
                else round(CC_EMA_OLD_WEIGHT * old + CC_EMA_NEW_WEIGHT * med, 2)
            )
            self._home_dc_sessions += 1
        else:
            old = self._home_learned_ac_kw
            self._home_learned_ac_kw = (
                round(med, 2)
                if old is None
                else round(CC_EMA_OLD_WEIGHT * old + CC_EMA_NEW_WEIGHT * med, 2)
            )
            self._home_ac_sessions += 1
        self._cc_samples.clear()
        self._cc_kind = None
        return True

    def home_power_profile(self) -> dict[str, Any]:
        """Return learned AC/DC home charging power and session counts."""
        return {
            "learned_ac_kw": self._home_learned_ac_kw,
            "learned_dc_kw": self._home_learned_dc_kw,
            "home_ac_sessions": self._home_ac_sessions,
            "home_dc_sessions": self._home_dc_sessions,
        }

    def _rollover(self, local_date: str) -> bool:
        local_month = local_date[:7]
        local_year = local_date[:4]
        rolled = False
        if self._today_key != local_date:
            self._today.reset()
            self._today_key = local_date
            rolled = True
        if self._month_key != local_month:
            self._month.reset()
            self._month_key = local_month
            rolled = True
        if self._year_key != local_year:
            self._year.reset()
            self._year_key = local_year
            rolled = True
        return rolled

    def _prune_history(self) -> None:
        while len(self._daily_history) > DAILY_HISTORY_LIMIT:
            del self._daily_history[min(self._daily_history)]
        while len(self._monthly_history) > MONTHLY_HISTORY_LIMIT:
            del self._monthly_history[min(self._monthly_history)]

    def _target_buckets(self, local_date: str) -> tuple[_Bucket, ...]:
        local_month = local_date[:7]
        return (
            self._today,
            self._month,
            self._year,
            self._from_start,
            self._daily_history.setdefault(local_date, _Bucket()),
            self._monthly_history.setdefault(local_month, _Bucket()),
        )

    def _record_session_start(self, local_date: str) -> None:
        for bucket in self._target_buckets(local_date):
            bucket.sessions_count += 1
        self._prune_history()

    def _record_energy(
        self, local_date: str, delta_kwh: float, in_home_zone: bool | None
    ) -> None:
        for bucket in self._target_buckets(local_date):
            bucket.add_energy(delta_kwh, in_home_zone)
        self._prune_history()

    def _record_delta_if_positive(
        self,
        local_date: str,
        delta_kwh: float,
        in_home_zone: bool | None,
    ) -> bool:
        if delta_kwh <= 0.0:
            return False
        if not self._session_counted:
            self._session_active = True
            self._record_session_start(local_date)
            self._session_counted = True
        self._record_energy(local_date, delta_kwh, in_home_zone)
        return True

    def _maybe_recover_soc_gap(
        self,
        ts: float,
        local_date: str,
        *,
        soc: float | None,
        odo: float | None,
        plugged: bool,
        in_home_zone: bool | None,
        cap: float,
    ) -> bool:
        if self._prev_ts is None or soc is None:
            return False
        delta_kwh, _ = compute_charge_delta_kwh(
            self._prev_ts,
            self._prev_power_kw,
            self._prev_soc_pct,
            self._prev_odo_km,
            self._prev_charging,
            now_ts=ts,
            power_kw=0.0,
            soc_pct=soc,
            odo_km=odo,
            charging=False,
            plugged=bool(plugged),
            degraded_battery=False,
            battery_capacity_kwh=cap,
        )
        return self._record_delta_if_positive(local_date, delta_kwh, in_home_zone)

    def ingest(
        self,
        now_ts: float,
        local_date: str,
        *,
        power_kw: float | None,
        charge_state: object,
        plugged: bool,
        soc_pct: float | None,
        odometer: float | None,
        in_home_zone: bool | None,
        degraded_battery: bool,
        battery_capacity_kwh: float = DEFAULT_BATTERY_CAPACITY_KWH,
        fast_charging: bool | None = None,
    ) -> bool:
        """Ingest one realtime or fields-only update. Returns True if persisted state changed."""
        if degraded_battery:
            return False
        ts = _safe_float(now_ts)
        if (
            ts is None
            or not isinstance(local_date, str)
            or not _DATE_RE.match(local_date)
        ):
            return False

        soc_raw = _safe_float(soc_pct)
        soc = soc_raw if (soc_raw is not None and 0.0 <= soc_raw <= 100.0) else None
        odo_raw = _safe_float(odometer)
        odo = odo_raw if (odo_raw is not None and odo_raw >= 0.0) else None
        cap_raw = _safe_float(battery_capacity_kwh)
        cap = cap_raw if cap_raw is not None else 0.0

        changed = self._rollover(local_date)
        if in_home_zone is not True and self._flush_cc_learning():
            changed = True

        if power_kw is None:
            # MQTT fields-only push: preserve trapezoid anchor unless session clearly stopped.
            cs_val = (
                (1.0 if charge_state else 0.0)
                if isinstance(charge_state, bool)
                else _safe_float(charge_state)
            )
            odo_advanced = (
                odo is not None
                and self._prev_odo_km is not None
                and odo > self._prev_odo_km + 0.1
            )
            explicit_charge_off = cs_val is not None and cs_val != 1.0
            stop_continuity = (not plugged) or explicit_charge_off or odo_advanced

            if not stop_continuity:
                dt_s = (ts - self._prev_ts) if self._prev_ts is not None else 0.0
                if dt_s > CHARGE_ENERGY_MAX_GAP and self._maybe_recover_soc_gap(
                    ts,
                    local_date,
                    soc=soc,
                    odo=odo,
                    plugged=bool(plugged),
                    in_home_zone=in_home_zone,
                    cap=cap,
                ):
                    self._prev_ts = ts
                    self._prev_power_kw = 0.0
                    self._prev_charging = False
                    self._prev_soc_pct = soc
                    if odo is not None:
                        self._prev_odo_km = odo
                    return True
                return changed

            if not odo_advanced and self._maybe_recover_soc_gap(
                ts,
                local_date,
                soc=soc,
                odo=odo,
                plugged=bool(plugged),
                in_home_zone=in_home_zone,
                cap=cap,
            ):
                changed = True

            was_active = self._prev_charging or self._session_active
            if self._prev_ts != ts or self._prev_charging or self._prev_power_kw != 0.0:
                changed = True
            self._prev_ts = ts
            self._prev_power_kw = 0.0
            self._prev_charging = False
            if soc is not None:
                if self._prev_soc_pct != soc:
                    changed = True
                self._prev_soc_pct = soc
            elif odo_advanced and self._prev_soc_pct is not None:
                self._prev_soc_pct = None
                changed = True
            if odo is not None:
                if self._prev_odo_km != odo:
                    changed = True
                self._prev_odo_km = odo
            if (not plugged) or odo_advanced:
                if self._flush_cc_learning():
                    changed = True
                if was_active:
                    changed = True
                self._session_active = False
                self._session_counted = False
            return changed

        pwr_raw = _safe_float(power_kw)
        pwr = pwr_raw if (pwr_raw is not None and pwr_raw > 0.0) else 0.0
        charging = _is_charging_state(charge_state) and pwr > 0.0

        delta_kwh, reset_cont = compute_charge_delta_kwh(
            self._prev_ts,
            self._prev_power_kw,
            self._prev_soc_pct,
            self._prev_odo_km,
            self._prev_charging,
            now_ts=ts,
            power_kw=pwr,
            soc_pct=soc,
            odo_km=odo,
            charging=charging,
            plugged=bool(plugged),
            degraded_battery=False,
            battery_capacity_kwh=cap,
        )

        if reset_cont:
            if self._flush_cc_learning():
                changed = True
            self._session_active = False
            self._session_counted = False

        if in_home_zone is True and charging:
            kind = classify_charge_kind(fast_charging, pwr)
            if (
                self._cc_kind is not None
                and self._cc_kind != kind
                and self._flush_cc_learning()
            ):
                changed = True
            max_pwr = CC_DC_MAX_POWER_KW if kind == "dc" else CC_AC_MAX_POWER_KW
            max_soc = CC_DC_SOC_MAX_PCT if kind == "dc" else CC_AC_SOC_MAX_PCT
            # Only collect constant-current phase samples so CV taper does not skew learned power.
            if (
                CC_MIN_POWER_KW <= pwr <= max_pwr
                and soc is not None
                and 0.0 <= soc < max_soc
            ):
                self._cc_kind = kind
                if len(self._cc_samples) < CC_MAX_SAMPLES:
                    self._cc_samples.append(pwr)

        if self._record_delta_if_positive(local_date, delta_kwh, in_home_zone):
            changed = True

        if charging:
            if not self._session_active:
                self._session_active = True
            if not self._session_counted:
                self._record_session_start(local_date)
                self._session_counted = True
                changed = True

        new_prev_charging = False if reset_cont else charging
        new_prev_pwr = 0.0 if reset_cont else pwr
        new_prev_soc = soc if (soc is not None or reset_cont) else self._prev_soc_pct
        new_prev_odo = odo if (odo is not None or reset_cont) else self._prev_odo_km

        if (
            self._prev_ts is None
            or self._prev_charging != new_prev_charging
            or self._prev_power_kw != new_prev_pwr
            or self._prev_soc_pct != new_prev_soc
            or self._prev_odo_km != new_prev_odo
            or charging
            or reset_cont
        ):
            changed = True

        self._prev_ts = ts
        self._prev_power_kw = new_prev_pwr
        self._prev_charging = new_prev_charging
        self._prev_soc_pct = new_prev_soc
        self._prev_odo_km = new_prev_odo

        if not plugged and not charging:
            if self._flush_cc_learning():
                changed = True
        if (not plugged and not charging) or reset_cont:
            if self._session_active or self._session_counted:
                changed = True
            self._session_active = False
            self._session_counted = False

        return changed

    def period_stats(self, period: str, current_local_date: str) -> dict[str, Any]:
        """Return rounded stats for 'today', 'month', 'year', or 'from_start'."""
        if period not in ("today", "month", "year", "from_start"):
            raise ValueError(f"Unsupported charging stats period: {period!r}")

        valid_date = isinstance(current_local_date, str) and bool(
            _DATE_RE.match(current_local_date)
        )
        if period == "today":
            p_key = current_local_date if valid_date else (self._today_key or "")
            bucket = (
                self._today
                if (valid_date and self._today_key == current_local_date)
                else _Bucket()
            )
            out = bucket.to_rounded_dict()
            out["period_key"] = p_key
            out["daily_series"] = [
                {"date": k, **self._daily_history[k].to_rounded_dict()}
                for k in sorted(self._daily_history)
            ]
            return out

        if period == "month":
            m_key = current_local_date[:7] if valid_date else (self._month_key or "")
            bucket = (
                self._month if (valid_date and self._month_key == m_key) else _Bucket()
            )
            out = bucket.to_rounded_dict()
            out["period_key"] = m_key
            return out

        if period == "year":
            y_key = current_local_date[:4] if valid_date else (self._year_key or "")
            bucket = (
                self._year if (valid_date and self._year_key == y_key) else _Bucket()
            )
            out = bucket.to_rounded_dict()
            out["period_key"] = y_key
            out["monthly_series"] = [
                {"month": k, **self._monthly_history[k].to_rounded_dict()}
                for k in sorted(self._monthly_history)
            ]
            return out

        out = self._from_start.to_rounded_dict()
        out["period_key"] = "from_start"
        return out

    def reset_from_start(self) -> None:
        """Zero From Start accumulators while keeping period buckets, history, and baselines."""
        self._from_start.reset()

    def to_dict(self) -> dict[str, Any]:
        """Serialize tracker state to a PII-free JSON-compatible dict."""
        return {
            "version": 1,
            "today_key": self._today_key,
            "month_key": self._month_key,
            "year_key": self._year_key,
            "today": self._today.to_dict(),
            "month": self._month.to_dict(),
            "year": self._year.to_dict(),
            "from_start": self._from_start.to_dict(),
            "daily_history": {
                k: self._daily_history[k].to_dict() for k in sorted(self._daily_history)
            },
            "monthly_history": {
                k: self._monthly_history[k].to_dict()
                for k in sorted(self._monthly_history)
            },
            "baseline": {
                "prev_ts": self._prev_ts,
                "prev_power_kw": self._prev_power_kw,
                "prev_soc_pct": self._prev_soc_pct,
                "prev_odo_km": self._prev_odo_km,
                "prev_charging": self._prev_charging,
                "session_active": self._session_active,
                "session_counted": self._session_counted,
            },
            "home_power": self.home_power_profile(),
        }

    @classmethod
    def from_dict(cls, raw: dict | None) -> ChargingStatsTracker:
        """Restore tracker from persisted JSON dict, ignoring malformed entries safely."""
        tracker = cls()
        if not isinstance(raw, dict):
            return tracker

        t_key = raw.get("today_key")
        if isinstance(t_key, str) and _DATE_RE.match(t_key):
            tracker._today_key = t_key
            tracker._today = _Bucket.from_dict(raw.get("today"))

        m_key = raw.get("month_key")
        if isinstance(m_key, str) and _MONTH_RE.match(m_key):
            tracker._month_key = m_key
            tracker._month = _Bucket.from_dict(raw.get("month"))

        y_key = raw.get("year_key")
        if isinstance(y_key, str) and _YEAR_RE.match(y_key):
            tracker._year_key = y_key
            tracker._year = _Bucket.from_dict(raw.get("year"))

        tracker._from_start = _Bucket.from_dict(raw.get("from_start"))

        raw_daily = raw.get("daily_history")
        if isinstance(raw_daily, dict):
            for k, v in raw_daily.items():
                if isinstance(k, str) and _DATE_RE.match(k):
                    tracker._daily_history[k] = _Bucket.from_dict(v)

        raw_monthly = raw.get("monthly_history")
        if isinstance(raw_monthly, dict):
            for k, v in raw_monthly.items():
                if isinstance(k, str) and _MONTH_RE.match(k):
                    tracker._monthly_history[k] = _Bucket.from_dict(v)

        tracker._prune_history()

        base = raw.get("baseline")
        if isinstance(base, dict):
            p_ts = _safe_float(base.get("prev_ts"))
            if p_ts is not None and p_ts > 0.0:
                tracker._prev_ts = p_ts
            p_pwr = _safe_float(base.get("prev_power_kw"))
            if p_pwr is not None and p_pwr >= 0.0:
                tracker._prev_power_kw = p_pwr
            p_soc = _safe_float(base.get("prev_soc_pct"))
            if p_soc is not None and 0.0 <= p_soc <= 100.0:
                tracker._prev_soc_pct = p_soc
            p_odo = _safe_float(base.get("prev_odo_km"))
            if p_odo is not None and p_odo >= 0.0:
                tracker._prev_odo_km = p_odo
            if isinstance(base.get("prev_charging"), bool):
                tracker._prev_charging = base["prev_charging"]
            if isinstance(base.get("session_active"), bool):
                tracker._session_active = base["session_active"]
            if isinstance(base.get("session_counted"), bool):
                tracker._session_counted = base["session_counted"]

        hp = raw.get("home_power")
        if isinstance(hp, dict):
            ac_kw = _safe_float(hp.get("learned_ac_kw"))
            if ac_kw is not None and CC_MIN_POWER_KW <= ac_kw <= CC_AC_MAX_POWER_KW:
                tracker._home_learned_ac_kw = round(ac_kw, 2)
            dc_kw = _safe_float(hp.get("learned_dc_kw"))
            if dc_kw is not None and CC_MIN_POWER_KW <= dc_kw <= CC_DC_MAX_POWER_KW:
                tracker._home_learned_dc_kw = round(dc_kw, 2)
            for raw_key, attr in (
                ("home_ac_sessions", "_home_ac_sessions"),
                ("home_dc_sessions", "_home_dc_sessions"),
            ):
                sc = hp.get(raw_key)
                if not isinstance(sc, bool) and isinstance(sc, (int, float)):
                    sc_f = _safe_float(sc)
                    if sc_f is not None and sc_f >= 0.0 and float(int(sc_f)) == sc_f:
                        setattr(tracker, attr, int(sc_f))

        return tracker
