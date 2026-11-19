"""Pure Python long-term consumption tracker (EV / Hybrid) with no HA runtime deps."""
from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .const import DEFAULT_BATTERY_CAPACITY_KWH

WINDOW_100_KM = 100.0
WINDOW_1000_KM = 1000.0
MAX_STEP_GAP_KM = 50.0
MIN_SAMPLE_KM_EV = 5.0
MIN_SAMPLE_KM_HYBRID = 10.0

ELEC_RANGE_FIELDS = ("pureElectricRange", "dynamicPureElectricRange")


def _safe_float(value: object) -> float | None:
    """Convert value to a finite float or None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if math.isfinite(num) else None


def is_degraded_battery_frame(rt: dict | None) -> bool:
    """True when realtime reports 0 km electric range (placeholder frame with bogus SOC)."""
    if not isinstance(rt, dict):
        return False
    for key in ELEC_RANGE_FIELDS:
        if key in rt:
            val = _safe_float(rt[key])
            if val is not None:
                return val == 0.0
            return False
    return False


@dataclass
class _Segment:
    """Single driving delta in EV or Hybrid mode."""

    km: float
    kwh: float
    fuel_l: float = 0.0

    def to_dict(self, include_fuel: bool) -> dict[str, float]:
        data: dict[str, float] = {"km": self.km, "kwh": self.kwh}
        if include_fuel:
            data["fuel_l"] = self.fuel_l
        return data

    @classmethod
    def from_dict(cls, raw: object) -> _Segment | None:
        if not isinstance(raw, dict):
            return None
        km = _safe_float(raw.get("km"))
        kwh = _safe_float(raw.get("kwh"))
        fuel_l = _safe_float(raw.get("fuel_l", 0.0))
        if km is None or km <= 0.0 or kwh is None or fuel_l is None or fuel_l < 0.0:
            return None
        return cls(km=km, kwh=kwh, fuel_l=fuel_l)


def _trim_queue(queue: deque[_Segment], max_km: float) -> None:
    """Drop or proportionally trim oldest segments so total distance stays <= max_km."""
    total_km = sum(seg.km for seg in queue)
    while total_km > max_km and queue:
        excess = total_km - max_km
        oldest = queue[0]
        if oldest.km <= excess:
            total_km -= oldest.km
            queue.popleft()
        else:
            ratio = (oldest.km - excess) / oldest.km
            oldest.km -= excess
            oldest.kwh *= ratio
            oldest.fuel_l *= ratio
            break


def _slice_window(segments: Sequence[_Segment], target_km: float) -> tuple[float, float, float]:
    """Accumulate newest-to-oldest segments up to target_km with proportional boundary split."""
    remaining = target_km
    total_km = 0.0
    total_kwh = 0.0
    total_fuel = 0.0
    for seg in reversed(segments):
        if seg.km <= 0.0:
            continue
        if seg.km <= remaining:
            total_km += seg.km
            total_kwh += seg.kwh
            total_fuel += seg.fuel_l
            remaining -= seg.km
        else:
            ratio = remaining / seg.km
            total_km += remaining
            total_kwh += seg.kwh * ratio
            total_fuel += seg.fuel_l * ratio
            break
    return total_km, total_kwh, total_fuel


class ConsumptionTracker:
    """Tracks EV (kWh/100 km) and Hybrid (L/100 km) consumption over 100/1000 km and From Start."""

    def __init__(self) -> None:
        self._last_odo: float | None = None
        self._last_soc: float | None = None
        self._last_fuel: float | None = None
        self._ev_segments: deque[_Segment] = deque()
        self._hev_segments: deque[_Segment] = deque()
        self._from_start_ev_km: float = 0.0
        self._from_start_ev_kwh: float = 0.0
        self._from_start_hev_km: float = 0.0
        self._from_start_hev_fuel_l: float = 0.0
        self._from_start_hev_kwh: float = 0.0

    def ingest(
        self,
        odometer: float | None,
        soc_pct: float | None,
        fuel_l: float | None,
        *,
        engine_on: bool,
        charging_or_plugged: bool,
        degraded_battery: bool,
        battery_capacity_kwh: float,
    ) -> bool:
        """Ingest one realtime telemetry frame. Returns True if persisted state changed."""
        if degraded_battery:
            return False
        odo = _safe_float(odometer)
        soc = _safe_float(soc_pct)
        if odo is None or odo <= 0.0 or soc is None or soc <= 0.0:
            return False

        raw_fuel = _safe_float(fuel_l)
        fuel = raw_fuel if raw_fuel is not None and raw_fuel >= 0.0 else None
        cap = _safe_float(battery_capacity_kwh)
        if cap is None or cap <= 0.0:
            cap = DEFAULT_BATTERY_CAPACITY_KWH

        if self._last_odo is None or self._last_soc is None:
            self._last_odo = odo
            self._last_soc = soc
            self._last_fuel = fuel
            return True

        delta_km = odo - self._last_odo
        if delta_km < 0.0 or delta_km > MAX_STEP_GAP_KM:
            self._last_odo = odo
            self._last_soc = soc
            self._last_fuel = fuel
            return True

        if delta_km == 0.0:
            changed = False
            if (charging_or_plugged or soc > self._last_soc) and soc != self._last_soc:
                self._last_soc = soc
                changed = True
            if fuel is not None and (self._last_fuel is None or fuel > self._last_fuel):
                self._last_fuel = fuel
                changed = True
            return changed

        kwh_used = 0.0 if charging_or_plugged else ((self._last_soc - soc) / 100.0) * cap
        if engine_on:
            if fuel is not None and self._last_fuel is not None:
                fuel_used = 0.0 if fuel > self._last_fuel else (self._last_fuel - fuel)
            else:
                fuel_used = 0.0
            self._hev_segments.append(_Segment(km=delta_km, kwh=kwh_used, fuel_l=fuel_used))
            _trim_queue(self._hev_segments, WINDOW_1000_KM)
            self._from_start_hev_km += delta_km
            self._from_start_hev_fuel_l += fuel_used
            self._from_start_hev_kwh += kwh_used
        else:
            self._ev_segments.append(_Segment(km=delta_km, kwh=kwh_used))
            _trim_queue(self._ev_segments, WINDOW_1000_KM)
            self._from_start_ev_km += delta_km
            self._from_start_ev_kwh += kwh_used

        self._last_odo = odo
        self._last_soc = soc
        if fuel is not None:
            self._last_fuel = fuel
        return True

    def window_stats(self, mode: str, target_km: float | None) -> dict[str, Any]:
        """Compute consumption stats for mode ('ev' or 'hev') and distance window."""
        if mode not in ("ev", "hev"):
            raise ValueError(f"Unsupported consumption mode: {mode!r}")

        if mode == "ev":
            min_km = MIN_SAMPLE_KM_EV
            if target_km is None:
                km, kwh, fuel_l = self._from_start_ev_km, self._from_start_ev_kwh, 0.0
            else:
                km, kwh, fuel_l = _slice_window(self._ev_segments, float(target_km))
            ready = km >= min_km
            value = round((kwh / km) * 100.0, 3) if ready else None
            electric_kwh_100km = None
        else:
            min_km = MIN_SAMPLE_KM_HYBRID
            if target_km is None:
                km = self._from_start_hev_km
                kwh = self._from_start_hev_kwh
                fuel_l = self._from_start_hev_fuel_l
            else:
                km, kwh, fuel_l = _slice_window(self._hev_segments, float(target_km))
            ready = km >= min_km
            value = round((fuel_l / km) * 100.0, 3) if ready else None
            electric_kwh_100km = round((kwh / km) * 100.0, 3) if ready else None

        progress_pct = (
            round(min(100.0, (km / float(target_km)) * 100.0), 1)
            if target_km is not None and target_km > 0.0
            else None
        )
        return {
            "value": value,
            "sampled_km": round(km, 3),
            "window_target_km": float(target_km) if target_km is not None else None,
            "progress_pct": progress_pct,
            "energy_kwh": round(kwh, 3),
            "fuel_l": round(fuel_l, 3),
            "electric_kwh_100km": electric_kwh_100km,
        }

    def reset_from_start(self) -> None:
        """Zero From Start accumulators while keeping rolling queues and baselines intact."""
        self._from_start_ev_km = 0.0
        self._from_start_ev_kwh = 0.0
        self._from_start_hev_km = 0.0
        self._from_start_hev_fuel_l = 0.0
        self._from_start_hev_kwh = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize tracker state to a PII-free JSON-compatible dict."""
        return {
            "version": 1,
            "last_odo": self._last_odo,
            "last_soc": self._last_soc,
            "last_fuel": self._last_fuel,
            "ev_segments": [seg.to_dict(include_fuel=False) for seg in self._ev_segments],
            "hev_segments": [seg.to_dict(include_fuel=True) for seg in self._hev_segments],
            "from_start": {
                "ev_km": self._from_start_ev_km,
                "ev_kwh": self._from_start_ev_kwh,
                "hev_km": self._from_start_hev_km,
                "hev_fuel_l": self._from_start_hev_fuel_l,
                "hev_kwh": self._from_start_hev_kwh,
            },
        }

    @classmethod
    def from_dict(cls, raw: dict | None) -> ConsumptionTracker:
        """Restore tracker from persisted JSON dict, ignoring malformed entries safely."""
        tracker = cls()
        if not isinstance(raw, dict):
            return tracker

        odo = _safe_float(raw.get("last_odo"))
        soc = _safe_float(raw.get("last_soc"))
        fuel = _safe_float(raw.get("last_fuel"))
        if odo is not None and odo > 0.0 and soc is not None and soc > 0.0:
            tracker._last_odo = odo
            tracker._last_soc = soc
            tracker._last_fuel = fuel if (fuel is not None and fuel >= 0.0) else None

        raw_ev = raw.get("ev_segments")
        if isinstance(raw_ev, list):
            for item in raw_ev:
                seg = _Segment.from_dict(item)
                if seg is not None:
                    tracker._ev_segments.append(_Segment(km=seg.km, kwh=seg.kwh))
            _trim_queue(tracker._ev_segments, WINDOW_1000_KM)

        raw_hev = raw.get("hev_segments")
        if isinstance(raw_hev, list):
            for item in raw_hev:
                seg = _Segment.from_dict(item)
                if seg is not None:
                    tracker._hev_segments.append(seg)
            _trim_queue(tracker._hev_segments, WINDOW_1000_KM)

        fs = raw.get("from_start")
        if isinstance(fs, dict):
            ev_km = _safe_float(fs.get("ev_km"))
            ev_kwh = _safe_float(fs.get("ev_kwh"))
            hev_km = _safe_float(fs.get("hev_km"))
            hev_fuel = _safe_float(fs.get("hev_fuel_l"))
            hev_kwh = _safe_float(fs.get("hev_kwh"))
            if ev_km is not None and ev_km >= 0.0:
                tracker._from_start_ev_km = ev_km
            if ev_kwh is not None:
                tracker._from_start_ev_kwh = ev_kwh
            if hev_km is not None and hev_km >= 0.0:
                tracker._from_start_hev_km = hev_km
            if hev_fuel is not None and hev_fuel >= 0.0:
                tracker._from_start_hev_fuel_l = hev_fuel
            if hev_kwh is not None:
                tracker._from_start_hev_kwh = hev_kwh
        return tracker
