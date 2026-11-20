"""Tests for closure auto-sync on lock, realtime grace window, and CMD_PROBE lifecycle."""
from __future__ import annotations

import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fixtures as FX

from custom_components.lepas import coordinator as coord_mod
from custom_components.lepas.const import (
    AUTO_CLOSE_ON_LOCK_KEYS,
    CLOSURE_META_KEYS,
    CLOSURE_PROBE_COMMANDS,
    CMD_PROBE_DELAYS_S,
    DOMAIN,
    PROBE_MQTT_GRACE_S,
    PROBE_OPT_SETTLE_S,
)
from custom_components.lepas.core import commands as CMD
from custom_components.lepas.timers import CMD_PROBE, GRUPPO_POLL


def _coord(hass, entry):
    return hass.data[DOMAIN][entry.entry_id]


def _entity_obj(hass, platform: str, entity_id: str):
    comp = hass.data["entity_components"][platform]
    return next(e for e in comp.entities if e.entity_id == entity_id)


async def _deliver_mqtt(hass, coord, envelope: dict) -> None:
    msg = SimpleNamespace(
        payload=json.dumps(envelope).encode("utf-8"),
        topic="app/1/test/account/msgCenter/msg",
    )
    coord._on_car_message(None, None, msg)
    await hass.async_block_till_done()


async def _push_realtime(hass, coord, rt: dict) -> None:
    coord._on_probe_data(rt)
    await hass.async_block_till_done()


def test_closure_constants_and_timer_group() -> None:
    assert AUTO_CLOSE_ON_LOCK_KEYS == (
        "sunroofState",
        "sunshadeState",
        "frontLeftWindowState",
        "frontRightWindowState",
        "backLeftWindowState",
        "backRightWindowState",
    )
    assert "trunkDoor" not in AUTO_CLOSE_ON_LOCK_KEYS
    assert "hood" not in AUTO_CLOSE_ON_LOCK_KEYS
    assert set(AUTO_CLOSE_ON_LOCK_KEYS).issubset(CLOSURE_META_KEYS)
    assert {"frontLeftDoor", "frontRightDoor", "backLeftDoor", "backRightDoor", "trunkDoor", "hood", "doorLock"}.issubset(
        CLOSURE_META_KEYS
    )
    assert {
        "blocca",
        "sblocca",
        "baule_apri",
        "baule_chiudi",
        "finestrini_apri",
        "finestrini_chiudi",
        "finestrini_ventila",
        "tetto_apri",
        "tetto_chiudi",
        "tetto_ventila",
    }.issubset(CLOSURE_PROBE_COMMANDS)
    assert PROBE_MQTT_GRACE_S == 15
    assert PROBE_OPT_SETTLE_S == 60
    assert CMD_PROBE_DELAYS_S == (25, 65)
    assert CMD_PROBE in GRUPPO_POLL


async def test_blocca_ack_auto_closes_sunroof_sunshade_and_windows_keeps_trunk(
    hass, integrazione_avviata, monkeypatch
) -> None:
    coord = _coord(hass, integrazione_avviata)
    monkeypatch.setattr(coord, "async_probe", AsyncMock())
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0)
    sent: list[str] = []
    monkeypatch.setattr(CMD, "send", lambda _ctx, key, **_kw: sent.append(key) or "ok")

    await _deliver_mqtt(
        hass,
        coord,
        FX.telemetry_5a02(
            doorLock="1",
            sunroofState="1",
            sunshadeState="1",
            frontLeftWindowState="1",
            frontRightWindowState="1",
            backLeftWindowState="1",
            backRightWindowState="1",
            trunkDoor="1",
            hood="1",
        ),
    )
    assert hass.states.get("lock.lepas_lock").state == "unlocked"
    assert hass.states.get("cover.lepas_sunroof").state == "open"
    assert hass.states.get("cover.lepas_windows").state == "open"
    assert hass.states.get("cover.lepas_trunk").state == "open"

    # Put sunroof into optimistic open state to verify blocca ACK settles optimism too.
    await hass.services.async_call(
        "cover", "open_cover", {"entity_id": "cover.lepas_sunroof"}, blocking=True
    )
    await hass.async_block_till_done()
    sunroof_ent = _entity_obj(hass, "cover", "cover.lepas_sunroof")
    assert sunroof_ent._opt_value is False

    await hass.services.async_call("lock", "lock", {"entity_id": "lock.lepas_lock"}, blocking=True)
    await hass.async_block_till_done()
    assert sent == ["tetto_apri", "blocca"]

    # Result "3" is a valid Chery ACK (AB-LEP-016) omitting sunroof/sunshade/windows.
    await _deliver_mqtt(
        hass,
        coord,
        FX.envelope("1105", {"result": "3", "seq": "LOCK-1", "doorLock": "0"}),
    )

    assert hass.states.get("lock.lepas_lock").state == "locked"
    assert sunroof_ent._opt_value is None
    assert hass.states.get("cover.lepas_sunroof").state == "closed"
    assert hass.states.get("cover.lepas_windows").state == "closed"
    assert hass.states.get("binary_sensor.lepas_front_left_window").state == "off"
    assert hass.states.get("binary_sensor.lepas_front_right_window").state == "off"
    assert hass.states.get("binary_sensor.lepas_rear_left_window").state == "off"
    assert hass.states.get("binary_sensor.lepas_rear_right_window").state == "off"
    assert coord.data["fields"]["sunshadeState"] == "0"
    assert hass.states.get("cover.lepas_trunk").state == "open"
    assert hass.states.get("binary_sensor.lepas_hood").state == "on"
    for key in AUTO_CLOSE_ON_LOCK_KEYS:
        assert coord.data["msg_fields"].get(key) == "0"


async def test_rejected_blocca_does_not_auto_close_closures(
    hass, integrazione_avviata, monkeypatch
) -> None:
    coord = _coord(hass, integrazione_avviata)
    monkeypatch.setattr(coord, "async_probe", AsyncMock())
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0)
    monkeypatch.setattr(CMD, "send", lambda *_a, **_kw: "ok")

    await _deliver_mqtt(
        hass,
        coord,
        FX.telemetry_5a02(
            doorLock="1",
            sunroofState="1",
            sunshadeState="1",
            frontLeftWindowState="1",
            frontRightWindowState="1",
            backLeftWindowState="1",
            backRightWindowState="1",
            trunkDoor="1",
        ),
    )

    # Subcase A: explicit result "0" rejection
    await hass.services.async_call("lock", "lock", {"entity_id": "lock.lepas_lock"}, blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("lock.lepas_lock").state == "locked"

    await _deliver_mqtt(hass, coord, FX.envelope("1105", {"result": "0", "seq": "LOCK-FAIL-1"}))
    assert coord.data["cmd_rejected_other"] is True
    assert hass.states.get("lock.lepas_lock").state == "unlocked"
    assert hass.states.get("cover.lepas_sunroof").state == "open"
    assert hass.states.get("cover.lepas_windows").state == "open"
    for key in AUTO_CLOSE_ON_LOCK_KEYS:
        assert coord.data["fields"][key] == "1"

    # Subcase B: non-climate [0:95] rejection on blocca (AB-LEP-016)
    await hass.services.async_call("lock", "lock", {"entity_id": "lock.lepas_lock"}, blocking=True)
    await hass.async_block_till_done()
    await _deliver_mqtt(
        hass,
        coord,
        FX.envelope("1105", {"result": "1", "seq": "LOCK-FAIL-2", "reason": [{"modelId": "0", "code": "95"}]}),
    )
    assert coord.data["cmd_rejected_other"] is True
    assert hass.states.get("lock.lepas_lock").state == "unlocked"
    assert hass.states.get("cover.lepas_sunroof").state == "open"
    assert hass.states.get("cover.lepas_windows").state == "open"
    for key in AUTO_CLOSE_ON_LOCK_KEYS:
        assert coord.data["fields"][key] == "1"


async def test_external_lock_transition_auto_closes_when_fields_omitted(
    hass, integrazione_avviata, monkeypatch
) -> None:
    coord = _coord(hass, integrazione_avviata)
    monkeypatch.setattr(coord, "async_probe", AsyncMock())

    await _deliver_mqtt(
        hass,
        coord,
        FX.telemetry_5a02(
            doorLock="1",
            sunroofState="1",
            sunshadeState="1",
            frontLeftWindowState="1",
            frontRightWindowState="1",
            backLeftWindowState="1",
            backRightWindowState="1",
            trunkDoor="1",
            hood="1",
        ),
    )

    # Physical key / official app locks the car while frontLeftWindowState stays explicitly open.
    await _deliver_mqtt(
        hass,
        coord,
        FX.envelope("5A02", {"doorLock": "0", "frontLeftWindowState": "1"}),
    )

    assert hass.states.get("lock.lepas_lock").state == "locked"
    assert hass.states.get("cover.lepas_sunroof").state == "closed"
    assert coord.data["fields"]["sunshadeState"] == "0"
    assert coord.data["fields"]["frontRightWindowState"] == "0"
    assert coord.data["fields"]["backLeftWindowState"] == "0"
    assert coord.data["fields"]["backRightWindowState"] == "0"
    assert coord.data["fields"]["frontLeftWindowState"] == "1"
    assert hass.states.get("cover.lepas_windows").state == "open"
    assert hass.states.get("cover.lepas_trunk").state == "open"
    assert hass.states.get("binary_sensor.lepas_hood").state == "on"

    # Subsequent frame with doorLock already "0" (no transition) must not clobber open window.
    await _deliver_mqtt(hass, coord, FX.envelope("5A02", {"doorLock": "0"}))
    assert coord.data["fields"]["frontLeftWindowState"] == "1"


async def test_probe_updates_closures_inside_awake_window_after_grace_and_preserves_msg_fields(
    hass, integrazione_avviata, monkeypatch
) -> None:
    coord = _coord(hass, integrazione_avviata)
    monkeypatch.setattr(coord, "async_probe", AsyncMock())

    with coord._state_lock:
        coord._fields.update({
            "trunkDoor": "1",
            "frontHVACState": "1",
            "doorLock": "1",
            "sunroofState": "1",
        })
        coord._last_msg_ts = time.time() - (PROBE_MQTT_GRACE_S + 5)
        fields_snap = dict(coord._fields)
    coord._apply_update({"fields": fields_snap, "msg_fields": {}})
    await hass.async_block_till_done()

    # Inside awake_window (300s) but past PROBE_MQTT_GRACE_S (15s): closures update, HVAC stays protected.
    await _push_realtime(hass, coord, {"trunkDoor": "0", "frontHVACState": "0"})
    assert coord.data["fields"]["trunkDoor"] == "0"
    assert hass.states.get("cover.lepas_trunk").state == "closed"
    assert coord.data["fields"]["frontHVACState"] == "1"
    assert coord.data["probe_fields"] == {"trunkDoor": "0"}
    assert "trunkDoor" in coord.data["probe_changed_fields"]
    assert coord.data["msg_fields"] == {}

    # Inside grace window (<15s): blocked doorLock must NOT enter probe_fields or trigger auto-close.
    with coord._state_lock:
        coord._last_msg_ts = time.time()
    await _push_realtime(hass, coord, {"doorLock": "0"})
    assert coord.data["fields"]["doorLock"] == "1"
    assert coord.data["fields"]["sunroofState"] == "1"
    assert "doorLock" not in coord.data["probe_fields"]

    # Past grace window (>15s): accepted doorLock transition triggers auto-close for omitted keys.
    with coord._state_lock:
        coord._last_msg_ts = time.time() - (PROBE_MQTT_GRACE_S + 5)
    await _push_realtime(hass, coord, {"doorLock": "0"})
    assert coord.data["fields"]["doorLock"] == "0"
    assert coord.data["fields"]["sunroofState"] == "0"
    assert coord.data["fields"]["sunshadeState"] == "0"
    assert "doorLock" in coord.data["probe_changed_fields"]
    assert "sunroofState" in coord.data["probe_changed_fields"]
    assert coord.data["msg_fields"] == {}


async def test_optimistic_trunk_settles_on_manual_close_via_probe(
    hass, integrazione_avviata, monkeypatch
) -> None:
    coord = _coord(hass, integrazione_avviata)
    monkeypatch.setattr(coord, "async_probe", AsyncMock())
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0)
    sent: list[str] = []
    monkeypatch.setattr(CMD, "send", lambda _ctx, key, **_kw: sent.append(key) or "ok")

    await _deliver_mqtt(hass, coord, FX.telemetry_5a02(trunkDoor="0"))
    trunk_ent = _entity_obj(hass, "cover", "cover.lepas_trunk")

    # Open trunk via real cover service -> optimistic open
    await hass.services.async_call(
        "cover", "open_cover", {"entity_id": "cover.lepas_trunk"}, blocking=True
    )
    await hass.async_block_till_done()
    assert sent == ["baule_apri"]
    assert hass.states.get("cover.lepas_trunk").state == "open"
    assert trunk_ent._opt_value is False

    # Move past 15s grace; before PROBE_OPT_SETTLE_S (60s), unchanged trunkDoor="0" keeps optimism.
    with coord._state_lock:
        coord._last_msg_ts = time.time() - (PROBE_MQTT_GRACE_S + 5)
    await _push_realtime(hass, coord, {"trunkDoor": "0"})
    assert trunk_ent._opt_value is False
    assert hass.states.get("cover.lepas_trunk").state == "open"

    # Once elapsed >= PROBE_OPT_SETTLE_S (60s), probe_fields settles optimism to closed ("0").
    trunk_ent._opt_at = time.monotonic() - (PROBE_OPT_SETTLE_S + 1)
    await _push_realtime(hass, coord, {"trunkDoor": "0"})
    assert trunk_ent._opt_value is None
    assert hass.states.get("cover.lepas_trunk").state == "closed"

    # Immediate settle when probe reports a semantic change (trunkDoor "0" -> "1") before 60s.
    await hass.services.async_call(
        "cover", "close_cover", {"entity_id": "cover.lepas_trunk"}, blocking=True
    )
    await hass.async_block_till_done()
    assert trunk_ent._opt_value is True
    await _push_realtime(hass, coord, {"trunkDoor": "1"})
    assert trunk_ent._opt_value is None
    assert hass.states.get("cover.lepas_trunk").state == "open"


async def test_closure_command_arms_cmd_probe_and_respects_poll_enabled_and_stop(
    hass, integrazione_avviata, monkeypatch
) -> None:
    coord = _coord(hass, integrazione_avviata)
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0)
    monkeypatch.setattr(CMD, "send", lambda *_a, **_kw: "ok")
    probe_mock = AsyncMock()
    monkeypatch.setattr(coord, "async_probe", probe_mock)

    # Disabled poll_enabled must never arm CMD_PROBE.
    coord.poll_enabled = False
    await coord.async_send_command("blocca")
    await hass.async_block_till_done()
    assert not coord._timers.is_armed(CMD_PROBE)

    # Enabled poll_enabled arms CMD_PROBE stage 0 on closure commands, not on non-closure commands.
    coord.poll_enabled = True
    await coord.async_send_command("clima_on")
    await hass.async_block_till_done()
    assert not coord._timers.is_armed(CMD_PROBE)

    await coord.async_send_command("baule_apri")
    await hass.async_block_till_done()
    assert coord._timers.is_armed(CMD_PROBE)

    # Stage 0 fires -> probes once, resets _poll_busy, and arms stage 1.
    await coord._cmd_probe_cb(0, None)
    probe_mock.assert_awaited_once_with(force=True)
    assert coord._poll_busy is False
    assert coord._timers.is_armed(CMD_PROBE)

    # Stage 1 error still resets _poll_busy in finally and terminates sequence (no stage 2).
    coord.async_probe = AsyncMock(side_effect=RuntimeError("probe boom"))
    await coord._cmd_probe_cb(1, None)
    assert coord._poll_busy is False
    assert not coord._timers.is_armed(CMD_PROBE)

    # set_poll_enabled(False) cancels armed CMD_PROBE.
    await coord.async_send_command("blocca")
    await hass.async_block_till_done()
    assert coord._timers.is_armed(CMD_PROBE)
    coord.set_poll_enabled(False)
    assert not coord._timers.is_armed(CMD_PROBE)

    # async_stop() cancels CMD_PROBE and blocks future _schedule_cmd_probe_sequence calls.
    coord.poll_enabled = True
    await coord.async_send_command("sblocca")
    await hass.async_block_till_done()
    assert coord._timers.is_armed(CMD_PROBE)
    coord.async_stop()
    assert not coord._timers.is_armed(CMD_PROBE)
    coord._schedule_cmd_probe_sequence(0)
    assert not coord._timers.is_armed(CMD_PROBE)
