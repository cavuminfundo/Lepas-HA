"""Test delle capability per VIN, filtraggio entità e ripristino posizione."""
from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.lepas.__init__ import async_cleanup_disabled_entities
from custom_components.lepas.const import (
    CONF_VIN,
    DATA_CAPS_PROBED_V2,
    DATA_CAPS_PROBED_V3,
    DATA_VEHICLE_FEATURES,
    DOMAIN,
    ENTITY_FEATURE_MAP,
    entity_allowed,
    features_from_permissions,
)
from custom_components.lepas.coordinator import LepasCoordinator
from custom_components.lepas.naming import ID_PREFIX
from custom_components.lepas.sensor import _waiting_text


def test_v3_marker_distinct_from_v2():
    """Il marcatore V3 deve essere distinto da V2 per forzare il backfill una volta sola."""
    assert DATA_CAPS_PROBED_V3 != DATA_CAPS_PROBED_V2
    assert DATA_CAPS_PROBED_V3 == "caps_probed_v3"
    assert DATA_VEHICLE_FEATURES == "vehicle_features"


def test_features_fail_open_on_empty_or_none():
    """In caso di assenza dati o permessi vuoti, fail-open (nessuna feature disattivata)."""
    assert features_from_permissions(None) == {}
    assert features_from_permissions({}) == {}


def test_features_lepas_l8_real_profile():
    """Profilo reale 308 voci Lepas L8 PHEV: optional assenti -> False, presenti -> True."""
    perms = {
        202: 1, 203: 1, 204: 1, 205: 1, 206: 1, 207: 1, 209: 1, 210: 1,
        213: 1, 214: 1, 232: 1, 2045: 1, 2046: 1,
        2141: 1, 2142: 1, 2143: 1, 2144: 1,
        208: 0, 2081: 0, 2082: 0,
        215: 0, 2151: 0, 20416: 0,
        220: 0, 2201: 0, 2202: 0,
        401: 0, 4011: 0,
        2145: 0, 2146: 0, 2147: 0, 2148: 0,
        20412: 0, 20413: 0, 20414: 0, 20415: 0,
    }
    vf = features_from_permissions(perms)
    assert vf["steering_wheel_heating"] is False
    assert vf["front_windshield_electric"] is False
    assert vf["instant_charging"] is False
    assert vf["alarm"] is False
    assert vf["rear_left_seat_heating"] is False
    assert vf["rear_right_seat_ventilation"] is False
    assert vf["rear_center_seat"] is False
    assert vf["sunroof"] is True
    assert vf["front_windshield_defog"] is True
    assert vf["driver_seat_heating"] is True
    assert vf["scheduled_charging"] is True
    assert vf["windows"] is True
    assert vf["trunk"] is True
    assert vf["locks"] is True
    assert vf["find_car"] is True
    assert vf["climate"] is True


def test_features_uk_profile_enables_electric_windshield_and_wheel():
    """Profilo UK con parabrezza elettrico (215), volante riscaldato (208) e antifurto (401)."""
    perms = {208: 1, 2081: 1, 215: 1, 2151: 1, 214: 1, 2145: 1, 401: 1}
    vf = features_from_permissions(perms)
    assert vf["steering_wheel_heating"] is True
    assert vf["front_windshield_electric"] is True
    assert vf["rear_left_seat_heating"] is True
    assert vf["rear_center_seat"] is True
    assert vf["alarm"] is True


def test_features_partial_perms_fail_open():
    """Le chiavi non presenti nella risposta permessi non devono mai diventare False."""
    vf = features_from_permissions({208: 0})
    assert vf == {"steering_wheel_heating": False}
    assert vf.get("alarm", True) is True
    assert vf.get("sunroof", True) is True


async def test_entity_feature_map_alignment(hass: HomeAssistant, integrazione_avviata):
    """Tutti i suffissi in ENTITY_FEATURE_MAP devono corrispondere a entità registrate dalle piattaforme."""
    reg = er.async_get(hass)
    vin = integrazione_avviata.data[CONF_VIN]
    p_vin = f"{vin}_"
    p_pref = f"{ID_PREFIX}_{vin}_"
    registered_pairs: set[tuple[str, str]] = set()
    for ent in er.async_entries_for_config_entry(reg, integrazione_avviata.entry_id):
        uid = ent.unique_id
        if uid.startswith(p_pref):
            sfx = uid[len(p_pref) :]
        elif uid.startswith(p_vin):
            sfx = uid[len(p_vin) :]
        else:
            continue
        registered_pairs.add((ent.domain, sfx))

    for (domain, suffix), feat in ENTITY_FEATURE_MAP.items():
        assert (domain, suffix) in registered_pairs, (
            f"Coppia {(domain, suffix)} non registrata dalle piattaforme"
        )
        assert isinstance(feat, str) and feat


def test_entity_allowed_helper():
    """entity_allowed rispetta coord.feature_enabled o True per suffissi non mappati."""
    coord = MagicMock()
    coord.feature_enabled.side_effect = lambda f: f != "alarm"

    # Non in mappa -> sempre True
    assert entity_allowed(coord, "sensor", "battery") is True
    # In mappa -> coord.feature_enabled
    assert entity_allowed(coord, "switch", "antifurto") is False
    assert entity_allowed(coord, "button", "cmd_antifurto_on") is False
    assert entity_allowed(coord, "switch", "steerWheelHeating") is True


async def test_ensure_vehicle_identity_v3_branches(hass: HomeAssistant, monkeypatch):
    """Backfill v3: aggiorna entry.data, ctx.permessi in-place e schedula reload se ci sono feature False."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain=DOMAIN, data={"vin": "VIN123", "caps_probed_v2": True}, entry_id="e1")
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})["e1"] = coord
    ctx_orig = coord.ctx

    reloads = []
    monkeypatch.setattr(hass.config_entries, "async_schedule_reload", lambda eid: reloads.append(eid))
    monkeypatch.setattr(coord, "_fetch_vehicle_identity", lambda: {"caps_probed_v2": True})
    await coord.async_ensure_vehicle_identity()
    assert not entry.data.get(DATA_CAPS_PROBED_V3)
    assert reloads == []

    coord._probed_permessi = {208: 0, 207: 1}
    monkeypatch.setattr(
        coord,
        "_fetch_vehicle_identity",
        lambda: {DATA_CAPS_PROBED_V3: True, DATA_VEHICLE_FEATURES: {"steering_wheel_heating": False, "sunroof": True}},
    )
    await coord.async_ensure_vehicle_identity()
    assert entry.data.get(DATA_CAPS_PROBED_V3) is True
    assert coord.ctx is ctx_orig
    assert coord.ctx.permessi == {208: 0, 207: 1}
    assert reloads == ["e1"]


async def test_cleanup_disabled_entities(hass: HomeAssistant):
    """async_cleanup_disabled_entities rimuove solo le entità disabilitate dell'entry_id specificato."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry1 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_VIN: "VIN1",
            DATA_VEHICLE_FEATURES: {"steering_wheel_heating": False, "alarm": False, "sunroof": True},
        },
        entry_id="e1",
    )
    entry1.add_to_hass(hass)

    entry2 = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_VIN: "VIN2",
            DATA_VEHICLE_FEATURES: {"steering_wheel_heating": False},
        },
        entry_id="e2",
    )
    entry2.add_to_hass(hass)

    reg = er.async_get(hass)
    # Entità per entry1 con formato standard vin_suffix
    e1_wheel = reg.async_get_or_create(
        "switch", DOMAIN, "VIN1_steerWheelHeating", config_entry=entry1, original_name="Wheel"
    )
    # Entità per entry1 con formato ID_PREFIX_vin_suffix
    e1_alarm = reg.async_get_or_create(
        "switch", DOMAIN, f"{ID_PREFIX}_VIN1_antifurto", config_entry=entry1, original_name="Alarm"
    )
    # Entità abilitata per entry1
    e1_sunroof = reg.async_get_or_create(
        "cover", DOMAIN, "VIN1_tetto", config_entry=entry1, original_name="Sunroof"
    )
    # Entità per entry2 (non deve essere toccata quando si ripulisce entry1)
    e2_wheel = reg.async_get_or_create(
        "switch", DOMAIN, "VIN2_steerWheelHeating", config_entry=entry2, original_name="Wheel 2"
    )

    removed = await async_cleanup_disabled_entities(hass, entry1)
    assert removed == 2
    assert reg.async_get(e1_wheel.entity_id) is None
    assert reg.async_get(e1_alarm.entity_id) is None
    assert reg.async_get(e1_sunroof.entity_id) is not None
    assert reg.async_get(e2_wheel.entity_id) is not None


def test_coordinator_restore_position():
    """LepasCoordinator.restore_position valida coordinate e le applica solo se assenti."""
    coord = LepasCoordinator.__new__(LepasCoordinator)
    coord.position = None
    coord.data = {"position": None}
    coord._state_lock = MagicMock()
    coord._state_lock.__enter__ = MagicMock()
    coord._state_lock.__exit__ = MagicMock()
    coord._update = MagicMock()

    # Coordinate non valide o fuori bound
    assert coord.restore_position(float("nan"), 10.0) is False
    assert coord.restore_position(float("inf"), 10.0) is False
    assert coord.restore_position(95.0, 10.0) is False
    assert coord.restore_position(45.0, 185.0) is False
    assert coord._update.call_count == 0

    # Coordinate valide -> ripristinate
    assert coord.restore_position("45.123", "9.456") is True
    assert coord.position == {"lat": 45.123, "lon": 9.456}
    coord._update.assert_called_once_with({"position": {"lat": 45.123, "lon": 9.456}})

    # Se position è già presente, non sovrascrive
    assert coord.restore_position(46.0, 10.0) is False
    assert coord.position == {"lat": 45.123, "lon": 9.456}


def test_waiting_text():
    """_waiting_text restituisce 'In attesa' in IT o 'Waiting' in altre lingue."""
    hass_it = MagicMock()
    hass_it.config.language = "it-IT"
    assert _waiting_text(hass_it) == "In attesa"

    hass_en = MagicMock()
    hass_en.config.language = "en-US"
    assert _waiting_text(hass_en) == "Waiting"

    hass_nl = MagicMock()
    hass_nl.config.language = "nl"
    assert _waiting_text(hass_nl) == "Waiting"

    assert _waiting_text(None) == "In attesa"


async def test_platform_gating_and_sunroof_blind_default_disabled(
    hass: HomeAssistant, cloud, monkeypatch
):
    """Feature False escludono le entità da hass.states; sunshadeState nasce disabilitata di default."""
    import fixtures as FX
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    monkeypatch.setattr(LepasCoordinator, "_provision_certs", lambda self: (True, "ok"))
    monkeypatch.setattr(LepasCoordinator, "_connect_car", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_keepalive", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_telemetry_poll", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_drive_watch", lambda self: None)

    async def _no_backfill(self) -> None:
        return None

    monkeypatch.setattr(LepasCoordinator, "async_ensure_vehicle_identity", _no_backfill)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Lepas ({FX.VIN})",
        unique_id=FX.VIN,
        data={
            CONF_VIN: FX.VIN,
            "tuserid": FX.TUSERID,
            "email": FX.EMAIL,
            "pin": FX.PIN,
            DATA_CAPS_PROBED_V3: True,
            DATA_VEHICLE_FEATURES: {
                "steering_wheel_heating": False,
                "alarm": False,
                "front_windshield_electric": False,
                "instant_charging": False,
                "rear_left_seat_heating": False,
                "rear_center_seat": False,
                "sunroof": True,
            },
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    for excluded in (
        "switch.lepas_steering_wheel_heating",
        "switch.lepas_alarm",
        "button.lepas_alarm_on",
        "button.lepas_alarm_off",
        "switch.lepas_windshield_defrost",
        "switch.lepas_charging",
        "switch.lepas_rear_left_seat_heating",
        "sensor.lepas_rear_center_seat_heating",
    ):
        assert hass.states.get(excluded) is None, f"{excluded} non doveva essere creata"

    for enabled in (
        "switch.lepas_windshield_defog",
        "binary_sensor.lepas_windshield_heating",
        "cover.lepas_sunroof",
        "switch.lepas_driver_seat_heating",
    ):
        assert hass.states.get(enabled) is not None, f"{enabled} doveva essere attiva"

    reg = er.async_get(hass)
    blind_entry = reg.async_get("binary_sensor.lepas_sunroof_blind")
    assert blind_entry is not None
    assert blind_entry.disabled_by == er.RegistryEntryDisabler.INTEGRATION

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_text_sensors_and_sunroof_move_waiting_state(hass: HomeAssistant, integrazione_avviata):
    """Sensori esito diagnostici e sunroofMoveState partono come 'In attesa'/'Waiting' poi mostrano il valore live."""
    hass.config.language = "it"
    coord = hass.data[DOMAIN][integrazione_avviata.entry_id]
    coord.async_set_updated_data(dict(coord.data))
    await hass.async_block_till_done()

    for eid in (
        "sensor.lepas_command_result",
        "sensor.lepas_wake_up_result",
        "sensor.lepas_location_probe_result",
        "sensor.lepas_sunroof_movement_state",
    ):
        assert hass.states.get(eid).state == "In attesa"

    hass.config.language = "en"
    coord._update({"cmd_status": "OK", "fields": {"sunroofMoveState": "1"}})
    await hass.async_block_till_done()
    assert hass.states.get("sensor.lepas_command_result").state == "OK"
    assert hass.states.get("sensor.lepas_sunroof_movement_state").state == "1"
    assert hass.states.get("sensor.lepas_wake_up_result").state == "Waiting"


async def test_at_home_restores_from_device_tracker(hass: HomeAssistant, cloud, monkeypatch):
    """Al boot senza fix GPS live, LepasTracker ripristina la posizione e at_home vale 'on'."""
    import fixtures as FX
    from homeassistant.core import State
    from homeassistant.setup import async_setup_component
    from pytest_homeassistant_custom_component.common import (
        MockConfigEntry,
        mock_restore_cache,
    )

    hass.config.latitude, hass.config.longitude = 45.0, 9.0
    assert await async_setup_component(hass, "zone", {})
    await hass.async_block_till_done()

    mock_restore_cache(
        hass,
        [
            State("device_tracker.lepas_location", "home", {"latitude": 45.0, "longitude": 9.0}),
            State("switch.lepas_automatic_updates", "on"),
        ],
    )

    monkeypatch.setattr(LepasCoordinator, "_provision_certs", lambda self: (True, "ok"))
    monkeypatch.setattr(LepasCoordinator, "_connect_car", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_keepalive", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_telemetry_poll", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_drive_watch", lambda self: None)

    async def _no_backfill(self) -> None:
        return None

    monkeypatch.setattr(LepasCoordinator, "async_ensure_vehicle_identity", _no_backfill)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Lepas ({FX.VIN})",
        unique_id=FX.VIN,
        data={CONF_VIN: FX.VIN, "tuserid": FX.TUSERID, "email": FX.EMAIL, "pin": FX.PIN},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coord = hass.data[DOMAIN][entry.entry_id]
    assert coord.data.get("position") == {"lat": 45.0, "lon": 9.0}
    assert coord.data.get("last_pos_fix") is None
    assert hass.states.get("binary_sensor.lepas_at_home").state == "on"

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_set_poll_enabled_notifies_at_home_availability(hass: HomeAssistant, cloud, monkeypatch):
    """Toggling poll_enabled notifies availability-dependent entities (e.g. LepasAtHome)."""
    import fixtures as FX
    from homeassistant.setup import async_setup_component
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    hass.config.latitude, hass.config.longitude = 45.0, 9.0
    assert await async_setup_component(hass, "zone", {})
    await hass.async_block_till_done()

    monkeypatch.setattr(LepasCoordinator, "_provision_certs", lambda self: (True, "ok"))
    monkeypatch.setattr(LepasCoordinator, "_connect_car", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_keepalive", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_telemetry_poll", lambda self: None)
    monkeypatch.setattr(LepasCoordinator, "async_start_drive_watch", lambda self: None)

    async def _no_backfill(self) -> None:
        return None

    monkeypatch.setattr(LepasCoordinator, "async_ensure_vehicle_identity", _no_backfill)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Lepas ({FX.VIN})",
        unique_id=FX.VIN,
        data={CONF_VIN: FX.VIN, "tuserid": FX.TUSERID, "email": FX.EMAIL, "pin": FX.PIN},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coord = hass.data[DOMAIN][entry.entry_id]
    coord.set_poll_enabled(False)
    coord.restore_position(45.0, 9.0)
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.lepas_at_home").state == "unavailable"

    # Enabling poll afterwards must immediately notify LepasAtHome -> "on"
    coord.set_poll_enabled(True)
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.lepas_at_home").state == "on"

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
