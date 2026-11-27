"""Tests for GPS coordinate validation, missing-GPS fallback realignment, and cooldown guards."""
from __future__ import annotations

import asyncio
import json
import time
from types import SimpleNamespace

import fixtures as FX
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lepas.const import CONF_VIN, DOMAIN
from custom_components.lepas.coordinator import LepasCoordinator, _extract_geo
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
    entry_id: str,
    patch_probe: bool = True,
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
    if patch_probe:
        monkeypatch.setattr(coord, "async_probe", noop_probe)
    monkeypatch.setattr(coord._charging_store, "async_delay_save", lambda _fn, _d: None)
    monkeypatch.setattr(coord._consumption_store, "async_delay_save", lambda _fn, _d: None)
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


async def test_extract_geo_accepts_latitude_longitude_and_clears_stale_short_keys(
    hass: HomeAssistant, monkeypatch
) -> None:
    long_geo = _extract_geo(
        {
            "latitude": str(HOME_LAT),
            "longitude": str(HOME_LON),
            "lat": "",
            "lon": None,
            "altitude": "110",
        }
    )
    assert long_geo == {
        "latitude": str(HOME_LAT),
        "longitude": str(HOME_LON),
        "altitude": "110",
    }

    short_geo = _extract_geo(
        {
            "lat": HOME_LAT,
            "lon": HOME_LON,
            "latitude": "99",
            "longitude": "99",
        }
    )
    assert short_geo == {"lat": HOME_LAT, "lon": HOME_LON}
    assert _extract_geo({"lat": 0.0, "lon": 0.0}) is None
    assert _extract_geo({"lat": True, "lon": HOME_LON}) is None

    _entry, coord, _sent = _make_coord(hass, monkeypatch, entry_id="extract_geo_clear")
    coord._on_probe_data({"lat": str(AWAY_LAT), "lon": str(AWAY_LON), "odometer": "5000"})
    await hass.async_block_till_done()
    assert coord.position == {"lat": str(AWAY_LAT), "lon": str(AWAY_LON)}

    coord._on_probe_data(
        {"latitude": str(HOME_LAT), "longitude": str(HOME_LON), "odometer": "5005"}
    )
    await hass.async_block_till_done()
    assert coord.position == {"latitude": str(HOME_LAT), "longitude": str(HOME_LON)}
    assert "lat" not in coord.position
    assert "lon" not in coord.position
    assert coord.data["position"] == {"latitude": str(HOME_LAT), "longitude": str(HOME_LON)}
    assert coord._last_pos_fix_mono > 0.0
    coord.async_stop()


async def test_drive_home_without_gps_realigns_on_park_and_suppresses_false_away_park(
    hass: HomeAssistant, monkeypatch
) -> None:
    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="drive_home_no_gps")
    coord.poll_enabled = True
    coord.set_charge_window_mode("fixed", sync_charge=False)

    _send_1301(coord, AWAY_LAT, AWAY_LON)
    await hass.async_block_till_done()

    # Driving probe lacks GPS -> sets _trip_needs_gps_realign and car_in_use=True
    coord._on_probe_data(
        {
            "hVoltageState": "1",
            "engineState": "1",
            "odometer": "10010",
            "vehicleSpeed": "45",
        }
    )
    await hass.async_block_till_done()
    assert coord.car_in_use is True
    assert coord._trip_needs_gps_realign is True

    sveglia_calls = 0

    async def fake_sveglia() -> None:
        nonlocal sveglia_calls
        sveglia_calls += 1
        _send_1301(coord, HOME_LAT, HOME_LON)

    monkeypatch.setattr(coord, "async_assicura_sveglia", fake_sveglia)

    # Park at home while cached position is still AWAY -> away_park must wait for realignment
    coord._on_probe_data(
        {
            "hVoltageState": "0",
            "engineState": "0",
            "vehicleSpeed": "0",
            "odometer": "10010",
            "chargeGunState": "0",
            "chargeAppointPlans": [{"switchStatus": "1", "startTime": "1320"}],
        }
    )
    assert sent == []
    await hass.async_block_till_done(wait_background_tasks=True)

    assert sveglia_calls == 1
    assert coord.position["lat"] == str(HOME_LAT)
    assert coord._trip_needs_gps_realign is False
    assert sent == []
    coord.async_stop()


async def test_drive_away_without_gps_realigns_on_park_then_fires_away_park(
    hass: HomeAssistant, monkeypatch
) -> None:
    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="drive_away_no_gps")
    coord.poll_enabled = True
    coord.set_charge_window_mode("fixed", sync_charge=False)

    _send_1301(coord, HOME_LAT, HOME_LON)
    await hass.async_block_till_done()

    coord._on_probe_data(
        {
            "hVoltageState": "1",
            "engineState": "1",
            "odometer": "10025",
            "vehicleSpeed": "60",
        }
    )
    await hass.async_block_till_done()
    assert coord._trip_needs_gps_realign is True

    sveglia_calls = 0

    async def fake_sveglia() -> None:
        nonlocal sveglia_calls
        sveglia_calls += 1
        _send_1301(coord, AWAY_LAT, AWAY_LON)

    monkeypatch.setattr(coord, "async_assicura_sveglia", fake_sveglia)

    coord._on_probe_data(
        {
            "hVoltageState": "0",
            "engineState": "0",
            "vehicleSpeed": "0",
            "odometer": "10025",
            "chargeGunState": "0",
            "chargeAppointPlans": [{"switchStatus": "1", "startTime": "1320"}],
        }
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    assert sveglia_calls == 1
    assert len(sent) == 1
    assert sent[0][0] == "ricarica_prog_off"
    assert coord._trip_needs_gps_realign is False
    coord.async_stop()


async def test_fast_path_1301_race_reads_self_position_before_apply_update(
    hass: HomeAssistant, monkeypatch
) -> None:
    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="fast_path_race")
    coord.poll_enabled = True
    coord.set_charge_window_mode("fixed", sync_charge=False)

    _send_1301(coord, AWAY_LAT, AWAY_LON)
    await hass.async_block_till_done()

    coord._on_probe_data(
        {
            "hVoltageState": "1",
            "engineState": "1",
            "odometer": "10040",
            "vehicleSpeed": "30",
        }
    )
    await hass.async_block_till_done()

    async def fake_sveglia() -> None:
        # Update self.position and _last_pos_fix_mono immediately; _apply_update runs later on loop
        _send_1301(coord, HOME_LAT, HOME_LON)

    monkeypatch.setattr(coord, "async_assicura_sveglia", fake_sveglia)

    orig_in_home = coord._safe_in_home_zone
    observations: list[tuple[str | None, str | None, bool | None]] = []

    def spy_in_home(pos: dict | None) -> bool | None:
        res = orig_in_home(pos)
        if (
            coord._gps_realign_task is not None
            and asyncio.current_task() is coord._gps_realign_task
        ):
            data_pos = (coord.data or {}).get("position") or {}
            observations.append(
                (
                    pos.get("lat") if isinstance(pos, dict) else None,
                    data_pos.get("lat") if isinstance(data_pos, dict) else None,
                    res,
                )
            )
        return res

    monkeypatch.setattr(coord, "_safe_in_home_zone", spy_in_home)

    coord._on_probe_data(
        {
            "hVoltageState": "0",
            "engineState": "0",
            "vehicleSpeed": "0",
            "odometer": "10025",
            "chargeGunState": "0",
            "chargeAppointPlans": [{"switchStatus": "1", "startTime": "1320"}],
        }
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    assert observations == [(str(HOME_LAT), str(AWAY_LAT), True)]
    assert sent == []
    coord.async_stop()


async def test_plugin_while_realign_in_flight_merges_pending_and_arms_home_debounce(
    hass: HomeAssistant, monkeypatch
) -> None:
    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="plugin_in_flight")
    coord.poll_enabled = True
    coord.set_charge_window_mode("fixed", sync_charge=False)

    _send_1301(coord, AWAY_LAT, AWAY_LON)
    await hass.async_block_till_done()

    coord._on_probe_data(
        {
            "hVoltageState": "1",
            "engineState": "1",
            "odometer": "10055",
            "vehicleSpeed": "40",
        }
    )
    await hass.async_block_till_done()

    sveglia_started = asyncio.Event()
    release_sveglia = asyncio.Event()

    async def blocking_sveglia() -> None:
        sveglia_started.set()
        await release_sveglia.wait()

    monkeypatch.setattr(coord, "async_assicura_sveglia", blocking_sveglia)

    # Park -> launches in-flight realign task
    coord._on_probe_data(
        {
            "hVoltageState": "0",
            "engineState": "0",
            "vehicleSpeed": "0",
            "odometer": "10055",
            "chargeGunState": "0",
        }
    )
    await asyncio.wait_for(sveglia_started.wait(), timeout=1.0)
    assert coord._pending_realign_away_park is True
    assert coord._pending_realign_plug_in is False

    # Plug in while realign is still running and cached position is still AWAY
    _send_5a02(coord, engineState="0", hVoltageState="0", chargeGunState="1")
    await hass.async_block_till_done()
    assert sent == []
    assert not coord._timers.is_armed(CHARGE_PLUGIN_DEBOUNCE)
    assert coord._pending_realign_plug_in is True
    assert coord._pending_realign_away_park is True

    # 1301 HOME arrives and realign finishes -> arms 20s home debounce, no away sync
    _send_1301(coord, HOME_LAT, HOME_LON)
    release_sveglia.set()
    await hass.async_block_till_done(wait_background_tasks=True)

    assert coord._timers.is_armed(CHARGE_PLUGIN_DEBOUNCE)
    assert sent == []
    coord.async_stop()


async def test_cooldown_blocks_extra_localizza_but_evaluates_deferred_away_park(
    hass: HomeAssistant, monkeypatch
) -> None:
    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="cooldown_away_park")
    coord.poll_enabled = True
    coord.set_charge_window_mode("fixed", sync_charge=False)
    coord._last_gps_fallback_mono = time.monotonic()

    _send_1301(coord, AWAY_LAT, AWAY_LON)
    await hass.async_block_till_done()

    coord._on_probe_data(
        {
            "hVoltageState": "1",
            "engineState": "1",
            "odometer": "10080",
            "vehicleSpeed": "50",
        }
    )
    await hass.async_block_till_done()

    sveglia_calls = 0

    async def fake_sveglia() -> None:
        nonlocal sveglia_calls
        sveglia_calls += 1

    monkeypatch.setattr(coord, "async_assicura_sveglia", fake_sveglia)

    coord._on_probe_data(
        {
            "hVoltageState": "0",
            "engineState": "0",
            "vehicleSpeed": "0",
            "odometer": "10025",
            "chargeGunState": "0",
            "chargeAppointPlans": [{"switchStatus": "1", "startTime": "1320"}],
        }
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    assert sveglia_calls == 0
    assert coord._trip_needs_gps_realign is False
    assert len(sent) == 1
    assert sent[0][0] == "ricarica_prog_off"
    coord.async_stop()


async def test_charge_window_mode_off_still_realigns_gps_on_trip_end(
    hass: HomeAssistant, monkeypatch
) -> None:
    _entry, coord, sent = _make_coord(hass, monkeypatch, entry_id="mode_off_realign")
    coord.poll_enabled = True
    assert coord._charge_window_mode == "off"

    _send_1301(coord, AWAY_LAT, AWAY_LON)
    await hass.async_block_till_done()

    coord._on_probe_data(
        {
            "hVoltageState": "1",
            "engineState": "1",
            "odometer": "10110",
            "vehicleSpeed": "40",
        }
    )
    await hass.async_block_till_done()

    sveglia_calls = 0

    async def fake_sveglia() -> None:
        nonlocal sveglia_calls
        sveglia_calls += 1
        _send_1301(coord, HOME_LAT, HOME_LON)

    monkeypatch.setattr(coord, "async_assicura_sveglia", fake_sveglia)

    coord._on_probe_data(
        {
            "hVoltageState": "0",
            "engineState": "0",
            "vehicleSpeed": "0",
            "odometer": "10110",
            "chargeGunState": "0",
        }
    )
    await hass.async_block_till_done(wait_background_tasks=True)

    assert sveglia_calls == 1
    assert coord.position["lat"] == str(HOME_LAT)
    assert coord._trip_needs_gps_realign is False
    assert sent == []
    coord.async_stop()


async def test_startup_probe_boot_realign_once_only_when_online_and_missing_gps(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _entry, coord, _sent = _make_coord(
        hass, monkeypatch, entry_id="boot_realign", patch_probe=False
    )
    coord.poll_enabled = True
    assert coord.restore_position(HOME_LAT, HOME_LON) is True
    assert coord._last_pos_fix_mono == 0.0

    cloud.on(
        "/asr/manager/realtime",
        {"code": "000000", "data": {"odometer": "12500", "dumpEnergy": "80", "onlineStatus": "1"}},
    )
    cloud.on(
        "/asc/vehicleControl/queryVehicleLocation",
        {"code": "000000", "data": {"resultTime": "1795814172066"}},
    )
    cloud.on("/asd/travelManage/travelQuery", {"code": "A07900"})

    sveglia_calls = 0

    async def fake_sveglia() -> None:
        nonlocal sveglia_calls
        sveglia_calls += 1

    monkeypatch.setattr(coord, "async_assicura_sveglia", fake_sveglia)
    monkeypatch.setattr("custom_components.lepas.coordinator.GPS_REALIGN_WAIT_S", 0.01)

    await coord._startup_probe_cb(None)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert coord._online is True
    assert coord._probe_missing_gps is True
    assert coord._boot_gps_realign_done is True
    assert sveglia_calls == 1

    # Second startup probe callback must never re-trigger boot realignment
    coord._last_gps_fallback_mono = 0.0
    await coord._startup_probe_cb(None)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert sveglia_calls == 1
    coord.async_stop()

    # Offline vehicle must not trigger boot realignment
    _entry2, coord_off, _sent2 = _make_coord(
        hass, monkeypatch, entry_id="boot_offline", patch_probe=False
    )
    coord_off.poll_enabled = True
    cloud.on("/asr/manager/realtime", {"code": "A07900"})
    cloud.on("/asc/vehicleControl/queryVehicleLocation", {"code": "A07900"})
    off_calls = 0

    async def fake_sveglia_off() -> None:
        nonlocal off_calls
        off_calls += 1

    monkeypatch.setattr(coord_off, "async_assicura_sveglia", fake_sveglia_off)
    await coord_off._startup_probe_cb(None)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert coord_off._online is False
    assert off_calls == 0
    assert coord_off._boot_gps_realign_done is False
    coord_off.async_stop()


async def test_degraded_odometer_zero_frame_does_not_trigger_realign(
    hass: HomeAssistant, monkeypatch
) -> None:
    _entry, coord, _sent = _make_coord(hass, monkeypatch, entry_id="degraded_odo_zero")
    coord._on_probe_data({"lat": str(HOME_LAT), "lon": str(HOME_LON), "odometer": "12500"})
    assert coord._last_gps_odo == 12500.0
    assert coord._last_probe_odo == 12500.0
    assert coord._trip_needs_gps_realign is False

    # Degraded placeholder frame (odometer=0, vehicleSpeed=0) without GPS
    coord._on_probe_data(
        {"odometer": "0", "vehicleSpeed": "0", "dumpEnergy": "0", "pureElectricRange": "0"}
    )
    assert coord._trip_needs_gps_realign is False
    assert coord._last_probe_odo == 12500.0

    # Subsequent real frame at the same odometer=12500 must not falsely see an increase
    coord._on_probe_data({"odometer": "12500", "vehicleSpeed": "0", "dumpEnergy": "75"})
    assert coord._trip_needs_gps_realign is False
    coord._on_probe_data({"odometer": True, "vehicleSpeed": False})
    assert coord._trip_needs_gps_realign is False
    coord.async_stop()


async def test_async_stop_from_executor_thread_and_set_poll_enabled_false_cancel_cleanly(
    hass: HomeAssistant, monkeypatch
) -> None:
    # Part A: set_poll_enabled(False) cancels in-flight task and clears pending flags
    _entry1, coord1, _sent1 = _make_coord(hass, monkeypatch, entry_id="cancel_poll_off")
    coord1.poll_enabled = True
    started1 = asyncio.Event()
    never1 = asyncio.Event()

    async def wait_sveglia1() -> None:
        started1.set()
        await never1.wait()

    monkeypatch.setattr(coord1, "async_assicura_sveglia", wait_sveglia1)
    coord1._schedule_gps_realign_task(defer_away_park=True, defer_plug_in=True)
    task1 = coord1._gps_realign_task
    assert task1 is not None
    await asyncio.wait_for(started1.wait(), timeout=1.0)

    coord1.set_poll_enabled(False)
    assert coord1._pending_realign_away_park is False
    assert coord1._pending_realign_plug_in is False
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task1, timeout=1.0)
    assert coord1._gps_realign_task is None
    coord1.async_stop()

    # Part B: async_stop() from executor thread cancels task waiting on _wait_for_pos_fix
    _entry2, coord2, _sent2 = _make_coord(hass, monkeypatch, entry_id="cancel_executor_stop")
    coord2.poll_enabled = True
    waiting_for_fix = asyncio.Event()

    async def quick_sveglia2() -> None:
        return None

    orig_wait = coord2._wait_for_pos_fix

    async def wrapped_wait(baseline_mono: float, timeout: float = 15.0) -> bool:
        waiting_for_fix.set()
        return await orig_wait(baseline_mono, timeout=timeout)

    monkeypatch.setattr(coord2, "async_assicura_sveglia", quick_sveglia2)
    monkeypatch.setattr(coord2, "_wait_for_pos_fix", wrapped_wait)

    coord2._schedule_gps_realign_task(defer_away_park=True)
    task2 = coord2._gps_realign_task
    assert task2 is not None
    await asyncio.wait_for(waiting_for_fix.wait(), timeout=1.0)

    await hass.async_add_executor_job(coord2.async_stop)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert coord2._timers.closing is True
    assert task2.done()
    assert coord2._pending_realign_away_park is False
    assert coord2._pending_realign_plug_in is False
    assert coord2._gps_realign_task is None
