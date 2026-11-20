"""Tests for vehicle color auto-detection, V6 backfill, sensor attributes, and diagnostics."""
from __future__ import annotations

import json

import fixtures as FX
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lepas.const import (
    CONF_PIN,
    CONF_TUSERID,
    CONF_VEHICLE_NAME,
    CONF_VIN,
    DATA_CAPS_PROBED_V5,
    DATA_CAPS_PROBED_V6,
    DATA_VEHICLE_COLOR,
    DATA_VEHICLE_COLOR_CODE,
    DATA_VEHICLE_COLOR_NAME,
    DOMAIN,
    VEHICLE_COLOR_CODE_MAP,
    capabilities_from_item,
    normalize_vehicle_color,
)
from custom_components.lepas.coordinator import LepasCoordinator
from custom_components.lepas.diagnostics import async_get_config_entry_diagnostics
from custom_components.lepas.sensor import LepasSessionStatus


def _make_coord(
    hass,
    *,
    data: dict | None = None,
    options: dict | None = None,
    entry_id: str = "vehicle_color_entry",
) -> LepasCoordinator:
    base = {
        CONF_VIN: FX.VIN,
        CONF_TUSERID: FX.TUSERID,
        "email": FX.EMAIL,
        CONF_PIN: FX.PIN,
    }
    if data:
        base.update(data)
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=base,
        options=options or {},
        entry_id=entry_id,
    )
    entry.add_to_hass(hass)
    coord = LepasCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry_id] = coord
    return coord


@pytest.mark.parametrize(
    ("code", "name_en", "name_local", "expected"),
    [
        ("KME8", "", None, "black"),
        (" kme8 ", "", None, "black"),
        ("", "New Carbon Black", None, "black"),
        ("X1", "Pearl White", None, "white"),
        ("X2", "Phantom Grey", None, "grey"),
        ("X2", "Silver", None, "grey"),
        ("X3", "Aurora Teal", None, "teal"),
        ("X3", "Emerald Green", None, "teal"),
        ("X4", "Amethyst Violet", None, "violet"),
        ("X4", "Purple", None, "violet"),
        ("", "Silver Black", None, "grey"),
        ("", "Black Silver", None, "black"),
        ("", "Unknown Hue", None, None),
        ("", "whiten", None, None),
        ("", "blackish", None, None),
        ("", "Unknown Hue", "Bianco Perla", "white"),
        (None, None, None, None),
        (123, ["White"], {"color": "black"}, None),
    ],
)
def test_normalize_vehicle_color(code, name_en, name_local, expected):
    assert VEHICLE_COLOR_CODE_MAP == {"KME8": "black"}
    assert normalize_vehicle_color(code, name_en, name_local) == expected


def test_capabilities_from_item_vehicle_color():
    caps = capabilities_from_item({"colorCode": "KME8", "colorNameEn": "New Carbon Black"})
    assert caps[DATA_VEHICLE_COLOR] == "black"
    assert caps[DATA_VEHICLE_COLOR_CODE] == "KME8"
    assert caps[DATA_VEHICLE_COLOR_NAME] == "New Carbon Black"

    fallback = capabilities_from_item({"colorCode": "X1", "colorName": "Pearl White"})
    assert fallback[DATA_VEHICLE_COLOR] == "white"
    assert fallback[DATA_VEHICLE_COLOR_CODE] == "X1"
    assert fallback[DATA_VEHICLE_COLOR_NAME] == "Pearl White"

    ws_fallback = capabilities_from_item(
        {"colorCode": "X1", "colorNameEn": "   ", "colorName": "Bianco"}
    )
    assert ws_fallback[DATA_VEHICLE_COLOR] == "white"
    assert ws_fallback[DATA_VEHICLE_COLOR_NAME] == "Bianco"

    unknown = capabilities_from_item({"colorCode": "X99", "colorNameEn": "Unknown Hue"})
    assert unknown[DATA_VEHICLE_COLOR_CODE] == "X99"
    assert unknown[DATA_VEHICLE_COLOR_NAME] == "Unknown Hue"
    assert DATA_VEHICLE_COLOR not in unknown

    dirty = capabilities_from_item({"colorCode": None, "colorNameEn": 123, "colorName": " \t "})
    assert DATA_VEHICLE_COLOR not in dirty
    assert DATA_VEHICLE_COLOR_CODE not in dirty
    assert DATA_VEHICLE_COLOR_NAME not in dirty

    bounded = capabilities_from_item(
        {"colorCode": "K" * 90, "colorNameEn": "Black " + ("x" * 90)}
    )
    assert len(bounded[DATA_VEHICLE_COLOR_CODE]) == 64
    assert len(bounded[DATA_VEHICLE_COLOR_NAME]) == 64
    assert bounded[DATA_VEHICLE_COLOR] == "black"
    assert capabilities_from_item({}) == {}


async def test_v6_backfill_from_v5_preserves_name_and_notifies_once(hass, cloud):
    cloud.on(
        "/tsp/v1/app/vmc/queryList",
        data=[
            {
                "vin": FX.VIN,
                "nickname": "Cloud Name",
                "fullName": "LEPAS L8",
                "colorCode": "KME8",
                "colorNameEn": "New Carbon Black",
            }
        ],
    )
    cloud.on(
        "/tsp/v1/app/vmc/queryVehicleAuthority",
        data={"permissionList": [{"id": 212, "state": 1}]},
    )
    coord = _make_coord(
        hass,
        data={CONF_VEHICLE_NAME: "My Car", DATA_CAPS_PROBED_V5: True},
        entry_id="v6_backfill",
    )
    listener_calls: list[bool] = []
    coord.async_add_listener(lambda: listener_calls.append(True))

    await coord.async_ensure_vehicle_identity()

    assert cloud.count("/tsp/v1/app/vmc/queryList") == 1
    assert coord.vehicle_name == "My Car"
    assert coord.entry.data.get(CONF_VEHICLE_NAME) == "My Car"
    assert coord.entry.data.get(DATA_CAPS_PROBED_V6) is True
    assert coord.entry.data.get(DATA_CAPS_PROBED_V5) is True
    assert coord.vehicle_color == "black"
    assert coord.vehicle_color_code == "KME8"
    assert coord.vehicle_color_name == "New Carbon Black"
    assert coord.entry.data.get(DATA_VEHICLE_COLOR) == "black"
    assert coord.entry.data.get(DATA_VEHICLE_COLOR_CODE) == "KME8"
    assert coord.entry.data.get(DATA_VEHICLE_COLOR_NAME) == "New Carbon Black"
    assert len(listener_calls) == 1

    await coord.async_ensure_vehicle_identity()
    assert cloud.count("/tsp/v1/app/vmc/queryList") == 1
    assert len(listener_calls) == 1


async def test_v6_backfill_skips_listener_when_color_unchanged(hass, cloud):
    cloud.on(
        "/tsp/v1/app/vmc/queryList",
        data=[
            {
                "vin": FX.VIN,
                "nickname": "My Car",
                "fullName": "LEPAS L8",
                "colorCode": "KME8",
                "colorNameEn": "New Carbon Black",
            }
        ],
    )
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", data={"permissionList": []})
    coord = _make_coord(
        hass,
        data={
            CONF_VEHICLE_NAME: "My Car",
            DATA_CAPS_PROBED_V5: True,
            DATA_VEHICLE_COLOR: "black",
            DATA_VEHICLE_COLOR_CODE: "KME8",
            DATA_VEHICLE_COLOR_NAME: "New Carbon Black",
        },
        entry_id="v6_unchanged",
    )
    listener_calls: list[bool] = []
    coord.async_add_listener(lambda: listener_calls.append(True))

    await coord.async_ensure_vehicle_identity()

    assert coord.entry.data.get(DATA_CAPS_PROBED_V6) is True
    assert listener_calls == []


async def test_v6_backfill_preserves_cached_color_fail_open(hass, cloud):
    cloud.on(
        "/tsp/v1/app/vmc/queryList",
        data=[{"vin": FX.VIN, "nickname": "My Car", "fullName": "LEPAS L8"}],
    )
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", data={"permissionList": []})
    coord = _make_coord(
        hass,
        data={
            CONF_VEHICLE_NAME: "My Car",
            DATA_CAPS_PROBED_V5: True,
            DATA_VEHICLE_COLOR: "black",
            DATA_VEHICLE_COLOR_CODE: "KME8",
            DATA_VEHICLE_COLOR_NAME: "New Carbon Black",
        },
        entry_id="v6_fail_open",
    )
    listener_calls: list[bool] = []
    coord.async_add_listener(lambda: listener_calls.append(True))

    await coord.async_ensure_vehicle_identity()

    assert coord.entry.data.get(DATA_CAPS_PROBED_V6) is True
    assert coord.vehicle_color == "black"
    assert coord.vehicle_color_code == "KME8"
    assert coord.vehicle_color_name == "New Carbon Black"
    assert listener_calls == []


async def test_v6_backfill_teardown_guards(hass, cloud, monkeypatch):
    coord = _make_coord(
        hass,
        data={CONF_VEHICLE_NAME: "My Car", DATA_CAPS_PROBED_V5: True},
        entry_id="v6_closing",
    )
    update_calls: list[bool] = []
    notify_calls: list[bool] = []
    listener_calls: list[bool] = []
    orig_update = hass.config_entries.async_update_entry
    orig_notify = coord.async_update_listeners

    def spy_update(*args, **kwargs):
        update_calls.append(True)
        return orig_update(*args, **kwargs)

    def spy_notify():
        notify_calls.append(True)
        return orig_notify()

    monkeypatch.setattr(hass.config_entries, "async_update_entry", spy_update)
    monkeypatch.setattr(coord, "async_update_listeners", spy_notify)
    coord.async_add_listener(lambda: listener_calls.append(True))

    def closing_handler(_path, _body):
        coord._timers.closing = True
        return {
            "code": "000000",
            "data": [
                {
                    "vin": FX.VIN,
                    "nickname": "My Car",
                    "colorCode": "KME8",
                    "colorNameEn": "New Carbon Black",
                }
            ],
        }

    cloud.on("/tsp/v1/app/vmc/queryList", response=closing_handler)
    await coord.async_ensure_vehicle_identity()

    assert update_calls == []
    assert notify_calls == []
    assert listener_calls == []
    assert coord.entry.data.get(DATA_CAPS_PROBED_V6) is None
    assert coord.vehicle_color is None

    # Also aborts if entry is unloaded from hass.data[DOMAIN] mid-fetch
    coord_unloaded = _make_coord(
        hass,
        data={CONF_VEHICLE_NAME: "My Car", DATA_CAPS_PROBED_V5: True},
        entry_id="v6_unloaded",
    )
    notify_unloaded: list[bool] = []
    orig_notify_u = coord_unloaded.async_update_listeners
    monkeypatch.setattr(
        coord_unloaded,
        "async_update_listeners",
        lambda: (notify_unloaded.append(True), orig_notify_u())[1],
    )

    def unload_handler(_path, _body):
        hass.data[DOMAIN].pop("v6_unloaded", None)
        return {
            "code": "000000",
            "data": [
                {
                    "vin": FX.VIN,
                    "nickname": "My Car",
                    "colorCode": "KME8",
                    "colorNameEn": "New Carbon Black",
                }
            ],
        }

    cloud.on("/tsp/v1/app/vmc/queryList", response=unload_handler)
    await coord_unloaded.async_ensure_vehicle_identity()
    assert update_calls == []
    assert notify_unloaded == []


async def test_v6_backfill_failure_leaves_probed_unset(hass, cloud):
    cloud.on("/tsp/v1/app/vmc/queryList", raises=RuntimeError("network down"))
    coord = _make_coord(
        hass,
        data={CONF_VEHICLE_NAME: "My Car", DATA_CAPS_PROBED_V5: True},
        entry_id="v6_err",
    )

    await coord.async_ensure_vehicle_identity()

    assert coord.entry.data.get(DATA_CAPS_PROBED_V6) is None
    assert coord.vehicle_color is None


async def test_session_status_extra_state_attributes(hass):
    coord = _make_coord(hass, entry_id="sess_attrs")
    sensor = LepasSessionStatus(coord)
    assert sensor.extra_state_attributes is None

    coord.vehicle_color = "black"
    coord.vehicle_color_code = "KME8"
    coord.vehicle_color_name = "New Carbon Black"
    assert sensor.extra_state_attributes == {
        "vehicle_color": "black",
        "vehicle_color_code": "KME8",
        "vehicle_color_name": "New Carbon Black",
    }

    coord.vehicle_color = None
    coord.vehicle_color_code = "X99"
    coord.vehicle_color_name = "Unknown Hue"
    assert sensor.extra_state_attributes == {
        "vehicle_color_code": "X99",
        "vehicle_color_name": "Unknown Hue",
    }


async def test_diagnostics_includes_vehicle_color(hass, integrazione_avviata):
    coord = hass.data[DOMAIN][integrazione_avviata.entry_id]
    coord.vehicle_color = "black"
    coord.vehicle_color_code = "KME8"
    coord.vehicle_color_name = "New Carbon Black"

    diag = await async_get_config_entry_diagnostics(hass, integrazione_avviata)

    assert diag["vehicle"]["color"] == "black"
    assert diag["vehicle"]["color_code"] == "KME8"
    assert diag["vehicle"]["color_name"] == "New Carbon Black"
    assert FX.VIN not in json.dumps(diag)
