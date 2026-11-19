"""Unit and Home Assistant integration tests for EV / Hybrid consumption sensors."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lepas.const import (
    CONF_BATTERY_CAPACITY_KWH,
    CONF_VIN,
    DATA_POWER_TYPE,
    DEFAULT_BATTERY_CAPACITY_KWH,
    DOMAIN,
)
from custom_components.lepas.consumption import (
    WINDOW_1000_KM,
    ConsumptionTracker,
    is_degraded_battery_frame,
)
from custom_components.lepas.coordinator import LepasCoordinator


def test_ev_and_hybrid_split_and_refuel_recharge_filtering():
    t = ConsumptionTracker()
    assert (
        t.ingest(
            1000.0,
            80.0,
            30.0,
            engine_on=False,
            charging_or_plugged=False,
            degraded_battery=False,
            battery_capacity_kwh=18.4,
        )
        is True
    )
    assert (
        t.ingest(
            1010.0,
            70.0,
            30.0,
            engine_on=False,
            charging_or_plugged=False,
            degraded_battery=False,
            battery_capacity_kwh=18.4,
        )
        is True
    )
    ev_100 = t.window_stats("ev", 100.0)
    assert ev_100["sampled_km"] == pytest.approx(10.0)
    assert ev_100["value"] == pytest.approx(18.4, rel=1e-3)

    assert (
        t.ingest(
            1010.0,
            90.0,
            30.0,
            engine_on=False,
            charging_or_plugged=True,
            degraded_battery=False,
            battery_capacity_kwh=18.4,
        )
        is True
    )
    assert (
        t.ingest(
            1010.0,
            90.0,
            45.0,
            engine_on=False,
            charging_or_plugged=False,
            degraded_battery=False,
            battery_capacity_kwh=18.4,
        )
        is True
    )

    assert (
        t.ingest(
            1035.0,
            85.0,
            43.0,
            engine_on=True,
            charging_or_plugged=False,
            degraded_battery=False,
            battery_capacity_kwh=18.4,
        )
        is True
    )
    hyb_100 = t.window_stats("hev", 100.0)
    assert hyb_100["sampled_km"] == pytest.approx(25.0)
    assert hyb_100["value"] == pytest.approx(8.0, rel=1e-3)
    assert hyb_100["electric_kwh_100km"] == pytest.approx(3.68, rel=1e-3)


def test_minimum_thresholds_gap_guard_degraded_and_window_trim():
    t = ConsumptionTracker()
    t.ingest(
        100.0,
        80.0,
        20.0,
        engine_on=False,
        charging_or_plugged=False,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    t.ingest(
        104.0,
        76.0,
        20.0,
        engine_on=False,
        charging_or_plugged=False,
        degraded_battery=False,
        battery_capacity_kwh=20.0,
    )
    assert t.window_stats("ev", 100.0)["value"] is None
    assert (
        t.ingest(
            108.0,
            97.0,
            20.0,
            engine_on=False,
            charging_or_plugged=False,
            degraded_battery=True,
            battery_capacity_kwh=20.0,
        )
        is False
    )
    assert (
        t.ingest(
            200.0,
            50.0,
            15.0,
            engine_on=False,
            charging_or_plugged=False,
            degraded_battery=False,
            battery_capacity_kwh=20.0,
        )
        is True
    )
    assert t.window_stats("ev", 100.0)["sampled_km"] == pytest.approx(4.0)

    t2 = ConsumptionTracker()
    t2.ingest(
        1000.0,
        90.0,
        20.0,
        engine_on=False,
        charging_or_plugged=False,
        degraded_battery=False,
        battery_capacity_kwh=100.0,
    )
    t2.ingest(
        1030.0,
        87.0,
        20.0,
        engine_on=False,
        charging_or_plugged=False,
        degraded_battery=False,
        battery_capacity_kwh=100.0,
    )
    t2.ingest(
        1060.0,
        84.0,
        20.0,
        engine_on=False,
        charging_or_plugged=False,
        degraded_battery=False,
        battery_capacity_kwh=100.0,
    )
    t2.ingest(
        1090.0,
        78.0,
        20.0,
        engine_on=False,
        charging_or_plugged=False,
        degraded_battery=False,
        battery_capacity_kwh=100.0,
    )
    t2.ingest(
        1120.0,
        72.0,
        20.0,
        engine_on=False,
        charging_or_plugged=False,
        degraded_battery=False,
        battery_capacity_kwh=100.0,
    )
    assert t2.window_stats("ev", 100.0)["value"] == pytest.approx(16.0, rel=1e-3)
    assert t2.window_stats("ev", None)["value"] == pytest.approx(15.0, rel=1e-3)

    t2.reset_from_start()
    assert t2.window_stats("ev", None)["value"] is None
    assert t2.window_stats("ev", 100.0)["value"] == pytest.approx(16.0, rel=1e-3)

    restored = ConsumptionTracker.from_dict(t2.to_dict())
    assert restored.window_stats("ev", 100.0)["value"] == pytest.approx(16.0, rel=1e-3)
    assert is_degraded_battery_frame({"pureElectricRange": 0, "dumpEnergy": 97}) is True


def test_bev_none_fuel_parked_idle_and_negative_odo_anomaly():
    t = ConsumptionTracker()
    assert (
        t.ingest(
            100.0,
            80.0,
            None,
            engine_on=False,
            charging_or_plugged=False,
            degraded_battery=False,
            battery_capacity_kwh=50.0,
        )
        is True
    )
    assert (
        t.ingest(
            100.0,
            80.0,
            None,
            engine_on=False,
            charging_or_plugged=False,
            degraded_battery=False,
            battery_capacity_kwh=50.0,
        )
        is False
    )
    assert (
        t.ingest(
            120.0,
            72.0,
            None,
            engine_on=False,
            charging_or_plugged=False,
            degraded_battery=False,
            battery_capacity_kwh=50.0,
        )
        is True
    )
    assert t.window_stats("ev", 100.0)["value"] == pytest.approx(20.0, rel=1e-3)
    assert (
        t.ingest(
            90.0,
            70.0,
            None,
            engine_on=False,
            charging_or_plugged=False,
            degraded_battery=False,
            battery_capacity_kwh=50.0,
        )
        is True
    )
    assert t.window_stats("ev", 100.0)["sampled_km"] == pytest.approx(20.0)
    assert t.window_stats("ev", 100.0)["value"] == pytest.approx(20.0, rel=1e-3)


def test_1000km_queue_cap_hev_net_electric_and_malformed_dict():
    t = ConsumptionTracker()
    odo = 1000.0
    t.ingest(
        odo,
        90.0,
        40.0,
        engine_on=False,
        charging_or_plugged=False,
        degraded_battery=False,
        battery_capacity_kwh=100.0,
    )
    # 25 steps of 50 km = 1250 km total; rolling queue must cap at 1000 km while from_start keeps 1250 km.
    for _ in range(25):
        odo += 50.0
        t.ingest(
            odo,
            85.0,
            40.0,
            engine_on=False,
            charging_or_plugged=False,
            degraded_battery=False,
            battery_capacity_kwh=100.0,
        )
        # Recharge stationary so SOC stays healthy without polluting driving distance.
        t.ingest(
            odo,
            90.0,
            40.0,
            engine_on=False,
            charging_or_plugged=True,
            degraded_battery=False,
            battery_capacity_kwh=100.0,
        )

    stats_1000 = t.window_stats("ev", WINDOW_1000_KM)
    stats_fs = t.window_stats("ev", None)
    assert stats_1000["sampled_km"] == pytest.approx(1000.0)
    assert stats_1000["progress_pct"] == pytest.approx(100.0)
    assert stats_fs["sampled_km"] == pytest.approx(1250.0)
    assert stats_fs["progress_pct"] is None

    # HEV engine charging battery yields negative net electric_kwh_100km.
    t.ingest(
        odo + 20.0,
        95.0,
        38.0,
        engine_on=True,
        charging_or_plugged=False,
        degraded_battery=False,
        battery_capacity_kwh=100.0,
    )
    hev = t.window_stats("hev", 100.0)
    assert hev["value"] == pytest.approx(10.0, rel=1e-3)
    assert hev["electric_kwh_100km"] == pytest.approx(-25.0, rel=1e-3)

    # Malformed persisted payload must gracefully yield empty tracker.
    bad = ConsumptionTracker.from_dict(
        {
            "last_odo": "nan",
            "last_soc": -5,
            "ev_segments": ["bad", {"km": -1, "kwh": 2}, {"km": 10, "kwh": "inf"}],
            "from_start": {"ev_km": "oops"},
        }
    )
    assert bad.window_stats("ev", 100.0)["value"] is None


async def test_options_flow_persists_battery_capacity(hass):
    entry = MockConfigEntry(domain=DOMAIN, version=2, data={"vin": "TESTVIN"}, options={})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "poll_normal_min": 60,
            "poll_charging_min": 30,
            "vehicle_name": "Lepas L8",
            CONF_BATTERY_CAPACITY_KWH: 19.2,
        },
    )
    assert result2["type"] == "create_entry"
    assert result2["data"][CONF_BATTERY_CAPACITY_KWH] == pytest.approx(19.2)
    assert DEFAULT_BATTERY_CAPACITY_KWH == 18.4


async def test_coordinator_ingests_realtime_and_persists_store(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_VIN: "VINCONS01"},
        options={CONF_BATTERY_CAPACITY_KWH: 20.0},
    )
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    await coord.async_load_consumption()

    coord._on_probe_data(
        {
            "odometer": 500,
            "dumpEnergy": 80,
            "oilSurplus": 30,
            "pureElectricRange": 100,
            "engineState": 0,
            "chargeState": 0,
            "chargeGunState": 0,
        }
    )
    coord._on_probe_data(
        {
            "odometer": 510,
            "dumpEnergy": 70,
            "oilSurplus": 30,
            "pureElectricRange": 85,
            "engineState": 0,
            "chargeState": 0,
            "chargeGunState": 0,
        }
    )
    stats = coord.consumption_stats("ev", 100.0)
    assert stats["value"] == pytest.approx(20.0, rel=1e-3)

    await coord.async_flush_consumption()
    coord2 = LepasCoordinator(hass, entry)
    await coord2.async_load_consumption()
    assert coord2.consumption_stats("ev", 100.0)["value"] == pytest.approx(20.0, rel=1e-3)

    await coord2.async_reset_consumption_from_start()
    assert coord2.consumption_stats("ev", None)["value"] is None
    assert coord2.consumption_stats("ev", 100.0)["value"] == pytest.approx(20.0, rel=1e-3)


async def test_coordinator_corrupt_store_and_unload_flush(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_VIN: "VINCORRUPT1"},
        options={CONF_BATTERY_CAPACITY_KWH: 18.4},
    )
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    store_path = Path(coord._consumption_store.path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text("{corrupt-json", encoding="utf-8")

    # Corrupt Store JSON must not break boot; falls back to fresh tracker.
    await coord.async_load_consumption()
    assert coord.consumption_stats("ev", 100.0)["value"] is None

    with (
        patch.object(LepasCoordinator, "_connect_car"),
        patch.object(LepasCoordinator, "async_provision_certs", return_value=(True, "ok")),
        patch.object(LepasCoordinator, "async_check_session"),
        patch.object(LepasCoordinator, "async_start_keepalive"),
        patch.object(LepasCoordinator, "async_start_telemetry_poll"),
        patch.object(LepasCoordinator, "async_start_drive_watch"),
        patch.object(LepasCoordinator, "async_ensure_vehicle_identity"),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        live_coord = hass.data[DOMAIN][entry.entry_id]
        live_coord._on_probe_data(
            {
                "odometer": 100,
                "dumpEnergy": 80,
                "pureElectricRange": 100,
                "engineState": 0,
                "chargeState": 0,
                "chargeGunState": 0,
            }
        )
        live_coord._on_probe_data(
            {
                "odometer": 110,
                "dumpEnergy": 70,
                "pureElectricRange": 85,
                "engineState": 0,
                "chargeState": 0,
                "chargeGunState": 0,
            }
        )
        await hass.async_block_till_done()
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    reloaded = LepasCoordinator(hass, entry)
    await reloaded.async_load_consumption()
    assert reloaded.consumption_stats("ev", 100.0)["value"] == pytest.approx(18.4, rel=1e-3)


async def test_consumption_sensors_and_reset_button_entities(hass, integrazione_avviata):
    coord = next(iter(hass.data[DOMAIN].values()))
    coord._on_probe_data(
        {
            "odometer": 1000,
            "dumpEnergy": 80,
            "oilSurplus": 30,
            "pureElectricRange": 100,
            "engineState": 0,
            "chargeState": 0,
            "chargeGunState": 0,
        }
    )
    coord._on_probe_data(
        {
            "odometer": 1010,
            "dumpEnergy": 70,
            "oilSurplus": 30,
            "pureElectricRange": 85,
            "engineState": 0,
            "chargeState": 0,
            "chargeGunState": 0,
        }
    )
    coord._on_probe_data(
        {
            "odometer": 1030,
            "dumpEnergy": 65,
            "oilSurplus": 28,
            "pureElectricRange": 80,
            "engineState": 1,
            "chargeState": 0,
            "chargeGunState": 0,
        }
    )
    await hass.async_block_till_done()

    ev_100 = hass.states.get("sensor.lepas_ev_consumption_100km")
    assert ev_100 is not None and float(ev_100.state) == pytest.approx(18.4, rel=1e-2)
    assert ev_100.attributes["unit_of_measurement"] == "kWh/100 km"
    assert ev_100.attributes["state_class"] == "measurement"
    assert ev_100.attributes["sampled_km"] == pytest.approx(10.0)
    assert ev_100.attributes["window_target_km"] == pytest.approx(100.0)
    assert ev_100.attributes["progress_pct"] == pytest.approx(10.0)

    hyb_100 = hass.states.get("sensor.lepas_hybrid_consumption_100km")
    assert hyb_100 is not None and float(hyb_100.state) == pytest.approx(10.0, rel=1e-2)
    assert hyb_100.attributes["unit_of_measurement"] == "L/100 km"
    assert "electric_consumption_kwh_100km" in hyb_100.attributes

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": "button.lepas_reset_consumption_from_start"},
        blocking=True,
    )
    assert hass.states.get("sensor.lepas_ev_consumption_from_start").state == "unknown"
    assert hass.states.get("sensor.lepas_hybrid_consumption_from_start").state == "unknown"
    assert float(hass.states.get("sensor.lepas_ev_consumption_100km").state) == pytest.approx(
        18.4, rel=1e-2
    )


async def test_bev_hides_hybrid_consumption_sensors(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_VIN: "VINBEV01", DATA_POWER_TYPE: 0},
    )
    entry.add_to_hass(hass)
    with (
        patch("custom_components.lepas.coordinator.LepasCoordinator._connect_car"),
        patch(
            "custom_components.lepas.coordinator.LepasCoordinator.async_provision_certs",
            return_value=(True, "ok"),
        ),
        patch("custom_components.lepas.coordinator.LepasCoordinator.async_check_session"),
        patch("custom_components.lepas.coordinator.LepasCoordinator.async_start_keepalive"),
        patch("custom_components.lepas.coordinator.LepasCoordinator.async_start_telemetry_poll"),
        patch("custom_components.lepas.coordinator.LepasCoordinator.async_start_drive_watch"),
        patch("custom_components.lepas.coordinator.LepasCoordinator.async_ensure_vehicle_identity"),
    ):
        try:
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert hass.states.get("sensor.lepas_ev_consumption_100km") is not None
            assert hass.states.get("button.lepas_reset_consumption_from_start") is not None
            for hyb in ("100km", "1000km", "from_start"):
                assert hass.states.get(f"sensor.lepas_hybrid_consumption_{hyb}") is None
        finally:
            if entry.entry_id in hass.data.get(DOMAIN, {}):
                await hass.config_entries.async_unload(entry.entry_id)
                await hass.async_block_till_done()
