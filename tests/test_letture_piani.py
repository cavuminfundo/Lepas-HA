"""Le due «letture gratuite»: piano di partenza e piano di ricarica, letti DALL'AUTO.

Gratuite perché non aggiungono una sola chiamata verso il cloud del costruttore: sono campi che
l'auto ci manda già e che finora buttavamo via (`appointmentTravel` compariva 0 volte in tutto il
package prima del 2026-08-10).

⚠️ **Il test che conta è `test_le_date_finte_non_vengono_esposte`.** Il record del piano di
partenza porta `createTime`, `updateTime` e `id`, che sembrano dire quando il piano è stato
impostato. **Non lo dicono: il backend li rigenera a ogni interrogazione.** Misurato confrontando
due letture reali a 6 settimane e mezzo di distanza (25/06 e 10/08):

    travelTime 350 · travelDate [1,2,3,4,5] · travelAppointMainId 63372   →  IDENTICI
    id 234252577 → 295802237 · createTime/updateTime → l'istante della lettura   →  CAMBIATI

Il contenuto è un piano vero; l'involucro è rigenerato. Esporre quelle date significherebbe dire
all'utente «impostato oggi alle 09:31» di un piano che non tocca da mesi — un dato inventato con
l'autorità del «letto dall'auto», che è il modo peggiore di sbagliare.
"""
from __future__ import annotations

import pytest


# Record reale letto dall'auto il 2026-08-10 (VIN e identificativi non sensibili qui: sono id
# interni del piano, non del veicolo).
PIANO_REALE = {
    "travelTime": 350,
    "createTime": 1786347068000,
    "travelDate": [1, 2, 3, 4, 5],
    "travelAppointMainId": 63372,
    "updateTime": 1786347068000,
    "id": 295802237,
    "switcher": 0,
}


@pytest.fixture
def sensore(core):
    """Il sensore del piano di partenza, con un coordinator finto minimale."""
    from custom_components.lepas.sensor import LepasDeparturePlan

    class CoordFinto:
        data: dict = {}
        config_entry = None

    s = LepasDeparturePlan.__new__(LepasDeparturePlan)
    s.coordinator = CoordFinto()
    return s


def _con(sensore, piano):
    sensore.coordinator.data = {"realtime": {"appointmentTravelSetVOS": [piano]}}
    return sensore


# ───────────────────────── piano di partenza ─────────────────────────

def test_piano_spento_dice_disattivata(sensore):
    """`switcher = 0`: c'è un piano in memoria ma non scatterà. Mostrare l'ora sarebbe
    peggio che non mostrarla — l'utente crederebbe che l'auto parta preparata."""
    assert _con(sensore, PIANO_REALE)._live_value() == "Disattivata"
    assert sensore.extra_state_attributes["attiva"] is False


def test_piano_spento_con_main_switcher_zero(sensore):
    """`mainSwitcher = "0"` disattiva il piano anche se `switcher` del singolo slot è 1."""
    attivo = dict(PIANO_REALE, switcher=1)
    sensore.coordinator.data = {"realtime": {"mainSwitcher": "0", "appointmentTravelSetVOS": [attivo]}}
    assert sensore._live_value() == "Disattivata"
    assert sensore.extra_state_attributes["attiva"] is False


def test_piano_spento_con_main_switcher_zero_senza_lista(sensore):
    """`/asd/travelManage/travelQuery` a piano spento ritorna `{mainSwitcher: 0}` senza lista."""
    sensore.coordinator.data = {"realtime": {"mainSwitcher": 0}}
    assert sensore._live_value() == "Disattivata"
    attrs = sensore.extra_state_attributes
    assert attrs is not None
    assert attrs["attiva"] is False
    assert attrs["riepilogo"] == "Disabled"


def test_piano_acceso_mostra_lorario(sensore):
    """350 minuti UTC dalla mezzanotte = 05:50 in UTC (senza hass/fuso locale)."""
    attivo = dict(PIANO_REALE, switcher=1)
    assert _con(sensore, attivo)._live_value() == "05:50"
    assert sensore.extra_state_attributes["orario"] == "05:50"


def test_piano_partenza_converte_travel_time_da_utc_a_fuso_locale(sensore, monkeypatch):
    """travelTime arriva in minuti UTC: 305 (05:05 UTC) diventa 06:05 in CET e 07:05 in CEST."""
    from datetime import datetime, timezone
    from types import SimpleNamespace
    from zoneinfo import ZoneInfo

    from custom_components.lepas import sensor as sensor_mod

    sensore.hass = SimpleNamespace(config=SimpleNamespace(time_zone="Europe/Rome"))
    rome = ZoneInfo("Europe/Rome")
    monkeypatch.setattr(sensor_mod.dt_util, "get_time_zone", lambda tz: ZoneInfo(tz))

    # Inverno (CET, UTC+1): 05:05 UTC (305 min) -> 06:05 locale
    monkeypatch.setattr(sensor_mod.dt_util, "utcnow", lambda: datetime(2026, 11, 17, 23, 0, tzinfo=timezone.utc))
    piano_inverno = dict(PIANO_REALE, switcher=1, travelTime=305)
    assert _con(sensore, piano_inverno)._live_value() == "06:05"
    assert sensore.extra_state_attributes["orario"] == "06:05"
    assert sensore.extra_state_attributes["giorni"] == [1, 2, 3, 4, 5]

    # Estate (CEST, UTC+2): 05:05 UTC -> 07:05 locale
    monkeypatch.setattr(sensor_mod.dt_util, "utcnow", lambda: datetime(2026, 8, 10, 10, 0, tzinfo=timezone.utc))
    assert _con(sensore, piano_inverno)._live_value() == "07:05"

    # Scavalco mezzanotte (23:30 UTC = 1410 min -> 00:30 CET giorno successivo, giorni traslati +1 con wrap 7->1)
    monkeypatch.setattr(sensor_mod.dt_util, "utcnow", lambda: datetime(2026, 11, 17, 23, 0, tzinfo=timezone.utc))
    piano_notte = dict(PIANO_REALE, switcher=1, travelTime=1410, travelDate=[5, 7])
    assert _con(sensore, piano_notte)._live_value() == "00:30"
    assert sensore.extra_state_attributes["giorni"] == [6, 1]
    assert rome is not None


def test_i_giorni_diventano_leggibili(sensore):
    """[1,2,3,4,5] = lunedì-venerdì, stessa numerazione di `cycleData`."""
    attrs = _con(sensore, PIANO_REALE).extra_state_attributes
    assert attrs["giorni"] == [1, 2, 3, 4, 5]
    assert attrs["giorni_testo"] == "lun, mar, mer, gio, ven"


def test_le_date_finte_non_vengono_esposte(sensore):
    """⚠️ Il test che protegge dall'errore peggiore: `createTime`/`updateTime`/`id` sono
    rigenerati a ogni interrogazione e NON devono comparire fra gli attributi."""
    attrs = _con(sensore, PIANO_REALE).extra_state_attributes
    for vietato in ("createTime", "updateTime", "id", "travelAppointMainId"):
        assert vietato not in attrs, (
            f"{vietato} è un valore rigenerato dal backend: esporlo racconta all'utente "
            f"una data che non è mai stata quella in cui ha impostato il piano"
        )


@pytest.mark.parametrize("rt", [
    {}, {"appointmentTravelSetVOS": None}, {"appointmentTravelSetVOS": []},
    {"appointmentTravelSetVOS": "non una lista"}, {"appointmentTravelSetVOS": [None]},
])
def test_nessun_piano_non_esplode(sensore, rt):
    """Campo assente o malformato ⇒ nessun valore e nessun attributo, mai un'eccezione."""
    sensore.coordinator.data = {"realtime": rt}
    assert sensore._live_value() is None
    assert sensore.extra_state_attributes is None


@pytest.mark.parametrize("minuti", [-1, 1440, 99999, "abc", None])
def test_orari_impossibili_non_vengono_mostrati(sensore, minuti):
    """Un orario fuori scala è un dato sbagliato, non un viaggio esotico: meglio niente."""
    attivo = dict(PIANO_REALE, switcher=1, travelTime=minuti)
    assert _con(sensore, attivo)._live_value() is None
    assert "orario" not in (sensore.extra_state_attributes or {})


# ───────────────────────── piano di ricarica programmata ─────────────────────────

@pytest.fixture
def switch_ricarica(core):
    from custom_components.lepas.switch import LepasScheduledChargeSwitch

    class CoordFinto:
        data: dict = {"fields": {}}
        config_entry = None

    s = LepasScheduledChargeSwitch.__new__(LepasScheduledChargeSwitch)
    s.coordinator = CoordFinto()
    return s


def test_attributi_dal_piano_dellauto(switch_ricarica):
    """Il piano che l'auto rimanda (push 110D) diventa visibile: finora l'utente poteva vedere
    solo le proprie preferenze locali, e un piano cambiato dall'app ufficiale restava invisibile."""
    switch_ricarica.coordinator.data = {"fields": {"chargeAppointPlans": [
        {"cycleData": [1, 2, 3, 4, 5, 6, 7], "startTime": "480",
         "switchStatus": "1", "timeConsuming": "360"}]}}

    attrs = switch_ricarica.extra_state_attributes
    assert attrs["orario_sull_auto"] == "08:00"
    assert attrs["durata_ore_sull_auto"] == 6.0
    assert attrs["giorni_sull_auto"] == [1, 2, 3, 4, 5, 6, 7]


def test_attributi_anche_se_il_campo_arriva_come_stringa(switch_ricarica):
    """Il 5A02 può consegnare la lista già serializzata: stessa lettura, come fa `_live_on`."""
    switch_ricarica.coordinator.data = {"fields": {"chargeAppointPlans":
        "[{'cycleData': [1, 2, 3], 'startTime': '465', 'switchStatus': '1', 'timeConsuming': '720'}]"}}

    attrs = switch_ricarica.extra_state_attributes
    assert attrs["orario_sull_auto"] == "07:45"
    assert attrs["durata_ore_sull_auto"] == 12.0


@pytest.mark.parametrize("fields", [
    {}, {"chargeAppointPlans": None}, {"chargeAppointPlans": []},
    {"chargeAppointPlans": "spazzatura {"}, {"chargeAppointPlans": [{}]},
])
def test_nessun_piano_ricarica_nessun_attributo(switch_ricarica, fields):
    """⚠️ Il 5A02 è un diario delle VARIAZIONI: il campo manca quasi sempre, ed è normale.
    Assenza di attributi ≠ assenza di piano, e non deve mai diventare un errore."""
    switch_ricarica.coordinator.data = {"fields": fields}
    assert switch_ricarica.extra_state_attributes is None
