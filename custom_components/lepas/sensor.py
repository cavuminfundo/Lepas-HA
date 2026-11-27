"""Sensor: serratura (lock), livelli sedili (level) + batteria/velocità/sessione
+ sensori diagnostici del ponte (esiti comando/sveglia/sonda, timestamp).

Gli entity_id riproducono 1:1 quelli del bridge (lepas_*) per continuità storico.
Tutti i sensori sono RestoreSensor: al riavvio di HA ripristinano l'ultimo valore
noto come fallback (parità col bridge, che persisteva via MQTT retained) finché non
arriva un dato live dall'auto.
"""
from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .charging_stats import compute_charge_delta_kwh
from .const import (
    CHARGE_ENERGY_MAX_GAP,
    DATA_VEHICLE_COLOR,
    DATA_VEHICLE_COLOR_CODE,
    DATA_VEHICLE_COLOR_NAME,
    DEFAULT_BATTERY_CAPACITY_KWH,
    DOMAIN,
    FIELDS_AS_RICH_ENTITY,
    entity_allowed,
)
from .consumption import WINDOW_100_KM, WINDOW_1000_KM, _safe_float, is_degraded_battery_frame
from .coordinator import SENSORS, _pick_field
from .entity import LepasEntity, field_on, in_zona_casa
from .naming import ID_PREFIX
from .scheduler import (
    DEFAULT_HOME_CHARGE_POWER_KW,
    DesiredChargePlan,
    align_charge_start_minutes,
    compute_battery_heat_start_for_departure,
    compute_charge_start_for_departure,
    compute_charge_window,
    decode_charge_appoint_plan,
    normalize_climate_extras,
    parse_days_input,
    resolve_tzinfo,
)

# ───────────────────────── sensori "realtime" (Round B) ─────────────────────────
# Campi del canale REST /asr/manager/realtime (in coordinator.data["realtime"]),
# aggiornati al RISVEGLIO dell'auto (probe read-only). A differenza del 5A02 (MQTT),
# qui i VALORI reali di autonomia/odometro/gomme/consumi/ricarica ci sono davvero
# (sul 5A02 erano solo flag di unità "1"). Validati 1:1 contro il bean ufficiale
# CVRealtimeResBean dell'SDK Chery. Una tabella di spec evita 20+ classi gemelle.
#
# Valori/unità CONFERMATI dal vivo ad auto sveglia (2026-06-21, 84 campi):
#   pureElectricRange=60 km · mileageSurplus=215 km (benzina) · cruiseRange=134 (=215 km in miglia)
#   lFrontTyreKpa=292 (=42 psi) → kPa · gomme temp 34-35 °C · *TyreCall/socLowCall=0=ok
#   oilSurplus=23 → LITRI (215−60=155 km a benzina /23 L ≈ 15 L/100km) · averageFuel=0.0
#   avgHkPowerKwh50km=20.6 → kWh/100km · totalVoltage=323.1 V · totalCurrent=0.0 A (HV reali!)
#   remainChargeTime ASSENTE ad auto non in carica (comparirà sotto carica).

C = UnitOfTemperature.CELSIUS
KM = UnitOfLength.KILOMETERS
MIGLIA = UnitOfLength.MILES   # unità NATIVA di cruiseRange (vedi _RT_SENSORS)
KPA = UnitOfPressure.KPA
BAR = UnitOfPressure.BAR
MIN = UnitOfTime.MINUTES
VOLT = UnitOfElectricPotential.VOLT
AMP = UnitOfElectricCurrent.AMPERE
DIST = SensorDeviceClass.DISTANCE
TEMP = SensorDeviceClass.TEMPERATURE
PRESS = SensorDeviceClass.PRESSURE
DUR = SensorDeviceClass.DURATION
VOLTAGE = SensorDeviceClass.VOLTAGE
CURRENT = SensorDeviceClass.CURRENT
KW = UnitOfPower.KILO_WATT
POWER = SensorDeviceClass.POWER
MEAS = SensorStateClass.MEASUREMENT
TOTAL = SensorStateClass.TOTAL_INCREASING


@dataclass(frozen=True)
class _RtSpec:
    """Spec di un sensore realtime. `numeric=False` → valore grezzo (stato/enum)."""

    suffix: str           # unique_id suffix (stabile): f"{vin}_rt_<suffix>"
    name: str             # nome → "Lepas <name>" → entity_id slugificato
    # chiave nel dict realtime. Una TUPLA elenca nomi alternativi per la stessa grandezza,
    # e vince il primo presente nel frame: modelli diversi la chiamano in modo diverso
    # (una BEV manda `dynamicPureElectricRange` dove la PHEV manda `pureElectricRange`).
    # Su Lepas L8 il primo nome è quello che arriva già oggi → nessun cambiamento.
    field: str | tuple[str, ...]
    device_class: SensorDeviceClass | None = None
    unit: str | None = None
    state_class: SensorStateClass | None = None
    icon: str | None = None
    diag: bool = False
    numeric: bool = True
    vmap: dict | None = None  # codice grezzo → testo leggibile (campi enum)
    invalid: tuple = ()       # valori (float) = segnaposto "nessuna lettura" (HV spenta) → tieni l'ultimo noto
    compute: Callable | None = None  # valore CALCOLATO da più campi realtime (ignora `field`)
    scale: float | None = None  # fattore moltiplicativo sul valore grezzo (es. kPa→bar = 0.01)
    precision: int | None = None  # cifre decimali suggerite per la UI
    # VOLATILE: campo che ha senso SOLO in una condizione precisa (es. remainChargeTime
    # esiste solo mentre l'auto carica). Assente = la condizione è finita → il valore va
    # a "sconosciuto", NON si tiene l'ultimo noto. Senza questo flag «Tempo di ricarica
    # residuo» restava a 120 min per ore ad auto scollegata (fuorviante).
    volatile: bool = False


# ── Mappe codice→testo per i campi enum di ricarica ──
# I valori sono enum a 3 stati ("0"/"1"/"2", confermati dai confronti nel codice
# dell'app `rus_car_state_model.dart`). `0` = stato a riposo verificato dal vivo
# (auto parcheggiata non in carica). La semantica di 1/2 segue la convenzione EV;
# qualunque codice non previsto resta leggibile come "Sconosciuto (N)" (vedi
# LepasRealtimeSensor._live_value) → nessuna informazione persa, nessun valore inventato.
CHARGE_STATE_MAP = {"0": "Non in ricarica", "1": "In ricarica", "2": "Ricarica completata"}
APPT_CHARGE_STATE_MAP = {"0": "Disattivata", "1": "Attiva", "2": "In esecuzione"}
FAST_GUN_MAP = {"0": "Scollegata", "1": "Collegata", "2": "Collegata (ricarica rapida)"}


# Nomi alternativi dell'autonomia elettrica: la PHEV manda `pureElectricRange`, una BEV
# manda `dynamicPureElectricRange`. Un unico elenco, usato sia dalle spec sia
# dai calcoli qui sotto, così non si sfilano fra loro.
ELEC_RANGE_FIELDS = ("pureElectricRange", "dynamicPureElectricRange")


def _primo(rt: dict, *nomi: str):
    """Primo dei `nomi` presente nel frame, convertito a float. None se nessuno c'è."""
    for n in nomi:
        if n in rt:
            try:
                return float(rt[n])
            except (TypeError, ValueError):
                return None
    return None


def _frame_batteria_degradato(rt: dict | None) -> bool:
    """True se il frame realtime porta `pureElectricRange = 0`: NON è una lettura, è un
    segnaposto → in quel frame anche la percentuale batteria è da buttare.

    Trovato in campo il 2026-07-31. Alle 01:31 la ricarica si chiude a 100% (150 km); due
    minuti dopo, spenta l'alta tensione, il cloud serve un frame con `dumpEnergy` 97 e
    `pureElectricRange` 0 — e ci resta inchiodato **7 ore**, finché l'auto non si risveglia
    e torna a dire 100%. Non è un valore vecchio "quasi giusto": nello storico dei 10 giorni
    precedenti tutti e 5 i frame con 0 km sono degradati, e la percentuale che portavano era
    sbagliata in 3 casi su 5 (97% contro 82% reale il 26/07, 97% contro 47% il 29/07,
    34% contro 100% il 25/07). Il valore del segnaposto cambia nel tempo (34, poi 97),
    quindi non si può riconoscere dalla percentuale: l'unico indizio affidabile è lo 0 km.

    Perché lo 0 km si può usare come sentinella senza rischi: l'autonomia elettrica scala
    con la carica a ~1,5 km per punto (100% = 150 km, 45% = 69 km, 16% = 12 km), quindi uno
    zero VERO vorrebbe dire scendere sotto l'~8%. Questa vettura non è mai andata sotto il
    16% (minimo assoluto in 5 settimane di storico) perché tiene una riserva per l'ibrido.

    ⚠️ Quel ragionamento vale per QUESTA vettura (riserva per l'ibrido). Su una BEV uno zero
    potrebbe in teoria essere vero; l'effetto peggiore però è tenere l'ultimo valore noto per
    un frame, quindi la sentinella resta accettabile anche lì.
    """
    return is_degraded_battery_frame(rt)


def _cruise_range_miglia(rt: dict):
    """`cruiseRange` espresso in MIGLIA — o niente, se l'auto non permette di deciderlo.

    ── Il fatto misurato ────────────────────────────────────────────────────────────────
    Il centralino manda ALCUNE grandezze due volte, in due unità, come campi fratelli.
    Frame reale di un veicolo PHEV, 2026-08-24:

        mileageSurplus     209 km   ↔  cruiseRange            130   (rapporto 1,6077)
        pureElectricRange  145 km   ↔  pureElectricRangeMile   90   (rapporto 1,6111)
        lFrontTyreKpa      283      ↔  lFrontTyrePsi           41   (rapporto 6,90)

    Sono TRE grandezze, non tutte: `odometer`, `averageFuel` e le temperature arrivano una
    volta sola. E il dizionario dei campi dell'app contiene un gemello di `mileageSurplus`
    con un nome dedicato (`mileageSurplusMile`) che quest'auto **non manda**: quindi
    l'identificazione di `cruiseRange` come gemello imperiale è un'inferenza da tre campioni
    su una sola auto, non l'accoppiamento dichiarato dal costruttore.

    ── Perché non basta più inchiodare le miglia ────────────────────────────────────────
    Il sensore dichiarava miglia per costante. Se su un altro modello quel campo fosse in
    chilometri, Home Assistant convertirebbe un valore già metrico e mostrerebbe 1,6 volte
    l'autonomia vera. ⚠️ **Non è dimostrato che accada**: la misura di @ThomasMeyer1970 su
    un altro modello riguarda `mileageSurplus`, non questo campo, e la lettura che chiuderebbe la
    questione è stata chiesta (issue #3, e il filo su #7) e non è ancora tornata. Questa
    funzione è quindi una difesa, non la correzione di un difetto osservato.

    ── Come decide, e le tre cose da cui si difende ─────────────────────────────────────
    Sul rapporto fra due campi, che è una misura, e non sui selettori `rangeUnit` (dei quali
    si sa solo che esistono e che nella famiglia `*Unit` si osservano sia 1 sia 2 — su campi
    DIVERSI: `rangeUnit` è sempre stato 1 in ogni campione conservato, il 2 è di
    `avgHkPowerUnit`. Che 1 e 2 significhino km e miglia **non è misurato**).

    1. **Senza ancora non si indovina, e non si ripiega sul grezzo.** Manca o è zero
       `mileageSurplus` ⇒ `None` ⇒ resta l'ultimo valore noto. Restituire il grezzo
       sembrerebbe «fail open» ma su un'auto in chilometri farebbe **riapparire il difetto
       per quel frame** (misurato: 209 → 336,35 km) e per giunta lo scriverebbe nell'ultimo
       noto. È lo stesso guasto già pagato in v1.7.1 con `_range_totale`.
    2. **L'ancora si verifica quando l'auto lo consente.** Se arriva la coppia gemella *per
       nome* `pureElectricRange`/`pureElectricRangeMile`, il suo rapporto dice se i campi
       senza suffisso di QUEL veicolo sono metrici. Se lo nega, non si decide.

    ⚠️ **Limite noto, non coperto e non copribile da qui.** Non è detto che `cruiseRange` sia
    l'autonomia benzina: sul fork l'entità si chiama «Range Combined (Estimate)». Se su un
    modello fosse l'autonomia ELETTRICA in chilometri, il rapporto con `mileageSurplus`
    potrebbe valere ~1,609 per pura aritmetica (su una PHEV con 209 km di benzina e 130 di
    elettrico è esattamente così) e la funzione direbbe «è già in miglia». Una guardia che
    confronti `cruiseRange` con `pureElectricRange` è stata scritta e poi **rimossa**: in quel
    caso restituiva lo stesso identico valore del ramo normale — un ramo che non cambia niente
    è codice morto travestito da sicurezza — e in cambio faceva congelare il sensore sulla
    nostra auto ogni volta che l'autonomia elettrica, scendendo, passava vicino al valore di
    `cruiseRange`. Il caso si chiude con una misura sul J7, non con una difesa a indovinare.

    Un solo cancello converte: rapporto ≈1 fra `cruiseRange` e `mileageSurplus`. In ogni
    altro caso si spedisce il grezzo, cioè le miglia di sempre.
    """
    mi = _primo(rt, "cruiseRange")
    if mi is None or mi <= 0:
        # 0 è un segnaposto che il sensore pubblicava già come 0: non lo si trasforma.
        return mi

    # (2) l'ancora è verificabile? La coppia gemella PER NOME è l'unica prova diretta che i
    # campi senza suffisso di questo veicolo siano metrici.
    e_km = _primo(rt, *ELEC_RANGE_FIELDS)
    e_mi = _primo(rt, "pureElectricRangeMile")
    if e_km and e_mi and not (1.50 <= e_km / e_mi <= 1.72):
        return mi

    # (1) l'ancora
    km = _primo(rt, "mileageSurplus")
    if km is None or km <= 0:
        return None

    if 0.93 <= km / mi <= 1.07:        # stesso numero ⇒ cruiseRange è in chilometri
        return mi / 1.609344
    return mi                           # tutto il resto: il grezzo, come si è sempre fatto


def _range_totale(rt: dict):
    """Autonomia totale REALE = elettrica (`pureElectricRange`) + benzina (`mileageSurplus`).
    None se manca un pezzo → resta l'ultimo valore noto (RestoreSensor).

    ⚠️ NON usare `cruiseRange` come totale: il dump head unit lo dava per il combinato del
    cruscotto (ID_DISPLAY_MILEAGE), ma è falso. Sembrava "statico" perché non seguiva
    l'autonomia elettrica; il 2026-07-22 si è capito il perché — è l'autonomia BENZINA in
    miglia (182 km/1,609 = 113 e 215 km/1,609 = 134, due campioni a un mese di distanza).
    Quindi non contiene affatto la parte elettrica. La somma elettrica+benzina segue lo
    stato batteria → è la scelta corretta."""
    # 0 km = segnaposto, non una lettura: sommarlo farebbe crollare il totale di ~150 km
    # (visto il 30/07: 251 → 125 km per tutta la notte). Vedi _frame_batteria_degradato.
    if _frame_batteria_degradato(rt):
        return None
    elec = _primo(rt, *ELEC_RANGE_FIELDS)
    fuel = _primo(rt, "mileageSurplus")
    if elec is None or fuel is None:
        return None
    return elec + fuel


def _range_totale_bev(rt: dict):
    """Autonomia totale su BEV CONFERMATO = solo la parte elettrica (non c'è serbatoio).

    Sostituisce `_range_totale` unicamente quando il backend dichiara `powerType == 0`.
    ⚠️ Non si ottiene lo stesso effetto trattando la benzina mancante come 0: su una PHEV
    un `mileageSurplus` assente per un frame farebbe crollare il totale di ~150 km — è
    esattamente il difetto corretto in v1.7.1. Qui la differenza la fa la capability
    dichiarata, non l'assenza del campo."""
    if _frame_batteria_degradato(rt):
        return None
    return _primo(rt, *ELEC_RANGE_FIELDS)


_RT_SENSORS: list[_RtSpec] = [
    # ── P1 · autonomia / chilometri (valori km confermati dal vivo) ──
    # 0 km = segnaposto "alta tensione spenta", NON autonomia esaurita → tieni l'ultimo noto
    # invece di mostrare 0 km per ore ad auto carica (vedi _frame_batteria_degradato).
    _RtSpec("range_elettrico", "Autonomia elettrica", ELEC_RANGE_FIELDS,
            DIST, KM, MEAS, "mdi:map-marker-distance", invalid=(0.0,)),
    # mileageSurplus = autonomia a BENZINA (motore termico), NON il totale: verificato dal
    # vivo 2026-06-23 che resta 215 km mentre l'autonomia elettrica scende (60→27 km) e il
    # carburante è invariato (oilSurplus 23 L) → segue il serbatoio, non la batteria.
    _RtSpec("range_benzina", "Autonomia benzina", "mileageSurplus",
            DIST, KM, MEAS, "mdi:gas-station"),
    # Autonomia TOTALE = elettrica + benzina (campo CALCOLATO). Vedi _range_totale.
    # (cruiseRange NON usato come totale: è l'autonomia benzina in miglia — vedi sotto.)
    _RtSpec("range_totale", "Autonomia totale", "",
            DIST, KM, MEAS, "mdi:map-marker-distance", compute=_range_totale),
    # cruiseRange = `mileageSurplus` (autonomia benzina) espresso in MIGLIA. RISOLTO il
    # 2026-07-22 confrontando due campioni a un mese di distanza:
    #     182 km / 1,609344 = 113,09  →  cruiseRange 113   (22/07)
    #     215 km / 1,609344 = 133,59  →  cruiseRange 134   (21/06)
    # Ecco perché sembrava "statico": non lo era, si muoveva in lockstep con l'autonomia
    # benzina. Non è quindi una stima combinata e NON va usato per l'autonomia totale — è
    # lo stesso dato in un'altra unità (di qui il campo `rangeUnit` che l'auto invia).
    # Tenuto come diagnostico: conferma dal vivo l'unità di misura scelta dal cloud.
    # Dichiarare l'unità VERA (miglia) non è un dettaglio: con `device_class`
    # distanza è Home Assistant a convertire per l'utente, quindi il sensore
    # mostrerà ~182 km invece di un "113 km" che sarebbe semplicemente falso.
    # precision=0: la conversione miglia→km produce 181,855872, sei decimali di
    # falsa precisione su un dato che l'auto manda arrotondato all'unità.
    # L'unità DICHIARATA resta miglia — stabile, così Home Assistant non registra un
    # cambio di unità e non spezza lo storico — mentre è il VALORE a essere normalizzato
    # per veicolo. Vedi _cruise_range_miglia: l'unità è una proprietà dell'auto, non una
    # costante del codice.
    _RtSpec("range_combinato", "Autonomia benzina (miglia)", "cruiseRange",
            DIST, MIGLIA, MEAS, "mdi:map-marker-distance", diag=True, precision=0,
            compute=_cruise_range_miglia),
    _RtSpec("odometro", "Odometro", "odometer",
            DIST, KM, TOTAL, "mdi:counter"),
    _RtSpec("km_ibrido", "Chilometraggio ibrido", "hybridMileage",
            DIST, KM, TOTAL, "mdi:counter", diag=True),
    # ── P1 · TPMS pressione (campo auto in kPa → mostrata in BAR come nell'app: ÷100) ──
    _RtSpec("gomma_ant_sx_press", "Pressione gomma ant. SX", "lFrontTyreKpa",
            PRESS, BAR, MEAS, "mdi:car-tire-alert", scale=0.01, precision=2),
    _RtSpec("gomma_ant_dx_press", "Pressione gomma ant. DX", "rFrontTyreKpa",
            PRESS, BAR, MEAS, "mdi:car-tire-alert", scale=0.01, precision=2),
    _RtSpec("gomma_post_sx_press", "Pressione gomma post. SX", "lRearTyreKpa",
            PRESS, BAR, MEAS, "mdi:car-tire-alert", scale=0.01, precision=2),
    _RtSpec("gomma_post_dx_press", "Pressione gomma post. DX", "rRearTyreKpa",
            PRESS, BAR, MEAS, "mdi:car-tire-alert", scale=0.01, precision=2),
    # ── P1 · TPMS temperatura (°C, diagnostica) ──
    _RtSpec("gomma_ant_sx_temp", "Temperatura gomma ant. SX", "lFrontTyreTemp",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    _RtSpec("gomma_ant_dx_temp", "Temperatura gomma ant. DX", "rFrontTyreTemp",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    _RtSpec("gomma_post_sx_temp", "Temperatura gomma post. SX", "lRearTyreTemp",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    _RtSpec("gomma_post_dx_temp", "Temperatura gomma post. DX", "rRearTyreTemp",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    # ── P2 · consumi e residui (unità confermate dal vivo) ──
    _RtSpec("consumo_carburante", "Consumo medio carburante", "averageFuel",
            None, "L/100 km", MEAS, "mdi:gas-station"),
    # avgHkPowerKwh50km=20.6 dal vivo → kWh/100km (il nome "50km" è fuorviante).
    # -100 = segnaposto "nessun dato" ad auto ferma (HV spenta) → tieni l'ultimo noto.
    # `avgHkPower` è il nome che usano le BEV per la stessa grandezza (es. 17.7 = 177 Wh/km).
    _RtSpec("consumo_elettrico", "Consumo medio elettrico",
            ("avgHkPowerKwh50km", "avgHkPower"),
            None, "kWh/100 km", MEAS, "mdi:lightning-bolt", invalid=(-100.0,)),
    # oilSurplus=23 dal vivo → LITRI (confermato dal calcolo autonomia benzina).
    _RtSpec("carburante_residuo", "Carburante residuo", "oilSurplus",
            None, "L", MEAS, "mdi:fuel"),
    # ── P2 · batteria alta tensione (valide SOLO ad auto in marcia/ricarica) ──
    # Da ferma l'auto manda 0 V / -1000 A = segnaposto "HV spenta", non letture reali:
    # marcati invalidi → il sensore tiene l'ultimo valore noto invece di azzerarsi.
    _RtSpec("tensione_hv", "Tensione batteria HV", "totalVoltage",
            VOLTAGE, VOLT, MEAS, "mdi:flash", diag=True, invalid=(0.0,)),
    _RtSpec("corrente_hv", "Corrente batteria HV", "totalCurrent",
            CURRENT, AMP, MEAS, "mdi:current-dc", diag=True, invalid=(-1000.0,)),
    # ── P2 · ricarica ──
    # remainChargeTime: ASSENTE ad auto non in carica (comparirà sotto carica). Assunto
    # in MINUTI — da riconfermare a vettura in carica. chargeState/appointmentChargeState/
    # fastChargingGunStatus = codici (tutti 0 = a riposo dal vivo) → grezzi da decodificare.
    _RtSpec("tempo_ricarica", "Tempo di ricarica residuo", "remainChargeTime",
            DUR, MIN, None, "mdi:timer-sand", volatile=True),
    _RtSpec("potenza_ricarica", "Potenza di ricarica", "chargingPower",
            POWER, KW, MEAS, "mdi:ev-station", volatile=True),
    _RtSpec("stato_ricarica", "Stato ricarica", "chargeState",
            None, None, None, "mdi:ev-station", diag=True, numeric=False,
            vmap=CHARGE_STATE_MAP),
    _RtSpec("ricarica_prog_stato", "Ricarica programmata · stato", "appointmentChargeState",
            None, None, None, "mdi:calendar-clock", diag=True, numeric=False,
            vmap=APPT_CHARGE_STATE_MAP),
    _RtSpec("presa_rapida", "Presa ricarica rapida", "fastChargingGunStatus",
            None, None, None, "mdi:ev-plug-ccs2", diag=True, numeric=False,
            vmap=FAST_GUN_MAP),
    # ── P2 · clima target ──
    _RtSpec("temp_imp_sx", "Temperatura impostata SX", "frontSetTempLeft",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    _RtSpec("temp_imp_dx", "Temperatura impostata DX", "frontSetTempRight",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    # NB (2026-06-25): la cattura live del payload realtime (91 campi) ha SMENTITO i campi
    # del bean SDK che NON sono inviati da questa vettura (inCarTemperature, a/bOdoMeter,
    # chargingPower, averageSpeed, insFuelConsum, fastRemainChargeTime, tmpParkCountdown):
    # rimossi perché restavano `unknown` per sempre. Le novità verificate (oilCall/
    # electricityCall/engineState/hVoltageState) sono binary_sensor → vedi binary_sensor.py.
]

# ── Adattamento ai modelli SOLO ELETTRICI ────────────────────────────────────────────────
# Regola: si cambia qualcosa SOLO con `powerType == 0` dichiarato dal backend. Capability
# sconosciuta ⇒ tutto come sul modello base Lepas, entità comprese.

# Sensori che parlano del motore termico: su una BEV confermata non vengono proprio creati,
# invece di restare `unknown` per sempre. `range_combinato` è qui perché è `mileageSurplus`
# in miglia — cioè benzina anche lui.
_SENSORI_SOLO_TERMICO = frozenset({
    "range_benzina", "range_combinato", "consumo_carburante", "carburante_residuo",
    "km_ibrido",
})

# Campi specifici BEV (assenti sulla PHEV): si creano soltanto a BEV confermata.
_RT_SENSORI_BEV: list[_RtSpec] = [
    # autonomia omologata WLTP (valore fisso di targa, non una lettura) → diagnostica
    _RtSpec("range_wltp", "Autonomia WLTP", "wltcPureElectricRange",
            DIST, KM, MEAS, "mdi:map-marker-distance", diag=True),
    # efficienza dichiarata dall'auto in miglia/kWh: serve a chi ha HA in unità imperiali,
    # perché HA non sa convertire kWh/100 km (energia-per-distanza).
    _RtSpec("efficienza_mi_kwh", "Efficienza elettrica (mi/kWh)", "avgHkPowerMikwh",
            None, "mi/kWh", MEAS, "mdi:lightning-bolt", diag=True),
]


def _rt(coord, field: str | tuple[str, ...]) -> str | None:
    """Valore grezzo del campo realtime, o None se assente/vuoto.

    Con una tupla di nomi alternativi vince il PRIMO presente e valorizzato: serve ai
    modelli che chiamano la stessa grandezza in modo diverso (BEV vs PHEV)."""
    rt = coord.data.get("realtime") or {}
    for nome in ((field,) if isinstance(field, str) else field):
        v = rt.get(nome)
        if v is not None and str(v).strip() not in ("", "None"):
            return str(v)
    return None


def _waiting_text(hass: HomeAssistant | None) -> str:
    """Restituisce 'In attesa' se la lingua di HA è italiano, altrimenti 'Waiting'."""
    lang = (getattr(getattr(hass, "config", None), "language", None) or "it").split("-")[0].lower()
    return "In attesa" if lang == "it" else "Waiting"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    ents: list = [
        LepasFieldSensor(coord, s)
        for s in SENSORS
        if s["comp"] == "sensor"
        and s["key"] not in FIELDS_AS_RICH_ENTITY
        and entity_allowed(coord, "sensor", s["key"])
    ]
    ents.append(LepasBattery(coord))
    ents.append(LepasSpeed(coord))
    # Piano di partenza programmata: dato che l'auto ci manda già a ogni sonda e che finora
    # buttavamo via. Sola lettura — il comando `appointmentTravel` non è implementato.
    ents.append(LepasDeparturePlan(coord))
    # Contatori energia di ricarica casa/fuori (solo BEV: `chargingPower` esiste solo li').
    # Due entita' e non una con attributo: nella dashboard Energia una sorgente e' un'entita'.
    ents.append(LepasChargedEnergy(coord, home=True))
    ents.append(LepasChargedEnergy(coord, home=False))
    # — sensori "ricchi" dal canale realtime (Round B): autonomia, odometro, gomme,
    #   consumi, ricarica, clima target —
    # Su BEV CONFERMATA (powerType == 0) si tolgono i sensori del motore termico e si
    # aggiungono i campi che mandano solo le elettriche. Capability sconosciuta ⇒ elenco
    # invariato: su Lepas L8 esce esattamente ciò che usciva prima.
    bev = coord.is_pure_electric()
    specs = [s for s in _RT_SENSORS if not (bev and s.suffix in _SENSORI_SOLO_TERMICO)]
    if bev:
        # senza serbatoio l'autonomia totale è quella elettrica: il calcolo a due addendi
        # resterebbe a None per sempre (manca `mileageSurplus`).
        specs = [replace(s, compute=_range_totale_bev) if s.suffix == "range_totale" else s
                 for s in specs]
        specs += _RT_SENSORI_BEV
    ents += [LepasRealtimeSensor(coord, s) for s in specs]
    ents.append(LepasSessionStatus(coord))
    # — sensori diagnostici (parità col bridge) —
    ents.append(LepasTextSensor(coord, "Lepas Esito comando", "cmd_status", "cmd_status", "mdi:car-cog"))
    ents.append(LepasTextSensor(coord, "Lepas Esito sveglia", "wake_status", "wake_status", "mdi:car-connected"))
    ents.append(LepasTextSensor(coord, "Lepas Esito sonda posizione", "probe_status", "probe_status", "mdi:crosshairs-gps"))
    ents.append(LepasTimestampSensor(coord, "Lepas Ultimo contatto", "lastseen", "last_seen", "mdi:car-clock"))
    ents.append(LepasTimestampSensor(coord, "Lepas Ultima sveglia", "wake_ts", "last_wake", "mdi:car-clock"))
    ents.append(LepasTimestampSensor(coord, "Lepas Ultima posizione", "pos_fix", "last_pos_fix", "mdi:map-marker-clock"))
    # [2.0] freschezza del frame auto (resultTime del realtime): quanto è vecchio il dato
    #       batteria/odometro mostrato — utile ad auto ferma per sapere se è recente o stantio.
    ents.append(LepasTimestampSensor(coord, "Lepas Dati auto aggiornati", "car_data_ts", "car_data_ts", "mdi:database-clock"))
    if entity_allowed(coord, "sensor", "scheduled_charging_window"):
        ents.append(LepasScheduledChargingWindowSensor(coord))
    ents.append(LepasNextDepartureSensor(coord))
    ents.extend(
        LepasConsumptionSensor(coord, spec)
        for spec in _CONSUMPTION_SPECS
        if not (bev and spec.mode == "hev")
    )
    ents.extend(LepasChargingStatsSensor(coord, spec) for spec in _CHARGING_STATS_SPECS)
    add(ents)


class _LepasRestoreSensor(LepasEntity, RestoreSensor):
    """Base sensore Lepas che sopravvive al riavvio di HA.

    Lo stato (telemetria 5A02, realtime, diagnostica) è in-memory nel coordinator
    → dopo un restart torna `unknown`. Qui ripristiniamo l'ultimo valore noto e lo
    usiamo come fallback finché non arriva un dato live. Le sottoclassi forniscono
    `_live_value()` (valore corrente dal coordinator, o None se assente)."""

    def __init__(self, coord, name: str, unique_suffix: str) -> None:
        super().__init__(coord, name, unique_suffix, entity_id_format=ENTITY_ID_FORMAT)
        self._restored = None
        self._ultimo_noto = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None:
            self._restored = last.native_value

    def _live_value(self):
        """Sottoclassi: valore corrente dal coordinator, o None se assente."""
        raise NotImplementedError

    @property
    def native_value(self):
        # ⚠️ «ultimo valore noto» = l'ultimo LETTO DAVVERO, non quello ripristinato all'avvio.
        # Prima il fallback era il solo `_restored`, che è fotografato una volta sola quando
        # HA parte e non si muove più: un segnaposto (HV spenta, 0 V, 0 km…) non riportava
        # all'ultima lettura buona ma a quella di giorni prima. Con HA riavviato di rado la
        # differenza è enorme — è la stessa classe di errore del 97% del 31/07, e senza
        # questo la protezione sul frame degradato non avrebbe niente di sensato a cui
        # ripiegare. `_restored` resta la rete di sicurezza per il primo dato dopo l'avvio.
        live = self._live_value()
        if live is not None:
            self._ultimo_noto = live
            return live
        return self._ultimo_noto if self._ultimo_noto is not None else self._restored


class LepasFieldSensor(_LepasRestoreSensor):
    """serratura (0=Bloccata/1=Sbloccata), livello sedile (Livello N) o valore grezzo."""

    def __init__(self, coord, spec: dict) -> None:
        super().__init__(coord, f"Lepas {spec['name']}", spec["key"])
        self._key = spec["key"]
        self._kind = spec["kind"]
        if spec.get("icon"):
            self._attr_icon = spec["icon"]
        # campi tecnici (es. codice di fase del tetto) → tra i dettagli diagnostici
        if spec.get("diag"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def _live_value(self):
        v = self.coordinator.data.get("fields", {}).get(self._key)
        if v is None:
            return None
        if self._kind == "lock":
            return "Bloccata" if str(v) in ("0", "0.0") else "Sbloccata"
        if self._kind == "level":
            return f"Livello {v}"
        return str(v)

    @property
    def native_value(self):
        val = super().native_value
        if val is None and self._key == "sunroofMoveState":
            return _waiting_text(self.hass)
        return val


class LepasBattery(_LepasRestoreSensor):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coord) -> None:
        super().__init__(coord, "Lepas Batteria", "battery")

    def _live_value(self):
        rt = self.coordinator.data.get("realtime") or {}
        if "dumpEnergy" not in rt:
            return None
        # frame degradato (0 km di autonomia elettrica): la percentuale che porta non è una
        # lettura → tieni l'ultimo valore noto. Vedi _frame_batteria_degradato.
        if _frame_batteria_degradato(rt):
            return None
        try:
            soc = float(rt["dumpEnergy"])
        except (TypeError, ValueError):
            return None
        # dumpEnergy=0 = segnaposto "alta tensione spenta" (auto ferma), NON una carica
        # reale dello 0%: torna None così resta l'ultimo SOC noto (come fa l'app ufficiale).
        if soc <= 0:
            return None
        return soc

    @property
    def native_value(self):
        val = super().native_value
        # non riproporre uno "0%" stantio salvato prima del fix dei segnaposto: 0 non è un
        # ultimo-valore-noto valido per la batteria → meglio "sconosciuto" finché non arriva
        # una lettura vera (primo viaggio/ricarica o pulsante "Aggiorna stato completo").
        if val in (0, 0.0, "0", "0.0"):
            return None
        return val


class LepasSpeed(_LepasRestoreSensor):
    # device_class SPEED: senza, l'unità resta inchiodata a km/h. Con, Home Assistant
    # converte secondo il sistema di unità dell'utente (mph per chi ha HA in imperiale) e
    # permette l'override per-entità. Il valore nativo resta km/h → in Italia non cambia nulla.
    _attr_device_class = SensorDeviceClass.SPEED
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:speedometer"

    def __init__(self, coord) -> None:
        super().__init__(coord, "Lepas Velocità", "speed")

    def _live_value(self):
        rt = self.coordinator.data.get("realtime") or {}
        try:
            return float(rt["vehicleSpeed"]) if "vehicleSpeed" in rt else None
        except (TypeError, ValueError):
            return None


def _in_ricarica(v) -> bool:
    """True se `chargeState` dice "in ricarica".

    Tollera la forma float `'1.0'` che il canale realtime manda a volte: un confronto
    ingenuo `str(v) == "1"` teneva l'integrale fermo a zero senza dirlo — difetto trovato
    sulla linea fork e non ripetuto qui."""
    try:
        return float(v) == 1.0
    except (TypeError, ValueError):
        return False


class LepasChargedEnergy(LepasEntity, RestoreSensor):
    """Energia caricata mentre l'auto sta DENTRO (`home=True`) o FUORI (`home=False`) dalla
    zona `home` di Home Assistant.

    E' una STIMA ibrida: per intervalli ravvicinati (`<= CHARGE_ENERGY_MAX_GAP`) integra
    trapezoidalmente `chargingPower` (kW) nel tempo; per buchi di polling piu' larghi a
    veicolo fermo e collegato nella stessa zona riconcilia la variazione positiva di SoC
    (`dumpEnergy` * capacità batteria) tramite `compute_charge_delta_kwh()`. L'accumulo
    avviene solo quando la posizione GPS viva ricade dentro (`home=True`) o fuori
    (`home=False`) dalla zona `home` (`in_zona_casa`).

    Contatore di vita (`TOTAL_INCREASING`, kWh): si mette direttamente nella dashboard
    Energia come sorgente. Casa + Fuori ≈ energia totale caricata, divisa per luogo.

    Note sull'accuratezza:
      - i campioni arrivano dal poll realtime (~120 s durante la carica) → qualche punto
        percentuale di scarto da un contatore vero. Va bene per la dashboard Energia, NON
        e' una lettura fiscale;
      - se l'auto ha guidato nel frattempo (`odometer` avanzato) o il frame batteria e'
        degradato (`pureElectricRange == 0`), il buco non inventa energia;
      - quando la posizione viva e' ignota NESSUNO dei due contatori accumula: l'energia non
        viene mai attribuita alla zona sbagliata (la continuità cross-riavvio è gestita da
        `ChargingStatsTracker` su `Store`).
    """

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(self, coord, *, home: bool) -> None:
        self._home = home
        # Il prefisso "Lepas" e' la convenzione di questo file: da li' esce l'object_id
        # `lepas_...` dell'entity_id, e la translation_key e' quella senza prefisso.
        nome = ("Lepas Energia ricarica a casa" if home
                else "Lepas Energia ricarica fuori casa")
        super().__init__(coord, nome,
                         "energy_charged_home" if home else "energy_charged_away",
                         entity_id_format=ENTITY_ID_FORMAT)
        self._attr_icon = "mdi:home-lightning-bolt" if home else "mdi:ev-station"
        self._energia_wh: float = 0.0
        self._ultimo_ts: float | None = None
        self._ultima_potenza: float = 0.0
        self._era_attivo: bool = False
        self._ultimo_soc: float | None = None
        self._ultimo_odo: float | None = None
        self._ultimo_rt: dict | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None and last.native_value is not None:
            try:
                val = float(last.native_value)
            except (TypeError, ValueError):
                val = None
            if val is not None and val >= 0:
                self._energia_wh = val * 1000.0

    def _campiona(self) -> None:
        """Hybrid integration step on coordinator update (trapezoid <= 300s, SoC delta > 300s)."""
        data = getattr(self.coordinator, "data", None) or {}
        rt = data.get("realtime")
        if not isinstance(rt, dict):
            return
        if rt is getattr(self, "_ultimo_rt", None):
            return
        if is_degraded_battery_frame(rt):
            self._ultimo_rt = rt
            return

        fields = data.get("fields") or {}
        sources = (rt, fields)
        potenza = _safe_float(_pick_field(sources, "chargingPower"))
        if potenza is None or potenza < 0.0:
            potenza = 0.0
        carica = _in_ricarica(_pick_field(sources, "chargeState")) and potenza > 0.0
        plugged = (
            field_on(_pick_field(sources, "chargeGunState")) is True
            or field_on(_pick_field(sources, "fastChargingGunStatus")) is True
        )
        soc_raw = _safe_float(_pick_field(sources, "dumpEnergy"))
        soc = soc_raw if (soc_raw is not None and 0.0 < soc_raw <= 100.0) else None
        odo_raw = _safe_float(_pick_field(sources, "odometer"))
        odo = odo_raw if (odo_raw is not None and odo_raw >= 0.0) else None

        a_casa = in_zona_casa(self.hass, data.get("position"))
        ultimo_odo = getattr(self, "_ultimo_odo", None)

        if a_casa is None:
            self._ultimo_rt = rt
            if ultimo_odo is not None and odo is not None and odo > ultimo_odo + 0.1:
                self._ultimo_ts = None
                self._era_attivo = False
                self._ultima_potenza = 0.0
                self._ultimo_odo = odo
                self._ultimo_soc = soc
            return

        if a_casa != self._home:
            self._ultimo_rt = rt
            self._era_attivo = False
            self._ultimo_ts = None
            self._ultima_potenza = 0.0
            self._ultimo_soc = soc
            self._ultimo_odo = odo
            return

        now_ts = dt_util.utcnow().timestamp()
        cap = _safe_float(
            getattr(self.coordinator, "battery_capacity_kwh", DEFAULT_BATTERY_CAPACITY_KWH)
        )
        if cap is None or cap <= 0.0:
            cap = DEFAULT_BATTERY_CAPACITY_KWH
        ultimo_ts = getattr(self, "_ultimo_ts", None)
        if isinstance(ultimo_ts, datetime):
            ultimo_ts = ultimo_ts.timestamp()

        delta_kwh, reset_cont = compute_charge_delta_kwh(
            ultimo_ts,
            self._ultima_potenza,
            getattr(self, "_ultimo_soc", None),
            ultimo_odo,
            self._era_attivo,
            now_ts=now_ts,
            power_kw=potenza,
            soc_pct=soc,
            odo_km=odo,
            charging=carica,
            plugged=plugged,
            degraded_battery=False,
            battery_capacity_kwh=cap,
        )
        if delta_kwh > 0.0:
            self._energia_wh += delta_kwh * 1000.0
        self._ultimo_rt = rt
        self._ultimo_ts = now_ts
        self._ultima_potenza = 0.0 if reset_cont else potenza
        self._ultimo_soc = (
            soc if (soc is not None or reset_cont) else getattr(self, "_ultimo_soc", None)
        )
        self._ultimo_odo = odo if (odo is not None or reset_cont) else ultimo_odo
        self._era_attivo = False if reset_cont else carica

    def _handle_coordinator_update(self) -> None:
        self._campiona()
        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        # Sono contatori che integrano nel TEMPO: accumulano sul trapezio fra due campioni
        # realtime consecutivi. Con l'aggiornamento automatico spento l'auto viene letta una
        # volta sola (il seed all'avvio), due campioni attivi consecutivi non arrivano mai e
        # il valore non puo' crescere → meglio UNAVAILABLE che uno zero fermo e ingannevole.
        return bool(self.coordinator.poll_enabled)

    @property
    def native_value(self) -> float:
        return round(self._energia_wh / 1000.0, 3)


class LepasRealtimeSensor(_LepasRestoreSensor):
    """Sensore generico su un campo del canale realtime (vedi `_RT_SENSORS`).

    Stesso pattern di `LepasBattery`/`LepasSpeed` ma parametrico: device_class,
    unità e state_class arrivano dalla spec. `numeric=True` converte a float (None
    se non parsabile → emerge l'ultimo valore noto del RestoreSensor); `numeric=False`
    tiene il valore grezzo (codici di stato ricarica da decodificare)."""

    def __init__(self, coord, spec: _RtSpec) -> None:
        super().__init__(coord, f"Lepas {spec.name}", f"rt_{spec.suffix}")
        self._spec = spec
        if spec.device_class:
            self._attr_device_class = spec.device_class
        if spec.unit:
            self._attr_native_unit_of_measurement = spec.unit
        if spec.state_class:
            self._attr_state_class = spec.state_class
        if spec.icon:
            self._attr_icon = spec.icon
        if spec.precision is not None:
            self._attr_suggested_display_precision = spec.precision
        if spec.diag:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        # VOLATILE: nessun fallback all'ultimo valore noto. Se il campo è assente ora, la
        # sua condizione è finita (es. carica terminata → remainChargeTime sparisce dal
        # payload) e il valore corretto è "sconosciuto", non l'ultimo letto. Per gli altri
        # sensori vale invece la regola normale del RestoreSensor (tieni l'ultimo noto).
        if self._spec.volatile:
            live = self._live_value()
            if live is not None:
                return live
            if (self._spec.field == "remainChargeTime" or self._spec.suffix == "tempo_ricarica") and not _in_ricarica(_rt(self.coordinator, "chargeState")):
                return 0
            return None
        return super().native_value

    def _live_value(self):
        # campo CALCOLATO da più field realtime (es. autonomia totale = elettrica + benzina)
        if self._spec.compute is not None:
            rt = self.coordinator.data.get("realtime") or {}
            val = self._spec.compute(rt)
            return None if (val is None or val in self._spec.invalid) else val
        raw = _rt(self.coordinator, self._spec.field)
        if raw is None:
            return None
        if self._spec.vmap is not None:
            key = raw[:-2] if raw.endswith(".0") else raw  # "0.0" → "0"
            return self._spec.vmap.get(key, f"Sconosciuto ({raw})")
        if not self._spec.numeric:
            return raw
        try:
            val = float(raw)
        except (TypeError, ValueError):
            return None
        # segnaposto "nessuna lettura" (es. HV spenta) → None ⇒ resta l'ultimo valore noto
        if val in self._spec.invalid:
            return None
        return val * self._spec.scale if self._spec.scale is not None else val


class LepasSessionStatus(_LepasRestoreSensor):
    _attr_icon = "mdi:key-chain"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coord) -> None:
        super().__init__(coord, "Lepas Stato sessione", "session_detail")

    def _live_value(self):
        return self.coordinator.data.get("session_detail") or None

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        base = super().extra_state_attributes
        attrs: dict[str, str] = dict(base) if isinstance(base, Mapping) else {}
        for key, attr in (
            (DATA_VEHICLE_COLOR, "vehicle_color"),
            (DATA_VEHICLE_COLOR_CODE, "vehicle_color_code"),
            (DATA_VEHICLE_COLOR_NAME, "vehicle_color_name"),
        ):
            val = getattr(self.coordinator, attr, None)
            if isinstance(val, str) and val.strip():
                attrs[key] = val.strip()
        return attrs or None


class LepasTextSensor(_LepasRestoreSensor):
    """Sensore testuale diagnostico (esito ultimo comando/sveglia/sonda)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coord, name: str, suffix: str, data_key: str, icon: str) -> None:
        super().__init__(coord, name, suffix)
        self._data_key = data_key
        self._attr_icon = icon

    def _live_value(self):
        return self.coordinator.data.get(self._data_key) or None

    @property
    def native_value(self):
        # [H9] gli esiti diagnostici (comando/sveglia/sonda) NON si ripristinano: un
        # esito vecchio dopo un restart sarebbe fuorviante (sembrerebbe l'ultima azione
        # appena eseguita). Solo il valore live; in assenza → _waiting_text.
        live = self._live_value()
        return live if live is not None else _waiting_text(self.hass)


class LepasTimestampSensor(_LepasRestoreSensor):
    """Timestamp diagnostico (ultimo contatto/sveglia/posizione)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coord, name: str, suffix: str, data_key: str, icon: str) -> None:
        super().__init__(coord, name, suffix)
        self._data_key = data_key
        self._attr_icon = icon

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # [H10] device_class TIMESTAMP esige un datetime tz-aware: valida il valore
        # ripristinato (stringa ISO → parse), altrimenti None, per non emettere il
        # warning HA "Invalid datetime" e non mostrare un timestamp malformato.
        r = self._restored
        if isinstance(r, str):
            r = dt_util.parse_datetime(r)
        if not (isinstance(r, datetime) and r.tzinfo is not None):
            r = None
        self._restored = r

    def _live_value(self):
        return self.coordinator.data.get(self._data_key)


# Giorni della settimana come li numera il backend (1 = lunedì … 7 = domenica), stessa
# convenzione di `cycleData` nella ricarica programmata.
GIORNI = {1: "lun", 2: "mar", 3: "mer", 4: "gio", 5: "ven", 6: "sab", 7: "dom"}


def _orario(minuti) -> str | None:
    """`minuti dalla mezzanotte` → "HH:MM", o None se il valore non è un orario valido."""
    try:
        m = int(minuti)
    except (TypeError, ValueError):
        return None
    if not 0 <= m < 1440:
        return None
    return f"{m // 60:02d}:{m % 60:02d}"


def _orario_locale(minuti, hass=None) -> tuple[str | None, int]:
    """Converte `travelTime` (minuti dalla mezzanotte UTC) nel fuso locale di HA e delta giorni."""
    if _orario(minuti) is None:
        return None, 0
    m = int(minuti)
    tz = resolve_tzinfo(hass)
    utc_today = dt_util.utcnow().date()
    utc_dt = datetime(utc_today.year, utc_today.month, utc_today.day, m // 60, m % 60, tzinfo=timezone.utc)
    local_dt = utc_dt.astimezone(tz)
    return f"{local_dt.hour:02d}:{local_dt.minute:02d}", (local_dt.date() - utc_today).days


class LepasDeparturePlan(_LepasRestoreSensor):
    """Piano di partenza programmata, letto dall'auto (`appointmentTravelSetVOS`).

    **Non costa nulla:** il campo arriva già dentro il canale realtime a ogni sonda; finora lo
    buttavamo via (0 occorrenze di `appointmentTravel` in tutto il package). Questa entità è
    di sola LETTURA: il comando `appointmentTravel` non è implementato, quindi il piano si
    imposta ancora dall'app ufficiale.

    ⚠️ **`createTime`/`updateTime`/`id` NON vengono esposti, di proposito.** Sembrano dire
    quando il piano è stato impostato e invece **il backend li rigenera a ogni interrogazione**:
    misurato il 2026-08-10 confrontando due letture a 6 settimane e mezzo di distanza — il
    contenuto (`travelTime` 350, `travelDate` [1-5], `travelAppointMainId` 63372) è rimasto
    identico mentre `id`, `createTime` e `updateTime` erano cambiati e valevano l'istante
    esatto della lettura. Mostrarli significherebbe dire all'utente «impostato oggi alle 09:31»
    di un piano che non tocca da mesi.

    ⚠️ Sia `travelTime` sia `chargeAppointPlans.startTime` arrivano in minuti dalla mezzanotte
    **UTC** (verificato dal vivo il 2026-11-17 e il 2026-11-26 in CET) e vengono quindi
    convertiti nel fuso orario locale di Home Assistant."""

    _attr_icon = "mdi:calendar-arrow-right"

    def __init__(self, coord) -> None:
        super().__init__(coord, "Lepas Partenza programmata", "rt_partenza_programmata")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None or not isinstance(last_state.attributes, Mapping):
            return
        raw_sig = last_state.attributes.get("applied_schedule_sig")
        restore_fn = getattr(self.coordinator, "restore_applied_schedule_sig", None)
        if (
            callable(restore_fn)
            and getattr(self.coordinator, "_applied_schedule_sig", None) is None
            and isinstance(raw_sig, str)
            and raw_sig.strip()
        ):
            restore_fn(raw_sig)

    def _piano(self) -> dict | None:
        rt = self.coordinator.data.get("realtime") or {}
        piani = rt.get("appointmentTravelSetVOS")
        if isinstance(piani, list) and piani and isinstance(piani[0], dict):
            return piani[0]
        return None

    def _main_switcher_off(self) -> bool:
        rt = (self.coordinator.data or {}).get("realtime") or {}
        return isinstance(rt, dict) and field_on(rt.get("mainSwitcher")) is False

    def _is_piano_attivo(self, piano: dict) -> bool:
        if self._main_switcher_off():
            return False
        return str(piano.get("switcher", "0")).strip() not in ("", "0", "None", "False")

    def _live_value(self):
        piano = self._piano()
        if piano is None:
            return "Disattivata" if self._main_switcher_off() else None
        # `switcher` 0 o `mainSwitcher` 0 = piano memorizzato ma spento.
        if not self._is_piano_attivo(piano):
            return "Disattivata"
        orario, _ = _orario_locale(piano.get("travelTime"), getattr(self, "hass", None))
        return orario

    def _synced_with_ha(self, piano: dict | None) -> bool | None:
        occ_fn = getattr(self.coordinator, "next_departure_occurrence", None)
        build_fn = getattr(self.coordinator, "_build_native_departure_payload", None)
        if not callable(occ_fn) or not callable(build_fn):
            return None

        rt = (self.coordinator.data or {}).get("realtime")
        if not isinstance(rt, dict):
            return None

        main_state = field_on(rt.get("mainSwitcher"))
        if piano is None:
            if main_state is not False:
                return None
            return occ_fn(dt_util.now()) is None

        sw_state = field_on(piano.get("switcher"))
        if sw_state is None and main_state is not False:
            return None

        piani = rt.get("appointmentTravelSetVOS")
        any_sw_on = (
            any(field_on(p.get("switcher")) is True for p in piani if isinstance(p, dict))
            if isinstance(piani, list)
            else sw_state is True
        )
        car_active = (main_state is not False) and any_sw_on
        occ = occ_fn(dt_util.now())
        if occ is None:
            return not car_active
        if not car_active:
            return False

        raw_tt = piano.get("travelTime")
        if isinstance(raw_tt, bool) or raw_tt is None:
            return None
        try:
            car_utc_min = int(raw_tt)
        except (TypeError, ValueError):
            return None
        if not 0 <= car_utc_min < 1440:
            return None

        raw_days = piano.get("travelDate")
        if raw_days is None:
            raw_days = piano.get("travelWeekday")
        if raw_days is None:
            return None
        if raw_days == [] or (isinstance(raw_days, str) and not raw_days.strip()):
            car_days: set[int] = set()
        else:
            try:
                car_days = set(parse_days_input(raw_days))
            except ValueError:
                return None

        _, _, sig = build_fn(occ)
        _, exp_utc_min, exp_utc_days = sig
        return car_utc_min == exp_utc_min and car_days == set(exp_utc_days)

    @property
    def extra_state_attributes(self) -> dict | None:
        piano = self._piano()
        lang = _ux_lang(getattr(self, "hass", None))
        txt = _UX_TEXT[lang]
        has_pending_fn = getattr(self.coordinator, "has_pending_departure_changes", None)
        pending_attrs = (
            {
                "has_pending_changes": has_pending_fn(),
                "applied_schedule_sig": getattr(self.coordinator, "_applied_schedule_sig", None),
            }
            if callable(has_pending_fn)
            else {}
        )
        if piano is None:
            if not self._main_switcher_off():
                return pending_attrs or None
            return {
                "attiva": False,
                "riepilogo": txt["disabled"],
                "synced_with_ha": self._synced_with_ha(None),
                **pending_attrs,
            }
        giorni = piano.get("travelDate")
        giorni = list(giorni) if isinstance(giorni, list) else []
        attrs: dict = {"attiva": self._is_piano_attivo(piano)}
        orario, day_delta = _orario_locale(piano.get("travelTime"), getattr(self, "hass", None))
        if orario:
            attrs["orario"] = orario
            if day_delta and giorni:
                giorni = [((int(g) - 1 + day_delta) % 7) + 1 for g in giorni if isinstance(g, int) or str(g).isdigit()]
        if giorni:
            attrs["giorni"] = giorni
            attrs["giorni_testo"] = ", ".join(GIORNI.get(g, str(g)) for g in giorni)
        summary_parts = [p for p in (orario, attrs.get("giorni_testo")) if p]
        summary = " · ".join(summary_parts)
        if attrs["attiva"]:
            attrs["riepilogo"] = summary or txt["active"]
        else:
            attrs["riepilogo"] = f"{txt['disabled']} ({summary})" if summary else txt["disabled"]
        attrs["synced_with_ha"] = self._synced_with_ha(piano)
        attrs.update(pending_attrs)
        return attrs


_DAY_ABBR: dict[str, dict[int, str]] = {
    "it": {1: "Lun", 2: "Mar", 3: "Mer", 4: "Gio", 5: "Ven", 6: "Sab", 7: "Dom"},
    "en": {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"},
    "nl": {1: "Ma", 2: "Di", 3: "Wo", 4: "Do", 5: "Vr", 6: "Za", 7: "Zo"},
}

_UX_TEXT: dict[str, dict[str, str]] = {
    "it": {
        "next_day": "Giorno dopo ",
        "disabled": "Disattivata",
        "today": "Oggi",
        "tomorrow": "Domani",
        "quick": "rapida",
        "climate": "clima",
        "active": "Attiva",
    },
    "en": {
        "next_day": "Next day ",
        "disabled": "Disabled",
        "today": "Today",
        "tomorrow": "Tomorrow",
        "quick": "quick",
        "climate": "climate",
        "active": "Active",
    },
    "nl": {
        "next_day": "Volgende dag ",
        "disabled": "Uitgeschakeld",
        "today": "Vandaag",
        "tomorrow": "Morgen",
        "quick": "snel",
        "climate": "klimaat",
        "active": "Actief",
    },
}


def _ux_lang(hass: HomeAssistant | None) -> str:
    if hass is None or getattr(hass, "config", None) is None:
        return "en"
    code = (getattr(hass.config, "language", None) or "en").lower()[:2]
    return code if code in ("it", "en", "nl") else "en"


def _format_days(days: list[int], lang: str) -> str:
    abbr = _DAY_ABBR[lang]
    norm = sorted({int(d) for d in days if 1 <= int(d) <= 7})
    if not norm:
        return ""
    if len(norm) >= 2 and norm == list(range(norm[0], norm[-1] + 1)):
        return f"{abbr[norm[0]]}–{abbr[norm[-1]]}"
    return ", ".join(abbr[d] for d in norm)


class LepasScheduledChargingWindowSensor(LepasEntity, SensorEntity):
    """Diagnostic summary of the configured scheduled charging window."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:battery-clock-outline"

    def __init__(self, coord) -> None:
        super().__init__(
            coord,
            "Lepas Scheduled charging window",
            "scheduled_charging_window",
            object_id=f"{ID_PREFIX}_scheduled_charging_window",
            entity_id_format=ENTITY_ID_FORMAT,
            translation_key="scheduled_charging_window",
        )

    def _evaluate_plan(self) -> DesiredChargePlan | None:
        eval_fn = getattr(self.coordinator, "evaluate_charge_plan", None)
        if not callable(eval_fn):
            return None
        try:
            plan = eval_fn(dt_util.now())
        except Exception:  # noqa: BLE001
            return None
        return plan if isinstance(plan, DesiredChargePlan) else None

    def _power_profile(self) -> dict[str, object]:
        prof_fn = getattr(self.coordinator, "home_power_profile", None)
        if callable(prof_fn):
            try:
                prof = prof_fn()
                if isinstance(prof, Mapping):
                    return dict(prof)
            except Exception:  # noqa: BLE001
                return {
                    "learned_ac_kw": None,
                    "learned_dc_kw": None,
                    "home_ac_sessions": 0,
                    "home_dc_sessions": 0,
                }
        return {
            "learned_ac_kw": None,
            "learned_dc_kw": None,
            "home_ac_sessions": 0,
            "home_dc_sessions": 0,
        }

    def _window_params(self, plan: DesiredChargePlan | None = None) -> tuple[int, int, list[int]]:
        eff_fn = getattr(self.coordinator, "effective_charge_days", None)
        if (
            plan is not None
            and plan.action == "enable"
            and plan.start_minutes is not None
            and plan.duration_minutes is not None
        ):
            start_min = align_charge_start_minutes(plan.start_minutes)
            dur_min = int(plan.duration_minutes)
            if callable(eff_fn):
                days = list(eff_fn(list(plan.days) if plan.days else None))
            elif plan.days:
                days = list(plan.days)
            else:
                days = list(getattr(self.coordinator, "charge_days", [1, 2, 3, 4, 5, 6, 7]))
            return start_min, dur_min, days

        raw_start = int(getattr(self.coordinator, "charge_start_minutes", 480) or 0)
        start_min = align_charge_start_minutes(raw_start)
        dur_h = int(getattr(self.coordinator, "charge_duration_hours", 6) or 6)
        if callable(eff_fn):
            days = list(eff_fn())
        else:
            days = list(getattr(self.coordinator, "charge_days", [1, 2, 3, 4, 5, 6, 7]))
        return start_min, dur_h * 60, days

    def _synced_with_car(
        self,
        start_min: int,
        dur_h: float,
        days: list[int],
        *,
        dur_min: int | None = None,
        ref_date=None,
    ) -> bool | None:
        raw = (self.coordinator.data or {}).get("fields", {}).get("chargeAppointPlans")
        if not raw:
            return None
        try:
            plans = ast.literal_eval(raw) if isinstance(raw, str) else raw
            piano = plans[0] if isinstance(plans, list) and plans and isinstance(plans[0], dict) else None
        except (ValueError, SyntaxError, TypeError, IndexError):
            return None
        if piano is None:
            return None
        tz = resolve_tzinfo(getattr(self, "hass", None) or getattr(self.coordinator, "hass", None))
        decoded = decode_charge_appoint_plan(piano, tz, ref_date=ref_date)
        if (
            decoded is None
            or decoded["start_minutes"] is None
            or decoded["duration_minutes"] is None
            or decoded["days"] is None
        ):
            return None
        expected_dur_min = int(dur_min) if dur_min is not None else round(float(dur_h) * 60)
        return (
            decoded["start_minutes"] == start_min
            and decoded["duration_minutes"] == expected_dur_min
            and decoded["days"] == sorted(days)
        )

    @property
    def native_value(self) -> str:
        lang = _ux_lang(getattr(self, "hass", None))
        txt = _UX_TEXT[lang]
        plan = self._evaluate_plan()
        start_min, dur_min, days = self._window_params(plan)
        start_hhmm, end_hhmm, next_day = compute_charge_window(start_min, dur_min / 60.0, days)
        end_part = f"{txt['next_day']}{end_hhmm}" if next_day else end_hhmm
        days_lbl = _format_days(days, lang)
        base = f"{start_hhmm} → {end_part}"
        return (f"{base} · {days_lbl}" if days_lbl else base)[:255]

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        plan = self._evaluate_plan()
        prof = self._power_profile()
        start_min, dur_min, days = self._window_params(plan)
        dur_hours_val: int | float = (
            dur_min // 60 if dur_min % 60 == 0 else round(dur_min / 60.0, 2)
        )
        start_hhmm, end_hhmm, next_day = compute_charge_window(start_min, dur_min / 60.0, days)
        window_mode = getattr(self.coordinator, "charge_window_mode", "off")
        if not isinstance(window_mode, str) or window_mode not in ("off", "fixed", "smart_departure"):
            window_mode = "off"
        default_kw = float(
            getattr(self.coordinator, "home_charge_power", DEFAULT_HOME_CHARGE_POWER_KW)
            or DEFAULT_HOME_CHARGE_POWER_KW
        )
        ref_date = plan.ref_date if plan is not None else None
        return {
            "start_time": start_hhmm,
            "end_time": end_hhmm,
            "next_day": next_day,
            "duration_hours": dur_hours_val,
            "days": days,
            "synced_with_car": self._synced_with_car(
                start_min,
                dur_hours_val,
                days,
                dur_min=dur_min,
                ref_date=ref_date,
            ),
            "window_mode": window_mode,
            "effective_action": plan.action if plan is not None else "noop",
            "plan_reason": plan.reason if plan is not None else "mode_off",
            "estimated_duration_min": plan.estimated_duration_min if plan is not None else None,
            "soc_used": plan.soc_used if plan is not None else None,
            "charge_kind": plan.charge_kind if plan is not None else "ac",
            "effective_power_kw": plan.effective_power_kw if plan is not None else default_kw,
            "power_source": plan.power_source if plan is not None else "manual",
            "learned_ac_kw": prof.get("learned_ac_kw"),
            "learned_dc_kw": prof.get("learned_dc_kw"),
            "home_ac_sessions": int(prof.get("home_ac_sessions", 0) or 0),
            "home_dc_sessions": int(prof.get("home_dc_sessions", 0) or 0),
            "fallback_used": bool(plan.fallback_used) if plan is not None else False,
            "away_bypass_active": bool(plan.away_bypass_active) if plan is not None else False,
            "quick_override_active": bool(plan.quick_override_active) if plan is not None else False,
        }


class LepasNextDepartureSensor(LepasEntity, SensorEntity, RestoreEntity):
    """Diagnostic summary of the next scheduled departure and pre-climate window."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:car-clock"

    def __init__(self, coord) -> None:
        super().__init__(
            coord,
            "Lepas Next departure",
            "next_departure",
            object_id=f"{ID_PREFIX}_next_departure",
            entity_id_format=ENTITY_ID_FORMAT,
            translation_key="next_departure",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None:
            return
        raw_extras = last.attributes.get("climate_extras")
        if raw_extras is None:
            return
        try:
            normalized = normalize_climate_extras(raw_extras)
        except ValueError:
            return
        allowed_fn = getattr(self.coordinator, "allowed_departure_climate_extras", None)
        if callable(allowed_fn):
            allowed = set(allowed_fn())
            normalized = [k for k in normalized if k in allowed]
        self.coordinator.departure_climate_extras = normalized

    def _snapshot(self):
        now = dt_util.now()
        occ_fn = getattr(self.coordinator, "next_departure_occurrence", None)
        occ = occ_fn(now) if callable(occ_fn) else None
        return now, occ

    @property
    def native_value(self) -> str:
        lang = _ux_lang(getattr(self, "hass", None))
        txt = _UX_TEXT[lang]
        now, occ = self._snapshot()
        if occ is None:
            return txt["disabled"]
        delta_days = (occ.departure_at.date() - now.date()).days
        day_abbr = _DAY_ABBR[lang][occ.weekday]
        if delta_days == 0:
            day_lbl = txt["today"]
        elif delta_days == 1:
            day_lbl = f"{txt['tomorrow']} {day_abbr.lower()}"
        else:
            day_lbl = day_abbr
        dep_hhmm = f"{occ.departure_at.hour:02d}:{occ.departure_at.minute:02d}"
        climate_mode = getattr(self.coordinator, "departure_climate_mode", "at_home")
        parts: list[str] = []
        if occ.source == "quick":
            parts.append(txt["quick"])
        if climate_mode != "off":
            c_hhmm = f"{occ.climate_start_at.hour:02d}:{occ.climate_start_at.minute:02d}"
            parts.append(f"{txt['climate']} {c_hhmm}")
        detail = f" ({' · '.join(parts)})" if parts else ""
        return f"{day_lbl} {dep_hhmm}{detail}"[:255]

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        now, occ = self._snapshot()
        climate_mode = getattr(self.coordinator, "departure_climate_mode", "at_home")
        sync_charging = bool(getattr(self.coordinator, "sync_charge_to_departure", False))
        sync_battery = bool(getattr(self.coordinator, "sync_battery_heat_to_departure", False))
        allowed_fn = getattr(self.coordinator, "allowed_departure_climate_extras", None)
        allowed_extras = list(allowed_fn()) if callable(allowed_fn) else []
        extras = list(getattr(self.coordinator, "departure_climate_extras", []) or [])
        if occ is None:
            return {
                "departure_at": None,
                "climate_start_at": None,
                "source": None,
                "weekday": None,
                "climate_mode": climate_mode,
                "sync_charging": sync_charging,
                "planned_charge_start": None,
                "climate_extras": extras,
                "allowed_climate_extras": allowed_extras,
                "battery_heat_start": None,
            }
        planned_charge = None
        eval_fn = getattr(self.coordinator, "evaluate_charge_plan", None)
        plan: DesiredChargePlan | None = None
        if callable(eval_fn):
            try:
                cand = eval_fn(now)
                if isinstance(cand, DesiredChargePlan):
                    plan = cand
            except Exception:  # noqa: BLE001
                plan = None
        if plan is not None:
            if (
                plan.action == "enable"
                and plan.start_minutes is not None
                and (sync_charging or plan.quick_override_active)
            ):
                c_min = align_charge_start_minutes(plan.start_minutes)
                planned_charge = f"{c_min // 60:02d}:{c_min % 60:02d}"
        elif sync_charging:
            dur_h = int(getattr(self.coordinator, "charge_duration_hours", 6) or 6)
            c_min = compute_charge_start_for_departure(occ.departure_at_minutes, dur_h)
            planned_charge = f"{c_min // 60:02d}:{c_min % 60:02d}"
        battery_heat_start = None
        if sync_battery:
            b_min = compute_battery_heat_start_for_departure(occ.departure_at_minutes, 30)
            battery_heat_start = f"{b_min // 60:02d}:{b_min % 60:02d}"
        return {
            "departure_at": occ.departure_at.isoformat(),
            "climate_start_at": occ.climate_start_at.isoformat() if climate_mode != "off" else None,
            "source": occ.source,
            "weekday": occ.weekday,
            "climate_mode": climate_mode,
            "sync_charging": sync_charging,
            "planned_charge_start": planned_charge,
            "climate_extras": extras,
            "allowed_climate_extras": allowed_extras,
            "battery_heat_start": battery_heat_start,
        }


@dataclass(frozen=True)
class _ConsumptionSpec:
    """Descriptor for a rolling or cumulative consumption sensor."""

    key: str
    mode: str
    target_km: float | None
    unit: str
    icon: str


_CONSUMPTION_SPECS: tuple[_ConsumptionSpec, ...] = (
    _ConsumptionSpec("ev_consumption_100km", "ev", WINDOW_100_KM, "kWh/100 km", "mdi:lightning-bolt"),
    _ConsumptionSpec("ev_consumption_1000km", "ev", WINDOW_1000_KM, "kWh/100 km", "mdi:lightning-bolt"),
    _ConsumptionSpec("ev_consumption_from_start", "ev", None, "kWh/100 km", "mdi:lightning-bolt"),
    _ConsumptionSpec("hybrid_consumption_100km", "hev", WINDOW_100_KM, "L/100 km", "mdi:gas-station"),
    _ConsumptionSpec("hybrid_consumption_1000km", "hev", WINDOW_1000_KM, "L/100 km", "mdi:gas-station"),
    _ConsumptionSpec("hybrid_consumption_from_start", "hev", None, "L/100 km", "mdi:gas-station"),
)


class LepasConsumptionSensor(LepasEntity, SensorEntity):
    """Long-term EV or Hybrid consumption sensor backed by ConsumptionTracker."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2

    def __init__(self, coord, spec: _ConsumptionSpec) -> None:
        super().__init__(
            coord,
            f"Lepas {spec.key}",
            spec.key,
            object_id=f"{ID_PREFIX}_{spec.key}",
            entity_id_format=ENTITY_ID_FORMAT,
            translation_key=spec.key,
        )
        self._spec = spec
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_icon = spec.icon

    def _stats(self) -> dict[str, object]:
        return self.coordinator.consumption_stats(self._spec.mode, self._spec.target_km)

    @property
    def native_value(self) -> float | None:
        val = self._stats().get("value")
        return float(val) if val is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        stats = self._stats()
        attrs: dict[str, object] = {
            "sampled_km": stats.get("sampled_km", 0.0),
            "window_target_km": stats.get("window_target_km"),
            "progress_pct": stats.get("progress_pct"),
            "energy_kwh": stats.get("energy_kwh", 0.0),
            "fuel_l": stats.get("fuel_l", 0.0),
        }
        if self._spec.mode == "hev":
            attrs["electric_consumption_kwh_100km"] = stats.get("electric_kwh_100km")
        return attrs


@dataclass(frozen=True)
class _ChargingStatsSpec:
    """Descriptor for a periodic charging energy statistics sensor."""

    key: str
    period: str
    icon: str


_CHARGING_STATS_SPECS: tuple[_ChargingStatsSpec, ...] = (
    _ChargingStatsSpec("charging_energy_today", "today", "mdi:calendar-today"),
    _ChargingStatsSpec("charging_energy_month", "month", "mdi:calendar-month"),
    _ChargingStatsSpec("charging_energy_year", "year", "mdi:calendar"),
    _ChargingStatsSpec("charging_energy_from_start", "from_start", "mdi:ev-plug-type2"),
)


class LepasChargingStatsSensor(LepasEntity, SensorEntity):
    """Periodic charging energy sensor backed by ChargingStatsTracker."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL
    _attr_suggested_display_precision = 2

    def __init__(self, coord, spec: _ChargingStatsSpec) -> None:
        super().__init__(
            coord,
            f"Lepas {spec.key}",
            spec.key,
            object_id=f"{ID_PREFIX}_{spec.key}",
            entity_id_format=ENTITY_ID_FORMAT,
            translation_key=spec.key,
        )
        self._spec = spec
        self._attr_icon = spec.icon

    def _stats(self) -> dict[str, object]:
        return self.coordinator.charging_stats(self._spec.period)

    @property
    def native_value(self) -> float:
        val = self._stats().get("total_kwh", 0.0)
        return float(val) if val is not None else 0.0

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        stats = self._stats()
        attrs: dict[str, object] = {
            "home_kwh": stats.get("home_kwh", 0.0),
            "away_kwh": stats.get("away_kwh", 0.0),
            "sessions_count": stats.get("sessions_count", 0),
            "period_key": stats.get("period_key"),
        }
        if self._spec.period == "today":
            attrs["daily_series"] = stats.get("daily_series", [])
        elif self._spec.period == "year":
            attrs["monthly_series"] = stats.get("monthly_series", [])
        return attrs

