"""Contatori di energia di ricarica casa/fuori: l'aritmetica dell'integrale.

Questi test guardano il PASSO DI CAMPIONAMENTO, non il cablaggio a Home Assistant:
l'entita' viene costruita senza passare dal costruttore, perche' cio' che puo' essere
sbagliato qui e' il trapezio, il rifiuto dei buchi e l'attribuzione alla zona — non
l'istanziazione, che la suite delle entita' copre gia' altrove.

Tre di questi fallivano sulla forma ingenua del codice, quindi sono test di regressione e
non decorazione:
  * `test_buco_lungo_senza_soc_non_inventa_energia`
  * `test_buco_lungo_recupera_da_delta_soc`
  * `test_degraded_e_cambio_zona_non_inquinano_baseline`
  * `test_zona_ignota_non_attribuisce_a_nessuno`
  * `test_stato_carica_float_conta_come_in_ricarica`
"""

from __future__ import annotations

import datetime as dt

import pytest

from custom_components.lepas import sensor as S
from custom_components.lepas.const import CHARGE_ENERGY_MAX_GAP


class _CoordFinto:
    def __init__(
        self,
        potenza,
        stato="1",
        posizione=None,
        *,
        soc=None,
        odometer=None,
        plugged=True,
        pure_electric_range="100",
        battery_capacity_kwh=18.4,
    ):
        rt = {
            "chargingPower": potenza,
            "chargeState": stato,
            "pureElectricRange": pure_electric_range,
        }
        if soc is not None:
            rt["dumpEnergy"] = soc
        if odometer is not None:
            rt["odometer"] = odometer
        if plugged is not None:
            rt["chargeGunState"] = "1" if plugged else "0"
        self.data = {
            "realtime": rt,
            "fields": {},
            "position": posizione or {"lat": 1.0, "lon": 2.0},
        }
        self.poll_enabled = True
        self.battery_capacity_kwh = battery_capacity_kwh


def _contatore(home=True):
    """Istanza senza costruttore: qui interessa solo lo stato dell'integratore."""
    e = object.__new__(S.LepasChargedEnergy)
    e._home = home
    e._energia_wh = 0.0
    e._ultimo_ts = None
    e._ultima_potenza = 0.0
    e._era_attivo = False
    e._ultimo_soc = None
    e._ultimo_odo = None
    e._ultimo_rt = None
    return e


def _campiona(e, coord, a_casa, istante, monkeypatch):
    monkeypatch.setattr(S, "in_zona_casa", lambda hass, pos: a_casa)
    monkeypatch.setattr(S.dt_util, "utcnow", lambda: istante)
    e.coordinator = coord
    e.hass = None
    e._campiona()


T0 = dt.datetime(2026, 8, 24, 12, 0, 0, tzinfo=dt.UTC)


def test_stato_carica_float_conta_come_in_ricarica():
    """Il canale realtime manda a volte `'1.0'`: un confronto con la stringa `'1'` teneva
    l'integrale fermo a zero senza dirlo."""
    assert S._in_ricarica("1") is True
    assert S._in_ricarica("1.0") is True
    assert S._in_ricarica(1.0) is True
    assert S._in_ricarica("0") is False
    assert S._in_ricarica(None) is False
    assert S._in_ricarica("chi lo sa") is False


def test_trapezio_su_due_campioni_vicini(monkeypatch):
    """2 kW per 120 s = 0,0667 kWh. Il primo campione arma soltanto: non accumula."""
    e = _contatore(home=True)
    _campiona(e, _CoordFinto("2.0"), True, T0, monkeypatch)
    assert e.native_value == 0.0
    _campiona(e, _CoordFinto("2.0"), True, T0 + dt.timedelta(seconds=120), monkeypatch)
    assert e.native_value == pytest.approx(2.0 * 120 / 3600, abs=1e-3)


def test_buco_lungo_senza_soc_non_inventa_energia(monkeypatch):
    """Oltre CHARGE_ENERGY_MAX_GAP senza salto SoC valido non si inventa energia."""
    e = _contatore(home=True)
    _campiona(e, _CoordFinto("2.0"), True, T0, monkeypatch)
    troppo_tardi = T0 + dt.timedelta(seconds=CHARGE_ENERGY_MAX_GAP + 1)
    _campiona(e, _CoordFinto("2.0"), True, troppo_tardi, monkeypatch)
    assert e.native_value == 0.0


def test_buco_lungo_recupera_da_delta_soc(monkeypatch):
    """Gap > CHARGE_ENERGY_MAX_GAP con dumpEnergy 30 -> 70 recupera 7.36 kWh mantenendo monotonicita'."""
    e = _contatore(home=True)
    _campiona(
        e,
        _CoordFinto("0", stato="0", soc="30", odometer="500"),
        True,
        T0,
        monkeypatch,
    )
    assert e.native_value == 0.0

    dopo_buco = T0 + dt.timedelta(seconds=CHARGE_ENERGY_MAX_GAP + 120)
    _campiona(
        e,
        _CoordFinto("0", stato="0", soc="70", odometer="500"),
        True,
        dopo_buco,
        monkeypatch,
    )
    assert e.native_value == pytest.approx(7.36, abs=1e-3)

    # Monotonicita': calo SoC successivo non riduce il contatore TOTAL_INCREASING
    _campiona(
        e,
        _CoordFinto("0", stato="0", soc="65", odometer="500"),
        True,
        dopo_buco + dt.timedelta(seconds=CHARGE_ENERGY_MAX_GAP + 60),
        monkeypatch,
    )
    assert e.native_value == pytest.approx(7.36, abs=1e-3)


def test_degraded_e_cambio_zona_non_inquinano_baseline(monkeypatch):
    """Frame degradati, GPS assente, cambio zona e aggiornamenti non-realtime non falsano l'integrale."""
    e = _contatore(home=True)
    c1 = _CoordFinto("2.0", stato="1", soc="30", odometer="500")
    _campiona(e, c1, True, T0, monkeypatch)

    # Listener update sullo stesso oggetto realtime (es. cmd_status) non ri-integra
    _campiona(e, c1, True, T0 + dt.timedelta(seconds=60), monkeypatch)
    assert e.native_value == 0.0

    # Frame degradato (pureElectricRange == "0") non altera _ultimo_soc né accumula
    _campiona(
        e,
        _CoordFinto(
            "5.0", stato="1", soc="97", odometer="500", pure_electric_range="0"
        ),
        True,
        T0 + dt.timedelta(seconds=120),
        monkeypatch,
    )
    assert e._ultimo_soc == 30.0
    assert e.native_value == 0.0

    # GPS ignoto (a_casa is None) ad odometro invariato preserva _ultimo_soc
    _campiona(
        e,
        _CoordFinto("0", stato="0", soc="45", odometer="500"),
        None,
        T0 + dt.timedelta(seconds=500),
        monkeypatch,
    )
    assert e._ultimo_soc == 30.0
    assert e.native_value == 0.0

    # Cambio zona (True -> False) resetta continuità senza attribuire a home
    _campiona(
        e,
        _CoordFinto("3.0", stato="1", soc="60", odometer="500"),
        False,
        T0 + dt.timedelta(seconds=900),
        monkeypatch,
    )
    assert e.native_value == 0.0
    assert e._era_attivo is False
    assert e._ultimo_ts is None
    assert e._ultimo_soc == 60.0

    # Rientro a casa con odometro invariato: nessuna energia spuria dalla vecchia sessione
    _campiona(
        e,
        _CoordFinto("2.0", stato="1", soc="60", odometer="500"),
        True,
        T0 + dt.timedelta(seconds=1020),
        monkeypatch,
    )
    assert e.native_value == 0.0

    # Segmento successivo valido a casa accumula regolarmente
    _campiona(
        e,
        _CoordFinto("2.0", stato="1", soc="61", odometer="500"),
        True,
        T0 + dt.timedelta(seconds=1140),
        monkeypatch,
    )
    assert e.native_value == pytest.approx(2.0 * 120.0 / 3600.0, abs=1e-3)


def test_zona_ignota_non_attribuisce_a_nessuno(monkeypatch):
    """Senza fix GPS o senza `zone.home` l'energia non finisce nel contatore sbagliato: non finisce da nessuna
    parte. Meglio perdere un campione che attribuirlo alla zona sbagliata."""
    for casa in (True, False):
        e = _contatore(home=casa)
        _campiona(e, _CoordFinto("2.0"), None, T0, monkeypatch)
        _campiona(
            e, _CoordFinto("2.0"), None, T0 + dt.timedelta(seconds=120), monkeypatch
        )
        assert e.native_value == 0.0


def test_i_due_contatori_si_dividono_la_carica(monkeypatch):
    """La stessa carica a casa accumula su `home` e lascia `away` a zero."""
    casa, fuori = _contatore(home=True), _contatore(home=False)
    for e in (casa, fuori):
        _campiona(e, _CoordFinto("2.0"), True, T0, monkeypatch)
        _campiona(
            e, _CoordFinto("2.0"), True, T0 + dt.timedelta(seconds=120), monkeypatch
        )
    assert casa.native_value > 0
    assert fuori.native_value == 0.0


def test_potenza_zero_non_accumula(monkeypatch):
    """`chargeState` puo' dire "in ricarica" mentre la potenza e' ancora 0: non e' energia."""
    e = _contatore(home=True)
    _campiona(e, _CoordFinto("0"), True, T0, monkeypatch)
    _campiona(e, _CoordFinto("0"), True, T0 + dt.timedelta(seconds=120), monkeypatch)
    assert e.native_value == 0.0
