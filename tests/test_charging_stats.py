"""Unit and HA integration tests for charging_stats engine, coordinator Store, and entities."""

from __future__ import annotations

import datetime as dt
import json
from unittest.mock import MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lepas.charging_stats import (
    DAILY_HISTORY_LIMIT,
    MONTHLY_HISTORY_LIMIT,
    ChargingStatsTracker,
    compute_charge_delta_kwh,
)
from custom_components.lepas.const import (
    CHARGE_ENERGY_MAX_GAP,
    CONF_BATTERY_CAPACITY_KWH,
    CONF_VIN,
    DOMAIN,
)
from custom_components.lepas.coordinator import LepasCoordinator


def test_trapezoidal_within_max_gap():
    delta, reset_cont = compute_charge_delta_kwh(
        1000.0,
        2.0,
        30.0,
        100.0,
        True,
        now_ts=1120.0,
        power_kw=2.0,
        soc_pct=35.0,
        odo_km=100.0,
        charging=True,
        plugged=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert reset_cont is False
    assert delta == pytest.approx(2.0 * 120.0 / 3600.0, abs=1e-5)

    tracker = ChargingStatsTracker()
    tracker.ingest(
        1000.0,
        "2026-11-19",
        power_kw=2.0,
        charge_state="1",
        plugged=True,
        soc_pct=30.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    tracker.ingest(
        1120.0,
        "2026-11-19",
        power_kw=2.0,
        charge_state="1",
        plugged=True,
        soc_pct=35.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    stats = tracker.period_stats("today", "2026-11-19")
    assert stats["total_kwh"] == pytest.approx(0.067, abs=1e-3)


def test_gap_reconciles_with_soc_delta():
    delta, reset_cont = compute_charge_delta_kwh(
        1000.0,
        2.0,
        30.0,
        100.0,
        True,
        now_ts=2800.0,
        power_kw=2.0,
        soc_pct=50.0,
        odo_km=100.0,
        charging=True,
        plugged=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert reset_cont is False
    assert delta == pytest.approx(3.68, rel=1e-6)

    unchanged, reset_same = compute_charge_delta_kwh(
        1000.0,
        2.0,
        30.0,
        100.0,
        True,
        now_ts=2800.0,
        power_kw=2.0,
        soc_pct=30.0,
        odo_km=100.0,
        charging=True,
        plugged=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert reset_same is False
    assert unchanged == 0.0


def test_degraded_battery_frame_ignored():
    tracker = ChargingStatsTracker()
    tracker.ingest(
        1000.0,
        "2026-11-19",
        power_kw=2.0,
        charge_state="1",
        plugged=True,
        soc_pct=30.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert (
        tracker.ingest(
            1120.0,
            "2026-11-19",
            power_kw=5.0,
            charge_state="1",
            plugged=True,
            soc_pct=97.0,
            odometer=100.0,
            in_home_zone=True,
            degraded_battery=True,
            battery_capacity_kwh=18.4,
        )
        is False
    )
    assert tracker.period_stats("today", "2026-11-19")["total_kwh"] == 0.0

    tracker.ingest(
        2800.0,
        "2026-11-19",
        power_kw=2.0,
        charge_state="1",
        plugged=True,
        soc_pct=50.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert tracker.period_stats("today", "2026-11-19")["total_kwh"] == pytest.approx(
        3.68, rel=1e-4
    )


def test_odometer_advance_resets_continuity():
    delta, reset_cont = compute_charge_delta_kwh(
        1000.0,
        2.0,
        30.0,
        100.0,
        True,
        now_ts=2800.0,
        power_kw=0.0,
        soc_pct=50.0,
        odo_km=105.0,
        charging=False,
        plugged=False,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert delta == 0.0
    assert reset_cont is True

    tracker = ChargingStatsTracker()
    tracker.ingest(
        1000.0,
        "2026-11-19",
        power_kw=2.0,
        charge_state="1",
        plugged=True,
        soc_pct=30.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    tracker.ingest(
        2800.0,
        "2026-11-19",
        power_kw=2.0,
        charge_state="1",
        plugged=True,
        soc_pct=50.0,
        odometer=100.2,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert tracker.period_stats("today", "2026-11-19")["total_kwh"] == 0.0


def test_period_rollover_ingest_and_read():
    tracker = ChargingStatsTracker()
    tracker.ingest(
        1000.0,
        "2026-11-18",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=30.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    tracker.ingest(
        2800.0,
        "2026-11-18",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=50.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )

    same_day = tracker.period_stats("today", "2026-11-18")
    assert same_day["total_kwh"] == pytest.approx(3.68, rel=1e-4)

    next_day = tracker.period_stats("today", "2026-11-19")
    assert next_day["total_kwh"] == 0.0
    assert next_day["sessions_count"] == 0
    assert next_day["period_key"] == "2026-11-19"
    assert tracker.period_stats("month", "2026-11-19")["total_kwh"] == pytest.approx(
        3.68, rel=1e-4
    )

    next_month = tracker.period_stats("month", "2026-12-01")
    assert next_month["total_kwh"] == 0.0
    assert tracker.period_stats("year", "2026-12-01")["total_kwh"] == pytest.approx(
        3.68, rel=1e-4
    )

    next_year = tracker.period_stats("year", "2027-01-01")
    assert next_year["total_kwh"] == 0.0
    assert tracker.period_stats("from_start", "2027-01-01")[
        "total_kwh"
    ] == pytest.approx(3.68, rel=1e-4)

    tracker.ingest(
        4600.0,
        "2026-11-19",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=60.0,
        odometer=100.0,
        in_home_zone=False,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert tracker.period_stats("today", "2026-11-19")["total_kwh"] == pytest.approx(
        1.84, rel=1e-4
    )
    assert tracker.period_stats("month", "2026-11-19")["total_kwh"] == pytest.approx(
        5.52, rel=1e-4
    )
    assert tracker.period_stats("from_start", "2026-11-19")[
        "total_kwh"
    ] == pytest.approx(5.52, rel=1e-4)


def test_zone_attribution_and_none_preserves_total():
    tracker = ChargingStatsTracker()
    tracker.ingest(
        1000.0,
        "2026-11-19",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=10.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    tracker.ingest(
        2000.0,
        "2026-11-19",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=20.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    tracker.ingest(
        3000.0,
        "2026-11-19",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=30.0,
        odometer=100.0,
        in_home_zone=False,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    tracker.ingest(
        4000.0,
        "2026-11-19",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=40.0,
        odometer=100.0,
        in_home_zone=None,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    stats = tracker.period_stats("today", "2026-11-19")
    assert stats["total_kwh"] == pytest.approx(6.0)
    assert stats["home_kwh"] == pytest.approx(2.0)
    assert stats["away_kwh"] == pytest.approx(2.0)


def test_sessions_count_and_series_pruning():
    tracker = ChargingStatsTracker()
    ts = 1000.0
    # Session 1 with active -> brief pause while plugged -> resume -> unplug
    tracker.ingest(
        ts,
        "2026-11-19",
        power_kw=2.0,
        charge_state="1",
        plugged=True,
        soc_pct=30.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    tracker.ingest(
        ts + 120.0,
        "2026-11-19",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=30.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    tracker.ingest(
        ts + 240.0,
        "2026-11-19",
        power_kw=2.0,
        charge_state="1",
        plugged=True,
        soc_pct=31.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    tracker.ingest(
        ts + 360.0,
        "2026-11-19",
        power_kw=0.0,
        charge_state="0",
        plugged=False,
        soc_pct=31.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    assert tracker.period_stats("today", "2026-11-19")["sessions_count"] == 1

    # Generate 35 days across 14 months to exercise pruning limits
    tracker2 = ChargingStatsTracker()
    base_dt = dt.date(2025, 1, 1)
    t_cursor = 10000.0
    for idx in range(35):
        day = base_dt + dt.timedelta(days=idx if idx < 21 else 21 + (idx - 21) * 32)
        d_str = day.isoformat()
        tracker2.ingest(
            t_cursor,
            d_str,
            power_kw=3.6,
            charge_state="1",
            plugged=True,
            soc_pct=20.0,
            odometer=500.0,
            in_home_zone=True,
            degraded_battery=False,
            battery_capacity_kwh=20.0,
        )
        tracker2.ingest(
            t_cursor + 100.0,
            d_str,
            power_kw=3.6,
            charge_state="1",
            plugged=True,
            soc_pct=21.0,
            odometer=500.0,
            in_home_zone=True,
            degraded_battery=False,
            battery_capacity_kwh=20.0,
        )
        tracker2.ingest(
            t_cursor + 200.0,
            d_str,
            power_kw=0.0,
            charge_state="0",
            plugged=False,
            soc_pct=21.0,
            odometer=500.0,
            in_home_zone=True,
            degraded_battery=False,
            battery_capacity_kwh=20.0,
        )
        t_cursor += 1000.0

    last_date = (base_dt + dt.timedelta(days=21 + (34 - 21) * 32)).isoformat()
    daily_series = tracker2.period_stats("today", last_date)["daily_series"]
    monthly_series = tracker2.period_stats("year", last_date)["monthly_series"]
    assert len(daily_series) == DAILY_HISTORY_LIMIT
    assert [d["date"] for d in daily_series] == sorted(d["date"] for d in daily_series)
    assert daily_series[-1]["date"] == last_date
    assert len(monthly_series) == MONTHLY_HISTORY_LIMIT
    assert [m["month"] for m in monthly_series] == sorted(
        m["month"] for m in monthly_series
    )
    assert monthly_series[-1]["month"] == last_date[:7]


def test_reset_from_start_and_resilient_from_dict():
    tracker = ChargingStatsTracker()
    tracker.ingest(
        1000.0,
        "2026-11-19",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=20.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    tracker.ingest(
        2000.0,
        "2026-11-19",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=40.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    tracker.reset_from_start()
    fs = tracker.period_stats("from_start", "2026-11-19")
    assert fs == {
        "total_kwh": 0.0,
        "home_kwh": 0.0,
        "away_kwh": 0.0,
        "sessions_count": 0,
        "period_key": "from_start",
    }
    assert tracker.period_stats("today", "2026-11-19")["total_kwh"] == pytest.approx(
        4.0
    )
    assert tracker.period_stats("month", "2026-11-19")["total_kwh"] == pytest.approx(
        4.0
    )
    assert tracker.period_stats("year", "2026-11-19")["total_kwh"] == pytest.approx(4.0)

    restored = ChargingStatsTracker.from_dict(tracker.to_dict())
    assert restored.period_stats("today", "2026-11-19")["total_kwh"] == pytest.approx(
        4.0
    )

    corrupt = ChargingStatsTracker.from_dict(
        {
            "today_key": "bad-date",
            "today": {
                "total_kwh": float("nan"),
                "home_kwh": -5,
                "sessions_count": True,
            },
            "from_start": {
                "total_kwh": "inf",
                "home_kwh": "oops",
                "away_kwh": 1.5,
                "sessions_count": -2,
            },
            "daily_history": {
                "not-a-date": {"total_kwh": 10},
                "2026-11-19": {"total_kwh": -1},
            },
            "baseline": {"prev_ts": "bad", "prev_soc_pct": 150, "prev_power_kw": -3},
        }
    )
    assert corrupt.period_stats("today", "2026-11-19")["total_kwh"] == 0.0
    assert corrupt.period_stats("from_start", "2026-11-19")[
        "away_kwh"
    ] == pytest.approx(1.5)
    assert corrupt.period_stats("from_start", "2026-11-19")["total_kwh"] == 0.0
    assert (
        ChargingStatsTracker.from_dict(None).period_stats("from_start", "2026-11-19")[
            "total_kwh"
        ]
        == 0.0
    )


def test_unplugged_soc_drift_ignored():
    delta, reset_cont = compute_charge_delta_kwh(
        1000.0,
        0.0,
        50.0,
        100.0,
        False,
        now_ts=3000.0,
        power_kw=0.0,
        soc_pct=52.0,
        odo_km=100.0,
        charging=False,
        plugged=False,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert delta == 0.0
    assert reset_cont is False


def test_gap_recovered_session_counted():
    tracker = ChargingStatsTracker()
    tracker.ingest(
        1000.0,
        "2026-11-19",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=30.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    tracker.ingest(
        2800.0,
        "2026-11-19",
        power_kw=0.0,
        charge_state="0",
        plugged=True,
        soc_pct=50.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    stats = tracker.period_stats("today", "2026-11-19")
    assert stats["total_kwh"] == pytest.approx(3.68, rel=1e-4)
    assert stats["sessions_count"] == 1


def test_trapezoidal_requires_prev_charging_and_positive_dt():
    first, _ = compute_charge_delta_kwh(
        1000.0,
        2.0,
        30.0,
        100.0,
        False,
        now_ts=1120.0,
        power_kw=2.0,
        soc_pct=30.0,
        odo_km=100.0,
        charging=True,
        plugged=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert first == 0.0

    non_pos_dt, _ = compute_charge_delta_kwh(
        1000.0,
        2.0,
        30.0,
        100.0,
        True,
        now_ts=1000.0,
        power_kw=2.0,
        soc_pct=30.0,
        odo_km=100.0,
        charging=True,
        plugged=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert non_pos_dt == 0.0

    bad_soc, _ = compute_charge_delta_kwh(
        1000.0,
        0.0,
        30.0,
        100.0,
        True,
        now_ts=2000.0,
        power_kw=0.0,
        soc_pct=105.0,
        odo_km=100.0,
        charging=False,
        plugged=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert bad_soc == 0.0

    bad_neg_soc, _ = compute_charge_delta_kwh(
        1000.0,
        0.0,
        -2.0,
        100.0,
        True,
        now_ts=2000.0,
        power_kw=0.0,
        soc_pct=20.0,
        odo_km=100.0,
        charging=False,
        plugged=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert bad_neg_soc == 0.0

    bad_cap, _ = compute_charge_delta_kwh(
        1000.0,
        2.0,
        30.0,
        100.0,
        True,
        now_ts=1120.0,
        power_kw=2.0,
        soc_pct=40.0,
        odo_km=100.0,
        charging=True,
        plugged=True,
        degraded_battery=False,
        battery_capacity_kwh=0.0,
    )
    assert bad_cap == 0.0


def test_fields_only_power_none_preserves_trapezoid():
    # (a) Active charging + fields-only MQTT push keeps trapezoid anchor intact
    tracker = ChargingStatsTracker()
    tracker.ingest(
        1000.0,
        "2026-11-19",
        power_kw=2.0,
        charge_state="1",
        plugged=True,
        soc_pct=30.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    tracker.ingest(
        1030.0,
        "2026-11-19",
        power_kw=None,
        charge_state="1",
        plugged=True,
        soc_pct=None,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert tracker._prev_ts == 1000.0
    assert tracker._prev_power_kw == 2.0
    assert tracker._prev_charging is True

    tracker.ingest(
        1120.0,
        "2026-11-19",
        power_kw=2.0,
        charge_state="1",
        plugged=True,
        soc_pct=31.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert tracker.period_stats("today", "2026-11-19")["total_kwh"] == pytest.approx(
        2.0 * 120.0 / 3600.0, abs=1e-3
    )

    # (a2) power_kw=None over a long >300s gap reconciles SoC cleanly without double counting
    tracker_gap = ChargingStatsTracker()
    tracker_gap.ingest(
        1000.0,
        "2026-11-19",
        power_kw=2.0,
        charge_state="1",
        plugged=True,
        soc_pct=30.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    tracker_gap.ingest(
        2000.0,
        "2026-11-19",
        power_kw=None,
        charge_state="1",
        plugged=True,
        soc_pct=50.0,
        odometer=100.0,
        in_home_zone=True,
        degraded_battery=False,
        battery_capacity_kwh=18.4,
    )
    assert tracker_gap.period_stats("today", "2026-11-19")[
        "total_kwh"
    ] == pytest.approx(3.68, rel=1e-4)

    # (b) Unplug / charge_state == 0 / odometer advance resets continuity
    for stop_kwargs in (
        {"plugged": False, "charge_state": None, "odometer": 100.0},
        {"plugged": True, "charge_state": "0", "odometer": 100.0},
        {"plugged": True, "charge_state": "1", "odometer": 100.5},
    ):
        tr = ChargingStatsTracker()
        tr.ingest(
            1000.0,
            "2026-11-19",
            power_kw=3.0,
            charge_state="1",
            plugged=True,
            soc_pct=30.0,
            odometer=100.0,
            in_home_zone=True,
            degraded_battery=False,
            battery_capacity_kwh=18.4,
        )
        tr.ingest(
            1030.0,
            "2026-11-19",
            power_kw=None,
            soc_pct=None,
            in_home_zone=True,
            degraded_battery=False,
            battery_capacity_kwh=18.4,
            **stop_kwargs,
        )
        assert tr._prev_charging is False
        assert tr._prev_power_kw == 0.0
        if stop_kwargs["odometer"] > 100.1:
            assert tr._prev_soc_pct is None
        tr.ingest(
            1120.0,
            "2026-11-19",
            power_kw=3.0,
            charge_state="1",
            plugged=True,
            soc_pct=30.0,
            odometer=stop_kwargs["odometer"],
            in_home_zone=True,
            degraded_battery=False,
            battery_capacity_kwh=18.4,
        )
        assert tr.period_stats("today", "2026-11-19")["total_kwh"] == 0.0


async def test_coordinator_charging_store_load_delay_save_flush_and_reset(
    hass, hass_storage, monkeypatch
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_VIN: "VINCHG01"},
        options={CONF_BATTERY_CAPACITY_KWH: 20.0},
    )
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)

    # Corrupt Store load (OSError/JSONDecodeError) must fall back to empty tracker without raising
    orig_load = coord._charging_store.async_load

    async def _broken_load():
        raise json.JSONDecodeError("bad", "{broken-json", 1)

    monkeypatch.setattr(coord._charging_store, "async_load", _broken_load)
    await coord.async_load_charging_stats()
    assert coord.charging_stats("from_start")["total_kwh"] == 0.0
    monkeypatch.setattr(coord._charging_store, "async_load", orig_load)

    # Verify async_delay_save is invoked OUTSIDE _charging_lock (no deadlock on immediate snapshot_fn)
    snapshots = []

    def _spy_delay_save(snapshot_fn, delay):
        assert not coord._charging_lock.locked()
        snapshots.append((delay, snapshot_fn()))

    monkeypatch.setattr(coord._charging_store, "async_delay_save", _spy_delay_save)

    t0 = dt.datetime(2026, 11, 19, 10, 0, 0, tzinfo=dt.UTC)
    t1 = t0 + dt.timedelta(seconds=120)
    current_now = [t0]
    monkeypatch.setattr(
        "custom_components.lepas.coordinator.dt_util.utcnow", lambda: current_now[0]
    )
    monkeypatch.setattr(
        "custom_components.lepas.entity.in_zona_casa", lambda _h, _p: True
    )

    coord._apply_update(
        {
            "realtime": {
                "chargingPower": "3.0",
                "chargeState": "1",
                "chargeGunState": "1",
                "dumpEnergy": "40",
                "odometer": "1000",
                "pureElectricRange": "60",
            },
            "fields": {"chargeGunState": "1"},
            "position": {"lat": 45.0, "lon": 9.0},
        }
    )
    current_now[0] = t1
    coord._apply_update(
        {
            "realtime": {
                "chargingPower": "3.0",
                "chargeState": "1",
                "chargeGunState": "1",
                "dumpEnergy": "41",
                "odometer": "1000",
                "pureElectricRange": "62",
            },
            "fields": {"chargeGunState": "1"},
            "position": {"lat": 45.0, "lon": 9.0},
        }
    )
    assert len(snapshots) == 2
    assert snapshots[-1][0] == 30
    assert snapshots[-1][1]["from_start"]["total_kwh"] == pytest.approx(0.1, rel=1e-4)

    await coord.async_flush_charging_stats()
    persisted = hass_storage[coord._charging_store.key]["data"]
    assert persisted["from_start"]["total_kwh"] == pytest.approx(0.1, rel=1e-4)

    coord2 = LepasCoordinator(hass, entry)
    await coord2.async_load_charging_stats()
    monkeypatch.setattr(
        "custom_components.lepas.coordinator.dt_util.utcnow", lambda: t1
    )
    assert coord2.charging_stats("today")["total_kwh"] == pytest.approx(0.1, rel=1e-4)
    assert coord2.charging_stats("from_start")["total_kwh"] == pytest.approx(
        0.1, rel=1e-4
    )

    await coord2.async_reset_charging_from_start()
    assert coord2.charging_stats("from_start")["total_kwh"] == 0.0
    assert coord2.charging_stats("today")["total_kwh"] == pytest.approx(0.1, rel=1e-4)


async def test_coordinator_apply_update_noop_and_fields_only_precedence(
    hass, monkeypatch
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_VIN: "VINCHG02"},
        options={CONF_BATTERY_CAPACITY_KWH: 20.0},
    )
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    delay_calls = []
    monkeypatch.setattr(
        coord._charging_store, "async_delay_save", lambda fn, d: delay_calls.append(d)
    )
    monkeypatch.setattr(
        "custom_components.lepas.entity.in_zona_casa", lambda _h, _p: True
    )

    t0 = dt.datetime(2026, 11, 19, 10, 0, 0, tzinfo=dt.UTC)
    monkeypatch.setattr(
        "custom_components.lepas.coordinator.dt_util.utcnow", lambda: t0
    )

    # Non-telemetry patches must be strict no-ops
    coord._apply_update({"cmd_status": "ok"})
    coord._apply_update({"position": {"lat": 45.0, "lon": 9.0}})
    assert delay_calls == []
    assert coord._charging_tracker._prev_ts is None

    # Active realtime frame starts session
    coord._apply_update(
        {
            "realtime": {
                "chargingPower": "2.0",
                "chargeState": "1",
                "chargeGunState": "1",
                "dumpEnergy": "40",
                "odometer": "500",
                "pureElectricRange": "60",
            },
            "fields": {"chargeGunState": "1"},
        }
    )
    assert len(delay_calls) == 1

    # Fields-only push with stale realtime still in self.data must NOT reuse stale chargingPower,
    # and must respect AB-LEP-014 precedence msg_fields > fields
    t_push = t0 + dt.timedelta(seconds=60)
    monkeypatch.setattr(
        "custom_components.lepas.coordinator.dt_util.utcnow", lambda: t_push
    )
    coord._apply_update(
        {
            "fields": {"chargeGunState": "1", "chargeState": "1"},
            "msg_fields": {"chargeGunState": "0", "chargeState": "0"},
        }
    )
    assert coord._charging_tracker._prev_charging is False
    assert coord._charging_tracker._prev_power_kw == 0.0

    # Subsequent realtime frame at t0+120s must NOT integrate across the stopped push
    t2 = t0 + dt.timedelta(seconds=120)
    monkeypatch.setattr(
        "custom_components.lepas.coordinator.dt_util.utcnow", lambda: t2
    )
    coord._apply_update(
        {
            "realtime": {
                "chargingPower": "2.0",
                "chargeState": "1",
                "chargeGunState": "1",
                "dumpEnergy": "40",
                "odometer": "500",
                "pureElectricRange": "60",
            },
            "fields": {"chargeGunState": "1"},
        }
    )
    assert coord.charging_stats("today")["total_kwh"] == 0.0


async def test_coordinator_mocked_hass_states_safe(monkeypatch):
    mock_hass = MagicMock()
    mock_hass.data = {}
    mock_hass.config.path = lambda p: f"/tmp/{p}"
    mock_hass.states.get.return_value = MagicMock()
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_VIN: "VINMOCK01"},
        options={CONF_BATTERY_CAPACITY_KWH: 20.0},
    )
    coord = LepasCoordinator(mock_hass, entry)
    monkeypatch.setattr(coord, "async_set_updated_data", lambda _d: None)
    monkeypatch.setattr(coord._charging_store, "async_delay_save", lambda _fn, _d: None)

    t0 = dt.datetime(2026, 11, 19, 10, 0, 0, tzinfo=dt.UTC)
    t1 = t0 + dt.timedelta(seconds=120)
    current_now = [t0]
    monkeypatch.setattr(
        "custom_components.lepas.coordinator.dt_util.utcnow", lambda: current_now[0]
    )

    coord._apply_update(
        {
            "realtime": {
                "chargingPower": "3.0",
                "chargeState": "1",
                "chargeGunState": "1",
                "dumpEnergy": "30",
                "odometer": "100",
                "pureElectricRange": "50",
            },
            "fields": {"chargeGunState": "1"},
            "position": {"lat": 45.0, "lon": 9.0},
        }
    )
    current_now[0] = t1
    coord._apply_update(
        {
            "realtime": {
                "chargingPower": "3.0",
                "chargeState": "1",
                "chargeGunState": "1",
                "dumpEnergy": "31",
                "odometer": "100",
                "pureElectricRange": "51",
            },
            "fields": {"chargeGunState": "1"},
            "position": {"lat": 45.0, "lon": 9.0},
        }
    )
    stats = coord.charging_stats("today")
    assert stats["total_kwh"] == pytest.approx(0.1, rel=1e-4)
    assert stats["home_kwh"] == 0.0
    assert stats["away_kwh"] == 0.0


async def test_charging_stats_sensors_and_reset_button(
    hass, integrazione_avviata, monkeypatch
):
    coord = next(iter(hass.data[DOMAIN].values()))
    hass.states.async_set(
        "zone.home",
        "0",
        {"latitude": 45.0, "longitude": 9.0, "radius": 100},
    )
    assert coord.poll_enabled is False

    # Sensors remain available even when poll_enabled is False
    for suffix in ("today", "month", "year", "from_start"):
        st = hass.states.get(f"sensor.lepas_charging_energy_{suffix}")
        assert st is not None
        assert st.state not in ("unavailable", "unknown")
        assert st.attributes["device_class"] == "energy"
        assert st.attributes["state_class"] == "total"
        assert st.attributes["unit_of_measurement"] == "kWh"

    t0 = dt.datetime(2026, 11, 19, 12, 0, 0, tzinfo=dt.UTC)
    t1 = t0 + dt.timedelta(seconds=CHARGE_ENERGY_MAX_GAP + 60)
    current_now = [t0]
    monkeypatch.setattr(
        "custom_components.lepas.coordinator.dt_util.utcnow", lambda: current_now[0]
    )
    monkeypatch.setattr(
        "custom_components.lepas.sensor.dt_util.utcnow", lambda: current_now[0]
    )

    coord._on_probe_data(
        {
            "chargingPower": "0",
            "chargeState": "0",
            "chargeGunState": "1",
            "dumpEnergy": "30",
            "odometer": "500",
            "pureElectricRange": "50",
            "lat": 45.0,
            "lon": 9.0,
        }
    )
    await hass.async_block_till_done()
    current_now[0] = t1
    coord._on_probe_data(
        {
            "chargingPower": "0",
            "chargeState": "0",
            "chargeGunState": "1",
            "dumpEnergy": "50",
            "odometer": "500",
            "pureElectricRange": "80",
            "lat": 45.0,
            "lon": 9.0,
        }
    )
    await hass.async_block_till_done()

    today_st = hass.states.get("sensor.lepas_charging_energy_today")
    year_st = hass.states.get("sensor.lepas_charging_energy_year")
    fs_st = hass.states.get("sensor.lepas_charging_energy_from_start")
    assert float(today_st.state) == pytest.approx(3.68, rel=1e-3)
    assert today_st.attributes["home_kwh"] == pytest.approx(3.68, rel=1e-3)
    assert today_st.attributes["away_kwh"] == 0.0
    assert today_st.attributes["sessions_count"] == 1
    assert isinstance(today_st.attributes["daily_series"], list)
    assert len(today_st.attributes["daily_series"]) == 1
    assert isinstance(year_st.attributes["monthly_series"], list)
    assert float(fs_st.state) == pytest.approx(3.68, rel=1e-3)

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.lepas_reset_charging_from_start"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert (
        float(hass.states.get("sensor.lepas_charging_energy_from_start").state) == 0.0
    )
    assert float(
        hass.states.get("sensor.lepas_charging_energy_today").state
    ) == pytest.approx(3.68, rel=1e-3)
    assert float(
        hass.states.get("sensor.lepas_charging_energy_month").state
    ) == pytest.approx(3.68, rel=1e-3)
    assert float(
        hass.states.get("sensor.lepas_charging_energy_year").state
    ) == pytest.approx(3.68, rel=1e-3)
