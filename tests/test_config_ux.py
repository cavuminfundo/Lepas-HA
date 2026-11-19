"""Integration and UX tests for Round 2 HA platforms, sensors, and services."""
from __future__ import annotations

from datetime import datetime, time, timezone

import pytest
from homeassistant.const import ATTR_TEMPERATURE, EntityCategory
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, mock_restore_cache

import fixtures as FX
from custom_components.lepas.const import (
    CONF_PIN,
    CONF_TUSERID,
    CONF_VIN,
    DATA_CAPS_PROBED_V3,
    DATA_CAPS_PROBED_V4,
    DATA_VEHICLE_FEATURES,
    DOMAIN,
)
from custom_components.lepas.coordinator import LepasCoordinator
from custom_components.lepas.scheduler import DEPARTURE_DAY_SLUGS
from custom_components.lepas.sensor import LepasDeparturePlan
from custom_components.lepas.switch import LepasScheduledChargeSwitch


def _patch_io(monkeypatch) -> list[tuple[str, dict | None]]:
    """Neutralize external MQTT/cert/poll I/O and record cloud commands."""
    sent: list[tuple[str, dict | None]] = []

    async def fake_send(self, key: str, params: dict | None = None) -> str:
        sent.append((key, params))
        return "ok"

    async def no_backfill(self) -> None:
        return None

    monkeypatch.setattr(LepasCoordinator, "_provision_certs", lambda self: (True, "ok"))
    monkeypatch.setattr(LepasCoordinator, "_connect_car", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_keepalive", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_telemetry_poll", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_drive_watch", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_ensure_vehicle_identity", no_backfill)
    monkeypatch.setattr(LepasCoordinator, "async_send_command", fake_send)
    return sent


async def _setup_entry(
    hass: HomeAssistant,
    *,
    vin: str = FX.VIN,
    entry_id: str = "ux_entry_1",
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


# ───────────────────────── select entities ─────────────────────────


async def test_select_charge_days_options_restore_and_plan(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    mock_restore_cache(
        hass,
        [State("select.lepas_charge_days", "custom", {"days": [1, 4]})],
    )
    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        st = hass.states.get("select.lepas_charge_days")
        assert st is not None
        assert st.state == "custom"
        assert coord.charge_days == [1, 4]
        assert st.attributes["options"] == [
            "all_days",
            "weekdays",
            "weekend",
            "mon_wed_fri",
            "tue_thu_sat",
            "custom",
        ]

        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.lepas_charge_days", "option": "weekdays"},
            blocking=True,
        )
        assert coord.charge_days == [1, 2, 3, 4, 5]
        assert hass.states.get("select.lepas_charge_days").state == "weekdays"

        sw = next(
            e
            for e in hass.data["entity_components"]["switch"].entities
            if isinstance(e, LepasScheduledChargeSwitch)
        )
        assert sw._plan(1)["cycleData"] == [1, 2, 3, 4, 5]

        # Permission 2131=0 fallback forces [1..7] in _plan()
        coord._probed_permessi = {2131: 0}
        assert sw._plan(1)["cycleData"] == [1, 2, 3, 4, 5, 6, 7]
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_select_departure_climate_mode(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        st = hass.states.get("select.lepas_departure_climate_mode")
        assert st is not None
        assert st.state == "at_home"
        assert st.attributes["options"] == ["at_home", "anywhere", "off"]

        await hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": "select.lepas_departure_climate_mode", "option": "anywhere"},
            blocking=True,
        )
        assert coord.departure_climate_mode == "anywhere"
        assert hass.states.get("select.lepas_departure_climate_mode").state == "anywhere"
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_new_entities_feature_gating(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    entry_gated = await _setup_entry(
        hass,
        vin="L8TESTGATED000001",
        entry_id="ux_gated",
        features={"scheduled_charging": False, "climate": False},
    )
    try:
        for gated_eid in (
            "select.lepas_charge_days",
            "select.lepas_departure_climate_mode",
            "button.lepas_apply_charging_schedule",
            "switch.lepas_sync_charge_to_departure",
            "sensor.lepas_scheduled_charging_window",
        ):
            assert hass.states.get(gated_eid) is None, f"{gated_eid} must be gated out"
        # Ungated UX entities remain available
        assert hass.states.get("sensor.lepas_next_departure") is not None
        assert hass.states.get("switch.lepas_quick_departure") is not None
    finally:
        await hass.config_entries.async_unload(entry_gated.entry_id)
        await hass.async_block_till_done()


# ───────────────────────── time / switch / weekly / restore ─────────────────────────


async def test_quick_departure_sync_and_time_updates_and_auto_reset(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    sent = _patch_io(monkeypatch)
    tz = timezone.utc
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 10, 0, tzinfo=tz))

    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        # Existing entity_id preserved
        assert hass.states.get("time.lepas_charge_start_time").state == "08:00:00"
        assert hass.states.get("time.lepas_quick_departure_time").state == "18:00:00"
        assert hass.states.get("switch.lepas_quick_departure").state == "off"
        assert hass.states.get("switch.lepas_sync_charge_to_departure").state == "off"

        # Enable sync_charge_to_departure and quick_departure
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_sync_charge_to_departure"},
            blocking=True,
        )
        assert coord.sync_charge_to_departure is True

        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_quick_departure_time", "time": "07:00:00"},
            blocking=True,
        )
        assert coord.quick_departure_minutes == 420

        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_quick_departure"},
            blocking=True,
        )
        await hass.async_block_till_done(wait_background_tasks=True)

        assert coord.quick_departure_enabled is True
        assert hass.states.get("switch.lepas_quick_departure").state == "on"
        # 07:00 - 6h = 01:00 -> reflected on time.lepas_charge_start_time
        assert coord.charge_start_minutes == 60
        assert hass.states.get("time.lepas_charge_start_time").state == "01:00:00"
        assert any(k == "ricarica_prog_on" for k, _ in sent)

        # Auto-reset when preclimate fires for quick departure
        coord.departure_climate_mode = "anywhere"
        await coord._departure_tick_cb(_now=datetime(2026, 11, 17, 6, 50, tzinfo=tz))
        await hass.async_block_till_done()
        assert coord.quick_departure_enabled is False
        assert hass.states.get("switch.lepas_quick_departure").state == "off"
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_weekly_departure_pairs_and_restore(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    mock_restore_cache(
        hass,
        [
            State("switch.lepas_departure_mon_enabled", "on"),
            State("time.lepas_departure_mon_time", "06:30:00"),
            State("switch.lepas_departure_fri_enabled", "on"),
            State("time.lepas_departure_fri_time", "09:15:00"),
            State("time.lepas_quick_departure_time", "19:45:00"),
            State("switch.lepas_sync_charge_to_departure", "on"),
        ],
    )
    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        for slug in DEPARTURE_DAY_SLUGS.values():
            assert hass.states.get(f"switch.lepas_departure_{slug}_enabled") is not None
            assert hass.states.get(f"time.lepas_departure_{slug}_time") is not None

        assert hass.states.get("switch.lepas_departure_mon_enabled").state == "on"
        assert hass.states.get("time.lepas_departure_mon_time").state == "06:30:00"
        assert coord.departure_weekly[1] == (True, 6 * 60 + 30)
        assert coord.departure_weekly[5] == (True, 9 * 60 + 15)
        assert coord.quick_departure_minutes == 19 * 60 + 45
        assert coord.sync_charge_to_departure is True

        # Interactive update via HA services
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_departure_wed_enabled"},
            blocking=True,
        )
        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_departure_wed_time", "time": "08:20:00"},
            blocking=True,
        )
        assert coord.departure_weekly[3] == (True, 8 * 60 + 20)
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


# ───────────────────────── number & climate sync ─────────────────────────


async def test_number_notify_schedule_and_climate_target_temp_sync(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    mock_restore_cache(
        hass,
        [State("climate.lepas_climate", "off", {ATTR_TEMPERATURE: 23.0})],
    )
    tz = timezone.utc
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 10, 0, tzinfo=tz))

    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        # Restored climate target temperature pushed to coordinator
        assert coord.climate_target_temp == 23.0

        await hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": "climate.lepas_climate", ATTR_TEMPERATURE: 24.0},
            blocking=True,
        )
        assert coord.climate_target_temp == 24.0

        # Number changes notify scheduler and update synced charge start / window
        coord.quick_departure_minutes = 7 * 60
        coord.quick_departure_enabled = True
        coord.sync_charge_to_departure = True
        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.lepas_charge_duration", "value": 4},
            blocking=True,
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        assert coord.charge_duration_hours == 4
        # 07:00 - 4h = 03:00 (180 min)
        assert coord.charge_start_minutes == 180
        assert hass.states.get("time.lepas_charge_start_time").state == "03:00:00"

        await hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": "number.lepas_climate_duration", "value": 20},
            blocking=True,
        )
        assert coord.clima_duration == 20
        assert hass.states.get("sensor.lepas_next_departure").attributes["climate_start_at"].endswith(
            "06:40:00+00:00"
        )
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_climate_target_temp_syncs_from_realtime_without_clobbering_ha_override(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    mock_restore_cache(
        hass,
        [State("climate.lepas_climate", "off", {ATTR_TEMPERATURE: 21.0})],
    )
    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        assert hass.states.get("climate.lepas_climate").attributes[ATTR_TEMPERATURE] == 21.0

        # Auto riporta 23 °C su frontSetTempLeft -> climate.lepas_climate e coordinator si allineano
        coord.async_set_updated_data(
            {**coord.data, "realtime": {"frontSetTempLeft": "23.0", "frontSetTempRight": "23.0"}}
        )
        await hass.async_block_till_done()
        assert hass.states.get("climate.lepas_climate").attributes[ATTR_TEMPERATURE] == 23.0
        assert coord.climate_target_temp == 23.0

        # Cambio manuale da HA (clima OFF) -> successivo poll identico dell'auto non sovrascrive
        await hass.services.async_call(
            "climate",
            "set_temperature",
            {"entity_id": "climate.lepas_climate", ATTR_TEMPERATURE: 22.0},
            blocking=True,
        )
        coord.async_set_updated_data(
            {**coord.data, "realtime": {"frontSetTempLeft": "23.0", "frontSetTempRight": "23.0"}}
        )
        await hass.async_block_till_done()
        assert hass.states.get("climate.lepas_climate").attributes[ATTR_TEMPERATURE] == 22.0

        # Nuovo cambio reale in auto (24 °C) -> HA si aggiorna; sentinella fuori range ("0") -> ignorata
        coord.async_set_updated_data(
            {**coord.data, "realtime": {"frontSetTempLeft": "24.0", "frontSetTempRight": "24.0"}}
        )
        await hass.async_block_till_done()
        assert hass.states.get("climate.lepas_climate").attributes[ATTR_TEMPERATURE] == 24.0
        assert coord.climate_target_temp == 24.0

        coord.async_set_updated_data(
            {**coord.data, "realtime": {"frontSetTempLeft": "0", "frontSetTempRight": "0"}}
        )
        await hass.async_block_till_done()
        assert hass.states.get("climate.lepas_climate").attributes[ATTR_TEMPERATURE] == 24.0
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


# ───────────────────────── scheduled charging fallback & apply button ─────────────────────────


async def test_scheduled_charging_realtime_fallback_and_priority(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    mock_restore_cache(
        hass,
        [State("switch.lepas_scheduled_charging", "on")],
    )
    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        # Initially restored as ON when no telemetry present
        assert hass.states.get("switch.lepas_scheduled_charging").state == "on"

        # realtime appointmentChargeState = "0" -> off
        coord._on_probe_data({"appointmentChargeState": "0"})
        await hass.async_block_till_done()
        assert hass.states.get("switch.lepas_scheduled_charging").state == "off"

        # realtime appointmentChargeState = "1" -> on
        coord._on_probe_data({"appointmentChargeState": "1"})
        await hass.async_block_till_done()
        assert hass.states.get("switch.lepas_scheduled_charging").state == "on"

        # Unknown ("2" or None) -> None -> falls back to RestoreEntity ("on")
        coord._on_probe_data({"appointmentChargeState": "2"})
        await hass.async_block_till_done()
        assert hass.states.get("switch.lepas_scheduled_charging").state == "on"

        # chargeAppointPlans in fields takes priority over realtime appointmentChargeState
        coord._update(
            {
                "realtime": {"appointmentChargeState": "1"},
                "fields": {"chargeAppointPlans": [{"switchStatus": "0", "startTime": "480"}]},
            }
        )
        await hass.async_block_till_done()
        assert hass.states.get("switch.lepas_scheduled_charging").state == "off"
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_apply_charging_schedule_button(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    sent = _patch_io(monkeypatch)
    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        reg = er.async_get(hass)
        ent_entry = reg.async_get("button.lepas_apply_charging_schedule")
        assert ent_entry is not None
        assert ent_entry.entity_category == EntityCategory.CONFIG

        coord.charge_start_minutes = 23 * 60
        coord.charge_duration_hours = 6
        coord.charge_days = [1, 2, 3, 4, 5]

        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.lepas_apply_charging_schedule"},
            blocking=True,
        )
        assert len(sent) == 1
        key, params = sent[0]
        assert key == "ricarica_prog_on"
        assert params == {
            "mainSwitch": 1,
            "chargeAppointPlans": [
                {
                    "cycleData": [1, 2, 3, 4, 5],
                    "startTime": 23 * 60,
                    "switchStatus": 1,
                    "timeConsuming": 360,
                }
            ],
        }
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


# ───────────────────────── diagnostic sensors ─────────────────────────


async def test_charging_window_and_next_departure_sensors_multilang_and_riepilogo(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    tz = timezone.utc
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 10, 0, tzinfo=tz))  # Monday

    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        # Scheduled charging window: 23:00 + 6h = 05:00 next day
        coord.charge_start_minutes = 23 * 60
        coord.charge_duration_hours = 6
        coord.charge_days = [1, 2, 3, 4, 5, 6, 7]

        for lang, expected in (
            ("it", "23:00 → Giorno dopo 05:00 · Lun–Dom"),
            ("en", "23:00 → Next day 05:00 · Mon–Sun"),
            ("nl", "23:00 → Volgende dag 05:00 · Ma–Zo"),
        ):
            hass.config.language = lang
            coord.async_update_listeners()
            await hass.async_block_till_done()
            st = hass.states.get("sensor.lepas_scheduled_charging_window")
            assert st.state == expected
            assert st.attributes["next_day"] is True
            assert st.attributes["days"] == [1, 2, 3, 4, 5, 6, 7]
            assert st.attributes["synced_with_car"] is None

        # Car reports matching vs mismatching plan
        coord._update(
            {
                "fields": {
                    "chargeAppointPlans": [
                        {
                            "cycleData": [1, 2, 3, 4, 5, 6, 7],
                            "startTime": str(23 * 60),
                            "timeConsuming": "360",
                            "switchStatus": "1",
                        }
                    ]
                }
            }
        )
        await hass.async_block_till_done()
        assert hass.states.get("sensor.lepas_scheduled_charging_window").attributes["synced_with_car"] is True

        coord.charge_duration_hours = 5
        coord.async_update_listeners()
        await hass.async_block_till_done()
        assert hass.states.get("sensor.lepas_scheduled_charging_window").attributes["synced_with_car"] is False

        # Daytime non-next-day window with non-contiguous days
        coord.charge_start_minutes = 8 * 60
        coord.charge_duration_hours = 4
        coord.charge_days = [1, 3, 5]
        hass.config.language = "en"
        coord.async_update_listeners()
        await hass.async_block_till_done()
        day_win = hass.states.get("sensor.lepas_scheduled_charging_window")
        assert day_win.state == "08:00 → 12:00 · Mon, Wed, Fri"
        assert day_win.attributes["next_day"] is False
        assert day_win.attributes["days"] == [1, 3, 5]

        # Next departure: disabled
        for lang, expected_disabled in (("it", "Disattivata"), ("en", "Disabled"), ("nl", "Uitgeschakeld")):
            hass.config.language = lang
            coord.async_update_listeners()
            await hass.async_block_till_done()
            nd = hass.states.get("sensor.lepas_next_departure")
            assert nd.state == expected_disabled
            assert nd.attributes["source"] is None
            assert nd.attributes["departure_at"] is None

        # Next departure: quick today 18:00
        coord.quick_departure_enabled = True
        coord.quick_departure_minutes = 18 * 60
        coord.sync_charge_to_departure = True
        coord.charge_duration_hours = 6
        for lang, expected_quick in (
            ("it", "Oggi 18:00 (rapida · clima 17:45)"),
            ("en", "Today 18:00 (quick · climate 17:45)"),
            ("nl", "Vandaag 18:00 (snel · klimaat 17:45)"),
        ):
            hass.config.language = lang
            coord.async_update_listeners()
            await hass.async_block_till_done()
            nd = hass.states.get("sensor.lepas_next_departure")
            assert nd.state == expected_quick
            assert nd.attributes["source"] == "quick"
            assert nd.attributes["weekday"] == 1
            assert nd.attributes["climate_mode"] == "at_home"
            assert nd.attributes["sync_charging"] is True
            assert nd.attributes["planned_charge_start"] == "12:00"
            assert nd.attributes["departure_at"] == "2026-11-16T18:00:00+00:00"
            assert nd.attributes["climate_start_at"] == "2026-11-16T17:45:00+00:00"

        # Next departure: weekly tomorrow Tuesday 13:30
        coord.quick_departure_enabled = False
        coord.departure_weekly[2] = (True, 13 * 60 + 30)
        hass.config.language = "it"
        coord.async_update_listeners()
        await hass.async_block_till_done()
        nd_weekly = hass.states.get("sensor.lepas_next_departure")
        assert nd_weekly.state == "Domani mar 13:30 (clima 13:15)"
        assert nd_weekly.attributes["source"] == "weekly"
        assert nd_weekly.attributes["weekday"] == 2

        # LepasDeparturePlan converts UTC travelTime to hass.config.time_zone and preserves riepilogo
        hass.config.time_zone = "UTC"
        dp = next(
            e
            for e in hass.data["entity_components"]["sensor"].entities
            if isinstance(e, LepasDeparturePlan)
        )
        coord._on_probe_data(
            {
                "appointmentTravelSetVOS": [
                    {"travelTime": 350, "travelDate": [1, 2, 3, 4, 5], "switcher": 1}
                ]
            }
        )
        await hass.async_block_till_done()
        attrs = dp.extra_state_attributes
        assert attrs["attiva"] is True
        assert attrs["orario"] == "05:50"
        assert attrs["giorni"] == [1, 2, 3, 4, 5]
        assert attrs["giorni_testo"] == "lun, mar, mer, gio, ven"
        assert "05:50" in attrs["riepilogo"]
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


# ───────────────────────── services & lifecycle ─────────────────────────


async def test_services_validation_and_actions(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    sent = _patch_io(monkeypatch)
    tz = timezone.utc
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 10, 0, tzinfo=tz))

    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        # Accepts datetime.time, "HH:MM", "HH:MM:SS"
        await hass.services.async_call(
            DOMAIN,
            "set_quick_departure",
            {"time": time(7, 45), "enabled": True, "sync_charging": True},
            blocking=True,
        )
        assert coord.quick_departure_minutes == 7 * 60 + 45
        assert coord.quick_departure_enabled is True
        assert coord.sync_charge_to_departure is True
        assert len(sent) == 1

        await hass.services.async_call(
            DOMAIN,
            "set_quick_departure",
            {"time": "08:15:30", "enabled": False},
            blocking=True,
        )
        assert coord.quick_departure_minutes == 8 * 60 + 15
        assert coord.quick_departure_enabled is False

        await hass.services.async_call(
            DOMAIN,
            "set_charging_schedule",
            {"start_time": "22:30", "duration_hours": 5, "days": "weekdays", "apply": False},
            blocking=True,
        )
        assert coord.charge_start_minutes == 22 * 60 + 30
        assert coord.charge_duration_hours == 5
        assert coord.charge_days == [1, 2, 3, 4, 5]
        assert len(sent) == 1  # apply=False did not send command
        assert hass.states.get("time.lepas_charge_start_time").state == "22:30:00"
        assert hass.states.get("number.lepas_charge_duration").state == "5.0"
        assert hass.states.get("select.lepas_charge_days").state == "weekdays"

        await hass.services.async_call(
            DOMAIN,
            "set_charging_schedule",
            {"start_time": "23:15:00", "duration_hours": 4, "days": [1, 4], "apply": True},
            blocking=True,
        )
        assert len(sent) == 2
        assert sent[-1][0] == "ricarica_prog_on"
        assert sent[-1][1]["chargeAppointPlans"][0]["cycleData"] == [1, 4]
        assert hass.states.get("select.lepas_charge_days").state == "custom"

        # Validation errors raise ServiceValidationError
        for bad_dur in (True, False, 0, 13, 4.5, "6"):
            with pytest.raises(ServiceValidationError):
                await hass.services.async_call(
                    DOMAIN,
                    "set_charging_schedule",
                    {"duration_hours": bad_dur},
                    blocking=True,
                )

        for bad_time in ("25:00", "12:60", "not-a-time", "12:00:60", 123):
            with pytest.raises(ServiceValidationError):
                await hass.services.async_call(
                    DOMAIN,
                    "set_quick_departure",
                    {"time": bad_time},
                    blocking=True,
                )

        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN,
                "set_charging_schedule",
                {"days": "invalid_day_token"},
                blocking=True,
            )
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_services_multi_entry_and_lifecycle(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)

    entry1 = await _setup_entry(hass, vin="L8MULTI0000000001", entry_id="entry_1")
    assert hass.services.has_service(DOMAIN, "set_quick_departure")
    assert hass.services.has_service(DOMAIN, "set_charging_schedule")

    entry2 = await _setup_entry(hass, vin="L8MULTI0000000002", entry_id="entry_2")
    coord1 = hass.data[DOMAIN][entry1.entry_id]
    coord2 = hass.data[DOMAIN][entry2.entry_id]

    try:
        # Missing entry_id when >1 entry loaded -> ServiceValidationError
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN,
                "set_quick_departure",
                {"time": "07:00"},
                blocking=True,
            )

        # Invalid entry_id -> ServiceValidationError
        with pytest.raises(ServiceValidationError):
            await hass.services.async_call(
                DOMAIN,
                "set_quick_departure",
                {"entry_id": "nonexistent", "time": "07:00"},
                blocking=True,
            )

        # Valid entry_id targets only entry2
        await hass.services.async_call(
            DOMAIN,
            "set_quick_departure",
            {"entry_id": entry2.entry_id, "time": "07:15"},
            blocking=True,
        )
        assert coord2.quick_departure_enabled is True
        assert coord2.quick_departure_minutes == 7 * 60 + 15
        assert coord1.quick_departure_enabled is False

        # Unload 1 of 2 -> services stay registered
        assert await hass.config_entries.async_unload(entry1.entry_id)
        await hass.async_block_till_done()
        assert hass.services.has_service(DOMAIN, "set_quick_departure")
        assert hass.services.has_service(DOMAIN, "set_charging_schedule")

        # Now only 1 entry remains -> omitting entry_id works
        await hass.services.async_call(
            DOMAIN,
            "set_quick_departure",
            {"time": "09:00"},
            blocking=True,
        )
        assert coord2.quick_departure_minutes == 9 * 60
    finally:
        if entry1.entry_id in hass.data.get(DOMAIN, {}):
            await hass.config_entries.async_unload(entry1.entry_id)
        if entry2.entry_id in hass.data.get(DOMAIN, {}):
            await hass.config_entries.async_unload(entry2.entry_id)
        await hass.async_block_till_done()

    # Unloading the last entry removes both services
    assert not hass.services.has_service(DOMAIN, "set_quick_departure")
    assert not hass.services.has_service(DOMAIN, "set_charging_schedule")


async def test_setup_failure_after_forward_cleans_up_services(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)

    def _boom_task(coro, *_a, **_kw):
        coro.close()
        raise RuntimeError("boom post-forward")

    monkeypatch.setattr(hass, "async_create_background_task", _boom_task)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Lepas Fail Cleanup",
        unique_id="L8FAILCLEANUP0001",
        data={
            CONF_VIN: "L8FAILCLEANUP0001",
            CONF_TUSERID: FX.TUSERID,
            "email": FX.EMAIL,
            CONF_PIN: FX.PIN,
        },
        entry_id="fail_cleanup",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id) is False
    await hass.async_block_till_done()

    assert not hass.data.get(DOMAIN)
    assert not hass.services.has_service(DOMAIN, "set_quick_departure")
    assert not hass.services.has_service(DOMAIN, "set_charging_schedule")


# ───────────────────────── v1.21.0 native departure, battery heat & sensor UX ─────────────────────────


async def test_native_departure_and_battery_heat_feature_gating(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    entry_no_batt = await _setup_entry(
        hass,
        vin="L8NOBATT000000001",
        entry_id="ux_no_216",
        features={"battery_pack_heat": False, "scheduled_departure_control": True},
    )
    try:
        for hidden in (
            "switch.lepas_battery_pack_heat",
            "time.lepas_battery_pack_heat_time",
            "switch.lepas_sync_battery_heat_to_departure",
        ):
            assert hass.states.get(hidden) is None, f"{hidden} must be hidden when 216=0"
        assert hass.states.get("switch.lepas_native_departure_sync") is not None
        assert hass.states.get("button.lepas_apply_departure_schedule") is not None
    finally:
        await hass.config_entries.async_remove(entry_no_batt.entry_id)
        await hass.async_block_till_done()

    entry_no_dep = await _setup_entry(
        hass,
        vin="L8NODEP0000000001",
        entry_id="ux_no_212",
        features={"scheduled_departure_control": False, "battery_pack_heat": True},
    )
    try:
        assert hass.states.get("switch.lepas_native_departure_sync") is None
        assert hass.states.get("button.lepas_apply_departure_schedule") is None
        assert hass.states.get("switch.lepas_battery_pack_heat") is not None
        assert hass.states.get("time.lepas_battery_pack_heat_time") is not None
        assert hass.states.get("switch.lepas_sync_battery_heat_to_departure") is not None
    finally:
        await hass.config_entries.async_remove(entry_no_dep.entry_id)
        await hass.async_block_till_done()


async def test_native_departure_entities_restore_and_apply_button(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    sent = _patch_io(monkeypatch)
    tz = timezone.utc
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 6, 0, tzinfo=tz))
    mock_restore_cache(
        hass,
        [
            State("switch.lepas_native_departure_sync", "on"),
            State("switch.lepas_sync_battery_heat_to_departure", "on"),
            State("switch.lepas_quick_departure", "on"),
            State("time.lepas_quick_departure_time", "08:00:00"),
            State("switch.lepas_departure_mon_enabled", "on"),
            State("time.lepas_departure_mon_time", "07:30:00"),
        ],
    )

    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        # Boot restore must NOT dispatch cloud sync commands
        assert coord.native_departure_sync is True
        assert coord.sync_battery_heat_to_departure is True
        assert coord.quick_departure_enabled is True
        assert hass.states.get("switch.lepas_native_departure_sync").state == "on"
        assert sent == []

        reg = er.async_get(hass)
        btn_entry = reg.async_get("button.lepas_apply_departure_schedule")
        assert btn_entry is not None
        assert btn_entry.entity_category == EntityCategory.CONFIG

        # Manual apply button sends travelAppointControl
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.lepas_apply_departure_schedule"},
            blocking=True,
        )
        assert len(sent) == 1
        assert sent[0][0] == "partenza_prog_on"
        assert sent[0][1]["mainSwitcher"] == "1"

        # Turn off quick departure & weekday switches -> stays local draft until explicit Apply/Disable
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_quick_departure"},
            blocking=True,
        )
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_departure_mon_enabled"},
            blocking=True,
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        assert not any(k == "partenza_prog_off" for k, _ in sent)
        assert coord.has_pending_departure_changes() is True

        # Explicit apply when no departure is active sends partenza_prog_off & disables auto-sync
        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": "button.lepas_apply_departure_schedule"},
            blocking=True,
        )
        await hass.async_block_till_done(wait_background_tasks=True)
        assert any(k == "partenza_prog_off" for k, _ in sent)
        assert coord.native_departure_sync is False

        sent.clear()
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_native_departure_sync"},
            blocking=True,
        )
        assert coord.native_departure_sync is False
        assert sent == []
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_battery_pack_heat_switch_time_restore_telemetry_and_optimistic_revert(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    from homeassistant.exceptions import HomeAssistantError

    sent = _patch_io(monkeypatch)
    tz = timezone.utc
    hass.config.time_zone = "UTC"
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 6, 0, tzinfo=tz))
    mock_restore_cache(
        hass,
        [
            State("switch.lepas_battery_pack_heat", "on"),
            State("time.lepas_battery_pack_heat_time", "06:15:00"),
        ],
    )

    entry = await _setup_entry(hass)
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        assert hass.states.get("switch.lepas_battery_pack_heat").state == "on"
        assert coord.battery_heat_enabled is True
        assert hass.states.get("time.lepas_battery_pack_heat_time").state == "06:15:00"
        assert coord.battery_heat_minutes == 6 * 60 + 15
        assert sent == []

        # Changing time while enabled dispatches async_apply_battery_pack_heat
        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_battery_pack_heat_time", "time": "06:45:00"},
            blocking=True,
        )
        assert coord.battery_heat_minutes == 6 * 60 + 45
        assert sent == [("battery_heat_on", {"switchState": "1", "startTime": str(6 * 60 + 45)})]

        # Telemetry from realtime and fields updates state (fields takes priority)
        coord._on_probe_data({"batteryPackHeatState": "0"})
        await hass.async_block_till_done()
        assert hass.states.get("switch.lepas_battery_pack_heat").state == "off"

        coord._update(
            {
                "realtime": {"batteryPackHeatState": "0"},
                "fields": {"batteryPackHeatState": "1"},
            }
        )
        await hass.async_block_till_done()
        assert hass.states.get("switch.lepas_battery_pack_heat").state == "on"

        # Turn off via switch
        sent.clear()
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_battery_pack_heat"},
            blocking=True,
        )
        assert sent == [("battery_heat_off", {"switchState": "0", "startTime": "0"})]
        assert hass.states.get("switch.lepas_battery_pack_heat").state == "off"
        assert coord.battery_heat_enabled is False

        # Changing time while disabled updates local time WITHOUT sending cloud command
        sent.clear()
        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_battery_pack_heat_time", "time": "05:30:00"},
            blocking=True,
        )
        assert coord.battery_heat_minutes == 5 * 60 + 30
        assert sent == []

        # Optimistic revert on error when turning on fails
        # First clear fields so state tracks coordinator/optimistic cleanly
        coord._update({"fields": {}, "realtime": {}})
        await hass.async_block_till_done()
        assert hass.states.get("switch.lepas_battery_pack_heat").state == "off"

        async def failing_send(self, key: str, params: dict | None = None) -> str:
            raise RuntimeError("backend down")

        monkeypatch.setattr(LepasCoordinator, "async_send_command", failing_send)
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                "switch",
                "turn_on",
                {"entity_id": "switch.lepas_battery_pack_heat"},
                blocking=True,
            )
        assert hass.states.get("switch.lepas_battery_pack_heat").state == "off"
        assert coord.battery_heat_enabled is False
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_schedule_switches_and_times_notify_propagation_flags(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    mock_restore_cache(
        hass,
        [
            State("switch.lepas_native_departure_sync", "on"),
            State("switch.lepas_sync_battery_heat_to_departure", "on"),
            State("switch.lepas_quick_departure", "on"),
            State("time.lepas_quick_departure_time", "07:00:00"),
            State("switch.lepas_departure_mon_enabled", "on"),
            State("time.lepas_departure_mon_time", "07:30:00"),
        ],
    )

    calls: list[dict[str, bool]] = []
    orig_notify = LepasCoordinator.notify_schedule_changed

    def spy_notify(self, *, sync_charge: bool = False, sync_native: bool = False, sync_battery: bool = False) -> None:
        calls.append({"sync_charge": sync_charge, "sync_native": sync_native, "sync_battery": sync_battery})
        orig_notify(self, sync_charge=sync_charge, sync_native=sync_native, sync_battery=sync_battery)

    monkeypatch.setattr(LepasCoordinator, "notify_schedule_changed", spy_notify)

    entry = await _setup_entry(hass)
    try:
        # Every boot restore call must keep all sync_* flags False
        assert calls
        assert all(
            not c["sync_charge"] and not c["sync_native"] and not c["sync_battery"]
            for c in calls
        )

        # LepasScheduleSwitch("native_departure_sync") passes ONLY sync_native=enabled
        calls.clear()
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_native_departure_sync"},
            blocking=True,
        )
        assert calls == [{"sync_charge": False, "sync_native": False, "sync_battery": False}]
        calls.clear()
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_native_departure_sync"},
            blocking=True,
        )
        assert calls == [{"sync_charge": False, "sync_native": True, "sync_battery": False}]

        # LepasScheduleSwitch("sync_battery_heat_to_departure") passes ONLY sync_battery=enabled
        calls.clear()
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_sync_battery_heat_to_departure"},
            blocking=True,
        )
        assert calls == [{"sync_charge": False, "sync_native": False, "sync_battery": False}]
        calls.clear()
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_sync_battery_heat_to_departure"},
            blocking=True,
        )
        assert calls == [{"sync_charge": False, "sync_native": False, "sync_battery": True}]

        # LepasWeeklyDepartureSwitch: sync_charge=enabled, sync_native=False (draft until Apply), sync_battery=True
        calls.clear()
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_departure_mon_enabled"},
            blocking=True,
        )
        assert calls == [{"sync_charge": False, "sync_native": False, "sync_battery": True}]
        calls.clear()
        await hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": "switch.lepas_departure_mon_enabled"},
            blocking=True,
        )
        assert calls == [{"sync_charge": True, "sync_native": False, "sync_battery": True}]

        # LepasWeeklyDepartureTime: sync_charge untouched when day disabled, sync_native=False, sync_battery=True
        calls.clear()
        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_departure_tue_time", "time": "08:15:00"},
            blocking=True,
        )
        assert calls == [{"sync_charge": False, "sync_native": False, "sync_battery": True}]

        # quick_departure switch off/on + quick_departure_time set_value (draft until Apply/apply_native)
        calls.clear()
        await hass.services.async_call(
            "switch",
            "turn_off",
            {"entity_id": "switch.lepas_quick_departure"},
            blocking=True,
        )
        assert calls == [{"sync_charge": False, "sync_native": False, "sync_battery": True}]
        calls.clear()
        await hass.services.async_call(
            "time",
            "set_value",
            {"entity_id": "time.lepas_quick_departure_time", "time": "09:10:00"},
            blocking=True,
        )
        assert calls == [{"sync_charge": False, "sync_native": False, "sync_battery": True}]
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_next_departure_restore_extras_and_departure_plan_synced_with_ha(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    from zoneinfo import ZoneInfo

    _patch_io(monkeypatch)
    rome = ZoneInfo("Europe/Rome")
    hass.config.time_zone = "Europe/Rome"
    monkeypatch.setattr(dt_util, "now", lambda: datetime(2026, 11, 16, 6, 0, tzinfo=rome))
    mock_restore_cache(
        hass,
        [
            State(
                "sensor.lepas_next_departure",
                "Disabled",
                {
                    "climate_extras": [
                        "driver_seat_heating",
                        "driver_seat_ventilation",  # mutual exclusion -> ventilation wins
                        "steering_wheel_heating",
                        "windshield_defrost",  # filtered out by feature gating below
                    ]
                },
            )
        ],
    )

    entry = await _setup_entry(
        hass,
        features={
            "driver_seat_heating": True,
            "driver_seat_ventilation": True,
            "steering_wheel_heating": True,
            "front_windshield_electric": False,
        },
    )
    coord = hass.data[DOMAIN][entry.entry_id]

    try:
        # Restored, normalized (mutual exclusion resolved), and capability-filtered
        assert coord.departure_climate_extras == ["driver_seat_ventilation", "steering_wheel_heating"]
        nd = hass.states.get("sensor.lepas_next_departure")
        assert nd.attributes["climate_extras"] == ["driver_seat_ventilation", "steering_wheel_heating"]
        assert "windshield_defrost" not in nd.attributes["allowed_climate_extras"]
        assert "steering_wheel_heating" in nd.attributes["allowed_climate_extras"]
        assert nd.attributes["battery_heat_start"] is None

        # When departure + battery heat sync active -> battery_heat_start = T_dep - 30 min
        coord.departure_weekly[1] = (True, 7 * 60)
        coord.sync_battery_heat_to_departure = True
        coord.async_update_listeners()
        await hass.async_block_till_done()
        nd = hass.states.get("sensor.lepas_next_departure")
        assert nd.attributes["battery_heat_start"] == "06:30"

        # LepasDeparturePlan.synced_with_ha:
        # 1) HA has active Mon 07:00 CET (06:00 UTC = 360, weekday [1]) -> matching car plan -> True
        coord.sync_battery_heat_to_departure = False
        coord.departure_weekly[1] = (True, 7 * 60)
        coord._on_probe_data(
            {
                "appointmentTravelSetVOS": [
                    {"switcher": "1", "travelTime": 360, "travelDate": [1]}
                ]
            }
        )
        await hass.async_block_till_done()
        dp = hass.states.get("sensor.lepas_scheduled_departure")
        assert dp.attributes["orario"] == "07:00"  # AB-LEP-009 UTC->CET preserved
        assert dp.attributes["synced_with_ha"] is True

        # 2) Mismatched car time -> False
        coord._on_probe_data(
            {
                "appointmentTravelSetVOS": [
                    {"switcher": "1", "travelTime": 300, "travelDate": [1]}
                ]
            }
        )
        await hass.async_block_till_done()
        assert hass.states.get("sensor.lepas_scheduled_departure").attributes["synced_with_ha"] is False

        # 3) HA has NO active departure and car switcher == "0" -> True
        coord.departure_weekly[1] = (False, 7 * 60)
        coord._on_probe_data(
            {
                "appointmentTravelSetVOS": [
                    {"switcher": "0", "travelTime": 360, "travelDate": [1]}
                ]
            }
        )
        await hass.async_block_till_done()
        assert hass.states.get("sensor.lepas_scheduled_departure").attributes["synced_with_ha"] is True

        # 4) HA has NO active departure and car mainSwitcher == "0" -> True
        coord._on_probe_data(
            {
                "mainSwitcher": "0",
                "appointmentTravelSetVOS": [
                    {"switcher": "1", "travelTime": 360, "travelDate": [1]}
                ],
            }
        )
        await hass.async_block_till_done()
        assert hass.states.get("sensor.lepas_scheduled_departure").attributes["synced_with_ha"] is True

        # 5) HA has NO active departure and car switcher == "1" -> False
        coord._on_probe_data(
            {
                "appointmentTravelSetVOS": [
                    {"switcher": "1", "travelTime": 360, "travelDate": [1]}
                ]
            }
        )
        await hass.async_block_till_done()
        assert hass.states.get("sensor.lepas_scheduled_departure").attributes["synced_with_ha"] is False

        # 6) Unparseable travelTime when active -> None
        coord.departure_weekly[1] = (True, 7 * 60)
        coord._on_probe_data(
            {
                "appointmentTravelSetVOS": [
                    {"switcher": "1", "travelTime": "bad", "travelDate": [1]}
                ]
            }
        )
        await hass.async_block_till_done()
        assert hass.states.get("sensor.lepas_scheduled_departure").attributes["synced_with_ha"] is None

        # 7) Midnight CET->UTC rollover: Mon 00:30 CET == Sun 23:30 UTC (1410, [7])
        coord.departure_weekly[1] = (True, 30)
        coord._on_probe_data(
            {
                "appointmentTravelSetVOS": [
                    {"switcher": "1", "travelTime": 1410, "travelDate": [7]}
                ]
            }
        )
        await hass.async_block_till_done()
        dp_roll = hass.states.get("sensor.lepas_scheduled_departure")
        assert dp_roll.attributes["orario"] == "00:30"
        assert dp_roll.attributes["giorni"] == [1]
        assert dp_roll.attributes["synced_with_ha"] is True
    finally:
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()


async def test_next_departure_ignores_invalid_restored_climate_extras(
    hass: HomeAssistant, cloud, monkeypatch
) -> None:
    _patch_io(monkeypatch)
    mock_restore_cache(
        hass,
        [State("sensor.lepas_next_departure", "Disabled", {"climate_extras": ["bogus_key"]})],
    )
    entry = await _setup_entry(hass, vin="L8BADEXTRAS000001", entry_id="ux_bad_extras")
    try:
        coord = hass.data[DOMAIN][entry.entry_id]
        assert coord.departure_climate_extras == []
        assert hass.states.get("sensor.lepas_next_departure").attributes["climate_extras"] == []
    finally:
        await hass.config_entries.async_remove(entry.entry_id)
        await hass.async_block_till_done()
