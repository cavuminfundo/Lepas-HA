"""Coordinator Lepas — sostituisce ha_bridge.py (MQTT auto + sonda) in modo nativo.

Riceve via MQTT (mutual-TLS, paho in un thread) gli eventi 5A02 dell'auto, ne fa il
parsing (stesso identico mapping del bridge: vedi SENSORS) e tiene lo stato corrente
in `self.data`. Le entità native leggono da qui. Comandi/sveglia/sonda/sessione sono
delegati al "cuore di protocollo" in `core/` (eseguito in executor).

NB: i moduli `core/` leggono la config da env a import-time → impostiamo os.environ
DALL'entry prima di importarli (assunzione: una sola auto per istanza HA).
"""
from __future__ import annotations

import asyncio
from collections.abc import Sequence
import functools
import hashlib
import json
import logging
import math
import os
import shutil
import ssl
import threading
import time
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.event import async_call_later, async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, CAR_SEED, DEFAULT_AWAKE_WINDOW, DEFAULT_SESSION_EVERY, CERT_FILES,
    CONF_VIN, CONF_TUSERID, CONF_PIN, CONF_EMAIL, CONF_CERTS_SRC,
    CONF_PHONE, CONF_AREA_CODE, DEFAULT_AREA_CODE,
    CONF_LANGUAGE, LANGUAGE_FALLBACK,
    CONF_BFF, CONF_TSP_HOST, CONF_CAR_MQTT_HOST, CONF_CAR_MQTT_PORT, CONF_CHANNEL_ID,
    CONF_TENANT_CODE, CONF_COUNTRY_ID,
    CONF_POLL_NORMAL, CONF_POLL_CHARGING, DEFAULT_POLL_NORMAL_MIN,
    DEFAULT_POLL_CHARGING_MIN, POLL_WAKE_WAIT, A07900_WAKE_COOLDOWN_S,
    COMMAND_SETTLE_S, COMMAND_QUEUE_WAIT,
    HV_ON_POLL_EVERY, HV_ON_POLL_MAX,
    CHARGING_POLL_EVERY, CHARGING_POLL_MAX, DRIVE_WATCH_EVERY,
    CONF_VEHICLE_NAME, DATA_VEHICLE_MODEL, DATA_VEHICLE_BRAND,
    DATA_POWER_TYPE, DATA_CLIMATE_MIN, DATA_CLIMATE_MAX, DATA_CLIMATE_STEP,
    DATA_CLIMATE_LO, DATA_CLIMATE_HI, DATA_AIR_DURATIONS,
    DATA_CAPS_PROBED, DATA_CAPS_PROBED_V2, DATA_CAPS_PROBED_V3, DATA_CAPS_PROBED_V4,
    DATA_CAPS_PROBED_V5, DATA_VEHICLE_FEATURES,
    capabilities_from_item, features_from_permissions,
    CLIMA_MIN_DEFAULT, CLIMA_MAX_DEFAULT, CLIMA_STEP_DEFAULT,
    DEFAULTS, DIAG_SWITCH_FILE, NOTE_COMANDO_S,
)
from .scheduler import (
    DEPARTURE_CLIMATE_EXTRAS_COMMANDS,
    DEPARTURE_CLIMATE_EXTRAS_FEATURES,
    DepartureOccurrence,
    compute_battery_heat_start_for_departure,
    compute_charge_start_for_departure,
    compute_next_occurrence,
    local_schedule_to_utc,
    next_quick_departure_at,
    normalize_climate_extras,
    parse_days_input,
    shift_minutes,
)
from .timers import (
    TimerRegistry, GRUPPO_POLL,
    KEEPALIVE, POLL, HV_POLL, STARTUP_PROBE, DRIVE_WATCH, AWAKE, DEPARTURE_TICK,
)

# Cert minimi per il mutual-TLS MQTT (il .cer del server non serve a tls_set, come nel bridge).
REQUIRED_CERTS = ("ca.pem", "client.pem", "client.key")

# P1-1: marcatore stabile restituito da core/session.py `check()` per «token morto».
# Deve restare allineato a `session.STATUS_EXPIRED` (il modulo core/ è importabile solo a
# runtime, dentro l'executor, quindi qui non lo si può importare a module-level).
SESSION_STATUS_EXPIRED = "EXPIRED"

# Orologi presenti nel frame realtime: vanno IGNORATI quando si confrontano due letture,
# altrimenti due risposte con dati identici risulterebbero sempre "cambiate".
_CAMPI_OROLOGIO = frozenset({"resultTime", "collectTime", "time", "updateTime"})


def _senza_orologi(o):
    """Copia della telemetria senza i campi-orologio, a qualsiasi profondità."""
    if isinstance(o, dict):
        return {k: _senza_orologi(v) for k, v in o.items() if k not in _CAMPI_OROLOGIO}
    if isinstance(o, list):
        return [_senza_orologi(v) for v in o]
    return o


def _impronta_telemetria(data: dict) -> str:
    """Impronta del CONTENUTO della telemetria: cambia solo se cambia un dato vero."""
    return hashlib.sha256(
        json.dumps(_senza_orologi(data), sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

_LOGGER = logging.getLogger(__name__)


def _derive_brand(text: str | None) -> str:
    """Marca dal nome/modello veicolo (es. 'Lepas L8' → 'Lepas')."""
    t = (text or "").upper()
    if "LEPAS" in t:
        return "Lepas"
    return "Chery"


# Mappa campo-auto → entità (identica al bridge: ha_bridge.py SENSORS).
# kind: open|onoff → binary_sensor ON se != 0 ; lock → 0=Bloccata/1=Sbloccata ; level → sensor 0-3
SENSORS = [
    {"key": "frontLeftDoor",  "name": "Porta anteriore SX",  "comp": "binary_sensor", "dclass": "door",   "kind": "open"},
    {"key": "frontRightDoor", "name": "Porta anteriore DX",  "comp": "binary_sensor", "dclass": "door",   "kind": "open"},
    {"key": "backLeftDoor",   "name": "Porta posteriore SX", "comp": "binary_sensor", "dclass": "door",   "kind": "open"},
    {"key": "backRightDoor",  "name": "Porta posteriore DX", "comp": "binary_sensor", "dclass": "door",   "kind": "open"},
    {"key": "trunkDoor",      "name": "Baule",               "comp": "binary_sensor", "dclass": "opening","kind": "open"},
    {"key": "hood",           "name": "Cofano",              "comp": "binary_sensor", "dclass": "opening","kind": "open"},
    {"key": "liftgateOperateState", "name": "Portellone in movimento", "comp": "binary_sensor", "dclass": "moving", "kind": "onoff"},
    {"key": "doorLock",       "name": "Serratura",           "comp": "sensor",        "dclass": None,     "kind": "lock"},
    {"key": "frontLeftWindowState",  "name": "Finestrino anteriore SX",  "comp": "binary_sensor", "dclass": "window", "kind": "open"},
    {"key": "frontRightWindowState", "name": "Finestrino anteriore DX",  "comp": "binary_sensor", "dclass": "window", "kind": "open"},
    {"key": "backLeftWindowState",   "name": "Finestrino posteriore SX", "comp": "binary_sensor", "dclass": "window", "kind": "open"},
    {"key": "backRightWindowState",  "name": "Finestrino posteriore DX", "comp": "binary_sensor", "dclass": "window", "kind": "open"},
    {"key": "sunroofState",   "name": "Tetto apribile",      "comp": "binary_sensor", "dclass": "window", "kind": "open"},
    {"key": "sunshadeState",  "name": "Tendina tetto",       "comp": "binary_sensor", "dclass": "window", "kind": "open", "diag": True},
    {"key": "frontHVACState", "name": "Clima",               "comp": "binary_sensor", "dclass": "running","kind": "onoff"},
    {"key": "airPurification","name": "Purificazione aria",  "comp": "binary_sensor", "dclass": "running","kind": "onoff"},
    {"key": "frontWindshieldHeat", "name": "Sbrinamento parabrezza", "comp": "binary_sensor", "dclass": "running", "kind": "onoff"},
    {"key": "fWinHeatingState","name": "Riscaldamento parabrezza", "comp": "binary_sensor", "dclass": "running", "kind": "onoff", "diag": True},
    {"key": "rWinHeatingState","name": "Riscaldamento lunotto",    "comp": "binary_sensor", "dclass": "running", "kind": "onoff"},
    {"key": "steerWheelHeating","name": "Riscaldamento volante",   "comp": "binary_sensor", "dclass": "running", "kind": "onoff"},
    {"key": "dSeatHeatingState","name": "Riscaldamento sedile guida",     "comp": "binary_sensor", "dclass": "running", "kind": "onoff"},
    {"key": "pSeatHeatingState","name": "Riscaldamento sedile passeggero","comp": "binary_sensor", "dclass": "running", "kind": "onoff"},
    {"key": "dSeatVentilateState","name": "Ventilazione sedile guida",      "comp": "binary_sensor", "dclass": "running", "kind": "onoff"},
    {"key": "pSeatVentilateState","name": "Ventilazione sedile passeggero", "comp": "binary_sensor", "dclass": "running", "kind": "onoff"},
    {"key": "lSeatHeatingState2","name": "Riscaldamento sedile post. SX",      "comp": "sensor", "dclass": None, "kind": "level", "icon": "mdi:car-seat-heater"},
    {"key": "rSeatHeatingState2","name": "Riscaldamento sedile post. DX",      "comp": "sensor", "dclass": None, "kind": "level", "icon": "mdi:car-seat-heater"},
    {"key": "mSeatHeatingState2","name": "Riscaldamento sedile post. centrale","comp": "sensor", "dclass": None, "kind": "level", "icon": "mdi:car-seat-heater"},
    {"key": "lSeatVentilateState2","name": "Ventilazione sedile post. SX",       "comp": "sensor", "dclass": None, "kind": "level", "icon": "mdi:car-seat-cooler"},
    {"key": "rSeatVentilateState2","name": "Ventilazione sedile post. DX",       "comp": "sensor", "dclass": None, "kind": "level", "icon": "mdi:car-seat-cooler"},
    {"key": "mSeatVentilateState2","name": "Ventilazione sedile post. centrale", "comp": "sensor", "dclass": None, "kind": "level", "icon": "mdi:car-seat-cooler"},
    # — telemetria aggiuntiva (campi già inviati dall'auto nel 5A02) —
    {"key": "chargeGunState", "name": "Spina ricarica",  "comp": "binary_sensor", "dclass": "plug",    "kind": "onoff"},
    {"key": "engineState",    "name": "Motore",          "comp": "binary_sensor", "dclass": "running", "kind": "onoff", "icon": "mdi:engine"},
    # sunroofMoveState = codice di FASE di movimento del tetto (valori 1/2/3/4/8, mai 0):
    # non è un on/off pulito (non c'è un valore "fermo" noto) → sensore diagnostico raw.
    {"key": "sunroofMoveState", "name": "Tetto · stato movimento", "comp": "sensor", "dclass": None, "kind": "value", "icon": "mdi:car-select", "diag": True},
    # NB campi NON mappati di proposito (verificato su events.jsonl reali, 2026-06-21):
    #   rangeUnit / averageFuelUnit / tirePressureUnit valgono SEMPRE "1" = sono FLAG di
    #   unità di misura, NON il valore. L'auto non invia su questo canale il valore reale
    #   di autonomia/consumo/pressione gomme → mapparli mostrerebbe "1" fisso. Rimandati:
    #   serve l'altro canale (realtime /asr/manager o struttura TPMS annidata) → Round B.
]
META = {s["key"]: s for s in SENSORS}

# Meta-campi dei push di CONFERMA comando (110x/1105/1135…): NON sono telemetria di
# stato del veicolo → non vanno messi tra i "fields" (vedi _on_car_message / Item 4).
CMD_CONFIRM_META = ("result", "resultTime", "seq", "reason", "hasAsy")

# `reason` dei push di conferma: lista di `{"code": …, "modelId": …}`, una voce per ogni
# CENTRALINA che l'auto ha segnalato. `modelId` identifica il modulo.
#
# Mappatura ricavata dal campo (2026-07-21…31, 22 cicli della macro «Raffredda tutto»
# incrociati con lo stato delle entità dopo il push), NON dalla documentazione:
#   * quando `reason` è assente → clima E tutti e quattro i sedili ventilati si accendono
#     nello stesso istante;
#   * quando `reason` contiene 9/10/11/13 → i sedili ventilati NON si accendono, mentre il
#     clima parte lo stesso. Sono quindi i quattro moduli sedile. Quale voce sia quale
#     sedile NON è stato distinto (falliscono sempre tutti e quattro insieme) → nessuno dei
#     quattro viene nominato singolarmente: inventare l'assegnazione sarebbe peggio che
#     tacerla.
#   * `0` compare con codici diversi (8, 9, 11, 95, 108) ed è il clima. Attenzione: comparire
#     qui NON significa che il clima non sia partito — nei casi osservati partiva comunque.
#     Per questo il messaggio dice «segnala un problema su», non «non è partito». Anzi: il
#     codice 95 è arrivato su PRATICAMENTE OGNI comando di spegnimento, compresi quelli
#     eseguiti alla perfezione (2026-08-01) → da solo il clima non è il segno di un guasto,
#     e `_format_cmd_result` non lo tratta più come tale.
#
# Aggiornamento 2026-08-01: due voci sono state DISTINTE isolando il comando singolo, cosa
# che le macro non permettevano (lì i quattro sedili falliscono sempre insieme). Inviando il
# solo riscaldamento del sedile guida la risposta è stata esattamente `[0:9, 4:1]`, e col
# solo ventilato `[0:9, 9:1]`: nessun altro modulo. Quindi 4 e 9 sono il sedile GUIDA, e per
# esclusione gli altri tre di ciascun gruppo sono gli altri tre sedili (l'auto ne ha quattro
# riscaldati e quattro ventilati) — questi ultimi restano senza posto assegnato, perché
# quale sia quale non è stato misurato.
#   * 15 e 16 compaiono SOLO nella macro «Riscalda tutto», che oltre ai sedili comanda
#     parabrezza, lunotto e volante: sarebbero i candidati naturali, ma non è verificato →
#     restano fuori tabella.
# I modelId fuori tabella si riportano grezzi (`modulo <id>`): meglio un id che una bugia.
REASON_MODULI = {
    "0": "clima",
    "4": "sedile guida riscaldato",   # isolato dal comando singolo (2026-08-01)
    "5": "sedile riscaldato",
    "6": "sedile riscaldato",
    "8": "sedile riscaldato",
    "9": "sedile guida ventilato",    # isolato dal comando singolo (2026-08-01)
    "10": "sedile ventilato",
    "11": "sedile ventilato",
    "13": "sedile ventilato",
}

# [MED] Campi "geo" ammessi in self.position (push 1301 / sonda realtime). Si tiene
# SOLO la geolocalizzazione: batteria/velocità/online vivono in self.data["realtime"].
GEO_KEYS = ("lat", "lon", "latitude", "longitude", "speed", "vehicleSpeed",
            "direction", "heading", "altitude", "gpsTime", "positionTime")


STATO_MAX = 255           # limite di Home Assistant sullo stato di un'entità
_SEP_NOTE = " · "


def unisci_esito_e_note(esito: str, note, limite: int = STATO_MAX) -> str:
    """Riattacca all'esito di un comando gli avvisi che l'utente deve leggere.

    Nasce da un difetto misurato il 2026-08-10: gli avvisi si pubblicavano su «Esito comando»
    come ogni altro passaggio, e il passaggio successivo li copriva. «durata 25′ non ammessa da
    questa vettura (5/10/15′) → uso 15′» è rimasto leggibile **12 millisecondi** — poi «invio
    Clima acceso…». La correzione della durata funzionava (all'auto sono arrivati 15 minuti):
    l'unica cosa che non funzionava era dirlo, che è però ciò che il changelog prometteva.
    Vale per l'intera famiglia degli avvisi pre-invio, compresi quelli sui permessi delle
    v1.11/1.12: su Lepas L8 se ne vede solo la durata perché gli altri non scattano.

    ⚠️ **Il limite non è un dettaglio di formattazione.** Lo stato di un'entità in Home
    Assistant non può superare 255 caratteri, e il componente tronca già a `[:255]` in sette
    punti. Sommare l'esito e un numero qualsiasi di avvisi lo supera facilmente su un veicolo
    che ne produce molti (la macro freddo dell'issue #1 ne genera due, uno dei quali elenca
    quattro sedili). Qui il troncamento è **dichiarato**: gli avvisi che non entrano non
    vengono tagliati a metà parola, si contano — un avviso mozzato è peggio di un avviso
    assente, perché sembra completo. Il registro li ha comunque tutti e interi.

    L'esito viene prima perché è ciò che l'utente sta cercando («è partito o no?»); gli avvisi
    seguono nell'ordine in cui sono stati prodotti, che è quello in cui il comando li ha
    incontrati."""
    testo = (esito or "").strip()
    pulite = [str(n).strip() for n in (note or []) if str(n).strip()]
    if not pulite:
        return testo[:limite]
    # Il nome del comando è già la prima cosa dell'esito: ripeterlo davanti a ogni avviso costa
    # spazio dentro un budget di 255 caratteri che è il vero motivo per cui un avviso resta
    # fuori. «Sbrina lunotto: HTTP 200 A00084 … · Sbrina lunotto: il costruttore non autorizza…»
    # spendeva 16 caratteri per dire due volte la stessa cosa, e con quei 16 l'avviso non
    # entrava (270 contro 255). Nel registro il prefisso resta: lì ogni riga si legge da sola,
    # qui no. Si toglie solo se è ESATTAMENTE lo stesso prefisso dell'esito.
    prefisso = testo.split(": ", 1)[0] + ": " if ": " in testo else None
    if prefisso:
        pulite = [n[len(prefisso):].strip() if n.startswith(prefisso) else n for n in pulite]
        pulite = [n for n in pulite if n]
    def _riga(accettate) -> str:
        return _SEP_NOTE.join([p for p in (testo, *accettate) if p])

    accettate: list[str] = []
    fuori = 0
    for i, n in enumerate(pulite):
        if len(_riga([*accettate, n])) <= limite:
            accettate.append(n)
        else:
            fuori = len(pulite) - i
            break
    while fuori:
        # Quanti ne restano fuori si dice, e la coda che lo dice occupa spazio a sua volta.
        #
        # ⚠️ Qui c'era il difetto che questa funzione esiste per non fare. Se la coda non
        # entrava si tagliava la fine del testo — ma «il testo» a quel punto contiene già gli
        # avvisi accettati, quindi a essere mozzato era l'ULTIMO AVVISO, non l'esito. Misurato
        # sul caso reale della macro freddo dell'issue #1: l'utente leggeva «…ricomposto in
        # un'unica richiesta al c · (+1 nel registro)». Un avviso tagliato sembra completo, che
        # è esattamente ciò che la docstring qui sopra promette di non fare mai.
        #
        # Ora si rinuncia all'avviso INTERO: esce dalla riga e va a ingrossare il conteggio. Si
        # perde un'informazione, ma non se ne inventa una monca — e nel registro c'è per esteso.
        coda = f"{_SEP_NOTE}(+{fuori} nel registro)"
        riga = _riga(accettate)
        if len(riga) + len(coda) <= limite:
            return riga + coda
        if not accettate:
            # Nessun avviso da sacrificare: resta solo l'esito, ed è l'unico caso in cui si
            # accorcia il testo — è l'ultima informazione in ordine di importanza e non è un
            # avviso. (Succede con un esito già lungo quanto tutto il limite.)
            return (riga[:max(0, limite - len(coda))].rstrip() + coda)[:limite]
        fuori += 1
        accettate.pop()
    return _riga(accettate)[:limite]


def _is_unit_flag(key: str) -> bool:
    """True se il campo è un FLAG DI UNITÀ DI MISURA, non un valore.

    Convenzione dell'API Chery: i campi che finiscono in `Unit` (`rangeUnit`,
    `averageFuelUnit`, `tirePressureUnit`, `avgHkPowerUnit`…) valgono sempre 1 o 2 e dicono
    solo *in che unità* è espresso il campo omonimo — non contengono un dato. La scoperta
    automatica dei campi non mappati (monitor diagnostico) li segnalava come "da mappare":
    rumore puro, che nascondeva gli eventuali campi VERI ancora da scoprire. Filtrarli per
    suffisso copre anche quelli che comparissero in futuro."""
    return key.endswith("Unit")


class LepasCoordinator(DataUpdateCoordinator):
    """Tiene la connessione MQTT all'auto e lo stato; espone azioni via core/."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=None)
        self.entry = entry
        cfg = {**DEFAULTS, **dict(entry.data)}
        self.vin = cfg[CONF_VIN]
        from .core import wake
        self.tuserid = wake._valid_tuserid(cfg.get(CONF_TUSERID))
        self.channel_id = str(cfg.get(CONF_CHANNEL_ID) or DEFAULTS[CONF_CHANNEL_ID])
        self.car_host = cfg[CONF_CAR_MQTT_HOST]
        self.car_port = int(cfg[CONF_CAR_MQTT_PORT])
        self.awake_window = DEFAULT_AWAKE_WINDOW
        # per-entry storage (token + certs) nella config dir di HA
        self.token_path = hass.config.path(f"{DOMAIN}_{self.vin}_token.json")
        self.certs_dir = hass.config.path(f"{DOMAIN}_{self.vin}_certs")
        self.certs_src = cfg.get(CONF_CERTS_SRC) or ""
        self.tsp_host = cfg[CONF_TSP_HOST]
        self.pin = cfg.get(CONF_PIN, "")
        self.bff = cfg[CONF_BFF]
        # tenant/countryId per-marchio (default = Lepas/Chery EU). `cfg` parte da DEFAULTS, quindi
        # gli entry esistenti (senza queste chiavi) restano sui valori storici.
        self.tenant_code = str(cfg.get(CONF_TENANT_CODE, DEFAULTS[CONF_TENANT_CODE]))
        self.country_id = str(cfg.get(CONF_COUNTRY_ID, DEFAULTS[CONF_COUNTRY_ID]))
        self.email = cfg.get(CONF_EMAIL, "")
        # login via SMS (alternativa all'email): se il telefono è valorizzato, la
        # riautenticazione userà il ramo mobile. area_code = prefisso in cifre.
        self.phone = cfg.get(CONF_PHONE, "")
        self.area_code = str(cfg.get(CONF_AREA_CODE, DEFAULT_AREA_CODE) or DEFAULT_AREA_CODE)
        # lingua (Accept-Language): assente negli entry esistenti → it-IT (comportamento storico)
        self.language = str(cfg.get(CONF_LANGUAGE) or LANGUAGE_FALLBACK)

        # identità veicolo per il device HA. Priorità: override manuale (opzioni) →
        # valore salvato in entry.data (config flow / backfill) → None (→ fallback in entity.py).
        opt = entry.options or {}
        override = str(opt.get(CONF_VEHICLE_NAME) or "").strip()
        self.vehicle_name = override or cfg.get(CONF_VEHICLE_NAME) or None
        self.vehicle_model = cfg.get(DATA_VEHICLE_MODEL) or None
        self.vehicle_brand = cfg.get(DATA_VEHICLE_BRAND) or None

        # P2-6: qui la configurazione veniva copiata in `os.environ` perché i moduli
        # core/ la leggevano da lì. Non più: la trasporta il `CoreCtx` (vedi `_build_ctx`),
        # passato per argomento. Due conseguenze concrete:
        #   * PIN ed email NON entrano mai nell'ambiente del processo Home Assistant,
        #     che è leggibile da qualunque cosa ci giri dentro;
        #   * con due veicoli configurati il secondo entry non sovrascrive più la
        #     configurazione del primo (era ambiente di PROCESSO, condiviso da entrambi).

        self._car = None  # paho mqtt.Client (importato in _connect_car, executor)
        # P2-4: registro UNICO dei timer (keep-alive, poll, follow-up HV, sonda iniziale,
        # battito marcia). Prima erano cinque attributi `_*_unsub` cancellati in tre punti
        # e ri-armati in altri due → poll orfani che contattavano il cloud a integrazione
        # spenta. Ora l'invariante «dopo lo stop nessun timer si ri-arma» vive in un posto
        # solo: `TimerRegistry.close()`.
        self._timers = TimerRegistry()
        # poll telemetria periodico (sveglia+lettura). Intervalli in MINUTI dalle opzioni
        # (0 = off): a riposo `poll_normal_min`, alla colonnina `poll_charging_min`.
        opt = entry.options or {}
        self.poll_normal_min = int(opt.get(CONF_POLL_NORMAL, DEFAULT_POLL_NORMAL_MIN))
        self.poll_charging_min = int(opt.get(CONF_POLL_CHARGING, DEFAULT_POLL_CHARGING_MIN))
        # Fotografia delle opzioni applicate da QUESTA istanza: l'update listener la
        # confronta con quelle correnti per capire se un aggiornamento dell'entry ha
        # davvero toccato le opzioni (→ serve un reload) oppure solo `entry.data`
        # (→ nessun reload). Vedi `_async_options_updated` in __init__.py.
        self.applied_options = dict(opt)
        self._poll_busy = False       # evita sovrapposizioni tra cicli
        # follow-up "alta tensione accesa": quando l'HV è on (marcia/ricarica) la telemetria
        # realtime è VERA → rileggiamo a raffica per catturare odometro/SOC che salgono, poi
        # smettiamo da soli quando si rispegne. Zero comandi all'auto (vedi HV_ON_POLL_* in const).
        self._hv_poll_count = 0       # letture ravvicinate fatte nella finestra HV-on (cap HV_ON_POLL_MAX)
        # [2.0] esito dell'ULTIMA sonda realtime: True = auto raggiungibile dal cloud
        # (000000, c'è un frame), False = offline (A07900), None = sconosciuto. Usato dal
        # ciclo di poll per svegliare SOLO quando serve (auto che dorme davvero).
        self._online: bool | None = None
        # interruttore "Aggiornamento automatico" (switch): SPENTO di default — il poll
        # sveglia l'auto, quindi parte solo se l'utente lo accende esplicitamente. La
        # scelta dell'utente viene poi ricordata tra i riavvii (switch RestoreEntity).
        self.poll_enabled = False
        self._cmd_gate = asyncio.Lock()  # serializza i comandi: l'auto ne esegue uno alla volta (coda, non rifiuto)
        # sveglia in volo, condivisa da chi la chiede nello stesso momento (vedi
        # `async_assicura_sveglia`): due `localizza` ravvicinati sono un doppione, non una
        # sveglia più efficace — e il secondo si prende un A00082.
        self._sveglia_task: asyncio.Task | None = None
        self._fields: dict[str, str] = {}
        self._state_lock = threading.Lock()  # [H2] serializza _fields/position tra thread paho/executor/loop
        self._last_msg_ts: float = 0.0
        self._last_a07900_wake_ts: float = 0.0
        self._mqtt_msg_event: asyncio.Event = asyncio.Event()
        # contatore dei push di CONFERMA comando (non della telemetria): è l'ancora di
        # `_settle_after_command`. Vedi lì perché non basta `last_seen`.
        self._confirm_n: int = 0
        # Avvisi dell'ULTIMO comando (durata corretta, campi saltati, rifiuto annunciato) e
        # l'istante in cui sono stati prodotti. Si riattaccano all'esito e alla conferma che
        # lo sostituisce, altrimenti restano leggibili una manciata di millisecondi — vedi
        # `unisci_esito_e_note`. Scritti dal thread dell'executor (`_send_command`) e letti dal
        # thread paho (la conferma): l'assegnazione è di una lista NUOVA e mai una `append` sul
        # posto, così chi legge vede o gli avvisi di prima o quelli di dopo, mai una lista a
        # metà. Per due valori scritti insieme e letti insieme non serve un lock.
        self._note_cmd: list[str] = []
        self._note_cmd_at: float | None = None
        self.position: dict | None = None
        self.data = {"fields": {}, "msg_fields": {}, "position": None,
                     "awake": False, "car_connected": False,
                     "session_ok": None, "session_detail": "",
                     # — sensori diagnostici (parità col bridge) —
                     "cmd_status": None, "wake_status": None, "probe_status": None,
                     "last_seen": None, "last_wake": None, "last_pos_fix": None,
                     # Istante in cui la telemetria dell'auto è CAMBIATA l'ultima volta:
                     # dice quanto è fresco il dato batteria/odometro mostrato. Vedi
                     # `_on_probe_data` per il perché non si usi il timestamp del cloud.
                     "car_data_ts": None,
                     "realtime": None}
        # Impronta dell'ultima telemetria vista, per accorgersi di quando cambia davvero.
        # `None` = nessuna lettura ancora fatta in questa sessione.
        self._impronta_dati: str | None = None
        # Monitor diagnostico per lo SVILUPPATORE (diag.py): `None` = dormiente. Finché
        # resta None ogni punto di aggancio è un solo `is not None` e non si alloca nulla
        # — vale soprattutto per `_on_car_message`, che gira a ogni push dell'auto.
        self._diag = None
        self._diag_stop_unsub = None
        # P2-6: contesto dei moduli core/ (config + stato per-veicolo). Creato pigramente
        # dalla proprietà `ctx`, una volta sola: contiene l'anti-lockout del PIN e la cache
        # del taskId, che devono sopravvivere fra un comando e l'altro.
        self._ctx = None
        self._mqtt_up_ts = 0.0   # istante dell'ultima connect MQTT (uptime nel monitor)
        # Programmatore partenze e ricarica intelligente (stato in-memory, popolato da UI/servizi).
        self.clima_duration: int = 15
        self.charge_duration_hours: int = 6
        self.charge_start_minutes: int = 480
        self.charge_days: list[int] = [1, 2, 3, 4, 5, 6, 7]
        self.climate_target_temp: float = 21.0
        self.quick_departure_enabled: bool = False
        self.quick_departure_minutes: int = 1080
        self.departure_weekly: dict[int, tuple[bool, int]] = {
            d: (False, 420) for d in range(1, 8)
        }
        self.departure_climate_mode: str = "at_home"
        self.sync_charge_to_departure: bool = False
        self._probed_permessi: dict[int, int] | None = None
        self._departure_busy: bool = False
        self._quick_target_at: datetime | None = None
        self._fired_climate_key: str | None = None
        self._attempted_climate_key: str | None = None
        self._last_synced_charge_sig: tuple | None = None
        self._last_attempted_charge_sig: tuple | None = None
        self.native_departure_sync: bool = False
        self.battery_heat_enabled: bool = False
        self.battery_heat_minutes: int = 420
        self.sync_battery_heat_to_departure: bool = False
        self.departure_climate_extras: list[str] = []
        self._quick_native_until: datetime | None = None
        self._quick_applied_native: bool = False
        self._last_synced_native_dep_sig: tuple | None = None
        self._last_attempted_native_dep_sig: tuple | None = None
        self._last_synced_battery_sig: tuple | None = None
        self._last_attempted_battery_sig: tuple | None = None
        self._cached_travel_appoint: dict | None = None
        self._departure_lock: asyncio.Lock = asyncio.Lock()
        self._applied_schedule_sig: str | None = None

    def feature_enabled(self, feature: str) -> bool:
        """True se la feature è abilitata per questo veicolo (fail-open su chiave assente)."""
        vf = self.entry.data.get(DATA_VEHICLE_FEATURES) or {}
        return bool(vf.get(feature, True))

    def restore_position(self, lat: float, lon: float) -> bool:
        """Ripristina la posizione GPS da RestoreEntity (senza toccare last_pos_fix)."""
        try:
            flat, flon = float(lat), float(lon)
        except (TypeError, ValueError):
            return False
        if not (math.isfinite(flat) and math.isfinite(flon) and -90.0 <= flat <= 90.0 and -180.0 <= flon <= 180.0):
            return False
        geo = {"lat": flat, "lon": flon}
        with self._state_lock:
            if self.position is not None or self.data.get("position") is not None:
                return False
            self.position = dict(geo)
        self._update({"position": geo})
        return True

    # ───────────────── provisioning certificati mutual-TLS (FASE 3c) ─────────────────
    async def async_provision_certs(self) -> tuple[bool, str]:
        """Garantisce i cert mutual-TLS nella certs_dir per-entry. Ritorna (ok, dettaglio).

        Strategia (il provisioning ex-novo dei cert non è ancora automatizzabile —
        i 4 cert nascono dalla registrazione device dell'app, non riproducibile qui):
          1) se i 3 cert richiesti sono GIÀ nella certs_dir → ok;
          2) altrimenti, se `certs_src` (cartella dentro il filesystem di HA) li
             contiene → li copia nella certs_dir;
          3) altrimenti → (False) con istruzioni su dove metterli a mano.
        """
        return await self.hass.async_add_executor_job(self._provision_certs)

    def _provision_certs(self) -> tuple[bool, str]:
        os.makedirs(self.certs_dir, mode=0o700, exist_ok=True)

        def _have_required() -> bool:
            return all(os.path.isfile(os.path.join(self.certs_dir, f)) for f in REQUIRED_CERTS)

        if _have_required():
            return True, "cert presenti"

        # 1) override manuale: cartella indicata in certs_src
        if self.certs_src and os.path.isdir(self.certs_src):
            copied = []
            for f in CERT_FILES:
                src = os.path.join(self.certs_src, f)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(self.certs_dir, f))
                    os.chmod(os.path.join(self.certs_dir, f), 0o600)
                    copied.append(f)
            if _have_required():
                return True, f"cert importati da {self.certs_src}: {', '.join(copied)}"

        # 2) auto-provisioning dai cert universali per-regione bundlati (vedi cert_bundle)
        try:
            from .cert_bundle import decrypt_region
            certs = decrypt_region(self.car_host)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("[certs] bundle non disponibile per %s: %s", self.car_host, err)
            certs = None
        if certs:
            try:
                for name, data in certs.items():
                    p = os.path.join(self.certs_dir, name)
                    with open(p, "wb") as fh:
                        fh.write(data)
                    os.chmod(p, 0o600)
            except OSError as err:
                return False, f"scrittura cert dal bundle fallita in {self.certs_dir}: {err}"
            if _have_required():
                return True, f"cert auto-provisioned ({self.car_host})"

        return False, (f"cert mutual-TLS mancanti per {self.car_host}: regione non nel bundle. "
                       f"Copia {', '.join(REQUIRED_CERTS)} in {self.certs_dir} "
                       f"(oppure indica una cartella in certs_src).")

    # ───────────────── ciclo di vita MQTT auto ─────────────────
    async def async_start(self) -> None:
        """Avvia la connessione MQTT all'auto (paho gira in un thread proprio)."""
        await self.async_setup_diag()
        await self.hass.async_add_executor_job(self._connect_car)
        self.async_start_departure_scheduler()

    # ───────────────── monitor diagnostico (sviluppatore) ─────────────────
    async def async_setup_diag(self) -> None:
        """Accende il monitor se esiste la bandierina `lepas_diag.on` nella config dir.

        Nessun file → esce subito e tutto resta dormiente. Con il file, arma anche il
        timer di auto-spegnimento: il monitor è pensato per restare acceso pochi giorni,
        non deve poter essere dimenticato acceso (logger verboso + file su disco).

        Eccezione: bandierina a `0` → `read_switch` ritorna `math.inf` e il timer NON
        viene armato. Lo spegnimento torna manuale (si cancella la bandierina), scelta
        di chi sviluppa quando l'evento da osservare è raro e una finestra fissa
        rischierebbe di scadere proprio prima che capiti.

        Idempotente: `async_setup_entry` lo arma presto (prima del primo controllo
        sessione) e `async_start` lo richiama poco dopo — la seconda chiamata non deve
        creare un secondo scrittore sullo stesso file né riarmare l'auto-spegnimento."""
        if self._diag is not None:
            return
        from .diag import DiagRecorder, read_switch
        path = self.hass.config.path(DIAG_SWITCH_FILE)
        until = await self.hass.async_add_executor_job(read_switch, path)
        if until is None:
            return
        jsonl = self.hass.config.path(f"{DOMAIN}_{self.vin}_diag.jsonl")
        self._diag = await self.hass.async_add_executor_job(
            # il telefono va passato come vin/email: negli account SMS è l'identità di login
            functools.partial(DiagRecorder, jsonl, self.vin, self.email, until,
                              phone=self.phone)
        )
        if until == math.inf:
            _LOGGER.warning(
                "[diag] monitor diagnostico ATTIVO SENZA SCADENZA → %s (dati già "
                "oscurati; si spegne solo cancellando %s)",
                jsonl, path,
            )
            return
        self._diag_stop_unsub = async_call_later(
            self.hass, max(60.0, until - time.time()), self._diag_autostop_cb
        )
        _LOGGER.warning(
            "[diag] monitor diagnostico ATTIVO fino al %s → %s (dati già oscurati; "
            "rimuovi %s per spegnerlo prima)",
            dt_util.as_local(dt_util.utc_from_timestamp(until)).isoformat(timespec="minutes"),
            jsonl, path,
        )

    async def _diag_autostop_cb(self, _now) -> None:
        self._diag_stop_unsub = None
        # in executor: `close()` fa il join del thread scrittore e il disarmo tocca il
        # filesystem — nessuno dei due deve girare sull'event loop.
        await self.hass.async_add_executor_job(self._diag_shutdown, True)
        _LOGGER.warning("[diag] monitor diagnostico terminato (scadenza raggiunta)")

    def _diag_shutdown(self, disarm: bool = False) -> None:
        """Spegne il monitor. `disarm=True` rinomina anche la bandierina (scadenza), così
        non riparte al prossimo avvio; su unload la lascia com'è (l'utente ha ancora
        giorni a disposizione e il monitor deve riprendere al reload)."""
        rec, self._diag = self._diag, None
        # P2-6: l'aggancio del monitor vive nel contesto del veicolo, non più in un
        # global di modulo condiviso da tutte le auto.
        if self._ctx is not None:
            self._ctx.diag_hook = None
        if rec is not None:
            rec.close()
        if disarm:
            from .diag import disarm_switch
            disarm_switch(self.hass.config.path(DIAG_SWITCH_FILE))

    # ───────────────── keep-alive sessione (refresh token periodico) ─────────────────
    def async_start_keepalive(self) -> None:
        """Pianifica un refresh sessione periodico per non far scadere il token.

        `_bff_login` rinnova da sé l'access_token col refresh_token quando scade
        → ricontrollare la sessione ogni `DEFAULT_SESSION_EVERY` tiene
        viva la sessione anche da fermi (rotazione del refresh_token prima che la
        sua finestra si chiuda) ed evita una riautenticazione a sorpresa per inattività. Come
        bonus aggiorna le entità sessione. Non protegge dall'apertura dell'app
        ufficiale (sessione singola lato cloud → richiede nuovo login)."""
        if self._timers.is_armed(KEEPALIVE):
            return
        self._timers.arm(KEEPALIVE, lambda: async_track_time_interval(
            self.hass, self._keepalive, timedelta(seconds=DEFAULT_SESSION_EVERY)
        ))

    async def _keepalive(self, _now) -> None:
        try:
            # Prima il rinnovo PROATTIVO: se il token è a fine vita lo si rinnova adesso,
            # con la sessione ancora viva. Aspettare che scada significa rinnovare fino a
            # 15 minuti dopo la scadenza (la cadenza di questo timer), all'estremo della
            # finestra utile del refresh_token. Sola lettura verso il cloud.
            rinnovato, motivo = await self.hass.async_add_executor_job(self._refresh_proattivo)
            if rinnovato:
                _LOGGER.debug("[keepalive] token rinnovato in anticipo")
            elif motivo not in ("non_serve", "non_determinabile"):
                _LOGGER.debug("[keepalive] rinnovo anticipato non riuscito: %s", motivo)
            ok, detail = await self.async_check_session()
            _LOGGER.debug("[keepalive] sessione %s — %s", "ok" if ok else "KO", detail)
        except Exception as err:  # noqa: BLE001 — un errore di rete non deve fermare il timer
            _LOGGER.debug("[keepalive] errore non bloccante: %s", err)

    def _refresh_proattivo(self) -> tuple[bool, str]:
        from .core import session as SESSION
        return SESSION.refresh_se_prossimo_a_scadere(self.ctx)

    # ───────────────── stato «auto sveglia» (con scadenza) ─────────────────
    # L'auto è considerata sveglia finché continua a mandare messaggi. Prima il flag veniva
    # acceso a ogni messaggio e non si spegneva MAI: bastava un solo push perché restasse
    # `on` per giorni. Non era un difetto solo estetico — `do_wake` chiede proprio a questo
    # flag se l'auto è già sveglia (`core/wake.py`), quindi il pulsante «Sveglia auto»
    # rispondeva «già sveglia» e non mandava nulla, saltando anche il ripiego su Localizza.
    def _auto_e_sveglia(self) -> bool:
        """Sorgente di verità: si misura sul tempo dall'ultimo messaggio dell'auto."""
        with self._state_lock:
            ultimo = self._last_msg_ts
        return bool(ultimo) and (time.time() - ultimo) < self.awake_window

    @property
    def auto_sveglia(self) -> bool:
        """Accesso pubblico allo stato «sveglia» per le entità (switch macro comfort).

        Le entità NON devono leggere `data["awake"]`: quel flag è la fotografia dell'ultimo
        aggiornamento e resta acceso fino alla scadenza del timer, mentre qui la domanda è
        «l'auto sta pubblicando ADESSO?». La differenza conta: sbagliarla farebbe saltare la
        sveglia a un'auto che dorme, e la macro comfort andrebbe in timeout."""
        return self._auto_e_sveglia()

    @callback
    def _arma_scadenza_sveglia(self) -> None:
        """Programma lo spegnimento del flag a fine finestra. Nessun contatto col cloud:
        per questo NON appartiene al gruppo dell'interruttore «Aggiornamento automatico»."""
        self._timers.arm(AWAKE, lambda: async_call_later(
            self.hass, self.awake_window + 1, self._scadenza_sveglia_cb))

    async def _scadenza_sveglia_cb(self, _now) -> None:
        if self._auto_e_sveglia():
            self._arma_scadenza_sveglia()   # nel frattempo è arrivato altro: si riparte
            return
        if self.data.get("awake"):
            self._update({"awake": False})

    # ───────────────── poll telemetria periodico (sveglia + lettura) ─────────────────
    def async_start_telemetry_poll(self) -> None:
        """Avvia il poll periodico se almeno un intervallo è attivo (>0).

        Timer auto-rischedulante (`async_call_later`): l'intervallo è DINAMICO — più
        breve quando l'auto è attaccata alla colonnina (`poll_charging_min`), altrimenti
        `poll_normal_min`. Ogni ciclo SVEGLIA l'auto (vehicleLocation = posizione) e
        forza una lettura realtime (telemetria)."""
        if not self.poll_enabled:
            _LOGGER.debug("[poll] disattivato dall'interruttore")
            return
        if self.poll_normal_min <= 0 and self.poll_charging_min <= 0:
            _LOGGER.debug("[poll] disattivato (entrambi gli intervalli a 0)")
            return
        if not self._timers.is_armed(POLL):
            self._schedule_next_poll()
        # SEED iniziale: una lettura realtime ~15s dopo l'avvio (dato il tempo alla MQTT di
        # connettersi). Se l'auto è in carica/marcia (HV acceso) il follow-up ravvicinato a 2 min
        # parte SUBITO, senza attendere il primo poll periodico (fino a 30 min) — l'auto a riposo
        # NON manda MQTT, quindi senza questo seed dopo un riavvio in carica i sensori restavano
        # fermi finché non scattava il poll. Sola lettura: nessun comando all'auto. One-shot.
        if not self._timers.is_armed(STARTUP_PROBE):
            self._timers.arm(STARTUP_PROBE,
                             lambda: async_call_later(self.hass, 15, self._startup_probe_cb))

    async def _startup_probe_cb(self, _now) -> None:
        self._timers.cancel(STARTUP_PROBE)
        try:
            await self.async_probe(force=True)
        except Exception as err:  # noqa: BLE001 — il seed non deve far fallire l'avvio
            _LOGGER.debug("[poll] probe iniziale (seed) fallito: %s", err)

    @callback
    def set_poll_enabled(self, on: bool) -> None:
        """Attiva/disattiva il poll periodico a runtime (switch "Aggiornamento automatico")."""
        self.poll_enabled = on
        if on:
            self.async_start_telemetry_poll()
            self.async_start_drive_watch()
        else:
            # P0-5/P2-4: si spegne l'INTERO gruppo in un colpo solo. Prima i timer erano
            # cancellati uno per uno e il follow-up HV/ricarica — quello a 2 minuti — era
            # stato dimenticato: con lo switch su OFF durante una carica il loop continuava
            # a interrogare il cloud per ore. Il keep-alive resta apposta: tiene viva la
            # sessione senza mai contattare l'auto.
            self._timers.cancel_many(GRUPPO_POLL)
            self._hv_poll_count = 0
        if not self._timers.closing:
            self.async_update_listeners()

    # ───────────────── programmatore partenze e ricarica intelligente ─────────────────
    def async_start_departure_scheduler(self) -> None:
        """Avvia il tick al minuto dello schedulatore partenze/ricarica (sopravvive a poll OFF)."""
        if self._timers.closing or self._timers.is_armed(DEPARTURE_TICK):
            return
        self._timers.arm(
            DEPARTURE_TICK,
            lambda: async_track_time_interval(
                self.hass,
                self._departure_timer_cb,
                timedelta(minutes=1),
            ),
        )

    async def _departure_timer_cb(self, now: datetime) -> None:
        await self._departure_tick_cb(_now=dt_util.as_local(now))

    def next_departure_occurrence(
        self, now: datetime | None = None
    ) -> DepartureOccurrence | None:
        """Calcola la prossima partenza attiva (rapida o settimanale)."""
        ref = now if now is not None else dt_util.now()
        return compute_next_occurrence(
            ref,
            self.departure_weekly,
            self.quick_departure_enabled,
            self.quick_departure_minutes,
            self.clima_duration,
        )

    def effective_charge_days(self, target_days=None) -> list[int]:
        """Giorni effettivi da inviare in cycleData, con ripiego [1..7] se 2131 == 0."""
        if not self.feature_enabled("scheduled_charging_custom_days"):
            return [1, 2, 3, 4, 5, 6, 7]
        if isinstance(self._probed_permessi, dict) and self._probed_permessi.get(2131) == 0:
            return [1, 2, 3, 4, 5, 6, 7]
        src = self.charge_days if target_days is None else target_days
        return parse_days_input(src)

    def _local_tzinfo(self):
        tz_name = getattr(getattr(self.hass, "config", None), "time_zone", None)
        return (dt_util.get_time_zone(tz_name) if tz_name else None) or dt_util.DEFAULT_TIME_ZONE

    def effective_departure_days(self, target_days=None) -> list[int]:
        """Giorni effettivi per travelWeekday, con ripiego [1..7] se 2121 == 0."""
        if not self.feature_enabled("scheduled_departure_custom_days"):
            return [1, 2, 3, 4, 5, 6, 7]
        if isinstance(self._probed_permessi, dict) and self._probed_permessi.get(2121) == 0:
            return [1, 2, 3, 4, 5, 6, 7]
        if target_days is not None:
            return parse_days_input(target_days)
        active = [
            d
            for d in range(1, 8)
            if isinstance(self.departure_weekly.get(d), tuple) and self.departure_weekly[d][0]
        ]
        return active or [1, 2, 3, 4, 5, 6, 7]

    def _extra_feature_allowed(self, extra_key: str) -> bool:
        feat = DEPARTURE_CLIMATE_EXTRAS_FEATURES.get(extra_key)
        if not feat or not self.feature_enabled(feat):
            return False
        if isinstance(self._probed_permessi, dict):
            if features_from_permissions(self._probed_permessi).get(feat) is False:
                return False
        return True

    def allowed_departure_climate_extras(self) -> list[str]:
        """Chiavi extra clima consentite dalle capability del veicolo."""
        return [k for k in DEPARTURE_CLIMATE_EXTRAS_COMMANDS if self._extra_feature_allowed(k)]

    async def async_set_departure_climate_extras(self, extras: Sequence[str]) -> list[str]:
        """Valida, normalizza e salva gli extra clima da inviare al pre-clima di partenza."""
        if self._timers.closing:
            return list(self.departure_climate_extras)
        normalized = normalize_climate_extras(extras)
        filtered = [k for k in normalized if self._extra_feature_allowed(k)]
        self.departure_climate_extras = filtered
        self.async_update_listeners()
        return list(filtered)

    def _native_departure_server_id(self) -> object | None:
        rt = (self.data or {}).get("realtime") or {}
        for source in (rt, self._cached_travel_appoint):
            if not isinstance(source, dict):
                continue
            vos = source.get("appointmentTravelSetVOS")
            if isinstance(vos, list) and vos and isinstance(vos[0], dict):
                sid = vos[0].get("id")
                if sid is not None and str(sid).strip() != "":
                    return sid
            sid = source.get("id")
            if sid is not None and str(sid).strip() != "":
                return sid
        return None

    def _build_native_departure_payload(
        self, occ: DepartureOccurrence | None
    ) -> tuple[str, dict, tuple]:
        server_id = self._native_departure_server_id()
        if occ is None:
            rt = (self.data or {}).get("realtime") or {}
            existing_time: str | None = None
            for source in (rt, self._cached_travel_appoint):
                if not isinstance(source, dict):
                    continue
                vos = source.get("appointmentTravelSetVOS")
                if isinstance(vos, list) and vos and isinstance(vos[0], dict):
                    raw_t = vos[0].get("travelTime")
                    if raw_t is not None and str(raw_t).strip().isdigit():
                        existing_time = str(int(str(raw_t).strip()) % 1440)
                        break
            off_days = self.effective_departure_days([1])
            plan: dict[str, object] = {
                "planId": 1,
                "switcher": "0",
                "travelTime": existing_time if existing_time is not None else "420",
                "travelWeekday": [str(d) for d in off_days],
            }
            if server_id is not None:
                plan["id"] = server_id
            return (
                "partenza_prog_off",
                {"mainSwitcher": "0", "appointmentTravelAOS": [plan]},
                ("0", 0, ()),
            )

        local_min = occ.departure_at_minutes
        if occ.source == "quick":
            target_days = [occ.weekday]
        else:
            target_days = [
                d
                for d in range(1, 8)
                if isinstance(self.departure_weekly.get(d), tuple)
                and self.departure_weekly[d][0]
                and (int(self.departure_weekly[d][1]) % 1440) == local_min
            ] or [occ.weekday]
        eff_local_days = self.effective_departure_days(target_days)
        tz = occ.departure_at.tzinfo or self._local_tzinfo()
        utc_min, utc_days = local_schedule_to_utc(
            local_min,
            eff_local_days,
            tz,
            ref_date=occ.departure_at.date(),
        )
        plan = {
            "planId": 1,
            "switcher": "1",
            "travelTime": str(utc_min),
            "travelWeekday": [str(d) for d in utc_days],
        }
        if server_id is not None:
            plan["id"] = server_id
        return (
            "partenza_prog_on",
            {"mainSwitcher": "1", "appointmentTravelAOS": [plan]},
            ("1", utc_min, tuple(utc_days)),
        )

    async def _async_refresh_travel_appoint_realtime(self) -> None:
        """Riallinea `realtime` da `/asd/travelManage/travelQuery` dopo appointmentTravel."""
        if self._timers.closing:
            return
        try:
            res = await self.async_query_travel_appoint()
        except Exception as err:  # noqa: BLE001 — refresh best-effort post comando
            _LOGGER.debug("[scheduler] refresh travelQuery post-comando fallito: %s", type(err).__name__)
            return
        if self._timers.closing or not isinstance(res, dict):
            return
        rt = dict((self.data or {}).get("realtime") or {})
        if "mainSwitcher" in res:
            rt["mainSwitcher"] = res["mainSwitcher"]
        if "appointmentTravelSetVOS" in res:
            rt["appointmentTravelSetVOS"] = res["appointmentTravelSetVOS"]
        elif str(res.get("mainSwitcher")).strip().lower() in ("0", "false"):
            rt.pop("appointmentTravelSetVOS", None)
        self._apply_update({"realtime": rt})

    async def _post_settle_travel_refresh(self) -> None:
        if self._timers.closing:
            return
        try:
            await self._settle_after_command()
            if not self._timers.closing:
                await self._async_refresh_travel_appoint_realtime()
        except asyncio.CancelledError:
            return

    def departure_schedule_signature(self) -> str:
        """Firma JSON canonica dell'intero piano partenza (rapida + 7 giorni)."""
        quick: list[object] = (
            [True, int(self.quick_departure_minutes) % 1440]
            if self.quick_departure_enabled
            else [False, None]
        )
        weekly: list[list[object]] = []
        for d in range(1, 8):
            entry = self.departure_weekly.get(d)
            if isinstance(entry, tuple) and len(entry) >= 2 and bool(entry[0]):
                weekly.append([d, True, int(entry[1]) % 1440])
            else:
                weekly.append([d, False, None])
        return json.dumps({"q": quick, "w": weekly}, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _weekly_signature_part(raw_sig: str | None) -> list | None:
        if not isinstance(raw_sig, str) or not raw_sig.strip():
            return None
        try:
            parsed = json.loads(raw_sig)
        except (TypeError, ValueError):
            return None
        if not isinstance(parsed, dict):
            return None
        weekly = parsed.get("w")
        return weekly if isinstance(weekly, list) else None

    def _is_weekly_dirty(self) -> bool:
        return (
            self._applied_schedule_sig is not None
            and self._weekly_signature_part(self.departure_schedule_signature())
            != self._weekly_signature_part(self._applied_schedule_sig)
        )

    def has_active_departure_schedule(self) -> bool:
        if self.quick_departure_enabled:
            return True
        return any(
            isinstance(self.departure_weekly.get(d), tuple) and bool(self.departure_weekly[d][0])
            for d in range(1, 8)
        )

    def _is_car_departure_active(self) -> bool | None:
        rt = (self.data or {}).get("realtime")
        if not isinstance(rt, dict):
            return None
        from .entity import field_on

        main_state = field_on(rt.get("mainSwitcher"))
        if main_state is False:
            return False
        piani = rt.get("appointmentTravelSetVOS")
        if not isinstance(piani, list) or not piani:
            return None
        any_sw_on: bool | None = None
        for p in piani:
            if not isinstance(p, dict):
                continue
            sw = field_on(p.get("switcher"))
            if sw is True:
                return True
            if sw is False and any_sw_on is None:
                any_sw_on = False
        return any_sw_on

    def has_pending_departure_changes(self) -> bool:
        car_active = self._is_car_departure_active()
        if not self.has_active_departure_schedule():
            return car_active is True or (
                car_active is None and self._applied_schedule_sig is not None
            )
        return (
            self._applied_schedule_sig is None
            or self.departure_schedule_signature() != self._applied_schedule_sig
        )

    def restore_applied_schedule_sig(self, raw_sig: str | None) -> None:
        """Ripristina `_applied_schedule_sig` dal sensore Persistito al boot."""
        if self._applied_schedule_sig is None and isinstance(raw_sig, str) and raw_sig.strip():
            self._applied_schedule_sig = raw_sig.strip()
        if not self._timers.closing:
            self.async_update_listeners()

    async def _schedule_travel_refresh(self) -> None:
        await self._async_refresh_travel_appoint_realtime()
        if not self._timers.closing and hasattr(self.hass, "async_create_background_task"):
            self.hass.async_create_background_task(
                self._post_settle_travel_refresh(),
                f"{DOMAIN}_travel_refresh",
            )

    async def async_apply_departure_schedule(self) -> None:
        """Override manuale: invia subito appointmentTravel (ON o OFF) e abilita auto-sync."""
        if self._timers.closing:
            return
        async with self._departure_lock:
            await self._async_apply_departure_schedule_locked(enable_native_sync=True)

    async def _async_apply_departure_schedule_locked(
        self,
        *,
        enable_native_sync: bool = True,
    ) -> None:
        if self._timers.closing:
            return
        now = dt_util.now()
        occ = self.next_departure_occurrence(now)
        cmd_key, body, sig = self._build_native_departure_payload(occ)
        if self._timers.closing:
            return
        await self.async_send_command(cmd_key, body)
        if self._timers.closing:
            return
        self._last_synced_native_dep_sig = sig
        self._last_attempted_native_dep_sig = None
        if occ is not None:
            self._applied_schedule_sig = self.departure_schedule_signature()
            if enable_native_sync:
                self.native_departure_sync = True
        else:
            self._applied_schedule_sig = None
            self.native_departure_sync = False
            self._quick_applied_native = False
        self.async_update_listeners()
        await self._schedule_travel_refresh()

    async def async_disable_departure_schedule(self) -> None:
        """Disattiva sull'auto (fail-closed) e poi azzera tutti i giorni, rapida e sync in HA."""
        if self._timers.closing:
            return
        async with self._departure_lock:
            if self._timers.closing:
                return
            cmd_key, body, _ = self._build_native_departure_payload(None)
            await self.async_send_command(cmd_key, body)
            if self._timers.closing:
                return
            self.quick_departure_enabled = False
            self._quick_target_at = None
            self._quick_native_until = None
            self._quick_applied_native = False
            for d in range(1, 8):
                entry = self.departure_weekly.get(d)
                mins = int(entry[1]) % 1440 if isinstance(entry, tuple) and len(entry) >= 2 else 420
                self.departure_weekly[d] = (False, mins)
            self.native_departure_sync = False
            self._applied_schedule_sig = None
            self._last_synced_native_dep_sig = None
            self._last_attempted_native_dep_sig = None
            self.async_update_listeners()
            if self.sync_battery_heat_to_departure:
                await self._async_sync_battery_for_occurrence(None)
                if self._timers.closing:
                    return
            await self._schedule_travel_refresh()

    async def _async_sync_native_departure(self, occ: DepartureOccurrence | None) -> bool:
        if self._timers.closing:
            return False
        cmd_key, body, sig = self._build_native_departure_payload(occ)
        if (
            sig == self._last_synced_native_dep_sig
            or sig == self._last_attempted_native_dep_sig
        ):
            return False
        try:
            await self.async_send_command(cmd_key, body)
        except Exception as err:  # noqa: BLE001 — evita retry storm ogni 60s
            if self._timers.closing:
                return False
            self._last_attempted_native_dep_sig = sig
            _LOGGER.warning(
                "[scheduler] sincronizzazione partenza nativa fallita (%s)",
                type(err).__name__,
            )
            return False
        if self._timers.closing:
            return False
        self._last_synced_native_dep_sig = sig
        self._last_attempted_native_dep_sig = None
        await self._schedule_travel_refresh()
        return True

    def _sync_battery_heat_start_local(self, occ: DepartureOccurrence | None) -> bool:
        if not self.sync_battery_heat_to_departure or occ is None:
            return False
        start_min = compute_battery_heat_start_for_departure(occ.departure_at_minutes, 30)
        if self.battery_heat_minutes != start_min:
            self.battery_heat_minutes = start_min
            return True
        return False

    async def async_apply_battery_pack_heat(
        self,
        *,
        enabled: bool | None = None,
        minutes: int | None = None,
    ) -> None:
        """Applica manualmente stato e orario di batteryPackHeat."""
        if self._timers.closing:
            return
        if minutes is not None:
            m = int(minutes)
            if not 0 <= m < 1440:
                raise ValueError(f"battery heat minutes out of range 0..1439: {minutes!r}")
            self.battery_heat_minutes = m
        if enabled is not None:
            self.battery_heat_enabled = bool(enabled)

        self.async_update_listeners()
        if self._timers.closing:
            return

        tz = self._local_tzinfo()
        if self.battery_heat_enabled:
            local_min = int(self.battery_heat_minutes) % 1440
            ref_local = dt_util.now().astimezone(tz)
            utc_min, _ = local_schedule_to_utc(local_min, None, tz, ref_date=ref_local.date())
            cmd_key = "battery_heat_on"
            params = {"switchState": "1", "startTime": str(utc_min)}
            sig_key = "manual"
            occ = self.next_departure_occurrence(dt_util.now())
            if (
                self.sync_battery_heat_to_departure
                and occ is not None
                and compute_battery_heat_start_for_departure(occ.departure_at_minutes, 30) == local_min
            ):
                sig_key = occ.key
            sig: tuple = (sig_key, True, utc_min)
        else:
            cmd_key = "battery_heat_off"
            params = {"switchState": "0", "startTime": "0"}
            sig = ("off", False, 0)

        await self.async_send_command(cmd_key, params)
        if self._timers.closing:
            return
        self._last_synced_battery_sig = sig
        self._last_attempted_battery_sig = None

    async def _async_sync_battery_for_occurrence(
        self,
        occ: DepartureOccurrence | None,
        *,
        force_off: bool = False,
    ) -> None:
        if self._timers.closing:
            return
        if occ is None:
            was_on = self.battery_heat_enabled or (
                self._last_synced_battery_sig is not None and bool(self._last_synced_battery_sig[1])
            )
            if not (force_off or was_on):
                return
            sig: tuple = ("off", False, 0)
            cmd_key = "battery_heat_off"
            params = {"switchState": "0", "startTime": "0"}
            target_enabled = False
        else:
            local_min = compute_battery_heat_start_for_departure(occ.departure_at_minutes, 30)
            heat_dt = shift_minutes(occ.departure_at, -30)
            tz = occ.departure_at.tzinfo or self._local_tzinfo()
            utc_min, _ = local_schedule_to_utc(local_min, None, tz, ref_date=heat_dt.date())
            sig = (occ.key, True, utc_min)
            cmd_key = "battery_heat_on"
            params = {"switchState": "1", "startTime": str(utc_min)}
            target_enabled = True

        if sig == self._last_synced_battery_sig or sig == self._last_attempted_battery_sig:
            return
        try:
            await self.async_send_command(cmd_key, params)
        except Exception as err:  # noqa: BLE001 — evita retry storm ogni 60s
            if self._timers.closing:
                return
            self._last_attempted_battery_sig = sig
            _LOGGER.warning(
                "[scheduler] sincronizzazione preriscaldamento batteria fallita (%s)",
                type(err).__name__,
            )
            return
        if self._timers.closing:
            return
        self.battery_heat_enabled = target_enabled
        self._last_synced_battery_sig = sig
        self._last_attempted_battery_sig = None
        self.async_update_listeners()

    async def async_query_travel_appoint(self) -> dict | None:
        """Query on-demand del piano di partenza nativa (mai nel polling passivo)."""
        if self._timers.closing:
            return None
        from .core import commands as CMD

        res = await self.hass.async_add_executor_job(CMD.query_travel_appoint, self.ctx)
        if self._timers.closing:
            return None
        if isinstance(res, dict):
            self._cached_travel_appoint = res
        return res

    async def async_query_battery_pack_heat(self) -> dict | None:
        """Query on-demand dello stato di preriscaldamento batteria (mai nel polling passivo)."""
        if self._timers.closing:
            return None
        from .core import commands as CMD

        res = await self.hass.async_add_executor_job(CMD.query_battery_pack_heat, self.ctx)
        if self._timers.closing:
            return None
        return res

    def _anchor_quick_target(self, now: datetime, *, force: bool = False) -> None:
        if not self.quick_departure_enabled:
            self._quick_target_at = None
            return
        q_min = int(self.quick_departure_minutes) % 1440
        if force or self._quick_target_at is None:
            self._quick_target_at = next_quick_departure_at(now, q_min)
            return
        anchored_min = self._quick_target_at.hour * 60 + self._quick_target_at.minute
        if anchored_min != q_min:
            self._quick_target_at = next_quick_departure_at(now, q_min)

    def _sync_charge_start_local(self, occ: DepartureOccurrence | None) -> bool:
        if not self.sync_charge_to_departure or occ is None:
            return False
        dur_h = int(self.charge_duration_hours or 6)
        start_min = compute_charge_start_for_departure(occ.departure_at_minutes, dur_h)
        if self.charge_start_minutes != start_min:
            self.charge_start_minutes = start_min
            return True
        return False

    def _charge_sync_window_active(self, now: datetime, occ: DepartureOccurrence) -> bool:
        if occ.source == "quick":
            return True
        dur_h = int(self.charge_duration_hours or 6)
        charge_start_at = shift_minutes(occ.departure_at, -dur_h * 60)
        return shift_minutes(charge_start_at, -60) <= now < occ.departure_at

    @callback
    def notify_schedule_changed(
        self,
        *,
        sync_charge: bool = False,
        sync_native: bool = False,
        sync_battery: bool = False,
    ) -> None:
        """Aggiorna ancora rapida, orario ricarica/batteria locale e UI; opzionalmente sync cloud."""
        if self._timers.closing:
            return
        self._quick_native_until = None
        self._quick_applied_native = False
        self._last_attempted_native_dep_sig = None
        self._last_attempted_battery_sig = None
        self._last_attempted_charge_sig = None
        now = dt_util.now()
        self._anchor_quick_target(now)
        occ = self.next_departure_occurrence(now)
        self._sync_charge_start_local(occ)
        self._sync_battery_heat_start_local(occ)
        self.async_update_listeners()
        if (
            sync_charge
            and self.sync_charge_to_departure
            and occ is not None
            and not self._timers.closing
            and self._charge_sync_window_active(now, occ)
        ):
            self.hass.async_create_background_task(
                self._async_sync_charge_for_occurrence(occ),
                f"{DOMAIN}_charge_sync",
            )
        if sync_native and self.native_departure_sync and not self._timers.closing:
            self.hass.async_create_background_task(
                self._async_sync_native_departure(occ),
                f"{DOMAIN}_native_dep_sync",
            )
        if sync_battery and self.sync_battery_heat_to_departure and not self._timers.closing:
            self.hass.async_create_background_task(
                self._async_sync_battery_for_occurrence(occ),
                f"{DOMAIN}_battery_heat_sync",
            )

    async def async_set_quick_departure(
        self,
        minutes: int | None = None,
        enabled: bool = True,
        *,
        sync_charging: bool | None = None,
        apply_native: bool | None = None,
    ) -> None:
        """Imposta la partenza rapida una tantum e sincronizza subito se richiesto."""
        if self._timers.closing:
            return
        parsed_minutes: int | None = None
        if minutes is not None:
            parsed_minutes = int(minutes)
            if not 0 <= parsed_minutes < 1440:
                raise ValueError(f"quick departure minutes out of range 0..1439: {minutes!r}")

        async with self._departure_lock:
            if self._timers.closing:
                return
            if parsed_minutes is not None:
                self.quick_departure_minutes = parsed_minutes
            if sync_charging is not None:
                self.sync_charge_to_departure = bool(sync_charging)
            self.quick_departure_enabled = bool(enabled)
            self._quick_native_until = None
            self._quick_applied_native = False
            self._last_attempted_native_dep_sig = None
            self._last_attempted_battery_sig = None
            self._last_attempted_charge_sig = None

            now = dt_util.now()
            self._anchor_quick_target(now, force=True)
            occ = self.next_departure_occurrence(now)
            self._sync_charge_start_local(occ)
            self._sync_battery_heat_start_local(occ)
            self.async_update_listeners()

            if (
                self.sync_charge_to_departure
                and occ is not None
                and not self._timers.closing
                and self._charge_sync_window_active(now, occ)
            ):
                await self._async_sync_charge_for_occurrence(occ)
                if self._timers.closing:
                    return

            if apply_native is True:
                await self._async_apply_departure_schedule_locked(enable_native_sync=False)
                if self._timers.closing:
                    return
                if self.quick_departure_enabled and not self.native_departure_sync:
                    self._quick_applied_native = True
            elif apply_native is None and self.native_departure_sync:
                weekly_dirty = self._is_weekly_dirty()
                sent_ok = await self._async_sync_native_departure(occ)
                if self._timers.closing:
                    return
                if sent_ok and not weekly_dirty:
                    if occ is not None:
                        self._applied_schedule_sig = self.departure_schedule_signature()
                    else:
                        self._applied_schedule_sig = None
                    self.async_update_listeners()

            if self.sync_battery_heat_to_departure and apply_native is not False:
                await self._async_sync_battery_for_occurrence(occ)
                if self._timers.closing:
                    return

    async def async_apply_charging_schedule(
        self,
        *,
        start_minutes: int | None = None,
        duration_hours: int | None = None,
        days=None,
    ) -> None:
        """Override manuale: invia subito ricarica_prog_on ignorando blocchi anti-duplicato."""
        if self._timers.closing:
            return
        if start_minutes is not None:
            m = int(start_minutes)
            if not 0 <= m < 1440:
                raise ValueError(f"start_minutes out of range 0..1439: {start_minutes!r}")
            self.charge_start_minutes = m
        if duration_hours is not None:
            dur = int(duration_hours)
            if not 1 <= dur <= 12:
                raise ValueError(f"duration_hours out of range 1..12: {duration_hours!r}")
            self.charge_duration_hours = dur
        if days is not None:
            self.charge_days = parse_days_input(days)

        self.async_update_listeners()
        if self._timers.closing:
            return

        dur_h = int(self.charge_duration_hours or 6)
        start_min = int(self.charge_start_minutes) % 1440
        eff_days = self.effective_charge_days()
        plan = {
            "cycleData": list(eff_days),
            "startTime": start_min,
            "switchStatus": 1,
            "timeConsuming": dur_h * 60,
        }
        await self.async_send_command(
            "ricarica_prog_on",
            {"mainSwitch": 1, "chargeAppointPlans": [plan]},
        )
        if self._timers.closing:
            return

        now = dt_util.now()
        occ = self.next_departure_occurrence(now)
        target_iso = "manual"
        if self.sync_charge_to_departure and occ is not None:
            occ_start_min = compute_charge_start_for_departure(occ.departure_at_minutes, dur_h)
            occ_charge_start = shift_minutes(occ.departure_at, -dur_h * 60)
            occ_days = self.effective_charge_days([occ_charge_start.isoweekday()])
            if occ_start_min == start_min and tuple(occ_days) == tuple(eff_days):
                target_iso = occ_charge_start.isoformat()
        self._last_synced_charge_sig = (target_iso, start_min, dur_h, tuple(eff_days))
        self._last_attempted_charge_sig = None

    async def _async_sync_charge_for_occurrence(self, occ: DepartureOccurrence) -> None:
        if self._timers.closing:
            return
        dur_h = int(self.charge_duration_hours or 6)
        start_min = compute_charge_start_for_departure(occ.departure_at_minutes, dur_h)
        charge_start_at = shift_minutes(occ.departure_at, -dur_h * 60)
        days = self.effective_charge_days([charge_start_at.isoweekday()])
        sig = (charge_start_at.isoformat(), start_min, dur_h, tuple(days))
        if sig == self._last_synced_charge_sig or sig == self._last_attempted_charge_sig:
            return

        plan = {
            "cycleData": list(days),
            "startTime": int(start_min),
            "switchStatus": 1,
            "timeConsuming": dur_h * 60,
        }
        try:
            await self.async_send_command(
                "ricarica_prog_on",
                {"mainSwitch": 1, "chargeAppointPlans": [plan]},
            )
        except Exception as err:  # noqa: BLE001 — evita retry storm ogni 60s
            if self._timers.closing:
                return
            self._last_attempted_charge_sig = sig
            _LOGGER.warning("[scheduler] sincronizzazione ricarica fallita: %s", err)
            return
        if self._timers.closing:
            return
        self._last_synced_charge_sig = sig
        self._last_attempted_charge_sig = None

    def _current_position(self) -> dict | None:
        pos = (self.data or {}).get("position")
        if isinstance(pos, dict):
            return pos
        with self._state_lock:
            return dict(self.position) if isinstance(self.position, dict) else None

    def _vehicle_running_or_moving(self) -> bool:
        from .entity import field_on

        data = self.data or {}
        rt = data.get("realtime") or {}
        data_fields = data.get("fields") or {}
        with self._state_lock:
            fields_snapshot = dict(self._fields)

        def _read(key: str):
            v = rt.get(key)
            if v is None:
                v = data_fields.get(key)
            if v is None:
                v = fields_snapshot.get(key)
            return v

        if field_on(_read("engineState")):
            return True
        sp = _read("vehicleSpeed")
        try:
            if sp is not None and float(sp) > 0:
                return True
        except (TypeError, ValueError):
            pass
        return False

    async def _maybe_trigger_preclimate(self, occ: DepartureOccurrence) -> bool:
        if self._timers.closing:
            return False
        if self.departure_climate_mode == "at_home":
            from .entity import in_zona_casa

            casa = self.hass.states.get("zone.home")
            if (
                casa is not None
                and casa.attributes.get("latitude") is not None
                and casa.attributes.get("longitude") is not None
            ):
                if in_zona_casa(self.hass, self._current_position()) is not True:
                    self._fired_climate_key = occ.key
                    _LOGGER.info("[scheduler] pre-clima saltato: veicolo non in zona casa")
                    return False

        if self._vehicle_running_or_moving():
            _LOGGER.debug("[scheduler] pre-clima saltato: veicolo acceso o in movimento")
            return False

        lo, hi, _step = self.climate_limits()
        temp = min(hi, max(lo, float(self.climate_target_temp)))
        dur = int(self.clima_duration or 15)
        self._attempted_climate_key = occ.key
        try:
            await self.async_send_command(
                "clima_on",
                {"temperature": f"{temp:.1f}", "times": str(dur)},
            )
        except Exception as err:  # noqa: BLE001 — evita retry ogni 60s su errore
            if self._timers.closing:
                return False
            _LOGGER.warning("[scheduler] avvio pre-clima fallito: %s", type(err).__name__)
        else:
            if self._timers.closing:
                return False
            self._fired_climate_key = occ.key
            try:
                extras = normalize_climate_extras(self.departure_climate_extras)
            except ValueError:
                extras = []
            for extra_key in extras:
                if not self._extra_feature_allowed(extra_key):
                    continue
                if self._timers.closing:
                    return False
                cmd_key = DEPARTURE_CLIMATE_EXTRAS_COMMANDS[extra_key]
                try:
                    await self.async_send_command(cmd_key)
                except Exception as extra_err:  # noqa: BLE001 — non azzera _fired_climate_key
                    if self._timers.closing:
                        return False
                    _LOGGER.warning(
                        "[scheduler] extra clima '%s' fallito (%s)",
                        extra_key,
                        type(extra_err).__name__,
                    )
                if self._timers.closing:
                    return False

        if occ.source == "quick" and self.quick_departure_enabled:
            self._quick_native_until = occ.departure_at
            self.quick_departure_enabled = False
            self._quick_target_at = None
            return True
        return False

    async def _departure_tick_cb(self, _now: datetime | None = None) -> None:
        """Tick al minuto dello schedulatore partenze (pre-clima + sync ricarica/partenza/batteria)."""
        if self._timers.closing or self._departure_busy or self._departure_lock.locked():
            return
        self._departure_busy = True
        try:
            async with self._departure_lock:
                if self._timers.closing:
                    return
                now = _now if _now is not None else dt_util.now()
                ui_dirty = False
                quick_expired = False

                if (
                    self.quick_departure_enabled
                    and self._quick_target_at is not None
                    and now >= self._quick_target_at
                ):
                    self.quick_departure_enabled = False
                    self._quick_target_at = None
                    self._quick_native_until = None
                    ui_dirty = True
                    quick_expired = True

                if self._quick_native_until is not None and now >= self._quick_native_until:
                    self._quick_native_until = None
                    self._quick_target_at = None
                    quick_expired = True

                if (
                    self._quick_applied_native
                    and not self.quick_departure_enabled
                    and self._quick_native_until is None
                ):
                    quick_expired = True

                occ = self.next_departure_occurrence(now)

                if occ is not None and self.departure_climate_mode != "off":
                    if occ.climate_start_at <= now < occ.departure_at:
                        if (
                            occ.key != self._fired_climate_key
                            and occ.key != self._attempted_climate_key
                        ):
                            if await self._maybe_trigger_preclimate(occ):
                                ui_dirty = True
                            if self._timers.closing:
                                return

                if ui_dirty:
                    self.async_update_listeners()
                    ui_dirty = False

                holding_quick = (
                    self._quick_native_until is not None and now < self._quick_native_until
                )

                if occ is not None and self.sync_charge_to_departure:
                    if self._sync_charge_start_local(occ):
                        self.async_update_listeners()
                    if self._charge_sync_window_active(now, occ):
                        await self._async_sync_charge_for_occurrence(occ)
                        if self._timers.closing:
                            return

                if not holding_quick:
                    weekly_dirty = self._is_weekly_dirty()
                    if (not weekly_dirty or (quick_expired and occ is None)) and (
                        self.native_departure_sync or (quick_expired and self._quick_applied_native)
                    ):
                        if quick_expired:
                            self._last_attempted_native_dep_sig = None
                        _, _, sig = self._build_native_departure_payload(occ)
                        sent_ok = await self._async_sync_native_departure(occ)
                        if self._timers.closing:
                            return
                        if quick_expired and (sent_ok or sig == self._last_synced_native_dep_sig):
                            self._quick_applied_native = False
                            if occ is not None:
                                self._applied_schedule_sig = self.departure_schedule_signature()
                            else:
                                self._applied_schedule_sig = None
                                self.native_departure_sync = False
                            self.async_update_listeners()
                        elif sent_ok and not weekly_dirty:
                            if occ is not None:
                                self._applied_schedule_sig = self.departure_schedule_signature()
                            elif self._applied_schedule_sig is not None:
                                self._applied_schedule_sig = None
                            self.async_update_listeners()
                    elif quick_expired and weekly_dirty and occ is not None:
                        self._quick_applied_native = False

                    if self.sync_battery_heat_to_departure:
                        if self._sync_battery_heat_start_local(occ):
                            self.async_update_listeners()
                        if quick_expired:
                            self._last_attempted_battery_sig = None
                        await self._async_sync_battery_for_occurrence(occ, force_off=quick_expired)
                        if self._timers.closing:
                            return
        finally:
            self._departure_busy = False

    def async_start_drive_watch(self) -> None:
        """Avvia il battito di rilevamento marcia (sola lettura). È legato a `poll_enabled`
        (interruttore "Aggiornamento automatico"): ogni `DRIVE_WATCH_EVERY` controlla se l'HV è
        acceso e, in caso, fa partire il follow-up ravvicinato. Idempotente."""
        if self._timers.is_armed(DRIVE_WATCH) or not self.poll_enabled:
            return
        self._timers.arm(DRIVE_WATCH, lambda: async_track_time_interval(
            self.hass, self._drive_watch_cb, timedelta(seconds=DRIVE_WATCH_EVERY)
        ))

    async def _drive_watch_cb(self, _now) -> None:
        """Una lettura realtime di SOLA LETTURA per accorgersi che l'auto è in marcia (l'auto in
        movimento non manda push MQTT). Se il follow-up ravvicinato è già in corso (marcia/ricarica)
        o un ciclo di poll è in corso, salta: non si sovrappone. Se trova l'HV acceso, `async_probe`
        arma da sé il loop a 60s che seguirà tutto il viaggio. NESSUN comando/sveglia all'auto."""
        if not self.poll_enabled or self._timers.is_armed(HV_POLL) or self._poll_busy:
            return
        self._poll_busy = True
        try:
            await self.async_probe(force=True)
        except Exception as err:  # noqa: BLE001 — un errore di rete non deve fermare il timer
            _LOGGER.debug("[drive-watch] lettura non riuscita: %s", err)
        finally:
            self._poll_busy = False

    def _is_plugged(self) -> bool:
        """True se la spina di ricarica è collegata (chargeGunState != 0). Legge il
        valore più fresco: realtime se presente, altrimenti l'ultimo 5A02 via MQTT."""
        from .entity import field_on
        rt = self.data.get("realtime") or {}
        v = rt.get("chargeGunState")
        if v is None:
            with self._state_lock:
                v = self._fields.get("chargeGunState")
        return bool(field_on(v))

    def _schedule_next_poll(self) -> None:
        """Rischedula il prossimo poll in base allo stato spina attuale. Se lo stato
        corrente ha intervallo 0 (modalità disattivata) NON sveglia, ma ricontrolla più
        tardi (per accorgersi quando cambia l'attacco alla colonnina)."""
        mins = self.poll_charging_min if self._is_plugged() else self.poll_normal_min
        if not mins or mins <= 0:
            # stato attuale off → recheck con l'altro intervallo (o 60 min) senza svegliare
            mins = self.poll_charging_min or self.poll_normal_min or 60
        self._timers.arm(POLL, lambda: async_call_later(
            self.hass, mins * 60, self._telemetry_poll_cb))

    async def _telemetry_poll_cb(self, _now) -> None:
        self._timers.cancel(POLL)
        try:
            mins = self.poll_charging_min if self._is_plugged() else self.poll_normal_min
            if mins and mins > 0 and not self._poll_busy:
                self._poll_busy = True
                try:
                    await self._do_poll_cycle()
                finally:
                    self._poll_busy = False
        except Exception as err:  # noqa: BLE001 — un errore non deve fermare il timer
            _LOGGER.debug("[poll] errore non bloccante: %s", err)
        finally:
            # rischedula SOLO se il poll è ancora attivo: se set_poll_enabled(False) è
            # arrivato durante il ciclo (await), trovava _poll_unsub=None e non poteva
            # cancellare nulla → senza questa guardia riarmeremmo un timer "zombie".
            if self.poll_enabled:
                self._schedule_next_poll()

    async def _do_poll_cycle(self) -> None:
        """Un ciclo di poll. [2.0] SVEGLIA CONDIZIONALE: prima una lettura realtime di SOLA
        LETTURA; se l'auto risulta ONLINE (il cloud ha un frame, A07900 assente) i sensori sono
        già aggiornati e NON si sveglia — l'auto resta raggiungibile per ore, e a riposo la
        sveglia aggiornerebbe solo il GPS, non batteria/odometro (servirebbe l'alta tensione).
        Si sveglia (vehicleLocation/1301) SOLO se la sonda la trova offline, per ri-portarla
        online. Risparmia 12V e riduce la contesa con l'app ufficiale."""
        plugged = self._is_plugged()
        _LOGGER.debug("[poll] ciclo: prima lettura realtime read-only (plugged=%s)", plugged)
        try:
            await self.async_probe(force=True)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("[poll] lettura realtime fallita: %s", err)
        if self._online:
            _LOGGER.debug("[poll] auto online: dati già freschi, niente sveglia")
            return
        # auto offline (A07900) → una sveglia + rilettura per riportarla online
        _LOGGER.debug("[poll] auto offline: sveglio (localizza) e rileggo")
        # sveglia CONDIVISA: se la macro comfort ne ha già una in volo si aspetta quella,
        # invece di spedirne una seconda che si prenderebbe un A00082 (vedi il metodo).
        await self.async_assicura_sveglia()
        await asyncio.sleep(POLL_WAKE_WAIT)
        try:
            await self.async_probe(force=True)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("[poll] lettura realtime fallita: %s", err)

    def _connect_car(self) -> None:
        # import qui (executor): a livello modulo causa un blocking-call warning nel loop.
        import paho.mqtt.client as mqtt

        seed = os.environ.get("CAR_SEED", CAR_SEED)
        car_user = self.tuserid
        car_pass = hashlib.md5((self.tuserid + seed).encode()).hexdigest()
        client_id = f"app_{self.channel_id}_{self.tuserid}"   # esatto: ACL del broker
        topic = f"app/{self.channel_id}/{self.tuserid}/account/msgCenter/msg"

        c = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                        client_id=client_id, protocol=mqtt.MQTTv311, clean_session=False)
        c.username_pw_set(car_user, car_pass)
        c.tls_set(ca_certs=os.path.join(self.certs_dir, "ca.pem"),
                  certfile=os.path.join(self.certs_dir, "client.pem"),
                  keyfile=os.path.join(self.certs_dir, "client.key"),
                  cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
        c.tls_insecure_set(True)  # il broker usa un CN non combaciante (come nel bridge)

        def on_connect(cl, u, flags, rc, props=None):
            ok = (rc == 0) or (getattr(rc, "value", 1) == 0)
            self._update({"car_connected": ok})
            _LOGGER.info("[auto] MQTT on_connect rc=%s → %s (sub %s)",
                         rc, "connesso" if ok else "RIFIUTATO",
                         f"app/{self.channel_id}/***/account/msgCenter/msg" if ok else "-")
            if ok:
                cl.subscribe(topic, qos=1)
            if self._diag is not None:
                self._mqtt_up_ts = time.time()
                self._diag.record("mqtt_conn", event="connect", rc=str(rc), ok=ok)

        def on_disconnect(cl, u, *a):
            self._update({"car_connected": False})
            _LOGGER.info("[auto] MQTT disconnesso")
            if self._diag is not None:
                # uptime della sessione appena caduta: sessioni cortissime = flapping.
                up = round(time.time() - self._mqtt_up_ts, 1) if self._mqtt_up_ts else None
                self._mqtt_up_ts = 0.0
                rc = str(a[1]) if len(a) > 1 else (str(a[0]) if a else "?")
                self._diag.record("mqtt_conn", event="disconnect", rc=rc, uptime_s=up)

        c.on_connect = on_connect
        c.on_disconnect = on_disconnect
        c.on_message = self._on_car_message
        # [H4] backoff di riconnessione (evita lo storming a 1s di default su rete giù)
        c.reconnect_delay_set(min_delay=1, max_delay=120)
        # [H4] il connect iniziale può fallire (DNS/cert/rete) → ConfigEntryNotReady,
        #      così HA riprova il setup invece di lasciare il client appeso.
        try:
            c.connect(self.car_host, self.car_port, keepalive=60)
        except Exception as err:  # noqa: BLE001
            raise ConfigEntryNotReady(
                f"connessione MQTT auto fallita ({self.car_host}:{self.car_port}): {err}"
            ) from err
        c.loop_start()
        self._car = c

    def async_stop(self) -> None:
        """[MED] Spegnimento MQTT. Bloccante (loop_stop fa join del thread paho) →
        chiamato in executor da async_unload_entry. `disconnect()` PRIMA di
        `loop_stop()`: così il loop processa il CONNACK/DISCONNECT e il thread esce
        pulito senza un join che attende il keepalive."""
        # P0-4/P2-4: teardown UNICO. `close()` cancella tutti i timer e vieta ogni futuro
        # `arm()`: una lettura già in volo che al ritorno provasse a ri-armare il follow-up
        # non ci riesce più. Prima ogni timer si cancellava a mano qui, e bastava
        # dimenticarne uno (o ri-armarlo altrove) per lasciare un poll orfano sul cloud.
        self._timers.close()
        try:
            self.hass.loop.call_soon_threadsafe(self._mqtt_msg_event.set)
        except RuntimeError:
            pass
        if self._diag_stop_unsub is not None:
            self._diag_stop_unsub()
            self._diag_stop_unsub = None
        # NB: `disarm=False` — l'unload non consuma la finestra del monitor, che riprende
        # al reload con la scadenza originale (calcolata sull'mtime della bandierina).
        self._diag_shutdown()
        if self._car is not None:
            try:
                self._car.disconnect()
                self._car.loop_stop()
            except Exception as err:  # noqa: BLE001 — lo stop non deve far fallire l'unload
                _LOGGER.debug("[auto] errore in async_stop: %s", err)
            self._car = None

    def _on_car_message(self, c, u, msg) -> None:
        """Parsing identico a ha_bridge.car_on_message (thread paho → push verso HA)."""
        try:
            obj = json.loads(msg.payload.decode("utf-8"))
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("[auto] payload MQTT non decodificabile: %s", err)
            return
        content = obj.get("content", obj)
        data = content.get("data", {}) if isinstance(content, dict) else {}
        if not isinstance(data, dict):
            data = {}
        svc = str(content.get("serviceType")) if isinstance(content, dict) else ""
        now = time.time()
        now_dt = dt_util.utcnow()
        _LOGGER.debug("[auto] messaggio ricevuto (svc %s): %d campi", svc or "?", len(data))

        patch = {"last_seen": now_dt}

        # [MED] serviceType 1301 = push POSIZIONE (lat/lon) → device_tracker. Si
        # discrimina sul TIPO messaggio (non sulla sola presenza di lat/lon) e si
        # tiene in position SOLO la geolocalizzazione (no **data).
        if svc == "1301" and "lat" in data and "lon" in data:
            geo = {k: data[k] for k in GEO_KEYS if k in data}
            with self._state_lock:
                self.position = geo
                pos_copy = dict(geo)
            patch["position"] = pos_copy
            patch["last_pos_fix"] = now_dt

        # [Item4] push di CONFERMA comando: l'auto risponde a ogni vehicleControl/X con un
        # messaggio 110x/1105/1135 che porta result/resultTime/seq (+ reason sui guasti)
        # OLTRE ai campi di stato reali. Lo riconosciamo dalla presenza di result/seq (la
        # telemetria 5A02 "pura" non li ha). I campi di stato vanno comunque in fields;
        # i meta-campi (CMD_CONFIRM_META) NO (non sono stato del veicolo).
        is_confirmation = "result" in data or "seq" in data

        # I campi di stato di QUESTO messaggio, tenuti a parte da `fields`. Non è un doppione:
        # `fields` è CUMULATIVO — accumula l'ultimo valore noto di ogni campo e se lo porta
        # dietro per giorni — mentre qui c'è solo ciò che l'auto ha appena detto. Chi deve
        # decidere «l'auto ha spento il preset» ha bisogno del secondo: sul primo mescolerebbe
        # un valore fresco con uno vecchio di ieri e concluderebbe qualcosa che nessuno ha
        # affermato. Serve alla macro comfort (`switch.py`), l'unica entità senza uno stato
        # reale proprio da confrontare.
        msg_fields: dict[str, str] = {}
        # [H2] _fields/_last_msg_ts toccati anche dall'executor → sotto lock; emetti una COPIA
        with self._state_lock:
            was_awake = bool(self._last_msg_ts) and (now - self._last_msg_ts) < self.awake_window
            self._last_msg_ts = now
            for k, v in data.items():
                if k != "time" and k not in CMD_CONFIRM_META:
                    self._fields[k] = str(v)
                    msg_fields[k] = str(v)
            fields_copy = dict(self._fields)

        # [diag] auto-discovery: chiavi 5A02 che l'auto manda ma che META non mappa. È il
        # canale per scoprire la telemetria ancora mancante (autonomia/TPMS). Fuori dal
        # lock e solo a monitor acceso: il percorso caldo resta un `is not None`.
        #
        # Solo il 5A02: `META` descrive la telemetria di STATO, quindi confrontare con
        # essa i campi di un push di POSIZIONE (1301) segnalava `lat`/`lon` come "campi
        # non mappati" — falsi positivi, perché sono già gestiti dal ramo posizione e
        # alimentano il device_tracker. Peggio: così una coordinata finiva registrata
        # come campione (fuga vista in campo il 2026-07-20). `GEO_KEYS` resta escluso
        # comunque, nel caso l'auto infilasse la posizione dentro un 5A02.
        if self._diag is not None and svc == "5A02":
            for k, v in data.items():
                if (k != "time" and k not in CMD_CONFIRM_META and k not in META
                        and k not in GEO_KEYS and not _is_unit_flag(k)):
                    self._diag.note_unknown_field(k, v, svc)

        patch.update({"fields": fields_copy, "msg_fields": msg_fields, "awake": True})
        if is_confirmation:
            patch["cmd_status"] = self._esito_con_note(self._format_cmd_result(data))
            # [H2] il contatore è l'ancora della pausa di coda → si tocca sotto lock, perché
            # lo legge il loop mentre qui siamo nel thread paho. Farlo avanzare SBLOCCA il
            # comando successivo: da qui in poi l'auto non è più occupata da questo.
            with self._state_lock:
                self._confirm_n += 1
            # [diag] il push di conferma GREZZO. Senza, del fallimento resta solo la frase
            # tradotta: i codici in `reason` (modulo + codice per ogni centralina che non ha
            # eseguito) non si possono decodificare a posteriori, ed è l'unica traccia che
            # dice PERCHÉ una macro comfort è riuscita a metà. Il payload passa da `redact()`
            # come tutto il resto — la posizione, se mai comparisse qui, viene rimossa.
            if self._diag is not None:
                self._diag.record("cmd_ack", svc=svc or "?", result=str(data.get("result", "")),
                                  reason=data.get("reason"), data=data)
        self._update(patch)

        # Lo stato «sveglia» ha una scadenza: senza, resterebbe acceso per sempre (vedi
        # `_auto_e_sveglia`). Si ri-arma a ogni messaggio, dal loop perché qui siamo nel
        # thread di paho.
        self.hass.loop.call_soon_threadsafe(self._arma_scadenza_sveglia)
        self.hass.loop.call_soon_threadsafe(self._mqtt_msg_event.set)

        # [H3] fronte di risveglio → una sonda realtime (sola lettura). Lo schedule del
        # task DEVE avvenire sul loop: dal thread paho usa call_soon_threadsafe.
        if not was_awake:
            self.hass.loop.call_soon_threadsafe(
                lambda: self.hass.async_create_task(self.async_probe())
            )

        # [HV] l'auto è IN MARCIA (motore acceso) → l'alta tensione è ON e il realtime ha i
        # valori VERI (odometro/SOC che salgono). Forziamo una lettura realtime (bypassa il
        # cooldown della sonda) che a sua volta avvia il follow-up ravvicinato finché l'HV resta
        # acceso. Solo se non c'è già un follow-up in corso, per non accavallare letture.
        driving = False
        try:
            driving = int(float(fields_copy.get("engineState", 0))) == 1
        except (TypeError, ValueError):
            driving = False
        # [Ricarica] spina collegata → carica in corso: avvia anche qui il follow-up ravvicinato,
        # così il refresh automatico parte appena si attacca la colonnina (senza attendere il poll
        # periodico dei 39 min) e segue l'avanzamento. `field_on` come in _is_plugged().
        from .entity import field_on
        plugged = field_on(fields_copy.get("chargeGunState"))
        # P0-5: rispetta lo switch "Aggiornamento automatico" (e lo stop) anche su questa
        # via d'ingresso, altrimenti un push MQTT ri-accendeva il follow-up a poll disattivato.
        if (driving or plugged) and not self._timers.is_armed(HV_POLL) and not is_confirmation \
                and self.poll_enabled and not self._timers.closing:
            self.hass.loop.call_soon_threadsafe(
                lambda: self.hass.async_create_task(self.async_probe(force=True))
            )

    @staticmethod
    def _solo_clima(reason) -> bool:
        """True se l'auto ha segnalato SOLTANTO il clima (`modelId` 0), nient'altro.

        Serve a non gridare al lupo. Il clima compare in `reason` anche quando tutto è
        andato bene: il codice 95 arriva su praticamente ogni comando di SPEGNIMENTO, e il
        2026-08-01 è arrivato pure su uno «spegni clima» eseguito correttamente. Trattarlo
        come guasto significava mostrare «Eseguito solo in parte ⚠️» a chi aveva appena
        spento il clima senza il minimo problema.

        Un `reason` deforme (il backend potrebbe cambiare forma) NON è «solo clima»: si
        torna al ramo prudente, che lo riporta grezzo invece di archiviarlo come innocuo."""
        if not isinstance(reason, (list, tuple)) or not reason:
            return False
        if not all(isinstance(v, dict) for v in reason):
            return False
        return all(str(v.get("modelId")) == "0" for v in reason)

    @staticmethod
    def _descrivi_reason(reason) -> str:
        """`reason` grezzo → elenco leggibile di moduli, con i codici in coda.

        Da `[{'code':'11','modelId':'0'},{'code':'1','modelId':'9'}, …]` ricava
        «clima, 4× sedile ventilato (codici 0:11, 9:1, …)». I moduli si contano invece di
        ripeterli, i codici restano perché sono l'unico appiglio per capire a posteriori
        *cosa* è andato storto. Se la struttura non è quella attesa si torna al grezzo:
        meglio illeggibile che inventato."""
        if not isinstance(reason, (list, tuple)) or not all(
                isinstance(v, dict) for v in reason):
            return str(reason)
        nomi: list[str] = []
        conteggio: dict[str, int] = {}
        codici: list[str] = []
        for voce in reason:
            mid = str(voce.get("modelId", "?"))
            nome = REASON_MODULI.get(mid, f"modulo {mid}")
            if nome not in conteggio:
                nomi.append(nome)
            conteggio[nome] = conteggio.get(nome, 0) + 1
            codici.append(f"{mid}:{voce.get('code', '?')}")
        elenco = ", ".join(f"{conteggio[n]}× {n}" if conteggio[n] > 1 else n for n in nomi)
        return f"{elenco} (codici {', '.join(codici)})"

    def _esito_con_note(self, esito: str) -> str:
        """L'esito della conferma dell'auto, con riattaccati gli avvisi del nostro comando.

        Senza questo, riattaccarli all'esito dell'INVIO non servirebbe a nulla: la conferma
        arriva pochi secondi dopo e riscrive lo stato da capo, portandosi via gli avvisi
        insieme al resto. Il difetto tornerebbe identico, solo con qualche secondo di vita in
        più invece di 12 millisecondi.

        ⚠️ Solo se la conferma può ESSERE la risposta al nostro comando (`NOTE_COMANDO_S`).
        Il canale dei push è condiviso con l'app ufficiale: senza la finestra, un comando dato
        dal telefono mezz'ora dopo si vedrebbe attaccare i nostri avvisi, che parlano di
        tutt'altro. Correlare davvero conferma e comando richiederebbe il `seq`, che spediamo
        ma di cui non è mai stato misurato se l'auto lo rimandi indietro uguale — quindi qui si
        usa il tempo, che è un'approssimazione ma dichiarata."""
        if not self._note_cmd or self._note_cmd_at is None:
            return esito
        if (time.monotonic() - self._note_cmd_at) > NOTE_COMANDO_S:
            return esito
        return unisci_esito_e_note(esito, self._note_cmd)

    @staticmethod
    def _format_cmd_result(data: dict) -> str:
        """Traduce l'esito REALE di un push di conferma comando in una frase per l'utente.

        Distinto dall'"accettato" del backend (A00079, mostrato all'invio): qui è ciò che
        l'AUTO riporta dopo aver provato a eseguire. Interpretazione CONSERVATIVA, basata
        sui dati reali (events.jsonl 2026-06-21) e sul significato del bean:
          - `reason` (lista) è popolato SOLO sui guasti → se presente, qualcosa NON è andato;
          - `result`: 5 = operazione asincrona ancora in corso (sempre con hasAsy=1);
            1/2 = eseguito/applicato (stato del veicolo aggiornato);
          - codici diversi → riportati grezzi, senza inventarne il significato.

        Sul `reason` la frase è cambiata (2026-07-31) dopo aver verificato in campo che cosa
        succede davvero all'auto quando arriva: NON è un fallimento totale. Nei 22 cicli
        osservati della macro comfort il clima partiva comunque e a non partire erano i
        sedili ventilati. «L'auto ha segnalato un problema ❌» seguito dal dump Python della
        lista era quindi doppiamente inutile: allarmava più del dovuto e non diceva su cosa.
        Ora si nominano i moduli segnalati e si dice che l'esecuzione è PARZIALE.

        Seconda correzione (2026-08-01): se l'UNICO modulo segnalato è il clima non si parla
        più di problema. Vedi `_solo_clima` — quel caso arriva su comandi perfettamente
        riusciti, e l'avviso era un falso allarme sistematico."""
        result = str(data.get("result", "")).strip()
        reason = data.get("reason")
        if reason and LepasCoordinator._solo_clima(reason):
            return ("Comando ricevuto dall'auto — unica segnalazione: "
                    f"{LepasCoordinator._descrivi_reason(reason)}. "
                    "Da sola non indica un guasto.")[:255]
        if reason:  # l'auto segnala uno o più moduli che non hanno eseguito
            return ("Eseguito solo in parte ⚠️ — l'auto segnala un problema su: "
                    f"{LepasCoordinator._descrivi_reason(reason)}")[:255]
        if result == "5":
            return "Comando in esecuzione sull'auto… ⏳"
        if result in ("1", "2"):
            return "Comando eseguito e confermato dall'auto ✅"
        return f"Conferma ricevuta dall'auto (codice esito {result or '?'})"[:255]

    def _update(self, patch: dict) -> None:
        """Aggiorna self.data e notifica le entità (thread-safe dal thread paho)."""
        self.hass.loop.call_soon_threadsafe(self._apply_update, patch)

    def _apply_update(self, patch: dict) -> None:
        self.data = {**self.data, **patch}
        self.async_set_updated_data(self.data)

    # ───────────────── contesto per i moduli core/ (P2-6) ─────────────────
    def _build_ctx(self):
        """Costruisce il `CoreCtx` di QUESTO veicolo dal config entry.

        Sostituisce il vecchio `_bind_core`, che prima di ogni chiamata riscriveva i
        global dei moduli `core/` e mezza dozzina di variabili in `os.environ`. Quel
        meccanismo aveva tre difetti concreti:

        * con DUE veicoli configurati, il secondo entry sovrascriveva la configurazione
          del primo → un comando poteva partire verso l'auto sbagliata;
        * fra il bind e l'uso effettivo girava codice in thread executor: un reload
          dell'entry nel mezzo lasciava metà moduli configurati col vecchio account;
        * PIN ed email finivano in `os.environ`, leggibile da qualunque cosa giri dentro
          Home Assistant.

        Ora la configurazione è un oggetto passato per argomento: ogni entry ha il suo,
        e non esiste stato condiviso da sincronizzare.
        """
        from .core.context import CoreCtx

        return CoreCtx(
            vin=self.vin,
            tuserid=self.tuserid,
            pin=self.pin,
            email=self.email,
            phone=self.phone,
            area_code=self.area_code,
            language=self.language,
            token_path=self.token_path,
            # taskId nella config dir per-VIN: sopravvive agli update HACS e non è
            # condiviso fra veicoli.
            taskid_file=self.hass.config.path(f"{DOMAIN}_{self.vin}_taskid.txt"),
            src_dir=os.path.join(os.path.dirname(__file__), "core"),
            tsp_host=self.tsp_host,
            bff=self.bff,
            channel_id=self.channel_id,
            tenant_code=self.tenant_code,
            country_id=self.country_id,
            mint_taskid=os.environ.get("LEPAS_MINT_TASKID", "1") not in ("0", "", "false", "no"),
            # Capability della vettura con nomi NEUTRI: `core/` è autonomo e non importa nulla
            # dal package padre, quindi non può conoscere le chiavi `DATA_*` di const.py.
            caps=self._caps_correnti(),
        )

    @property
    def ctx(self):
        """Il contesto del veicolo, creato una volta sola.

        Lo STATO per-veicolo (anti-lockout del PIN, taskId in cache, cooldown di sveglia
        e sonda) vive qui dentro: dev'essere lo stesso oggetto per tutta la vita
        dell'entry, altrimenti il contatore anti-lockout si azzererebbe a ogni comando e
        la protezione contro il blocco dell'account non scatterebbe mai."""
        if self._ctx is None:
            self._ctx = self._build_ctx()
        # il monitor diagnostico si accende/spegne a runtime → si riallinea a ogni uso
        # (è un semplice riferimento a funzione, costo nullo)
        self._ctx.diag_hook = self._diag.record if self._diag is not None else None
        return self._ctx

    # NB: non esiste un `_apply_pin_change`. Riconfigurare il PIN RICARICA l'entry, quindi
    # nasce un coordinator nuovo con un contesto nuovo — il PIN aggiornato ci arriva da sé.
    # Resta necessario l'azzeramento ESPLICITO dell'anti-lockout (`ctx.reset_pin_lockout()`
    # in `repairs.py`/`config_flow.py`), perché quello vive in memoria e sopravviverebbe.

    # ───────────────── coda comandi (l'auto ne esegue uno alla volta) ─────────────────
    async def _settle_after_command(self) -> None:
        """Pausa dopo un comando, prima che parta il prossimo in coda: aspetta il push di
        CONFERMA dell'auto oppure COMMAND_SETTLE_S, quale che arrivi prima. Serve a non
        ricolpire l'auto mentre è ancora occupata (A00082).

        ⚠️ L'ancora è `_confirm_n`, NON `last_seen`. `last_seen` avanza a OGNI messaggio, e
        un'auto sveglia manda telemetria 5A02 ogni pochi secondi: la pausa usciva quindi al
        primo mezzo secondo — proprio nel caso in cui serviva, cioè con la vettura desta e un
        comando appena partito. Risultato misurato in campo (luglio 2026): la coda non
        proteggeva da due pressioni ravvicinate e il secondo comando tornava A00082 «auto
        occupata». Contando solo le conferme la pausa dura finché l'auto ha davvero
        risposto."""
        anchor = self._confirm_n
        deadline = time.monotonic() + COMMAND_SETTLE_S
        while time.monotonic() < deadline:
            await asyncio.sleep(0.5)
            if self._confirm_n != anchor:
                return   # l'auto ha confermato → si può passare al comando successivo

    async def _sveglia_una_volta(self) -> None:
        """Un `localizza` (vehicleLocation = sveglia + GPS, benigno) che non propaga errori.

        Non solleva di proposito: la sveglia è un mezzo, non il fine, e chi la chiede deve
        poter proseguire comunque — è quello che facevano già, ciascuno per conto suo, sia la
        macro comfort sia il ciclo di poll."""
        try:
            await self.async_send_command("localizza")
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("[sveglia] localizza non riuscito: %s", err)

    async def async_assicura_sveglia(self) -> None:
        """Sveglia l'auto UNA volta sola: chi arriva mentre un `localizza` è già in volo
        aspetta QUELLO invece di spedirne un altro.

        ⚠️ Non decide *se* svegliare: la condizione resta di chi chiama, e i due chiamanti
        guardano segnali diversi (la macro `auto_sveglia`, cioè il traffico MQTT recente; il
        poll `_online`, cioè la risposta del realtime). Qui si toglie solo il doppione.

        Serviva: nel diario diagnostico ci sono **13 coppie di `localizza` a meno di 60
        secondi l'una dall'altra, 6 delle quali finite in A00082** («veicolo occupato») — la
        macro e il poll che si svegliavano l'auto a vicenda, ciascuno occupando uno slot
        della coda e la pausa che lo segue. Il secondo `localizza` non aggiunge nulla:
        l'auto o si è svegliata col primo, o non si sveglia.

        `shield` perché la sveglia è condivisa: se il task che l'ha chiesta per primo viene
        annullato (una chiamata di servizio interrotta), gli altri in attesa non devono
        perderla con lui."""
        task = self._sveglia_task
        if task is None or task.done():
            # Task di BACKGROUND: uno normale verrebbe atteso allo spegnimento di Home
            # Assistant, e una sveglia può restare in coda fino a COMMAND_QUEUE_WAIT più la
            # chiamata HTTP — decine di secondi di arresto in più per qualcosa che a quel
            # punto non serve più a nessuno.
            task = self._sveglia_task = self.hass.async_create_background_task(
                self._sveglia_una_volta(), f"{DOMAIN}_sveglia")
        try:
            await asyncio.shield(task)
        finally:
            if self._sveglia_task is task and task.done():
                self._sveglia_task = None   # non trattenere un task concluso

    async def _wait_for_car_wake(
        self, baseline_ts: float, timeout: float = POLL_WAKE_WAIT
    ) -> bool:
        """Attende fino a `timeout` s che arrivi un push MQTT successivo a `baseline_ts`."""
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            if self._timers.closing:
                return False
            with self._state_lock:
                if self._last_msg_ts > baseline_ts:
                    return True
            self._mqtt_msg_event.clear()
            with self._state_lock:
                if self._last_msg_ts > baseline_ts:
                    return True
            if self._timers.closing:
                return False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            try:
                await asyncio.wait_for(self._mqtt_msg_event.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                with self._state_lock:
                    return (not self._timers.closing) and (self._last_msg_ts > baseline_ts)

    def _should_wake_retry_on_a07900(
        self, key: str, err: Exception, allow_wake_retry: bool
    ) -> bool:
        """True sse `err` è un A07900 idoneo a una singola sveglia + retry protetto."""
        if not allow_wake_retry or key == "localizza" or self._timers.closing:
            return False
        if getattr(err, "code", None) != "A07900":
            return False
        if self.auto_sveglia:
            return False
        return (
            self._last_a07900_wake_ts == 0.0
            or (time.monotonic() - self._last_a07900_wake_ts) >= A07900_WAKE_COOLDOWN_S
        )

    # ───────────────── azioni (delega a core/, in executor) ─────────────────
    async def async_send_command(
        self,
        key: str,
        params: dict | None = None,
        *,
        _allow_wake_retry: bool = True,
    ) -> str:
        """Invia un comando serializzato dietro una coda: l'auto ne esegue uno alla volta, quindi
        un secondo comando ASPETTA il suo turno invece di fallire. Limite d'attesa COMMAND_QUEUE_WAIT.

        Il chiamante torna appena il comando è stato inviato (la UI resta reattiva); lo slot della
        coda resta occupato ancora un po' in background — fino alla conferma dell'auto o a
        COMMAND_SETTLE_S — così il PROSSIMO della coda non parte mentre l'auto è ancora occupata."""
        try:
            await asyncio.wait_for(self._cmd_gate.acquire(), timeout=COMMAND_QUEUE_WAIT)
        except asyncio.TimeoutError as err:
            raise HomeAssistantError(
                "L'auto è ancora impegnata coi comandi precedenti — riprova tra qualche istante."
            ) from err
        t0 = time.monotonic()

        def _abort_command(err: Exception) -> None:
            if self._diag is not None:
                self._diag.record("command", key=key, ok=False,
                                  duration_ms=int((time.monotonic() - t0) * 1000),
                                  reason=getattr(err, "reason", None),
                                  code=getattr(err, "code", None),
                                  err_type=type(err).__name__, msg=str(err))
            # P2-5: instradamento per CAUSA tramite la tabella unica. Entrambi i percorsi
            # (questo e il fallback di `_wake`) chiamano lo STESSO helper: prima erano due
            # catene di `if` scritte a mano, e quella del fallback classificava come «PIN
            # errato» rifiuti che erano di permessi o di sessione.
            self._instrada_rimedio(err)

        # ⚠️ Il rilascio dello slot NON può stare solo nei rami che si vedono. Prima era
        # scritto in due punti — il ramo `except Exception` qui sotto e il task di rilascio
        # differito, creato solo in caso di successo — e in mezzo restava un buco: la
        # cancellazione del task chiamante. `asyncio.CancelledError` deriva da
        # `BaseException`, quindi NON passa da `except Exception`: attraversava la funzione
        # senza rilasciare niente e senza creare il task che rilascia. Da lì in poi la coda
        # restava chiusa PER SEMPRE (nessun watchdog, nessuna auto-guarigione) e ogni comando
        # successivo — compresi quelli del poll automatico — falliva dopo 30 secondi con
        # «L'auto è ancora impegnata», fino al riavvio di Home Assistant. Basta un'automazione
        # in `mode: restart` che si ri-attivi mentre l'invio è in volo.
        # Con la bandiera + `finally` il rilascio è UNO solo ed è per costruzione impossibile
        # farlo due volte (`asyncio.Lock.release()` su un lock non preso solleva RuntimeError).
        # ⚠️ Rilasciare non ferma il thread dell'executor: il comando parte comunque verso
        # l'auto, mentre Home Assistant lo considera annullato.
        consegnato = False
        wake_err: Exception | None = None
        pre_cmd_status = self.data.get("cmd_status")
        err_cmd_status: str | None = None
        err_note_cmd: list[str] = []
        err_note_cmd_at: float | None = None
        try:
            res = await self.hass.async_add_executor_job(self._send_command, key, params)
            consegnato = True
        except Exception as err:  # noqa: BLE001 — instrada il rimedio, poi RILANCIA
            if self._should_wake_retry_on_a07900(key, err, _allow_wake_retry):
                wake_err = err
                cur_status = self.data.get("cmd_status")
                err_cmd_status = (
                    cur_status if (cur_status and cur_status != pre_cmd_status)
                    else str(err)[:STATO_MAX]
                )
                err_note_cmd = list(self._note_cmd)
                err_note_cmd_at = self._note_cmd_at
            else:
                _abort_command(err)
                raise
        finally:
            # invio non andato a buon fine (errore, cancellazione, arresto): libera lo slot.
            # In caso di successo NON si rilascia qui: lo slot resta occupato ancora un po',
            # ed è `_hold_then_release` a restituirlo dopo la pausa di rispetto.
            if not consegnato:
                self._cmd_gate.release()

        if wake_err is not None:
            self._last_a07900_wake_ts = time.monotonic()
            with self._state_lock:
                baseline_ts = self._last_msg_ts
            await self.async_assicura_sveglia()
            woke = (
                not self._timers.closing
                and await self._wait_for_car_wake(baseline_ts, timeout=POLL_WAKE_WAIT)
            )
            if woke:
                return await self.async_send_command(
                    key, params, _allow_wake_retry=False
                )
            self._note_cmd = err_note_cmd
            self._note_cmd_at = err_note_cmd_at
            self._apply_update({"cmd_status": err_cmd_status})
            _abort_command(wake_err)
            raise wake_err

        if self._diag is not None:
            self._diag.record("command", key=key, ok=True,
                              duration_ms=int((time.monotonic() - t0) * 1000), result=res)
        # comando riuscito → un eventuale avviso "PIN errato" non ha più ragione d'essere
        self._clear_pin_issue()

        async def _hold_then_release() -> None:
            try:
                await self._settle_after_command()
            finally:
                self._cmd_gate.release()

        self.hass.async_create_background_task(_hold_then_release(), f"{DOMAIN}_cmd_settle")
        return res

    def _send_command(self, key: str, params: dict | None = None) -> str:
        from .core import commands as CMD
        msgs: list[str] = []
        note: list[str] = []

        def emit(m):
            msgs.append(str(m))
            _LOGGER.info("[cmd] %s", m)
            self._update({"cmd_status": str(m)[:STATO_MAX]})

        def avvisa(m):
            """Avviso che l'utente deve poter LEGGERE, non solo un passaggio.

            Passa comunque da `emit` — il registro e lo stato istantaneo restano come prima —
            ma viene anche conservato, perché pubblicarlo e basta non lo faceva arrivare a
            nessuno: il passaggio successivo lo copriva in millisecondi."""
            note.append(str(m))
            emit(m)

        # Gli avvisi appartengono a QUESTO comando: si azzerano all'inizio, non alla fine.
        # Azzerarli dopo lascerebbe scoperta la finestra in cui il comando è in volo, e una
        # conferma in arrivo si porterebbe dietro gli avvisi del comando precedente.
        self._note_cmd, self._note_cmd_at = [], time.monotonic()
        try:
            CMD.send(self.ctx, key, emit=emit, params=params, avvisa=avvisa)
        finally:
            # Anche su comando fallito: gli avvisi spiegano PERCHÉ è fallito, ed è lì che
            # servono di più. `finally` per la stessa ragione del resto di questa release —
            # un'eccezione, compresa una cancellazione, non deve far sparire l'informazione.
            self._note_cmd = list(note)
            # ⚠️ La ricomposizione sta QUI dentro, e non dopo il `try`, per un difetto che è
            # sopravvissuto alla release che diceva di averlo chiuso. Un comando rifiutato
            # (`A00084` e ogni altro codice di fallimento) fa sollevare `commands.send()`:
            # con queste righe fuori dal `finally` non venivano mai eseguite, e sullo stato
            # restava l'esito nudo dell'ultimo `emit`. Cioè gli avvisi si vedevano solo
            # quando il comando riusciva — mentre il caso in cui l'utente ha davvero bisogno
            # di sapere *perché* è quello in cui il comando è stato rifiutato. Sul veicolo
            # dell'issue #1 sono i quattro comandi che gli interessano di più («raffredda
            # tutto», lunotto, sedili posteriori): finivano tutti nel registro e basta.
            # L'ultimo `emit` ha già pubblicato l'esito NUDO: qui lo si riscrive con gli
            # avvisi attaccati. Due aggiornamenti invece di uno, ma è l'unico modo per
            # comporre una riga che `core/` non può conoscere (non sa nulla di Home Assistant
            # né del limite dei 255 caratteri).
            esito = msgs[-1] if msgs else "inviato"
            # ⚠️ La ricomposizione sta DENTRO il `try`, e non una riga sopra. Un problema nel
            # comporre o nel MOSTRARE l'esito non deve mai sostituirsi all'errore vero: sul
            # percorso d'eccezione un `raise` da qui rimpiazzerebbe la `CommandError` e con
            # essa il `reason` su cui il coordinator instrada il rimedio (PIN, riautenticazione,
            # permessi) — l'utente si vedrebbe chiedere il PIN per un errore di formattazione.
            # Tenere fuori `unisci_esito_e_note` era esattamente il difetto che questo lavoro
            # dice di chiudere, lasciato indietro di una riga: è la funzione che qui si riscrive,
            # cioè la più esposta delle due. `finale` parte dall'esito nudo, così esiste comunque
            # un valore da restituire. Meglio uno stato non aggiornato che un rimedio sbagliato.
            finale = esito
            try:
                finale = unisci_esito_e_note(esito, note)
                if finale != esito:
                    self._update({"cmd_status": finale})
            except Exception as err:  # noqa: BLE001
                finale = esito
                _LOGGER.debug("[cmd] esito con avvisi non pubblicato: %s", err)
        return finale

    def _instrada_rimedio(self, err: Exception, dal_loop: bool = True) -> str:
        """Errore di comando → azione di rimedio, decisa dalla tabella unica (P2-5).

        Punto SOLO di instradamento: lo condividono il comando dalla UI e il fallback
        della sveglia. `dal_loop=False` quando si è in un thread executor, dove le
        chiamate a Home Assistant vanno schedulate sul loop.

        Il PIN errato NON tocca `session_ok`: la sessione è valida e i sensori
        funzionano: il problema è solo il PIN a 4 cifre dei comandi remoti, e proporre
        la riautenticazione sarebbe il rimedio sbagliato (il login non cambia il PIN).
        """
        from .core import routing

        azione = routing.azione_per_reason(getattr(err, "reason", None))
        if azione == routing.AZIONE_REAUTH:
            if dal_loop:
                self.entry.async_start_reauth(self.hass)
            else:
                self.hass.add_job(self.entry.async_start_reauth, self.hass)
        elif azione == routing.AZIONE_REPAIR_PIN:
            if dal_loop:
                self._raise_pin_issue(str(err))
            else:
                self.hass.add_job(self._raise_pin_issue, str(err))
        # AZIONE_AVVISO: nessun rimedio automatico. Il dettaglio è già stato pubblicato
        # su «Esito comando» dall'`emit`, quindi l'utente lo vede comunque.
        return azione

    # ───────────────── Repair "PIN comandi errato" (riconfig senza smontare) ─────────────────
    @property
    def _pin_issue_id(self) -> str:
        return f"pin_wrong_{self.entry.entry_id}"

    @callback
    def _raise_pin_issue(self, detail: str) -> None:
        """Crea un avviso di riparazione HA (fixabile) per il PIN comandi errato.

        NON tocca `session_ok`: la sessione è valida (i sensori funzionano), il problema è
        solo il PIN a 4 cifre dei comandi remoti. L'avviso apre la riconfig del PIN."""
        from homeassistant.helpers import issue_registry as ir
        ir.async_create_issue(
            self.hass, DOMAIN, self._pin_issue_id,
            is_fixable=True,
            severity=ir.IssueSeverity.ERROR,
            translation_key="pin_wrong",
            data={"entry_id": self.entry.entry_id},
        )

    @callback
    def _clear_pin_issue(self) -> None:
        """Chiude l'avviso "PIN errato" (un comando è andato a buon fine → PIN ora corretto)."""
        from homeassistant.helpers import issue_registry as ir
        ir.async_delete_issue(self.hass, DOMAIN, self._pin_issue_id)

    async def async_query_theft(self) -> int | None:
        """Stato antifurto via REST (read-only); None se non disponibile."""
        return await self.hass.async_add_executor_job(self._query_theft)

    def _query_theft(self) -> int | None:
        from .core import commands as CMD
        return CMD.query_theft_switch(self.ctx)

    async def async_wake(self) -> None:
        await self.hass.async_add_executor_job(self._wake)

    def _wake(self) -> None:
        from .core import wake as WAKE

        def emit(m):
            _LOGGER.info("[wake] %s", m)
            self._update({"wake_status": str(m)[:255]})

        self._update({"last_wake": dt_util.utcnow()})
        # is_awake: se l'auto sta già pubblicando su MQTT non serve l'SMS.
        result = WAKE.do_wake(self.ctx, emit,
                              is_awake=self._auto_e_sveglia, send_sms=True)
        # [FALLBACK] smsAwaken inaffidabile (test 2026-06-21: A07900 due volte) → se non ha
        # svegliato l'auto, ripiega su un comando REALE (vehicleLocation), che la sveglia al
        # primo colpo e restituisce anche il GPS. A livello coordinator per non creare import
        # circolari (wake.py è importato da commands.py).
        if not (isinstance(result, dict) and result.get("online")):
            if self._auto_e_sveglia():
                return  # nel frattempo è arrivato un messaggio MQTT → già sveglia
            emit("Sveglia SMS non efficace → ripiego su Localizza (vehicleLocation)…")
            try:
                self._send_command("localizza")
            except Exception as err:  # noqa: BLE001 — il fallback non deve far fallire la sveglia
                emit(f"fallback Localizza fallito: {err}")
                # P0-3/P2-5: `_send_command` qui è chiamato "a mano" (fuori da
                # async_send_command), quindi il routing del rimedio non scattava: un PIN
                # errato bruciava un tentativo di anti-lockout in SILENZIO, senza Repair né
                # reauth. Ora passa dallo STESSO helper della UI — non da una seconda catena
                # di `if` da tenere allineata. `dal_loop=False`: siamo in executor.
                self._instrada_rimedio(err, dal_loop=False)

    def _is_hv_on(self) -> bool:
        """True se l'alta tensione è accesa (marcia, ricarica o clima): è l'UNICO stato in cui
        /asr/manager/realtime riporta odometro/SOC/tensione REALI. Ad HV spento sono valori
        stantii/segnaposto (odometro vecchio, dumpEnergy=0, totalVoltage=0, totalCurrent=-1000).
        Legge il realtime più fresco (sonda) con ripiego sull'ultimo 5A02 via MQTT."""
        rt = self.data.get("realtime") or {}
        with self._state_lock:
            fields = dict(self._fields)
        for k in ("hVoltageState", "engineState"):
            v = rt.get(k)
            if v is None:
                v = fields.get(k)
            try:
                if int(float(v)) == 1:
                    return True
            except (TypeError, ValueError):
                pass
        # [2.0] rete di sicurezza: in marcia capita engineState=0 ma velocità>0 (verificato
        # dal vivo 2026-06-25: 38 km/h con engineState=0, hVoltageState=1) → l'auto è "sveglia"
        # sulla rete HV, quindi il realtime è reale e va seguito.
        sp = rt.get("vehicleSpeed")
        if sp is None:
            sp = fields.get("vehicleSpeed")
        try:
            if sp is not None and float(sp) > 0:
                return True
        except (TypeError, ValueError):
            pass
        return False

    @callback
    def _arm_hv_followup(self) -> None:
        """Dopo ogni lettura realtime: se c'è freschezza da seguire pianifica un'altra lettura
        ravvicinata, altrimenti (o raggiunto il cap) ferma il loop. Niente comandi all'auto: si
        limita a leggere. Due casi che tengono vivo il loop:
          - **HV acceso** (marcia/clima): segue odometro/SOC che salgono, intervallo 60s, cap ~90 min;
          - **spina collegata** (ricarica): segue l'avanzamento della carica per ORE, intervallo più
            rilassato (`CHARGING_POLL_EVERY`) e cap molto più alto (`CHARGING_POLL_MAX`).
        Durante una ricarica l'HV è acceso, quindi il realtime ha batteria/corrente/tempo-residuo
        veri: è proprio questo che permette il refresh automatico mentre la spina è collegata."""
        # Il loop si auto-rischedula, quindi qui è l'UNICO punto in cui si può spezzare.
        # P2-4: a registro chiuso `arm()` rifiuta da sé, quindi questa guardia non è più
        # ciò che TIENE l'invariante — resta perché evita il giro a vuoto e, soprattutto,
        # perché alimenta il contatore `hv_followup_orphan` del monitor diagnostico.
        if self._timers.closing or not self.poll_enabled:
            # [diag] TIMER ORFANO: qualcuno ha provato a ri-armare il follow-up DOPO lo
            # stop o a poll disattivato. L'evento serve a sapere se la corsa accade
            # davvero in campo, ora che le difese la impediscono.
            if self._diag is not None:
                self._diag.record("hv_followup", orphan=True, closing=self._timers.closing,
                                  poll_enabled=self.poll_enabled,
                                  had_timer=self._timers.is_armed(HV_POLL),
                                  hv_count=self._hv_poll_count)
            self._timers.cancel(HV_POLL)
            self._hv_poll_count = 0
            return
        if self._diag is not None:
            self._diag.record("hv_followup", orphan=False, plugged=self._is_plugged(),
                              hv_count=self._hv_poll_count)
        self._timers.cancel(HV_POLL)
        plugged = self._is_plugged()
        # la spina ha priorità: cap/intervallo "da ricarica" (più lunghi) coprono anche l'HV acceso
        if plugged:
            every, cap = CHARGING_POLL_EVERY, CHARGING_POLL_MAX
        elif self._is_hv_on():
            every, cap = HV_ON_POLL_EVERY, HV_ON_POLL_MAX
        else:
            self._hv_poll_count = 0
            return
        if self._hv_poll_count < cap:
            self._hv_poll_count += 1
            self._timers.arm(HV_POLL, lambda: async_call_later(
                self.hass, every, self._hv_followup_cb))
        else:
            self._hv_poll_count = 0

    async def _hv_followup_cb(self, _now) -> None:
        self._timers.cancel(HV_POLL)
        await self.async_probe(force=True)

    async def async_probe(self, force: bool = False) -> None:
        await self.hass.async_add_executor_job(self._probe, force)
        # se la lettura ha trovato l'HV acceso, segui la finestra di freschezza (auto-loop).
        # P0-4: se nel frattempo è arrivato lo stop, NON ri-armare (questa probe era già in volo).
        if self._timers.closing:
            return
        self._arm_hv_followup()

    def _probe(self, force: bool = False) -> None:
        from .core import probe as PROBE

        def emit(m):
            _LOGGER.info("[probe] %s", m)
            self._update({"probe_status": str(m)[:255]})

        # force=True (poll periodico): ignora il cooldown della sonda.
        res = PROBE.probe_once(self.ctx, emit, force=force, on_data=self._on_probe_data)
        # [2.0] memorizza se l'auto è raggiungibile dal cloud (per la sveglia condizionale del
        # ciclo di poll). Solo se la sonda è andata a buon fine: su busy/eccezione tieni l'ultimo.
        if isinstance(res, dict) and res.get("ok") and "online" in res:
            self._online = bool(res.get("online"))

    def _on_probe_data(self, data: dict) -> None:
        """Dati realtime (GPS/batteria/velocità/online/META stato) dalla sonda.

        Gira nel thread executor: gli accessi a self.position e self._fields sono
        serializzati col lock e si emette sempre una COPIA (no condivisione per riferimento)."""
        if not isinstance(data, dict):
            self._update({"realtime": data})
            return
        rt_copy = dict(data)
        if "mainSwitcher" not in rt_copy and "appointmentTravelSetVOS" not in rt_copy:
            prev_rt = (self.data or {}).get("realtime")
            if isinstance(prev_rt, dict):
                if "mainSwitcher" in prev_rt:
                    rt_copy["mainSwitcher"] = prev_rt["mainSwitcher"]
                if "appointmentTravelSetVOS" in prev_rt:
                    rt_copy["appointmentTravelSetVOS"] = prev_rt["appointmentTravelSetVOS"]
        patch: dict = {"realtime": rt_copy}
        # Freschezza del dato batteria/odometro. NON si usa più `resultTime`: misurato il
        # 22/07 che resta indietro mentre i valori cambiano davvero — resultTime fermo alle
        # 08:37:37 con la batteria passata da 41% a 40% dopo le 08:59, e `time` a 09:01:59.
        # Il sensore annunciava «dati vecchi di 24 minuti» mentre erano aggiornati, cioè
        # esattamente il contrario del suo scopo. Si guarda invece il CONTENUTO: il
        # timestamp avanza quando la telemetria cambia rispetto alla lettura precedente. Ad
        # auto ferma resta indietro — ed è proprio quello che l'utente vuole sapere.
        impronta = _impronta_telemetria(data)
        if self._impronta_dati is None:
            # Primo frame dopo l'avvio: non c'è nulla con cui confrontare. Si parte dal
            # timestamp dichiarato dall'auto invece di spacciare per "adesso" un dato
            # che potrebbe essere vecchio di ore.
            for tk in ("resultTime", "collectTime", "time", "updateTime"):
                raw = data.get(tk)
                try:
                    if raw not in (None, "", 0, "0"):
                        patch["car_data_ts"] = dt_util.utc_from_timestamp(int(float(raw)) / 1000)
                        break
                except (TypeError, ValueError):
                    continue
        elif impronta != self._impronta_dati:
            patch["car_data_ts"] = dt_util.utcnow()
        self._impronta_dati = impronta

        has_geo = "lat" in data and "lon" in data
        geo = {k: data[k] for k in GEO_KEYS if k in data} if has_geo else None
        # _state_lock non è rientrante: calcola awake inline senza chiamare _auto_e_sveglia().
        with self._state_lock:
            awake = bool(self._last_msg_ts) and (time.time() - self._last_msg_ts) < self.awake_window
            for k, v in data.items():
                if (
                    v is not None
                    and k in META
                    and k not in CMD_CONFIRM_META
                    and k != "time"
                    and k not in GEO_KEYS
                    and (not awake or k not in self._fields)
                ):
                    self._fields[k] = str(v)
            fields_copy = dict(self._fields)
            if geo is not None:
                self.position = {**(self.position or {}), **geo}
                pos_copy = dict(self.position)
        patch["fields"] = fields_copy
        if geo is not None:
            patch["position"] = pos_copy
            patch["last_pos_fix"] = dt_util.utcnow()
        self._update(patch)

    async def async_refresh_full_status(self) -> None:
        """Pulsante «Aggiorna stato completo»: porta in HA odometro/batteria/tensione VERI.

        Il canale realtime dà i valori reali SOLO con l'alta tensione accesa; non esiste un
        comando "leggero" che forzi un report fresco (verificato dal reverse-engineering della
        SDK Chery). Quindi: se l'HV è già acceso (marcia/ricarica) legge e basta; altrimenti
        accende BREVEMENTE il clima (unico modo per accendere l'alta tensione), legge i dati
        reali, poi rispegne il clima. ⚠️ ATTUA sull'auto: il clima resta acceso ~1 minuto."""
        def emit(m):
            _LOGGER.info("[refresh] %s", m)
            self._update({"probe_status": str(m)[:255]})

        # 1) lettura immediata: se l'HV è già acceso, è già tutto fresco
        await self.async_probe(force=True)
        if self._is_hv_on():
            emit("Stato aggiornato — alta tensione già accesa ✅")
            return

        # 2) accendi il clima per svegliare l'alta tensione
        emit("Accendo il clima per ~1 min per leggere i dati reali (odometro/batteria)…")
        try:
            await self.async_send_command("clima_on")
        except Exception as err:  # noqa: BLE001
            emit(f"Non riesco ad accendere il clima: {err}")
            return

        # 3) leggi il realtime finché l'alta tensione non è su (max ~2,5 min)
        got = False
        for _ in range(6):
            await asyncio.sleep(POLL_WAKE_WAIT)
            try:
                await self.async_probe(force=True)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("[refresh] lettura realtime fallita: %s", err)
            if self._is_hv_on():
                got = True
                break

        # 4) rispegni sempre il clima (anche in caso di insuccesso)
        try:
            await self.async_send_command("clima_off")
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("[refresh] spegnimento clima fallito: %s", err)
        emit("Stato aggiornato con dati reali ✅" if got
             else "L'auto non si è accesa in tempo — riprova, o si aggiornerà al prossimo viaggio")

    def is_pure_electric(self) -> bool:
        """True SOLO per un BEV confermato dal backend (`powerType == 0`).

        Deliberatamente falsa quando la capability è sconosciuta: si sopprime qualcosa
        (i sensori benzina) solo se si è CERTI che l'auto non abbia un motore termico.
        Su Lepas L8 PHEV, e su ogni entry che non ha mai letto le capability,
        il comportamento resta identico a prima."""
        return self.entry.data.get(DATA_POWER_TYPE) == 0

    def climate_limits(self) -> tuple[float, float, float]:
        """(min, max, step) del clima: quelli dichiarati dal backend per QUESTA vettura,
        altrimenti i default Lepas (16-30 °C, 1°). I valori sono già validati in
        `capabilities_from_item`, qui non serve ricontrollarli."""
        d = self.entry.data
        return (float(d.get(DATA_CLIMATE_MIN, CLIMA_MIN_DEFAULT)),
                float(d.get(DATA_CLIMATE_MAX, CLIMA_MAX_DEFAULT)),
                float(d.get(DATA_CLIMATE_STEP, CLIMA_STEP_DEFAULT)))

    def climate_extremes(self) -> tuple[float | None, float | None]:
        """(LO, HI) = il massimo freddo e il massimo caldo che QUESTA vettura accetta, o
        `(None, None)` se il backend non li ha dichiarati.

        Sono i valori che spediscono le macro «Raffredda tutto» / «Riscalda tutto»
        (es. 15.0 e 31.0). Fino alla v1.12.1 erano due costanti cablate.

        ⚠️ **`None` non va sostituito con i capi del range normale**, per quanto sembri
        ragionevole («senza LO/HI gli estremi sono min e max»). Sarebbe una dichiarazione
        inventata: il chiamante non potrebbe più distinguerla da una vera e spedirebbe
        16.0/30.0 al posto dei 15.0/31.0 di sempre — cioè cambierebbe il comportamento di
        utenti funzionanti sulla base di un dato che il backend non ha mai dato. La regola
        del componente è l'opposto: si cambia SOLO su dichiarazione esplicita."""
        d = self.entry.data
        lo, hi = d.get(DATA_CLIMATE_LO), d.get(DATA_CLIMATE_HI)
        if lo is None or hi is None:
            return (None, None)
        try:
            return (float(lo), float(hi))
        except (TypeError, ValueError):
            return (None, None)

    def air_durations(self) -> list[int]:
        """Le durate del clima ammesse dalla vettura, in minuti. Vuota = non dichiarate,
        e allora non si corregge niente (non sapere non autorizza a inventare)."""
        v = self.entry.data.get(DATA_AIR_DURATIONS)
        if not isinstance(v, (list, tuple)) or not v:
            return []
        try:
            return [int(x) for x in v]
        except (TypeError, ValueError):
            return []

    def _caps_correnti(self) -> dict:
        """Le capability con i nomi NEUTRI che usa `core/` (che non importa `const.py`).

        Le chiavi non dichiarate dal backend **non compaiono affatto**: `core/` distingue
        «assente» da «dichiarato», e l'assenza vuol dire «spedisci quello che spedivi».

        ⚠️ `clima_min`/`clima_max` e `clima_lo`/`clima_hi` sono due dichiarazioni DIVERSE e non
        vanno confuse: la prima è l'intervallo che si può impostare (`minTemperature`/
        `maxTemperature`), la seconda le due posizioni estreme LO/HI, che stanno **fuori** da
        quell'intervallo. Serve la prima per sapere se un setpoint è ammesso, la seconda per
        sapere cosa spedire quando si vuole «il massimo che quest'auto sa fare».
        ⚠️ Quel «fuori» è imposto da `const.capabilities_from_item` **solo quando il range è
        stato dichiarato** (`lo <= min` e `hi >= max`, estremi inclusi): senza `minTemperature`/
        `maxTemperature` la coppia LO/HI entra senza controlli di coerenza. Non darlo per
        garantito in un ragionamento che debba reggere su una vettura che non conosciamo.
        Qui si legge `entry.data` direttamente perché `climate_limits()` ricade sui default
        di default, e un default non è una dichiarazione: passarlo a `core/` sarebbe
        esattamente l'invenzione che `climate_extremes()` esiste per impedire."""
        caps: dict = {}
        tmin, tmax = self.entry.data.get(DATA_CLIMATE_MIN), self.entry.data.get(DATA_CLIMATE_MAX)
        # ⚠️ Entrambi o nessuno: mezzo intervallo non è un intervallo, e `_limita_temperatura`
        # salterebbe comunque la coppia incompleta. La `try` copre `entry.data` sporca (passa da
        # JSON); e poiché la tupla si assegna in blocco, un `float()` che solleva non lascia
        # dietro di sé mezza dichiarazione.
        if tmin is not None and tmax is not None:
            try:
                caps["clima_min"], caps["clima_max"] = float(tmin), float(tmax)
            except (TypeError, ValueError):
                pass
        lo, hi = self.climate_extremes()
        if lo is not None and hi is not None:
            caps["clima_lo"], caps["clima_hi"] = lo, hi
        durate = self.air_durations()
        if durate:
            caps["durate_aria"] = durate
        return caps

    async def async_ensure_vehicle_identity(self) -> None:
        """Backfill best-effort dell'identità veicolo (nome/modello/marca) per il device HA.

        Serve agli entry creati PRIMA che il config flow la salvasse: se manca in entry.data
        (e non c'è override manuale) la legge UNA volta da queryList e la persiste, così ai
        restart successivi è già in cache (niente nuove chiamate). Sola lettura, non blocca il
        setup: su errore resta il fallback "Lepas L8"."""
        # Le capability (BEV/PHEV, range clima) arrivano dalla STESSA risposta: se mancano si
        # rilegge anche quando il nome è già in cache — una volta sola, poi c'è il marcatore.
        if self._timers.closing:
            return
        override = bool(str((self.entry.options or {}).get(CONF_VEHICLE_NAME) or "").strip())
        nome_in_cache = bool(self.entry.data.get(CONF_VEHICLE_NAME))
        # Il marcatore è VERSIONATO: chi ha già `caps_probed`..`_v4` deve rileggere una
        # volta sola per le capability V5 (permessi 212/2121/216), poi si ferma di nuovo.
        caps_da_leggere = not self.entry.data.get(DATA_CAPS_PROBED_V5)
        if (override or nome_in_cache) and not caps_da_leggere:
            return  # nulla da chiedere: nome deciso e capability già interrogate
        info = await self.hass.async_add_executor_job(self._fetch_vehicle_identity)
        if self._timers.closing or not info:
            return
        if self.entry.entry_id not in self.hass.data.get(DOMAIN, {}):
            return  # integrazione scaricata durante la chiamata
        # L'identità si scrive SOLO se non c'era: un override manuale (o un nome già in
        # cache) non va mai sovrascritto solo perché siamo passati a leggere le capability.
        if override or nome_in_cache or not info.get(CONF_VEHICLE_NAME):
            for k in (CONF_VEHICLE_NAME, DATA_VEHICLE_MODEL, DATA_VEHICLE_BRAND):
                info.pop(k, None)
        else:
            self.vehicle_name = info.get(CONF_VEHICLE_NAME)
            self.vehicle_model = info.get(DATA_VEHICLE_MODEL)
            self.vehicle_brand = info.get(DATA_VEHICLE_BRAND)
        if not info:
            return  # niente di nuovo da persistere
        self.hass.config_entries.async_update_entry(
            self.entry, data={**self.entry.data, **info})  # → un reload (poi è in cache)
        # ⚠️ Riallineare il contesto A MANO. Il `CoreCtx` è memoizzato e viene costruito
        # PRIMA di questa lettura (lo costruisce `_fetch_vehicle_identity` stessa, per fare
        # il login), quindi nasce con le capability che c'erano allora: nessuna, al primo
        # avvio. E un cambio della sola `data` non fa ripartire l'entry — è una scelta
        # voluta, altrimenti il backfill si ricaricherebbe addosso. Senza questa riga le
        # capability appena lette resterebbero inutilizzate fino al riavvio di HA.
        # Si aggiorna il CONTENUTO, non l'oggetto: `ctx` deve restare lo stesso per tutta la
        # vita dell'entry, o l'anti-lockout del PIN si azzererebbe.
        if self._ctx is not None:
            self._ctx.caps = self._caps_correnti()
            probed_perms = getattr(self, "_probed_permessi", None)
            if probed_perms is not None:
                self._ctx.permessi = probed_perms
        vf = info.get(DATA_VEHICLE_FEATURES) or {}
        if any(v is False for v in vf.values()):
            from . import async_cleanup_disabled_entities
            await async_cleanup_disabled_entities(self.hass, self.entry)
            self.hass.config_entries.async_schedule_reload(self.entry.entry_id)

    def _fetch_vehicle_identity(self) -> dict | None:
        """queryList (sola lettura) → {vehicle_name, vehicle_model, vehicle_brand} per il VIN."""
        try:
            import requests
            from .core import wake
            from .core import lepas_auth as A
            from .core import permessi
            ctx = self.ctx
            token, tuid_login = wake._bff_login(ctx)
            access = wake._access_token(ctx)
            headers = A.headers_post("/tsp/v1/app/vmc/queryList", ctx=ctx, extra={
                "Authorization": f"Bearer {access}",
                "Content-Type": "application/json; charset=UTF-8",
                "Accept": "application/json, text/plain, */*"})
            j = requests.post(ctx.bff + "/tsp/v1/app/vmc/queryList",
                              data="{}", headers=headers, timeout=20).json()
            data = j.get("data")
            cands = []
            if isinstance(data, list):
                cands = data
            elif isinstance(data, dict):
                for k in ("controlCarList", "authorizedControlCarList", "carList", "vehicles"):
                    if isinstance(data.get(k), list):
                        cands += data[k]
                if not cands and "vin" in data:
                    cands = [data]
            item = next((x for x in cands if isinstance(x, dict)
                         and str(x.get("vin")) == self.vin), None)
            if item is None and cands and isinstance(cands[0], dict):
                item = cands[0]
            if not item:
                return None
            # Capability dalla STESSA risposta: powerType (BEV/termico) e range clima reale
            # della vettura. Il marcatore si scrive comunque, anche se il backend non le
            # dichiara: «chiesto e non c'è» ≠ «mai chiesto» (altrimenti si richiede a ogni avvio).
            caps: dict = {DATA_CAPS_PROBED: True, DATA_CAPS_PROBED_V2: True,
                          DATA_CAPS_PROBED_V4: True, DATA_CAPS_PROBED_V5: True,
                          **capabilities_from_item(item)}
            try:
                tuid = (
                    wake._valid_tuserid(getattr(self, "tuserid", ""))
                    or wake._valid_tuserid(tuid_login)
                    or wake._resolve_tuserid(ctx)
                )
                if token and tuid:
                    perms = permessi.leggi(ctx, token, tuid)
                    if perms:
                        caps[DATA_CAPS_PROBED_V3] = True
                        caps[DATA_VEHICLE_FEATURES] = features_from_permissions(perms)
                        self._probed_permessi = perms
            except Exception as p_err:  # noqa: BLE001
                _LOGGER.debug("[veicolo] permessi queryVehicleAuthority non recuperati: %s", p_err)

            nick = str(item.get("nickname") or "").strip()
            full = str(item.get("fullName") or "").strip()
            name = nick or (full.title() if full else "")
            if not name:
                return caps
            return {CONF_VEHICLE_NAME: name,
                    DATA_VEHICLE_MODEL: (full.title() if full else None),
                    DATA_VEHICLE_BRAND: _derive_brand(full or nick),
                    **caps}
        except Exception as err:  # noqa: BLE001 — best-effort, non deve far fallire il setup
            _LOGGER.debug("[veicolo] identità non recuperata: %s", err)
            return None

    async def async_check_session(self) -> tuple[bool, str]:
        ok, detail, status = await self.hass.async_add_executor_job(self._check_session)
        if ok and self.tuserid and self.entry.data.get(CONF_TUSERID) != self.tuserid:
            self.hass.config_entries.async_update_entry(
                self.entry, data={**self.entry.data, CONF_TUSERID: self.tuserid}
            )
        self._update({"session_ok": ok, "session_detail": detail})
        # P1-1 (H7): la reauth si decide sul MARCATORE STABILE, non sul testo umano. Prima si
        # faceva `detail.startswith("Sessione scaduta")`: bastava ritoccare il messaggio (o
        # tradurlo) per non aprire più la card «Riautentica». Solo EXPIRED = token morto; un
        # NET_ERROR è transitorio e NON deve far rifare il login all'utente.
        # HA deduplica: se una reauth è già in corso non ne apre un'altra.
        if self._diag is not None:
            # `status` è il marcatore stabile, `detail` il testo umano: registrarli
            # entrambi fa vedere subito un eventuale disallineamento fra i due (una
            # sessione KO che NON apre la reauth, o viceversa).
            self._diag.record("session", ok=ok, status=status, detail=detail,
                              triggered_reauth=(status == SESSION_STATUS_EXPIRED))
        if status == SESSION_STATUS_EXPIRED:
            self._avvisa_sessione_morta()
            self.entry.async_start_reauth(self.hass)
        elif ok:
            self._chiudi_avviso_sessione()
        return ok, detail

    # ───────────────── avviso in Home Assistant (sessione da riautenticare) ─────────────────
    # La sola card «Riautentica» è facile da non vedere: l'integrazione può restare ferma
    # per ore senza che nessuno se ne accorga (è successo davvero). La notifica dice in
    # chiaro COSA è rotto e COSA fare, e sparisce da sé quando la sessione torna viva.
    @property
    def _id_avviso(self) -> str:
        return f"{DOMAIN}_sessione_{self.entry.entry_id}"

    def _avvisa_sessione_morta(self) -> None:
        from homeassistant.components import persistent_notification

        auto = self.entry.data.get(CONF_VEHICLE_NAME) or self.vin or "Lepas"
        if (self.hass.config.language or "en").split("-")[0] == "it":
            titolo = f"{auto}: sessione scaduta"
            testo = (
                f"L'integrazione non riesce più a parlare con l'auto: comandi e sensori "
                f"restano fermi finché non riautentichi.\n\n"
                f"Vai su **Impostazioni → Dispositivi e servizi → Lepas Connect → "
                f"Riautentica** e inserisci la password dell'account.\n\n"
                f"La password serve solo a ripristinare la sessione e non viene salvata."
            )
        else:
            titolo = f"{auto}: session expired"
            testo = (
                f"The integration can no longer talk to the car: commands and sensors "
                f"stay frozen until you re-authenticate.\n\n"
                f"Go to **Settings → Devices & services → Lepas Connect → "
                f"Re-authenticate** and enter your account password.\n\n"
                f"The password is used only to restore the session and is not stored."
            )
        persistent_notification.async_create(
            self.hass, testo, title=titolo, notification_id=self._id_avviso)

    def _chiudi_avviso_sessione(self) -> None:
        from homeassistant.components import persistent_notification

        persistent_notification.async_dismiss(self.hass, self._id_avviso)

    def _check_session(self) -> tuple[bool, str, str]:
        from .core import session as SESSION
        ok, detail, status = SESSION.check(self.ctx)
        # Difesa contro il drift dei due letterali: se core/session.py cambiasse il valore di
        # STATUS_EXPIRED, la reauth continuerebbe a scattare (ci si allinea al modulo, che è
        # la fonte, invece di confrontare alla cieca la costante locale).
        if status == getattr(SESSION, "STATUS_EXPIRED", SESSION_STATUS_EXPIRED):
            status = SESSION_STATUS_EXPIRED
        if ok:
            from .core import wake
            if not wake._valid_tuserid(self.tuserid):
                try:
                    resolved = wake._resolve_tuserid(self.ctx)
                except Exception:  # noqa: BLE001
                    resolved = ""
                if wake._valid_tuserid(resolved):
                    self.tuserid = resolved
                    if self._ctx is not None:
                        self._ctx.tuserid = resolved
        return ok, detail, status

    def _login_with_password(self, password: str) -> tuple[bool, str]:
        """Riconia il token con la password (usa-e-getta, mai salvata) e ricontrolla la sessione."""
        from .core import session as SESSION
        return SESSION.login_with_password(self.ctx, password or "")
