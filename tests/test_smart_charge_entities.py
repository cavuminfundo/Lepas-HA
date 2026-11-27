"""Falsifiable HA entity tests for smart charging mode, power controls, sensors, and translations."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import fixtures as FX
import pytest
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

from custom_components.lepas.const import (
    CONF_PIN,
    CONF_TUSERID,
    CONF_VIN,
    DATA_CAPS_PROBED_V3,
    DATA_CAPS_PROBED_V4,
    DATA_VEHICLE_FEATURES,
    DOMAIN,
    ENTITY_FEATURE_MAP,
)
from custom_components.lepas.coordinator import LepasCoordinator
from custom_components.lepas.naming import CANON_ENTITY_ID, ID_PREFIX
from custom_components.lepas.number import LepasConfigNumber
from custom_components.lepas.select import LepasChargeWindowModeSelect
from custom_components.lepas.sensor import (
    LepasNextDepartureSensor,
    LepasScheduledChargingWindowSensor,
)
from custom_components.lepas.switch import LepasScheduleSwitch

HOME_LAT = 45.070312
HOME_LON = 7.686856
AWAY_LAT = 45.550000
AWAY_LON = 9.200000


def _patch_io(monkeypatch) -> list[tuple[str, dict | None]]:
    sent: list[tuple[str, dict | None]] = []

    async def fake_send(self, key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    async def no_backfill(self) -> None:
        return None

    async def noop_probe(self, force: bool = False) -> None:
        return None

    monkeypatch.setattr(LepasCoordinator, "_provision_certs", lambda self: (True, "ok"))
    monkeypatch.setattr(LepasCoordinator, "_connect_car", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_keepalive", lambda self: None)
    monkeypatch.setattr(
        LepasCoordinator, "async_start_telemetry_poll", lambda self: None
    )
    monkeypatch.setattr(LepasCoordinator, "async_start_drive_watch", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_ensure_vehicle_identity", no_backfill)
    monkeypatch.setattr(LepasCoordinator, "async_send_command", fake_send)
    monkeypatch.setattr(LepasCoordinator, "async_probe", noop_probe)
    return sent


async def _setup_entry(
    hass: HomeAssistant,
    *,
    vin: str = FX.VIN,
    entry_id: str = "smart_entities_entry",
    features: dict[str, bool] | None = None,
) -> MockConfigEntry:
    data: dict = {
        CONF_VIN: vin,
        CONF_TUSERID: FX.TUSERID,
        "email": FX.EMAIL,
        CONF_PIN: FX.PIN,
    }
    if features is not None:
        data[DATA_CAPS_PROBED_V3] = True
        data[DATA_CAPS_PROBED_V4] = True
        data[DATA_VEHICLE_FEATURES] = features
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Lepas ({vin})",
        unique_id=vin,
        data=data,
        entry_id=entry_id,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _make_direct_coord(
    hass: HomeAssistant, monkeypatch, entry_id: str
) -> tuple[LepasCoordinator, list[tuple[str, dict | None]]]:
    sent: list[tuple[str, dict | None]] = []

    async def fake_send(key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_VIN: FX.VIN,
            CONF_TUSERID: FX.TUSERID,
            "email": FX.EMAIL,
            CONF_PIN: FX.PIN,
        },
        entry_id=entry_id,
    )
    coord = LepasCoordinator(hass, entry)
    monkeypatch.setattr(coord, "async_send_command", fake_send)
    monkeypatch.setattr(coord._charging_store, "async_delay_save", lambda _fn, _d: None)
    return coord, sent


def _mount_direct(entity, hass: HomeAssistant, monkeypatch) -> list[object]:
    writes: list[object] = []
    entity.hass = hass
    monkeypatch.setattr(entity, "async_write_ha_state", lambda: writes.append(True))
    return writes


async def test_boot_migration_both_setup_orders(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    """First-boot migration and select-vs-switch boot conflict resolution work in both orders."""
    _patch_io(monkeypatch)

    # 1a. First boot (no select cache, switch="on"): select -> switch order
    mock_restore_cache(hass, [State("switch.lepas_sync_charge_to_departure", "on")])
    coord1, sent1 = _make_direct_coord(hass, monkeypatch, "boot_1a")
    sel1 = LepasChargeWindowModeSelect(coord1)
    sw1 = LepasScheduleSwitch(
        coord1,
        "Lepas Sync charging to departure",
        "sync_charge_to_departure",
        "sync_charge_to_departure",
        "mdi:battery-sync",
        sync_mode="charge",
    )
    _mount_direct(sel1, hass, monkeypatch)
    _mount_direct(sw1, hass, monkeypatch)

    await sel1.async_added_to_hass()
    assert coord1._charge_window_mode_restored is False
    assert coord1.charge_window_mode == "off"

    await sw1.async_added_to_hass()
    assert coord1._charge_window_mode_restored is False
    assert coord1.charge_window_mode == "smart_departure"
    assert coord1.sync_charge_to_departure is True
    assert sel1.current_option == "smart_departure"
    assert sw1.is_on is True
    assert sent1 == []
    coord1.async_stop()

    # 1b. First boot (no select cache, switch="on"): switch -> select order
    mock_restore_cache(hass, [State("switch.lepas_sync_charge_to_departure", "on")])
    coord2, sent2 = _make_direct_coord(hass, monkeypatch, "boot_1b")
    sel2 = LepasChargeWindowModeSelect(coord2)
    sw2 = LepasScheduleSwitch(
        coord2,
        "Lepas Sync charging to departure",
        "sync_charge_to_departure",
        "sync_charge_to_departure",
        "mdi:battery-sync",
        sync_mode="charge",
    )
    _mount_direct(sel2, hass, monkeypatch)
    _mount_direct(sw2, hass, monkeypatch)

    await sw2.async_added_to_hass()
    assert coord2.charge_window_mode == "smart_departure"
    assert coord2._charge_window_mode_restored is False

    await sel2.async_added_to_hass()
    assert coord2._charge_window_mode_restored is False
    assert coord2.charge_window_mode == "smart_departure"
    assert sel2.current_option == "smart_departure"
    assert sw2.is_on is True
    assert sent2 == []
    coord2.async_stop()

    # 2a. Conflict (select="fixed", switch="on"): select -> switch order
    mock_restore_cache(
        hass,
        [
            State("select.lepas_charge_window_mode", "fixed"),
            State("switch.lepas_sync_charge_to_departure", "on"),
        ],
    )
    coord3, sent3 = _make_direct_coord(hass, monkeypatch, "boot_2a")
    sel3 = LepasChargeWindowModeSelect(coord3)
    sw3 = LepasScheduleSwitch(
        coord3,
        "Lepas Sync charging to departure",
        "sync_charge_to_departure",
        "sync_charge_to_departure",
        "mdi:battery-sync",
        sync_mode="charge",
    )
    _mount_direct(sel3, hass, monkeypatch)
    _mount_direct(sw3, hass, monkeypatch)
    listener_hits3: list[str] = []
    unsub3 = coord3.async_add_listener(
        lambda: listener_hits3.append(coord3.charge_window_mode)
    )
    try:
        await sel3.async_added_to_hass()
        assert coord3._charge_window_mode_restored is True
        assert coord3.charge_window_mode == "fixed"
        assert listener_hits3 == ["fixed"]

        await sw3.async_added_to_hass()
        assert coord3.charge_window_mode == "fixed"
        assert coord3.sync_charge_to_departure is False
        assert sel3.current_option == "fixed"
        assert sw3.is_on is False
        assert sent3 == []
    finally:
        unsub3()
        coord3.async_stop()

    # 2b. Conflict (select="fixed", switch="on"): switch -> select order
    mock_restore_cache(
        hass,
        [
            State("select.lepas_charge_window_mode", "fixed"),
            State("switch.lepas_sync_charge_to_departure", "on"),
        ],
    )
    coord4, sent4 = _make_direct_coord(hass, monkeypatch, "boot_2b")
    sel4 = LepasChargeWindowModeSelect(coord4)
    sw4 = LepasScheduleSwitch(
        coord4,
        "Lepas Sync charging to departure",
        "sync_charge_to_departure",
        "sync_charge_to_departure",
        "mdi:battery-sync",
        sync_mode="charge",
    )
    _mount_direct(sel4, hass, monkeypatch)
    sw4_writes = _mount_direct(sw4, hass, monkeypatch)
    listener_hits4: list[str] = []
    unsub4 = coord4.async_add_listener(
        lambda: listener_hits4.append(coord4.charge_window_mode)
    )
    try:
        await sw4.async_added_to_hass()
        assert coord4.charge_window_mode == "smart_departure"

        await sel4.async_added_to_hass()
        assert coord4._charge_window_mode_restored is True
        assert coord4.charge_window_mode == "fixed"
        assert coord4.sync_charge_to_departure is False
        assert listener_hits4[-1] == "fixed"
        assert len(sw4_writes) >= 1
        assert sel4.current_option == "fixed"
        assert sw4.is_on is False
        assert sent4 == []
    finally:
        unsub4()
        coord4.async_stop()

    # 3. Full HA setup: conflict (select="fixed" vs switch="on") and power_auto="off"
    mock_restore_cache(
        hass,
        [
            State("select.lepas_charge_window_mode", "fixed"),
            State("switch.lepas_sync_charge_to_departure", "on"),
            State("switch.lepas_home_charge_power_auto", "off"),
        ],
    )
    entry = await _setup_entry(
        hass, vin="L8BOOTFULL0000001", entry_id="boot_full_conflict"
    )
    try:
        coord_full = hass.data[DOMAIN][entry.entry_id]
        assert coord_full.charge_window_mode == "fixed"
        assert coord_full.sync_charge_to_departure is False
        assert coord_full.home_charge_power_auto is False
        assert hass.states.get("select.lepas_charge_window_mode").state == "fixed"
        assert hass.states.get("switch.lepas_sync_charge_to_departure").state == "off"
        assert hass.states.get("switch.lepas_home_charge_power_auto").state == "off"
    finally:
        await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()


async def test_first_boot_migration_and_power_auto_default_ha_setup(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    """First boot without select cache migrates switch=on -> smart_departure and defaults power_auto=on."""
    _patch_io(monkeypatch)
    mock_restore_cache(hass, [State("switch.lepas_sync_charge_to_departure", "on")])
    entry_mig = await _setup_entry(
        hass, vin="L8BOOTFULL0000002", entry_id="boot_full_mig"
    )
    try:
        coord_mig = hass.data[DOMAIN][entry_mig.entry_id]
        assert coord_mig.charge_window_mode == "smart_departure"
        assert coord_mig.home_charge_power_auto is True
        assert (
            hass.states.get("select.lepas_charge_window_mode").state
            == "smart_departure"
        )
        assert hass.states.get("switch.lepas_sync_charge_to_departure").state == "on"
        assert hass.states.get("switch.lepas_home_charge_power_auto").state == "on"
    finally:
        await hass.config_entries.async_remove(entry_mig.entry_id)
        await hass.async_block_till_done()


async def test_bidirectional_sync_select_and_legacy_switch(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    """Select and legacy sync switch stay synchronized bidirectionally; power_auto toggles sync_charge."""
    sent = _patch_io(monkeypatch)
    hass.config.time_zone = "UTC"
    tz = UTC
    monkeypatch.setattr(
        dt_util, "now", lambda: datetime(2026, 11, 16, 10, 0, tzinfo=tz)
    )

    notify_calls: list[dict[str, bool]] = []
    orig_notify = LepasCoordinator.notify_schedule_changed

    def spy_notify(
        self,
        *,
        sync_charge: bool = False,
        sync_native: bool = False,
        sync_battery: bool = False,
    ) -> None:
        notify_calls.append(
            {
                "sync_charge": sync_charge,
                "sync_native": sync_native,
                "sync_battery": sync_battery,
            }
        )
        orig_notify(
            self,
            sync_charge=sync_charge,
            sync_native=sync_native,
            sync_battery=sync_battery,
        )

    monkeypatch.setattr(LepasCoordinator, "notify_schedule_changed", spy_notify)

    entry = await _setup_entry(hass, entry_id="bidir_sync")
    coord = hass.data[DOMAIN][entry.entry_id]
    hass.states.async_set(
        "zone.home",
        "zoning",
        {"latitude": HOME_LAT, "longitude": HOME_LON, "radius": 200},
    )
    coord.position = {"lat": HOME_LAT, "lon": HOME_LON}

    try:
        assert hass.states.get("select.lepas_charge_window_mode").state == "off"
        assert hass.states.get("switch.lepas_sync_charge_to_departure").state == "off"
        assert hass.states.get("select.lepas_charge_window_mode").attributes[
            "options"
        ] == [
            "off",
            "fixed",
            "smart_departure",
        ]

        # Legacy switch ON -> select becomes smart_departure
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_sync_charge_to_departure"},
            blocking=True,
        )
        assert coord.charge_window_mode == "smart_departure"
        assert (
            hass.states.get("select.lepas_charge_window_mode").state
            == "smart_departure"
        )

        # Legacy switch OFF while smart_departure -> select becomes fixed
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_sync_charge_to_departure"},
            blocking=True,
        )
        assert coord.charge_window_mode == "fixed"
        assert hass.states.get("select.lepas_charge_window_mode").state == "fixed"

        # Select smart_departure -> legacy switch becomes on
        await hass.services.async_call(
            "select",
            "select_option",
            {
                "entity_id": "select.lepas_charge_window_mode",
                "option": "smart_departure",
            },
            blocking=True,
        )
        assert coord.sync_charge_to_departure is True
        assert hass.states.get("switch.lepas_sync_charge_to_departure").state == "on"

        # Select off -> legacy switch becomes off
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.lepas_charge_window_mode", "option": "off"},
            blocking=True,
        )
        assert coord.sync_charge_to_departure is False
        assert hass.states.get("switch.lepas_sync_charge_to_departure").state == "off"

        # Invalid mode rejected
        with pytest.raises((ServiceValidationError, ValueError)):
            await hass.services.async_call(
                "select",
                "select_option",
                {"entity_id": "select.lepas_charge_window_mode", "option": "solar"},
                blocking=True,
            )

        # Power auto switch toggle propagates sync_charge=True on user toggle
        notify_calls.clear()
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_home_charge_power_auto"},
            blocking=True,
        )
        assert coord.home_charge_power_auto is False
        assert notify_calls[-1]["sync_charge"] is True

        notify_calls.clear()
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_home_charge_power_auto"},
            blocking=True,
        )
        assert coord.home_charge_power_auto is True
        assert notify_calls[-1]["sync_charge"] is True
        assert isinstance(sent, list)
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_home_charge_power_number_decimal_snapping_and_clamp(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    """Decimal step snapping, [1.4, 40.0] clamping, float preservation, and boot sync_charge=False."""
    sent = _patch_io(monkeypatch)
    hass.config.time_zone = "UTC"
    tz = UTC
    monkeypatch.setattr(
        dt_util, "now", lambda: datetime(2026, 11, 16, 22, 0, tzinfo=tz)
    )

    notify_calls: list[dict[str, bool]] = []
    orig_notify = LepasCoordinator.notify_schedule_changed

    def spy_notify(
        self,
        *,
        sync_charge: bool = False,
        sync_native: bool = False,
        sync_battery: bool = False,
    ) -> None:
        notify_calls.append(
            {
                "sync_charge": sync_charge,
                "sync_native": sync_native,
                "sync_battery": sync_battery,
            }
        )
        orig_notify(
            self,
            sync_charge=sync_charge,
            sync_native=sync_native,
            sync_battery=sync_battery,
        )

    monkeypatch.setattr(LepasCoordinator, "notify_schedule_changed", spy_notify)

    mock_restore_cache(hass, [State("number.lepas_home_charge_power", "3.0")])
    entry = await _setup_entry(hass, entry_id="power_number")
    coord = hass.data[DOMAIN][entry.entry_id]
    hass.states.async_set(
        "zone.home",
        "zoning",
        {"latitude": HOME_LAT, "longitude": HOME_LON, "radius": 200},
    )
    coord.position = {"lat": HOME_LAT, "lon": HOME_LON}

    try:
        # Boot restore: all notify calls must have sync_charge=False, and 3.0 must remain float
        assert sent == []
        assert all(not c["sync_charge"] for c in notify_calls)
        assert coord.home_charge_power == 3.0
        assert type(coord.home_charge_power) is float

        st = hass.states.get("number.lepas_home_charge_power")
        assert st is not None
        assert st.attributes["min"] == 1.4
        assert st.attributes["max"] == 40.0
        assert st.attributes["step"] == 0.1
        assert st.attributes["unit_of_measurement"] == UnitOfPower.KILO_WATT

        reg = er.async_get(hass)
        reg_entry = reg.async_get("number.lepas_home_charge_power")
        assert reg_entry is not None
        assert reg_entry.entity_category == EntityCategory.CONFIG

        num_entity = next(
            e
            for e in hass.data["entity_components"]["number"].entities
            if isinstance(e, LepasConfigNumber) and e._attr == "home_charge_power"
        )

        # Direct snapping + clamp tests
        assert num_entity._snap_value(2.3) == 2.3
        assert num_entity._snap_value(3.0) == 3.0
        assert num_entity._snap_value(2.34) == 2.3
        assert num_entity._snap_value(2.36) == 2.4
        assert num_entity._snap_value(0.2) == 1.4
        assert num_entity._snap_value(99.0) == 40.0

        await num_entity.async_set_native_value(3.0)
        assert coord.home_charge_power == 3.0
        assert type(coord.home_charge_power) is float

        await num_entity.async_set_native_value(0.2)
        assert coord.home_charge_power == 1.4
        await num_entity.async_set_native_value(99.0)
        assert coord.home_charge_power == 40.0

        # Integer-step number (charge_duration_hours) still pushes int
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.lepas_charge_duration", "value": 5},
            blocking=True,
        )
        assert coord.charge_duration_hours == 5
        assert type(coord.charge_duration_hours) is int

        # User update in smart_departure triggers sync_charge=True and sends ricarica_prog_on
        coord.set_charge_window_mode("smart_departure", sync_charge=False)
        coord.departure_weekly[2] = (True, 7 * 60)
        coord.home_charge_power_auto = False
        sent.clear()
        notify_calls.clear()

        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.lepas_home_charge_power", "value": 3.7},
            blocking=True,
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        assert coord.home_charge_power == 3.7
        assert type(coord.home_charge_power) is float
        assert notify_calls[-1]["sync_charge"] is True
        assert any(cmd == "ricarica_prog_on" for cmd, _ in sent)
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_ice_vehicle_feature_gating_excludes_new_entities(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    """Vehicles without scheduled_charging capability must not create the 3 smart-charging entities."""
    _patch_io(monkeypatch)

    # Canonical naming & feature map assertions
    assert (
        CANON_ENTITY_ID[("select", "charge_window_mode")]
        == "select.lepas_charge_window_mode"
    )
    assert (
        CANON_ENTITY_ID[("switch", "home_charge_power_auto")]
        == "switch.lepas_home_charge_power_auto"
    )
    assert (
        CANON_ENTITY_ID[("number", "home_charge_power")]
        == "number.lepas_home_charge_power"
    )
    assert ENTITY_FEATURE_MAP[("select", "charge_window_mode")] == "scheduled_charging"
    assert (
        ENTITY_FEATURE_MAP[("switch", "home_charge_power_auto")] == "scheduled_charging"
    )
    assert ENTITY_FEATURE_MAP[("number", "home_charge_power")] == "scheduled_charging"

    entry_ice = await _setup_entry(
        hass,
        vin="L8ICEVEHICLE00001",
        entry_id="ice_gated",
        features={"scheduled_charging": False},
    )
    try:
        reg = er.async_get(hass)
        for eid in (
            "select.lepas_charge_window_mode",
            "switch.lepas_home_charge_power_auto",
            "number.lepas_home_charge_power",
        ):
            assert hass.states.get(eid) is None, f"{eid} must not exist on ICE vehicle"
            assert reg.async_get(eid) is None, (
                f"{eid} must not be registered on ICE vehicle"
            )
    finally:
        await hass.config_entries.async_remove(entry_ice.entry_id)
        await hass.async_block_till_done()

    entry_ev = await _setup_entry(
        hass,
        vin="L8PHEVVEHICLE0001",
        entry_id="ev_enabled",
        features={"scheduled_charging": True},
    )
    try:
        reg = er.async_get(hass)
        for eid, sfx in (
            ("select.lepas_charge_window_mode", "charge_window_mode"),
            ("switch.lepas_home_charge_power_auto", "home_charge_power_auto"),
            ("number.lepas_home_charge_power", "home_charge_power"),
        ):
            assert hass.states.get(eid) is not None
            ent = reg.async_get(eid)
            assert ent is not None
            assert ent.entity_id.split(".", 1)[1].startswith(f"{ID_PREFIX}_")
            assert ent.unique_id == f"L8PHEVVEHICLE0001_{sfx}"
    finally:
        await hass.config_entries.async_unload(entry_ev.entry_id)
        await hass.async_block_till_done()


async def test_window_sensor_attributes_and_next_departure_parity(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    """Window sensor exposes Spec 4.1 attributes and matches next_departure planned_charge_start 1:1."""
    _patch_io(monkeypatch)
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    now_local = datetime(2026, 11, 16, 22, 0, tzinfo=rome)
    monkeypatch.setattr(dt_util, "now", lambda: now_local)
    monkeypatch.setattr(dt_util, "utcnow", lambda: now_local.astimezone(UTC))

    entry = await _setup_entry(hass, entry_id="sensor_parity")
    coord = hass.data[DOMAIN][entry.entry_id]
    hass.states.async_set(
        "zone.home",
        "zoning",
        {"latitude": HOME_LAT, "longitude": HOME_LON, "radius": 200},
    )

    try:
        # Seed learned AC (1 session, 3.4 kW) and DC (2 sessions, 24.0 kW)
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
            for s in range(2):
                base_ts = 2000.0 + s * 1000.0
                for i in range(4):
                    coord._charging_tracker.ingest(
                        base_ts + i * 120.0,
                        "2026-11-16",
                        power_kw=24.0,
                        charge_state="1",
                        plugged=True,
                        soc_pct=30.0 + i,
                        odometer=110.0 + s,
                        in_home_zone=True,
                        degraded_battery=False,
                        fast_charging=True,
                    )
                coord._charging_tracker.ingest(
                    base_ts + 600.0,
                    "2026-11-16",
                    power_kw=0.0,
                    charge_state="0",
                    plugged=False,
                    soc_pct=50.0,
                    odometer=110.0 + s,
                    in_home_zone=True,
                    degraded_battery=False,
                    fast_charging=True,
                )

        # Smart departure at home with 80% SoC -> 18.4*0.2/(3.4*0.9)*60 + 25 = 97.16m -> 105m
        # 07:00 - 105m = 05:15 -> aligned 05:15 (315 min)
        coord.position = {"lat": HOME_LAT, "lon": HOME_LON}
        coord._update(
            {
                "position": {"lat": HOME_LAT, "lon": HOME_LON},
                "realtime": {
                    "dumpEnergy": "80",
                    "pureElectricRange": "50",
                    "chargeGunState": "1",
                },
                "fields": {"chargeGunState": "1"},
            }
        )
        coord.departure_weekly[2] = (True, 7 * 60)
        coord.charge_duration_hours = 6
        coord.home_charge_power = 2.3
        coord.home_charge_power_auto = True
        coord.set_charge_window_mode("smart_departure", sync_charge=False)
        await hass.async_block_till_done()

        win = hass.states.get("sensor.lepas_scheduled_charging_window")
        nd = hass.states.get("sensor.lepas_next_departure")
        assert win is not None and nd is not None
        attrs = win.attributes

        assert attrs["window_mode"] == "smart_departure"
        assert attrs["effective_action"] == "enable"
        assert attrs["plan_reason"] == "smart_home"
        assert attrs["estimated_duration_min"] == 105
        assert attrs["soc_used"] == 80.0
        assert attrs["charge_kind"] == "ac"
        assert attrs["effective_power_kw"] == 3.4
        assert attrs["power_source"] == "learned_ac"
        assert attrs["learned_ac_kw"] == 3.4
        assert attrs["learned_dc_kw"] == 24.0
        assert attrs["home_ac_sessions"] == 1
        assert attrs["home_dc_sessions"] == 2
        assert attrs["fallback_used"] is False
        assert attrs["away_bypass_active"] is False
        assert attrs["quick_override_active"] is False
        assert attrs["start_time"] == "05:15"
        assert attrs["end_time"] == "07:00"
        assert nd.attributes["planned_charge_start"] == attrs["start_time"]

        # Away bypass -> effective_action="disable", away_bypass_active=True, planned_charge_start=None
        coord.position = {"lat": AWAY_LAT, "lon": AWAY_LON}
        coord._update({"position": {"lat": AWAY_LAT, "lon": AWAY_LON}})
        await hass.async_block_till_done()

        win_away = hass.states.get("sensor.lepas_scheduled_charging_window")
        nd_away = hass.states.get("sensor.lepas_next_departure")
        assert win_away.attributes["effective_action"] == "disable"
        assert win_away.attributes["plan_reason"] == "away_bypass"
        assert win_away.attributes["away_bypass_active"] is True
        assert nd_away.attributes["planned_charge_start"] is None

        # Fixed mode at home with quick departure override -> quick_override_active=True and 1:1 parity
        coord.position = {"lat": HOME_LAT, "lon": HOME_LON}
        coord._update({"position": {"lat": HOME_LAT, "lon": HOME_LON}})
        coord.set_charge_window_mode("fixed", sync_charge=False)
        coord.quick_departure_minutes = 8 * 60
        coord.quick_departure_enabled = True
        coord.notify_schedule_changed(sync_charge=False)
        await hass.async_block_till_done()

        win_q = hass.states.get("sensor.lepas_scheduled_charging_window")
        nd_q = hass.states.get("sensor.lepas_next_departure")
        assert win_q.attributes["window_mode"] == "fixed"
        assert win_q.attributes["effective_action"] == "enable"
        assert win_q.attributes["plan_reason"] == "quick_override"
        assert win_q.attributes["quick_override_active"] is True
        # 08:00 - 105m = 06:15
        assert win_q.attributes["start_time"] == "06:15"
        assert nd_q.attributes["planned_charge_start"] == "06:15"

        # Legacy stub coordinator fallback without evaluate_charge_plan/home_power_profile
        class _LegacyStubCoord:
            def __init__(self) -> None:
                self.vin = "LEGACYVIN0000001"
                self.vehicle_name = "Lepas"
                self.vehicle_brand = "Lepas"
                self.vehicle_model = "L8"
                self.data: dict = {}
                self.charge_start_minutes = 23 * 60
                self.charge_duration_hours = 6
                self.charge_days = [1, 2, 3, 4, 5, 6, 7]
                self.departure_climate_mode = "off"
                self.sync_charge_to_departure = True
                self.sync_battery_heat_to_departure = False
                self.departure_climate_extras: list[str] = []

            def next_departure_occurrence(self, ref_now: datetime):
                from custom_components.lepas.scheduler import compute_next_occurrence

                return compute_next_occurrence(ref_now, None, True, 8 * 60, 15)

        stub = _LegacyStubCoord()
        s_win = LepasScheduledChargingWindowSensor(stub)
        s_nd = LepasNextDepartureSensor(stub)
        s_win_attrs = s_win.extra_state_attributes
        assert s_win_attrs["start_time"] == "23:00"
        assert s_win_attrs["window_mode"] == "off"
        assert s_nd.extra_state_attributes["planned_charge_start"] == "02:00"
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_schedule_switch_turn_off_syncs_restore_in_fixed_and_smart_modes(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    """Turning off quick_departure, sync_charge, or weekly day syncs immediately."""
    sent = _patch_io(monkeypatch)
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 26, 20, 0, tzinfo=rome))

    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]
    try:
        hass.states.async_set(
            "zone.home", "zoning", {"latitude": HOME_LAT, "longitude": HOME_LON, "radius": 100}
        )
        coord.position = {"lat": HOME_LAT, "lon": HOME_LON}
        coord._update({"realtime": {"dumpEnergy": 80, "chargeState": 0}, "position": coord.position})
        coord.charge_start_minutes = 23 * 60
        coord.charge_duration_hours = 6
        coord.set_charge_window_mode("fixed", sync_charge=False)

        # 1. quick_departure ON -> quick_override, then turn_off restores fixed schedule immediately
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": "switch.lepas_quick_departure"}, blocking=True
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        sent.clear()
        await hass.services.async_call(
            "switch", "turn_off", {"entity_id": "switch.lepas_quick_departure"}, blocking=True
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        assert len(sent) == 1
        assert sent[0][0] == "ricarica_prog_on"
        assert sent[0][1]["chargeAppointPlans"][0]["timeConsuming"] == 360

        # 2. Turning off sync_charge_to_departure switches smart_departure -> fixed and syncs fixed
        coord.departure_weekly[5] = (True, 8 * 60)  # Fri 08:00
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.lepas_charge_window_mode", "option": "smart_departure"},
            blocking=True,
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        sent.clear()
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_sync_charge_to_departure"},
            blocking=True,
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        assert coord.charge_window_mode == "fixed"
        assert len(sent) == 1
        assert sent[0][0] == "ricarica_prog_on"
        assert sent[0][1]["chargeAppointPlans"][0]["timeConsuming"] == 360

        # 3. Turning off last weekly day in smart_departure immediately sends ricarica_prog_off
        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.lepas_charge_window_mode", "option": "smart_departure"},
            blocking=True,
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        sent.clear()
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_departure_fri_enabled"},
            blocking=True,
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        assert len(sent) == 1
        assert sent[0][0] == "ricarica_prog_off"
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_window_sensor_synced_with_car_plan_modes(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    """synced_with_car handles noop, disable, and enable/switchStatus across plan modes."""
    _patch_io(monkeypatch)
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    current_now = [datetime(2026, 11, 16, 22, 0, tzinfo=rome)]  # Monday CET (UTC+1)
    monkeypatch.setattr(dt_util, "now", lambda: current_now[0])
    monkeypatch.setattr(dt_util, "utcnow", lambda: current_now[0].astimezone(UTC))

    entry = await _setup_entry(
        hass, vin="L8SYNCSTATUS00001", entry_id="sync_status_modes"
    )
    coord = hass.data[DOMAIN][entry.entry_id]
    hass.states.async_set(
        "zone.home",
        "zoning",
        {"latitude": HOME_LAT, "longitude": HOME_LON, "radius": 200},
    )

    try:
        coord.departure_weekly[2] = (True, 7 * 60)  # Tue 07:00 CET
        coord.charge_start_minutes = 23 * 60  # 23:00 CET == 22:00 UTC (1320)
        coord.charge_duration_hours = 6
        coord.charge_days = [1, 2, 3, 4, 5, 6, 7]
        coord.home_charge_power = 2.3
        coord.home_charge_power_auto = False
        coord.position = {"lat": HOME_LAT, "lon": HOME_LON}

        # 1. mode_off -> None even when chargeAppointPlans matches manual fallback
        coord.set_charge_window_mode("off", sync_charge=False)
        coord._update(
            {
                "position": {"lat": HOME_LAT, "lon": HOME_LON},
                "realtime": {
                    "dumpEnergy": "80",
                    "chargeGunState": "1",
                    "chargeState": "0",
                },
                "fields": {
                    "chargeGunState": "1",
                    "chargeAppointPlans": [
                        {
                            "switchStatus": "1",
                            "startTime": "1320",
                            "timeConsuming": "360",
                            "cycleData": [1, 2, 3, 4, 5, 6, 7],
                        }
                    ],
                },
            }
        )
        await hass.async_block_till_done()
        win_off = hass.states.get("sensor.lepas_scheduled_charging_window")
        assert win_off.attributes["effective_action"] == "noop"
        assert win_off.attributes["plan_reason"] == "mode_off"
        assert win_off.attributes["synced_with_car"] is None

        # 2. fixed_home: switchStatus="1" + matching fields -> True; switchStatus="0" -> False
        coord.set_charge_window_mode("fixed", sync_charge=False)
        await hass.async_block_till_done()
        win_fixed_ok = hass.states.get("sensor.lepas_scheduled_charging_window")
        assert win_fixed_ok.attributes["plan_reason"] == "fixed_home"
        assert win_fixed_ok.attributes["synced_with_car"] is True

        coord._update(
            {
                "fields": {
                    "chargeGunState": "1",
                    "chargeAppointPlans": [{"switchStatus": "0"}],
                }
            }
        )
        await hass.async_block_till_done()
        win_fixed_off_min = hass.states.get("sensor.lepas_scheduled_charging_window")
        assert win_fixed_off_min.attributes["plan_reason"] == "fixed_home"
        assert win_fixed_off_min.attributes["synced_with_car"] is False

        coord._update(
            {
                "fields": {
                    "chargeGunState": "1",
                    "chargeAppointPlans": [
                        {
                            "switchStatus": "0",
                            "startTime": "1320",
                            "timeConsuming": "360",
                            "cycleData": [1, 2, 3, 4, 5, 6, 7],
                        }
                    ],
                }
            }
        )
        await hass.async_block_till_done()
        assert (
            hass.states.get("sensor.lepas_scheduled_charging_window").attributes[
                "synced_with_car"
            ]
            is False
        )

        # 3. smart_home (80% SoC @ 2.3kW => 135m => 04:45 CET = 225 UTC):
        # switchStatus="0" (without startTime) -> False; switchStatus="1" coherent -> True
        coord.set_charge_window_mode("smart_departure", sync_charge=False)
        coord._update(
            {
                "fields": {
                    "chargeGunState": "1",
                    "chargeAppointPlans": [{"switchStatus": "0"}],
                }
            }
        )
        await hass.async_block_till_done()
        win_smart_off = hass.states.get("sensor.lepas_scheduled_charging_window")
        assert win_smart_off.attributes["plan_reason"] == "smart_home"
        assert win_smart_off.attributes["synced_with_car"] is False

        coord._update(
            {
                "fields": {
                    "chargeGunState": "1",
                    "chargeAppointPlans": [
                        {
                            "switchStatus": "1",
                            "startTime": "225",
                            "timeConsuming": "135",
                            "cycleData": [2],
                        }
                    ],
                }
            }
        )
        await hass.async_block_till_done()
        win_smart_ok = hass.states.get("sensor.lepas_scheduled_charging_window")
        assert win_smart_ok.attributes["plan_reason"] == "smart_home"
        assert win_smart_ok.attributes["synced_with_car"] is True

        # 4. already_charged (soc=100, plugged=True) -> None even with matching fallback plan
        coord._update(
            {
                "realtime": {
                    "dumpEnergy": "100",
                    "chargeGunState": "1",
                    "chargeState": "0",
                },
                "fields": {
                    "chargeGunState": "1",
                    "chargeAppointPlans": [
                        {
                            "switchStatus": "1",
                            "startTime": "1320",
                            "timeConsuming": "360",
                            "cycleData": [1, 2, 3, 4, 5, 6, 7],
                        }
                    ],
                },
            }
        )
        await hass.async_block_till_done()
        win_full = hass.states.get("sensor.lepas_scheduled_charging_window")
        assert win_full.attributes["effective_action"] == "noop"
        assert win_full.attributes["plan_reason"] == "already_charged"
        assert win_full.attributes["synced_with_car"] is None

        # 5. away_bypass -> switchStatus="0": True, "1": False, absent: None
        coord.position = {"lat": AWAY_LAT, "lon": AWAY_LON}
        for raw_plan, expected in (
            ([{"switchStatus": "0"}], True),
            (
                [
                    {
                        "switchStatus": "1",
                        "startTime": "225",
                        "timeConsuming": "135",
                        "cycleData": [2],
                    }
                ],
                False,
            ),
            ([{"startTime": "225", "timeConsuming": "135", "cycleData": [2]}], None),
        ):
            coord._update(
                {
                    "position": {"lat": AWAY_LAT, "lon": AWAY_LON},
                    "realtime": {
                        "dumpEnergy": "80",
                        "chargeGunState": "1",
                        "chargeState": "0",
                    },
                    "fields": {
                        "chargeGunState": "1",
                        "chargeAppointPlans": raw_plan,
                    },
                }
            )
            await hass.async_block_till_done()
            win_away = hass.states.get("sensor.lepas_scheduled_charging_window")
            assert win_away.attributes["effective_action"] == "disable"
            assert win_away.attributes["plan_reason"] == "away_bypass"
            assert win_away.attributes["synced_with_car"] is expected

        # 6. late_plug_in -> switchStatus="0": True, "1": False, absent: None
        coord.position = {"lat": HOME_LAT, "lon": HOME_LON}
        current_now[0] = datetime(2026, 11, 17, 5, 30, tzinfo=rome)
        for raw_plan, expected in (
            ([{"switchStatus": "0"}], True),
            (
                [
                    {
                        "switchStatus": "1",
                        "startTime": "225",
                        "timeConsuming": "135",
                        "cycleData": [2],
                    }
                ],
                False,
            ),
            ([{"startTime": "225"}], None),
        ):
            coord._update(
                {
                    "position": {"lat": HOME_LAT, "lon": HOME_LON},
                    "realtime": {
                        "dumpEnergy": "80",
                        "chargeGunState": "1",
                        "chargeState": "0",
                    },
                    "fields": {
                        "chargeGunState": "1",
                        "chargeAppointPlans": raw_plan,
                    },
                }
            )
            await hass.async_block_till_done()
            win_late = hass.states.get("sensor.lepas_scheduled_charging_window")
            assert win_late.attributes["effective_action"] == "disable"
            assert win_late.attributes["plan_reason"] == "late_plug_in"
            assert win_late.attributes["synced_with_car"] is expected
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
