"""Sonda posizione (`probe.py`): il messaggio di stato non deve rivelare dove sei.

Il difetto vero, trovato in campo il 2026-07-20: il messaggio della sonda finisce come
STATO di un sensore — quindi nel database di Home Assistant, nel file «Scarica
diagnostica» e nel log dell'integrazione. Ci scriveva dentro «lat=…, lon=…»: la
posizione dell'auto usciva in chiaro da tre canali diversi.

Il fix è a monte (togliere le coordinate dal messaggio, non filtrarle a valle in tre
posti), quindi il posto giusto dove verificarlo è qui, alla sorgente. La posizione deve
comunque continuare ad arrivare al device_tracker, che è tutto un altro percorso.
"""
from __future__ import annotations

import fixtures as FX

LAT, LON = 40.904308, 14.349437


def _realtime_con_posizione():
    """Risposta realtime dell'auto sveglia, con coordinate e telemetria ricca."""
    return {"code": "000000", "data": {
        "lat": str(LAT), "lon": str(LON), "altitude": "120.5", "direction": "180",
        "vehicleSpeed": "0", "odometer": "4062", "dumpEnergy": "68",
        "electricRange": "3260", "onlineStatus": "1"}}


def test_il_messaggio_sonda_non_contiene_le_coordinate(core, cloud):
    """`probe_status` non deve mai contenere lat/lon: è pubblicato e persistito."""
    probe = core["probe"]
    ctx = _ctx()
    cloud.on("/asr/manager/realtime", _realtime_con_posizione())
    cloud.on("/asc/vehicleControl/queryVehicleLocation", {"code": "A07900"})
    cloud.on("/asd/travelManage/travelQuery", {"code": "A07900"})

    messaggi: list[str] = []
    probe.probe_once(ctx, messaggi.append, force=True)

    testo = " ".join(messaggi)
    assert str(LAT) not in testo, "latitudine nel messaggio della sonda"
    assert str(LON) not in testo, "longitudine nel messaggio della sonda"
    assert "120.5" not in testo, "altitudine nel messaggio della sonda"


def test_il_messaggio_sonda_tiene_la_telemetria_utile(core, cloud):
    """Il rovescio: odometro/energia/autonomia DEVONO restare, servono alla diagnostica
    e alla scoperta di campi nuovi (es. il valore `electricRange`, ancora da capire)."""
    probe = core["probe"]
    ctx = _ctx()
    cloud.on("/asr/manager/realtime", _realtime_con_posizione())
    cloud.on("/asc/vehicleControl/queryVehicleLocation", {"code": "A07900"})
    cloud.on("/asd/travelManage/travelQuery", {"code": "A07900"})

    messaggi: list[str] = []
    probe.probe_once(ctx, messaggi.append, force=True)

    testo = " ".join(messaggi)
    assert "odometer=4062" in testo
    assert "dumpEnergy=68" in testo
    assert "electricRange=3260" in testo


def test_la_posizione_arriva_comunque_al_device_tracker(core, cloud):
    """La posizione non si perde: `on_data` riceve i dati GREZZI (con lat/lon), che è il
    canale del device_tracker — separato dal messaggio leggibile."""
    probe = core["probe"]
    ctx = _ctx()
    cloud.on("/asr/manager/realtime", _realtime_con_posizione())
    cloud.on("/asc/vehicleControl/queryVehicleLocation", {"code": "A07900"})
    cloud.on("/asd/travelManage/travelQuery", {"code": "A07900"})

    ricevuti: dict = {}
    probe.probe_once(ctx, lambda m: None, force=True, on_data=ricevuti.update)

    assert ricevuti.get("lat") == str(LAT), "la posizione non è arrivata a on_data"
    assert ricevuti.get("lon") == str(LON)


def _ctx():
    from custom_components.lepas.core.context import CoreCtx
    return CoreCtx(vin=FX.VIN, tuserid=FX.TUSERID, pin=FX.PIN, email=FX.EMAIL,
                   tsp_host=FX.TSP_HOST, bff=FX.BFF)


def test_sonda_senza_gps_segnala_gps_assente_e_has_geo_false(core, cloud):
    """Realtime privo di coordinate + location con solo resultTime -> has_geo=False e GPS=assente."""
    probe = core["probe"]
    ctx = _ctx()
    cloud.on("/asr/manager/realtime", {"code": "000000", "data": {
        "odometer": "4062", "dumpEnergy": "68", "onlineStatus": "1"}})
    cloud.on("/asc/vehicleControl/queryVehicleLocation", {
        "code": "000000", "data": {"resultTime": "1795814172066"}})
    cloud.on("/asd/travelManage/travelQuery", {"code": "A07900"})

    messaggi: list[str] = []
    res = probe.probe_once(ctx, messaggi.append, force=True)

    testo = " ".join(messaggi)
    assert res["ok"] is True
    assert res["online"] is True
    assert res["has_geo"] is False
    assert "GPS=assente" in testo
    assert "odometer=4062" in testo


def test_sonda_realtime_con_lat_vuoto_non_sovrascrive_query_vehicle_location(core, cloud):
    """Realtime con lat='' e lon=None non deve cancellare le coordinate valide da queryVehicleLocation."""
    probe = core["probe"]
    ctx = _ctx()
    cloud.on("/asr/manager/realtime", {"code": "000000", "data": {
        "lat": "", "lon": None, "odometer": "4062", "dumpEnergy": "68"}})
    cloud.on("/asc/vehicleControl/queryVehicleLocation", {"code": "000000", "data": {
        "lat": str(LAT), "lon": str(LON), "direction": "180"}})
    cloud.on("/asd/travelManage/travelQuery", {"code": "A07900"})

    messaggi: list[str] = []
    ricevuti: dict = {}
    res = probe.probe_once(ctx, messaggi.append, force=True, on_data=ricevuti.update)

    testo = " ".join(messaggi)
    assert res["has_geo"] is True
    assert ricevuti.get("lat") == str(LAT)
    assert ricevuti.get("lon") == str(LON)
    assert ricevuti.get("odometer") == "4062"
    assert str(LAT) not in testo
    assert str(LON) not in testo
    assert "GPS=assente" not in testo


def test_sonda_accetta_latitude_longitude_e_scarta_null_island(core, cloud):
    """has_valid_geo accetta stringhe latitude/longitude e rifiuta Null Island (0, 0) e bool."""
    probe = core["probe"]
    assert probe.has_valid_geo({"latitude": str(LAT), "longitude": str(LON)}) is True
    assert probe.has_valid_geo({"lat": 0, "lon": 0}) is False
    assert probe.has_valid_geo({"latitude": "0.0", "longitude": "0.0"}) is False
    assert probe.has_valid_geo({"lat": True, "lon": LON}) is False
    assert probe.has_valid_geo({"latitude": LAT, "longitude": False}) is False
    assert probe.valid_coord(True, limit=90.0) is None
    assert probe.valid_coord("90.5", limit=90.0) is None

    ctx = _ctx()
    cloud.on("/asr/manager/realtime", {"code": "000000", "data": {
        "latitude": str(LAT), "longitude": str(LON), "odometer": "4100"}})
    cloud.on("/asc/vehicleControl/queryVehicleLocation", {"code": "A07900"})
    cloud.on("/asd/travelManage/travelQuery", {"code": "A07900"})

    messaggi: list[str] = []
    res = probe.probe_once(ctx, messaggi.append, force=True)
    testo = " ".join(messaggi)
    assert res["has_geo"] is True
    assert str(LAT) not in testo
    assert str(LON) not in testo

    cloud.on("/asr/manager/realtime", {"code": "000000", "data": {
        "lat": "0", "lon": "0", "odometer": "4100"}})
    messaggi_null: list[str] = []
    res_null = probe.probe_once(ctx, messaggi_null.append, force=True)
    assert res_null["has_geo"] is False
    assert "GPS=assente" in " ".join(messaggi_null)


def test_sonda_offline_restituisce_has_geo_false(core, cloud):
    """Con tutti gli endpoint in A07900, il risultato offline espone has_geo=False."""
    probe = core["probe"]
    ctx = _ctx()
    cloud.on("/asr/manager/realtime", {"code": "A07900"})
    cloud.on("/asc/vehicleControl/queryVehicleLocation", {"code": "A07900"})
    cloud.on("/asd/travelManage/travelQuery", {"code": "A07900"})

    res = probe.probe_once(ctx, lambda _m: None, force=True)
    assert res["ok"] is True
    assert res["online"] is False
    assert res["got_data"] is False
    assert res["has_geo"] is False
