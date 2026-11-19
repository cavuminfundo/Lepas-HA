"""Sensori realtime: quando un valore va tenuto e quando deve sparire.

I sensori Lepas sopravvivono al riavvio di HA tenendo l'ultimo valore noto — giusto per
l'odometro o la batteria, che restano veri anche se una singola lettura non li contiene.
Ma non per tutto: «Tempo di ricarica residuo» ha senso SOLO mentre l'auto carica. Quando
la carica finisce il campo sparisce dal payload, ed è proprio quello il segnale che deve
diventare «sconosciuto». Restava invece a 120 min per ore (trovato in campo il 2026-07-20).
"""
from __future__ import annotations

import json


def _coord(hass, entry):
    from custom_components.lepas.const import DOMAIN
    return hass.data[DOMAIN][entry.entry_id]


class _Msg:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
        self.topic = "x"


async def _push_realtime(hass, coord, rt: dict) -> None:
    """Simula una lettura realtime (il canale sonda), che aggiorna coord.data['realtime']."""
    coord._on_probe_data(rt)
    await hass.async_block_till_done()


# Una lettura realtime porta SEMPRE l'insieme completo dei campi (~91). L'unico che
# compare o sparisce a seconda dello stato è `remainChargeTime`: presente mentre l'auto
# carica, assente altrimenti. I due test simulano proprio quella transizione.
_IN_CARICA = {"odometer": "4062", "dumpEnergy": "68", "totalVoltage": "350.3",
              "remainChargeTime": "120", "chargeState": "1"}
_A_RIPOSO = {"odometer": "4062", "dumpEnergy": "80", "totalVoltage": "0",
             "chargeState": "0"}   # NB: senza remainChargeTime


def _entita(hass, entity_id):
    """L'OGGETTO entità (non solo lo stato), per manipolarne lo stato ripristinato."""
    comp = hass.data["entity_components"]["sensor"]
    return next(e for e in comp.entities if e.entity_id == entity_id)


async def test_tempo_ricarica_sparisce_a_carica_finita(hass, integrazione_avviata):
    """A carica finita (chargeState='0') il sensore va a 0 min, non all'ultimo valore noto;
    se invece l'auto è in ricarica (chargeState='1') ma il dato manca transitoriamente,
    resta unknown per non mostrare un falso 0 min."""
    coord = _coord(hass, integrazione_avviata)
    ent = "sensor.lepas_remaining_charge_time"
    _entita(hass, ent)._restored = 120.0     # come dopo un riavvio in carica

    await _push_realtime(hass, coord, _IN_CARICA)
    assert hass.states.get(ent).state == "120.0"

    # A riposo (chargeState="0") senza remainChargeTime -> 0 min
    await _push_realtime(hass, coord, _A_RIPOSO)
    stato = hass.states.get(ent).state
    assert stato in ("0", "0.0"), (
        f"«Tempo di ricarica residuo» doveva essere 0 min a riposo, invece è {stato}"
    )

    # In ricarica (chargeState="1") ma remainChargeTime transitoriamente assente -> unknown
    _IN_CARICA_TRANSITORIO = {
        "odometer": "4062", "dumpEnergy": "68", "totalVoltage": "350.3", "chargeState": "1"
    }
    await _push_realtime(hass, coord, _IN_CARICA_TRANSITORIO)
    stato_trans = hass.states.get(ent).state
    assert stato_trans in ("unknown", "unavailable"), (
        f"«Tempo di ricarica residuo» doveva essere unknown durante ricarica transitoria, invece è {stato_trans}"
    )


async def test_gli_altri_sensori_non_spariscono_a_fine_carica(hass, integrazione_avviata):
    """Il rovescio: la stessa transizione NON deve azzerare odometro e batteria, che
    nella lettura a riposo ci sono ancora. Solo il tempo di ricarica è volatile."""
    coord = _coord(hass, integrazione_avviata)

    await _push_realtime(hass, coord, _IN_CARICA)
    await _push_realtime(hass, coord, _A_RIPOSO)

    assert hass.states.get("sensor.lepas_odometer").state == "4062.0"
    assert hass.states.get("sensor.lepas_battery").state == "80.0"


async def test_un_solo_sensore_e_volatile(hass, integrazione_avviata):
    """Guard-rail: rendere volatile un sensore che non lo è lo farebbe sparire a ogni
    lettura parziale. Solo potenza e tempo residuo di ricarica lo sono."""
    from custom_components.lepas.sensor import _RT_SENSORS

    vol = [s.field for s in _RT_SENSORS if s.volatile]
    assert vol == ["remainChargeTime", "chargingPower"], f"sensori volatili inattesi: {vol}"


async def test_potenza_ricarica_disponibile_anche_su_phev(hass, integrazione_avviata):
    """La PHEV (Lepas L8) invia `chargingPower` sotto carica: il sensore kW esiste per tutti."""
    coord = _coord(hass, integrazione_avviata)
    ent = "sensor.lepas_charging_power"
    assert hass.states.get(ent) is not None

    await _push_realtime(hass, coord, {**_IN_CARICA, "chargingPower": "2.22"})
    assert hass.states.get(ent).state == "2.22"

    await _push_realtime(hass, coord, _A_RIPOSO)
    assert hass.states.get(ent).state in ("unknown", "unavailable")


# ───────── freschezza dei dati auto: si misura sul CONTENUTO, non sull'orologio ─────────
# Misurato in campo il 2026-07-22: il frame portava `resultTime` fermo alle 08:37:37 mentre
# i valori cambiavano davvero (batteria 41%→40% dopo le 08:59) e `time` diceva 09:01:59. Il
# sensore «Dati auto aggiornati» annunciava dati vecchi di 24 minuti mentre erano freschi —
# l'esatto contrario del suo scopo, e chi lo leggeva concludeva che l'integrazione era ferma.

def _frame(orologio_ms: int, batteria: int) -> dict:
    """Frame realtime minimo: `resultTime` è l'orologio del cloud, il resto sono i dati."""
    return {"resultTime": orologio_ms, "time": orologio_ms + 1_000_000,
            "dumpEnergy": str(batteria), "odometer": "4111", "pureElectricRange": "60"}


async def test_dati_auto_avanzano_quando_i_valori_cambiano(hass, integrazione_avviata):
    """Batteria scesa → il timestamp avanza, anche con l'orologio del cloud fermo."""
    coord = _coord(hass, integrazione_avviata)
    await _push_realtime(hass, coord, _frame(1_000_000_000_000, 41))
    primo = coord.data["car_data_ts"]
    await _push_realtime(hass, coord, _frame(1_000_000_000_000, 40))
    assert coord.data["car_data_ts"] != primo, \
        "la batteria è cambiata ma «Dati auto aggiornati» è rimasto indietro"


async def test_dati_auto_restano_fermi_se_nulla_cambia(hass, integrazione_avviata):
    """Auto ferma: rileggere gli stessi valori NON deve fingere freschezza.

    Rovescio del test precedente, e conta altrettanto: un timestamp che avanza a ogni
    lettura direbbe «aggiornato adesso» per un'auto parcheggiata da ore."""
    coord = _coord(hass, integrazione_avviata)
    await _push_realtime(hass, coord, _frame(1_000_000_000_000, 41))
    await _push_realtime(hass, coord, _frame(1_000_000_000_000, 41))
    fermo = coord.data["car_data_ts"]
    # cambia SOLO l'orologio del cloud: i dati sono identici
    await _push_realtime(hass, coord, _frame(1_000_000_900_000, 41))
    assert coord.data["car_data_ts"] == fermo


async def test_prima_lettura_parte_dall_orologio_dell_auto(hass, integrazione_avviata):
    """Al primo frame dopo l'avvio non c'è confronto possibile: si usa l'orologio dichiarato
    dall'auto invece di spacciare per «adesso» un dato magari vecchio di ore."""
    coord = _coord(hass, integrazione_avviata)
    await _push_realtime(hass, coord, _frame(1_000_000_000_000, 41))
    ts = coord.data["car_data_ts"]
    assert ts is not None and abs(ts.timestamp() - 1_000_000_000) < 2


async def test_autonomia_in_miglia_dichiara_l_unita_giusta(hass, integrazione_avviata):
    """`cruiseRange` è l'autonomia benzina in MIGLIA (182 km/1,609 = 113).

    Dichiararlo in km farebbe mostrare «113 km» — un numero semplicemente falso, e per di
    più in contraddizione con «Autonomia benzina» (182 km) sulla stessa dashboard."""
    from homeassistant.const import UnitOfLength

    from custom_components.lepas.sensor import _RT_SENSORS

    spec = next(s for s in _RT_SENSORS if s.field == "cruiseRange")
    assert spec.unit == UnitOfLength.MILES
    assert "miglia" in spec.name.lower()


# ───────── frame degradato: 0 km di autonomia elettrica = tutto il frame è da buttare ─────────
# Trovato in campo il 2026-07-31. Ricarica chiusa all'01:31 con 100% e 150 km; all'01:33,
# spenta l'alta tensione, arriva un frame con 97% e 0 km e il cloud lo ripete per 7 ore.
# L'utente vedeva 97% in HA e 100% sull'auto. La protezione che c'era scartava solo lo 0%,
# quindi un 97% "plausibile" passava indisturbato.

# Frame realtime nella forma in cui arrivano davvero: il degradato differisce dal buono
# SOLO per i due campi incriminati, così il test misura il criterio e non altro.
_CARICA_FINITA = {"odometer": "4062", "dumpEnergy": "100", "pureElectricRange": "150",
                  "mileageSurplus": "125", "chargeState": "2"}
_DEGRADATO = {"odometer": "4062", "dumpEnergy": "97", "pureElectricRange": "0",
              "mileageSurplus": "125", "chargeState": "0"}


async def test_batteria_ignora_il_frame_con_zero_km(hass, integrazione_avviata):
    """Il fix: dopo il 100% a carica finita, il frame degradato NON deve riportare a 97%."""
    coord = _coord(hass, integrazione_avviata)

    await _push_realtime(hass, coord, _CARICA_FINITA)
    assert hass.states.get("sensor.lepas_battery").state == "100.0"

    await _push_realtime(hass, coord, _DEGRADATO)
    assert hass.states.get("sensor.lepas_battery").state == "100.0", (
        "il segnaposto a 0 km ha sovrascritto la carica reale"
    )


async def test_autonomie_ignorano_il_frame_con_zero_km(hass, integrazione_avviata):
    """Stesso frame, stesso danno: l'autonomia elettrica andava a 0 km e la totale
    crollava di 150 km (251 → 125) per tutta la notte."""
    coord = _coord(hass, integrazione_avviata)

    await _push_realtime(hass, coord, _CARICA_FINITA)
    await _push_realtime(hass, coord, _DEGRADATO)

    assert hass.states.get("sensor.lepas_electric_range").state == "150.0"
    assert hass.states.get("sensor.lepas_total_range").state == "275.0"


async def test_una_carica_che_scende_davvero_passa(hass, integrazione_avviata):
    """Il rovescio, ed è il rischio vero di questa protezione: un calo LEGITTIMO (guida)
    deve passare. Il criterio è lo 0 km, non «la carica è scesa» — se fosse quello,
    l'auto guidata resterebbe inchiodata alla percentuale della partenza."""
    coord = _coord(hass, integrazione_avviata)

    await _push_realtime(hass, coord, _CARICA_FINITA)
    await _push_realtime(hass, coord, {**_CARICA_FINITA, "dumpEnergy": "62",
                                       "pureElectricRange": "93"})

    assert hass.states.get("sensor.lepas_battery").state == "62.0"
    assert hass.states.get("sensor.lepas_electric_range").state == "93.0"


async def test_il_criterio_non_scatta_se_manca_il_campo(hass, integrazione_avviata):
    """Campo assente ≠ campo a zero. Una lettura parziale senza `pureElectricRange` non
    deve essere scambiata per degradata, altrimenti la batteria smetterebbe di aggiornarsi
    ogni volta che il cloud manda un frame ridotto."""
    from custom_components.lepas.sensor import _frame_batteria_degradato

    assert _frame_batteria_degradato({"dumpEnergy": "97"}) is False
    assert _frame_batteria_degradato({"pureElectricRange": "0"}) is True
    assert _frame_batteria_degradato({"pureElectricRange": "12"}) is False

    coord = _coord(hass, integrazione_avviata)
    await _push_realtime(hass, coord, _CARICA_FINITA)
    await _push_realtime(hass, coord, {"odometer": "4062", "dumpEnergy": "62"})
    assert hass.states.get("sensor.lepas_battery").state == "62.0"


async def test_il_ripiego_e_l_ultima_lettura_non_quella_dell_avvio(hass, integrazione_avviata):
    """«Tieni l'ultimo valore noto» deve valere sull'ultima lettura VERA, non su quella
    ripristinata all'avvio di HA.

    Il ripiego era il solo valore ripristinato, fotografato una volta all'avvio e mai più
    aggiornato: con HA acceso da giorni un segnaposto non riportava all'ultima lettura buona
    ma a quella di giorni prima. Qui `_restored` = 20% (l'avvio), poi l'auto legge davvero
    47% e infine manda un segnaposto: deve restare 47, non tornare a 20."""
    coord = _coord(hass, integrazione_avviata)
    _entita(hass, "sensor.lepas_battery")._restored = 20.0

    await _push_realtime(hass, coord, {**_CARICA_FINITA, "dumpEnergy": "47",
                                       "pureElectricRange": "71"})
    assert hass.states.get("sensor.lepas_battery").state == "47.0"

    await _push_realtime(hass, coord, _DEGRADATO)
    assert hass.states.get("sensor.lepas_battery").state == "47.0"


async def test_ogni_entita_ha_un_nome_tradotto(hass, integrazione_avviata):
    """Il nome mostrato NON viene dal codice Python: viene da `strings.json`, con una chiave
    ricavata dallo slug del nome. Rinominare un'entità senza spostare anche la chiave la fa
    ripiegare sul nome della device class — successo davvero il 2026-07-22, dove «Autonomia
    benzina (miglia)» è comparsa in dashboard come «Distanza». Il codice restava corretto,
    quindi nessun test sui valori se ne sarebbe accorto: serve guardare le chiavi."""
    import json
    import pathlib

    from homeassistant.helpers import entity_registry as er

    base = pathlib.Path(__file__).resolve().parent.parent / "custom_components" / "lepas"
    strings = json.loads((base / "strings.json").read_text(encoding="utf-8"))
    voci = strings.get("entity", {})
    reg = er.async_get(hass)
    mancanti = []
    for e in er.async_entries_for_config_entry(reg, integrazione_avviata.entry_id):
        if not e.translation_key:
            continue
        piattaforma = e.entity_id.split(".", 1)[0]
        if e.translation_key not in voci.get(piattaforma, {}):
            mancanti.append(f"{e.entity_id} → entity.{piattaforma}.{e.translation_key}")
    assert not mancanti, "nomi senza traduzione:\n  " + "\n  ".join(sorted(mancanti))


def test_le_traduzioni_coprono_le_stesse_entita():
    """it/en devono elencare le stesse entità di strings.json: una voce mancante in una
    sola lingua darebbe un nome sbagliato solo ad alcuni utenti, ed è invisibile da qui."""
    import json
    import pathlib

    base = pathlib.Path(__file__).resolve().parent.parent / "custom_components" / "lepas"
    rif = json.loads((base / "strings.json").read_text(encoding="utf-8")).get("entity", {})
    for lingua in ("it", "en"):
        tr = json.loads((base / "translations" / f"{lingua}.json").read_text(encoding="utf-8"))
        for piattaforma, voci in rif.items():
            attese, trovate = set(voci), set(tr.get("entity", {}).get(piattaforma, {}))
            assert attese == trovate, (
                f"{lingua}.json, entity.{piattaforma}: "
                f"mancano {sorted(attese - trovate)}, in più {sorted(trovate - attese)}")


async def test_probe_popola_campi_stato_da_realtime(hass, integrazione_avviata):
    """I campi META presenti in /asr/manager/realtime devono popolare data['fields']
    (porte, serratura, cover, sensori diagnostici), escludendo CMD_CONFIRM_META/time/geo
    e senza emettere msg_fields."""
    coord = _coord(hass, integrazione_avviata)
    payload = {
        "odometer": "513",
        "dumpEnergy": "77",
        "pureElectricRange": "71",
        "frontLeftDoor": "0",
        "doorLock": "1",
        "trunkDoor": "1",
        "sunroofState": "0",
        "sunroofMoveState": "2",
        "chargeGunState": "1",
        "engineState": "0",
        "frontHVACState": "0",
        "result": "000000",
        "seq": "abc",
        "time": "1763360000000",
        "lat": 45.0,
        "lon": 9.0,
    }
    await _push_realtime(hass, coord, payload)

    assert hass.states.get("binary_sensor.lepas_front_left_door").state == "off"
    assert hass.states.get("lock.lepas_lock").state == "unlocked"
    assert hass.states.get("cover.lepas_trunk").state == "open"
    assert hass.states.get("sensor.lepas_sunroof_movement_state").state == "2"
    assert hass.states.get("binary_sensor.lepas_charging_cable").state == "on"

    fields = coord.data.get("fields") or {}
    for meta_key in ("result", "seq", "time", "lat", "lon"):
        assert meta_key not in fields
    assert not coord.data.get("msg_fields")


async def test_probe_non_sovrascrive_5a02_fresco_se_auto_sveglia(hass, integrazione_avviata):
    """Se è arrivato un 5A02 recente (auto sveglia), realtime riempie solo le chiavi
    mancanti senza sovrascrivere un campo già aggiornato dal push MQTT."""
    import time

    coord = _coord(hass, integrazione_avviata)
    with coord._state_lock:
        coord._last_msg_ts = time.time()
        coord._fields["doorLock"] = "1"

    await _push_realtime(hass, coord, {"doorLock": "0", "frontLeftDoor": "0"})

    fields = coord.data.get("fields") or {}
    assert fields["doorLock"] == "1"
    assert fields["frontLeftDoor"] == "0"
    assert hass.states.get("lock.lepas_lock").state == "unlocked"
    assert hass.states.get("binary_sensor.lepas_front_left_door").state == "off"

    # Valori None non sovrascrivono né popolano; fuori finestra awake, realtime aggiorna
    with coord._state_lock:
        coord._last_msg_ts = time.time() - (coord.awake_window + 5)
    await _push_realtime(hass, coord, {"doorLock": None})
    assert coord.data["fields"]["doorLock"] == "1"

    await _push_realtime(hass, coord, {"doorLock": "0"})
    assert coord.data["fields"]["doorLock"] == "0"
    assert hass.states.get("lock.lepas_lock").state == "locked"

    # Input non-dict (es. None) non solleva e non altera self._fields
    coord._on_probe_data(None)
    await hass.async_block_till_done()
    assert coord.data["fields"]["doorLock"] == "0"
