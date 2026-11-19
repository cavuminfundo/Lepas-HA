"""Test TDD per il retry automatico protetto con sveglia su A07900."""
from __future__ import annotations

import asyncio
import json
import time

import fixtures as FX
import pytest

from custom_components.lepas import coordinator as coord_mod
from custom_components.lepas.const import A07900_WAKE_COOLDOWN_S, DOMAIN
from custom_components.lepas.core.commands import CommandError


class _Msg:
    """Messaggio paho minimo per `_on_car_message`."""

    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload).encode()
        self.topic = "app/1/test/account/msgCenter/msg"


def _coordinator(hass, entry):
    return hass.data[DOMAIN][entry.entry_id]


async def test_a07900_sveglia_mqtt_ok_e_retry_riuscito(
    hass, integrazione_avviata, cloud, monkeypatch
):
    """A07900 con auto a riposo: rilascia _cmd_gate, sveglia via localizza, attende push MQTT
    e riprova il comando una sola volta riusando il taskId in cache senza richiamare checkPassword."""
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0.05)
    monkeypatch.setattr(coord_mod, "POLL_WAKE_WAIT", 2.0)

    tentativi = {"blocca": 0, "localizza": 0}
    gate_occupato_da_localizza: list[bool] = []

    def handler_blocca(_path, _body):
        tentativi["blocca"] += 1
        if tentativi["blocca"] == 1:
            return {"code": "A07900", "msg": "vehicle asleep"}
        return {"code": "000000", "msg": "ok"}

    def handler_localizza(_path, _body):
        tentativi["localizza"] += 1
        gate_occupato_da_localizza.append(coord._cmd_gate.locked())
        hass.loop.call_soon_threadsafe(
            hass.loop.call_later,
            0.08,
            lambda: coord._on_car_message(None, None, _Msg(FX.telemetry_5a02())),
        )
        return {"code": "000000", "msg": "ok"}

    cloud.on("/asc/vehicleControl/lockControl", handler_blocca)
    cloud.on("/asc/vehicleControl/vehicleLocation", handler_localizza)

    res = await coord.async_send_command("blocca")
    await hass.async_block_till_done()

    assert "000000" in res
    assert tentativi == {"blocca": 2, "localizza": 1}
    # Se il chiamante non avesse rilasciato _cmd_gate prima di async_assicura_sveglia(), localizza sarebbe andato in deadlock
    assert gate_occupato_da_localizza == [True]
    # checkPassword dev'essere stato chiamato 1 sola volta (cache taskId riusata tra localizza e retry)
    assert cloud.count("checkPassword") == 1
    # `_hold_then_release` di `blocca` (background task) impiega almeno 1 step da 0.5 s in `_settle_after_command`
    await asyncio.sleep(0.55)
    assert not coord._cmd_gate.locked()


async def test_a07900_timeout_mqtt_nessun_retry_e_ripristina_errore_originale(
    hass, integrazione_avviata, cloud, monkeypatch
):
    """Se nessun push MQTT arriva entro POLL_WAKE_WAIT: nessun retry, cmd_status ripristinato
    all'errore A07900 originale, _instrada_rimedio invocato e CommandError originale rilanciato."""
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0.02)
    monkeypatch.setattr(coord_mod, "POLL_WAKE_WAIT", 0.08)

    tentativi = {"blocca": 0, "localizza": 0}
    rimedi: list[Exception] = []
    orig_instrada = coord._instrada_rimedio

    def spy_instrada(err, dal_loop=True):
        rimedi.append(err)
        return orig_instrada(err, dal_loop=dal_loop)

    monkeypatch.setattr(coord, "_instrada_rimedio", spy_instrada)

    def handler_blocca(_path, _body):
        tentativi["blocca"] += 1
        return {"code": "A07900", "msg": "asleep"}

    def handler_localizza(_path, _body):
        tentativi["localizza"] += 1
        return {"code": "000000", "msg": "ok"}

    cloud.on("/asc/vehicleControl/lockControl", handler_blocca)
    cloud.on("/asc/vehicleControl/vehicleLocation", handler_localizza)

    with pytest.raises(CommandError) as exc_info:
        await coord.async_send_command("blocca")
    await hass.async_block_till_done()

    assert exc_info.value.code == "A07900"
    assert tentativi == {"blocca": 1, "localizza": 1}
    assert len(rimedi) == 1 and rimedi[0] is exc_info.value
    assert "A07900" in (coord.data.get("cmd_status") or "")
    assert "Localizza" not in (coord.data.get("cmd_status") or "")
    # `_hold_then_release` di `localizza` (background task) finisce entro ~0.5 s
    await asyncio.sleep(0.55)
    assert not coord._cmd_gate.locked()


async def test_a07900_cooldown_attivo_niente_sveglia_ne_retry(
    hass, integrazione_avviata, cloud
):
    """Con cooldown A07900_WAKE_COOLDOWN_S ancora attivo: nessuna sveglia e nessun retry."""
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0
    coord._last_a07900_wake_ts = time.monotonic() - (A07900_WAKE_COOLDOWN_S - 10)

    tentativi = {"blocca": 0, "localizza": 0}

    def handler_blocca(_path, _body):
        tentativi["blocca"] += 1
        return {"code": "A07900", "msg": "asleep"}

    def handler_localizza(_path, _body):
        tentativi["localizza"] += 1
        return {"code": "000000", "msg": "ok"}

    cloud.on("/asc/vehicleControl/lockControl", handler_blocca)
    cloud.on("/asc/vehicleControl/vehicleLocation", handler_localizza)

    with pytest.raises(CommandError) as exc_info:
        await coord.async_send_command("blocca")

    assert exc_info.value.code == "A07900"
    assert tentativi == {"blocca": 1, "localizza": 0}
    assert not coord._cmd_gate.locked()


async def test_a07900_auto_gia_sveglia_niente_sveglia_ne_retry(
    hass, integrazione_avviata, cloud
):
    """Se coord.auto_sveglia è True: nessuna sveglia ridondante né retry su A07900."""
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = time.time()
    assert coord.auto_sveglia is True

    tentativi = {"blocca": 0, "localizza": 0}

    def handler_blocca(_path, _body):
        tentativi["blocca"] += 1
        return {"code": "A07900", "msg": "asleep"}

    def handler_localizza(_path, _body):
        tentativi["localizza"] += 1
        return {"code": "000000", "msg": "ok"}

    cloud.on("/asc/vehicleControl/lockControl", handler_blocca)
    cloud.on("/asc/vehicleControl/vehicleLocation", handler_localizza)

    with pytest.raises(CommandError) as exc_info:
        await coord.async_send_command("blocca")

    assert exc_info.value.code == "A07900"
    assert tentativi == {"blocca": 1, "localizza": 0}


async def test_a07900_su_localizza_niente_ricorsione(
    hass, integrazione_avviata, cloud
):
    """Un A07900 su `localizza` non deve innescare un'altra sveglia né un retry."""
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0

    tentativi = {"localizza": 0}

    def handler_localizza(_path, _body):
        tentativi["localizza"] += 1
        return {"code": "A07900", "msg": "asleep"}

    cloud.on("/asc/vehicleControl/vehicleLocation", handler_localizza)

    with pytest.raises(CommandError) as exc_info:
        await coord.async_send_command("localizza")

    assert exc_info.value.code == "A07900"
    assert tentativi["localizza"] == 1
    assert not coord._cmd_gate.locked()


async def test_a07900_doppio_al_massimo_un_retry(
    hass, integrazione_avviata, cloud, monkeypatch
):
    """Se anche il retry post-risveglio ritorna A07900, si ferma dopo 1 solo retry."""
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0.02)
    monkeypatch.setattr(coord_mod, "POLL_WAKE_WAIT", 2.0)

    tentativi = {"blocca": 0, "localizza": 0}

    def handler_blocca(_path, _body):
        tentativi["blocca"] += 1
        return {"code": "A07900", "msg": "asleep"}

    def handler_localizza(_path, _body):
        tentativi["localizza"] += 1
        hass.loop.call_soon_threadsafe(
            hass.loop.call_later,
            0.05,
            lambda: coord._on_car_message(None, None, _Msg(FX.telemetry_5a02())),
        )
        return {"code": "000000", "msg": "ok"}

    cloud.on("/asc/vehicleControl/lockControl", handler_blocca)
    cloud.on("/asc/vehicleControl/vehicleLocation", handler_localizza)

    with pytest.raises(CommandError) as exc_info:
        await coord.async_send_command("blocca")
    await hass.async_block_till_done()

    assert exc_info.value.code == "A07900"
    assert tentativi == {"blocca": 2, "localizza": 1}
    assert not coord._cmd_gate.locked()


async def test_a07900_cancelled_error_durante_attesa_lascia_cmd_gate_libero(
    hass, integrazione_avviata, cloud, monkeypatch
):
    """Cancellazione mentre attende il risveglio MQTT: `_cmd_gate` resta libero e non parte il retry."""
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0.02)
    monkeypatch.setattr(coord_mod, "POLL_WAKE_WAIT", 5.0)

    tentativi = {"blocca": 0, "localizza": 0}
    localizza_partita = asyncio.Event()

    def handler_blocca(_path, _body):
        tentativi["blocca"] += 1
        return {"code": "A07900", "msg": "asleep"}

    def handler_localizza(_path, _body):
        tentativi["localizza"] += 1
        hass.loop.call_soon_threadsafe(localizza_partita.set)
        return {"code": "000000", "msg": "ok"}

    cloud.on("/asc/vehicleControl/lockControl", handler_blocca)
    cloud.on("/asc/vehicleControl/vehicleLocation", handler_localizza)

    task = asyncio.create_task(coord.async_send_command("blocca"))
    await asyncio.wait_for(localizza_partita.wait(), timeout=2.0)
    # `_settle_after_command` esegue almeno 1 step da 0.5 s prima di rilasciare lo slot di `localizza`
    await asyncio.sleep(0.55)
    assert not coord._cmd_gate.locked(), "_cmd_gate dev'essere libero durante l'attesa MQTT"

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await hass.async_block_till_done()

    assert tentativi == {"blocca": 1, "localizza": 1}
    assert not coord._cmd_gate.locked()


async def test_wait_for_car_wake_anti_race_e_sblocco_su_stop(
    hass, integrazione_avviata, cloud, monkeypatch
):
    """Push MQTT arrivato DURANTE `async_assicura_sveglia()` sblocca subito il retry (end-to-end
    su `baseline_ts`), e `async_stop()` durante attesa sblocca subito ritornando False."""
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0.02)
    monkeypatch.setattr(coord_mod, "POLL_WAKE_WAIT", 5.0)

    tentativi = {"blocca": 0, "localizza": 0}

    def handler_blocca(_path, _body):
        tentativi["blocca"] += 1
        if tentativi["blocca"] == 1:
            return {"code": "A07900", "msg": "asleep"}
        return {"code": "000000", "msg": "ok"}

    def handler_localizza(_path, _body):
        tentativi["localizza"] += 1
        # Il push MQTT arriva MENTRE `localizza` è ancora in esecuzione in executor
        coord._on_car_message(None, None, _Msg(FX.telemetry_5a02()))
        return {"code": "000000", "msg": "ok"}

    cloud.on("/asc/vehicleControl/lockControl", handler_blocca)
    cloud.on("/asc/vehicleControl/vehicleLocation", handler_localizza)

    res = await asyncio.wait_for(coord.async_send_command("blocca"), timeout=1.5)
    await hass.async_block_till_done()
    assert "000000" in res
    assert tentativi == {"blocca": 2, "localizza": 1}

    # Ora attesa reale sbloccata da async_stop() senza attendere i 5s
    new_baseline = coord._last_msg_ts
    waiter = asyncio.create_task(coord._wait_for_car_wake(new_baseline, timeout=5.0))
    await asyncio.sleep(0.05)
    coord.async_stop()
    assert await asyncio.wait_for(waiter, timeout=1.0) is False
