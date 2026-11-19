"""Custom component Lepas Connect — bootstrap."""
from __future__ import annotations

from datetime import datetime, time as dt_time
import logging
import os
import re

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError

from .const import (
    CONF_BFF,
    CONF_CHANNEL_ID,
    CONF_TENANT_CODE,
    DEFAULTS,
    DOMAIN,
    PLATFORMS,
    PRESET_LEPAS_EU,
    PRESETS,
)
from .scheduler import parse_days_input

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_QUICK_DEPARTURE = "set_quick_departure"
SERVICE_SET_CHARGING_SCHEDULE = "set_charging_schedule"
SERVICE_SET_DEPARTURE_CLIMATE_EXTRAS = "set_departure_climate_extras"
SERVICE_SET_BATTERY_PACK_HEAT = "set_battery_pack_heat"
SERVICE_DISABLE_DEPARTURE_SCHEDULE = "disable_departure_schedule"

_QUICK_DEPARTURE_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): object,
        vol.Optional("time"): object,
        vol.Optional("enabled"): object,
        vol.Optional("sync_charging"): object,
        vol.Optional("apply_native"): object,
    }
)

_CHARGING_SCHEDULE_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): object,
        vol.Optional("start_time"): object,
        vol.Optional("duration_hours"): object,
        vol.Optional("days"): object,
        vol.Optional("apply"): object,
    }
)

_DEPARTURE_CLIMATE_EXTRAS_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): object,
        vol.Required("extras"): object,
    }
)

_BATTERY_PACK_HEAT_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): object,
        vol.Optional("enabled"): object,
        vol.Optional("time"): object,
        vol.Optional("sync_to_departure"): object,
    }
)

_DISABLE_DEPARTURE_SCHEMA = vol.Schema(
    {
        vol.Optional("entry_id"): object,
    }
)

_CARD_PATH = f"/{DOMAIN}_card"
_CARD_URL = f"{_CARD_PATH}/lepas-card.js"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve e auto-carica la card Lovelace, UNA volta per istanza di Home Assistant.

    Guardato con `hass.data[f"{DOMAIN}_card"]` perché con due veicoli configurati
    `async_setup_entry` gira due volte, e registrare lo stesso static path / URL JS due volte
    fa rumore (o errore). Se il frontend non è caricato (headless) la card resta comunque
    usabile aggiungendo la risorsa a mano — quindi il fallimento non deve rompere il setup."""
    if getattr(hass, "http", None) is None or hass.data.get(f"{DOMAIN}_card"):
        return
    from homeassistant.components.http import StaticPathConfig

    lovelace_dir = os.path.join(os.path.dirname(__file__), "lovelace")
    await hass.http.async_register_static_paths(
        [StaticPathConfig(_CARD_PATH, lovelace_dir, False)]
    )
    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.loader import async_get_integration

        # La query di versione invalida la cache del browser sulla card a ogni aggiornamento:
        # senza, si continua a vedere la VECCHIA card (il modulo è cachato duro dal frontend).
        try:
            version = (await async_get_integration(hass, DOMAIN)).version
        except Exception:  # noqa: BLE001
            version = ""
        add_extra_js_url(hass, f"{_CARD_URL}?v={version}" if version else _CARD_URL)
    except Exception:  # noqa: BLE001 — frontend non caricato (headless) → card usabile a mano
        pass
    hass.data[f"{DOMAIN}_card"] = True

# P2-2: il "cuore di protocollo" è ora il sotto-pacchetto `.core`, importato normalmente
# (`from .core import commands`). Sono spariti — e con loro un'intera classe di problemi:
#
#   * `sys.path.insert(core/)`: inquinava il path dell'intero processo Home Assistant,
#     esponendo nomi generici (`commands`, `session`, `wake`) alle collisioni con altre
#     integrazioni;
#   * la cancellazione del `__pycache__` a ogni import e il ricaricamento da disco a ogni
#     setup: servivano solo perché i nomi nudi rendevano ambiguo QUALE modulo si stesse
#     caricando. Con gli import di pacchetto è Python a garantirlo, e l'aggiornamento
#     HACS invalida la cache da sé (i .pyc sono indicizzati per percorso completo).
#
# Effetto collaterale utile: i logger dei moduli core/ ora rispondono a `manifest.loggers`.


async def _async_migrate_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Porta gli entity_id gia' registrati ai nomi inglesi, una volta sola e in silenzio.

    Perche' serve, e perche' il codice da solo non basta. Home Assistant ritrova un'entita'
    dal suo `unique_id` e riusa l'`entity_id` che ha gia' in registro: l'`entity_id` che il
    codice calcola vale solo alla PRIMA registrazione. Senza questa funzione chi e' gia'
    installato terrebbe i vecchi ID per sempre e solo le installazioni nuove
    avrebbero i nomi inglesi - il peggiore dei due mondi, perche' una issue aperta da due
    utenti diversi parlerebbe di due entita' con nomi diversi.

    Cosa NON si perde: lo storico. Rinominando attraverso il registro, il recorder sposta da
    solo le statistiche a lungo termine e la cronologia degli stati (vedi
    `recorder/entity_registry.py`). Grafici e dashboard Energia continuano.

    Cosa si perde comunque, e nessuna migrazione puo' evitarlo: i riferimenti scritti a mano
    in automazioni, script e dashboard. Sono elencati nelle note di rilascio con la tabella
    vecchio -> nuovo.

    L'unico modo in cui il recorder fallisce e' silenzioso: se l'`entity_id` di destinazione
    esiste gia', logga "Cannot migrate history ... already in use" e lo storico resta
    indietro. Per questo qui si salta invece di sovrascrivere, e lo si dice a WARNING.
    """
    from homeassistant.helpers import entity_registry as er

    from .naming import ENGLISH_KEYS, ID_PREFIX

    reg = er.async_get(hass)
    esistenti = {e.entity_id for e in reg.entities.values()}
    fatti = 0
    for voce in er.async_entries_for_config_entry(reg, entry.entry_id):
        if voce.unique_id and any(voce.unique_id.endswith(sfx) for sfx in ("_otp_code", "_otp_confirm", "_otp_request")):
            try:
                reg.async_remove(voce.entity_id)
                esistenti.discard(voce.entity_id)
            except Exception:
                pass
            continue
        piattaforma, _, object_id = voce.entity_id.partition(".")
        old_key = None
        for prefix in (f"{DOMAIN}_",):
            if object_id.startswith(prefix):
                old_key = object_id[len(prefix):]
                break
        if old_key is None:
            continue
        inglese = ENGLISH_KEYS.get(old_key)
        if inglese is None:
            continue
        nuovo = f"{piattaforma}.{ID_PREFIX}_{inglese}"
        if nuovo == voce.entity_id:
            continue
        if nuovo in esistenti:
            _LOGGER.warning(
                "Lepas: %s non rinominata in %s perche' quel nome e' gia' in uso. "
                "Lo storico resterebbe indietro, quindi non si tocca niente.",
                voce.entity_id, nuovo)
            continue
        reg.async_update_entity(voce.entity_id, new_entity_id=nuovo)
        esistenti.discard(voce.entity_id)
        esistenti.add(nuovo)
        fatti += 1
    if not fatti:
        return
    _LOGGER.info(
        "Lepas: %d entita' rinominate ai nomi inglesi. Storico e statistiche seguono; "
        "i riferimenti scritti a mano in automazioni e dashboard vanno aggiornati.", fatti)


async def async_cleanup_disabled_entities(hass: HomeAssistant, entry: ConfigEntry) -> int:
    """Rimuove dal registro entità quelle confermate disabilitate per questo veicolo."""
    try:
        from homeassistant.helpers import entity_registry as er

        from .const import CONF_VIN, DATA_VEHICLE_FEATURES, ENTITY_FEATURE_MAP
        from .naming import ID_PREFIX

        vf = entry.data.get(DATA_VEHICLE_FEATURES) or {}
        if not isinstance(vf, dict) or not vf:
            return 0
        vin = str(entry.data.get(CONF_VIN, "")).strip()
        if not vin:
            return 0
        reg = er.async_get(hass)
        removed = 0
        p_vins = (f"{vin}_", f"{vin.upper()}_", f"{vin.lower()}_")
        p_prefs = (f"{ID_PREFIX}_{vin}_", f"{ID_PREFIX}_{vin.upper()}_", f"{ID_PREFIX}_{vin.lower()}_")
        for ent in list(er.async_entries_for_config_entry(reg, entry.entry_id)):
            uid = ent.unique_id
            suffix = None
            for p in p_prefs:
                if uid.startswith(p):
                    suffix = uid[len(p):]
                    break
            if suffix is None:
                for p in p_vins:
                    if uid.startswith(p):
                        suffix = uid[len(p):]
                        break
            if suffix is None:
                continue
            feat = ENTITY_FEATURE_MAP.get((ent.domain, suffix))
            if feat and vf.get(feat) is False:
                reg.async_remove(ent.entity_id)
                removed += 1
        return removed
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Lepas: errore cleanup entita' disabilitate: %s", err)
        return 0


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migra i config entry da versioni precedenti allo schema corrente."""
    if config_entry.version > 2:
        _LOGGER.warning(
            "Lepas: impossibile migrare config entry da versione futura %s",
            config_entry.version,
        )
        return False

    if config_entry.version == 1:
        data = dict(config_entry.data)
        bff = str(data.get(CONF_BFF) or DEFAULTS[CONF_BFF]).rstrip("/")
        tenant = str(data.get(CONF_TENANT_CODE) or DEFAULTS[CONF_TENANT_CODE])
        channel = str(data.get(CONF_CHANNEL_ID) or "")
        is_lepas_eu = (
            bff == DEFAULTS[CONF_BFF].rstrip("/")
            and tenant == DEFAULTS[CONF_TENANT_CODE]
        )
        if is_lepas_eu and channel in ("", "1"):
            new_channel = PRESETS[PRESET_LEPAS_EU][CONF_CHANNEL_ID]
            data[CONF_CHANNEL_ID] = new_channel
            _LOGGER.info(
                "Lepas: config entry migrata a v2 (channel_id %s -> %s)",
                channel or "<default>",
                new_channel,
            )
        hass.config_entries.async_update_entry(config_entry, data=data, version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Inizializza l'integrazione da un config entry."""
    from .coordinator import LepasCoordinator

    # PRIMA di costruire qualunque entita': il rename tocca il registro, e il registro va
    # sistemato mentre nessuna entita' e' ancora montata.
    try:
        await _async_migrate_entity_ids(hass, entry)
    except Exception as err:
        _LOGGER.warning("Lepas: errore migrazione entita': %s", err)

    try:
        await async_cleanup_disabled_entities(hass, entry)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Lepas: errore cleanup entita' disabilitate: %s", err)

    coordinator = LepasCoordinator(hass, entry)

    # FASE 3c: i cert mutual-TLS devono esserci PRIMA di connettere l'MQTT auto.
    ok, detail = await coordinator.async_provision_certs()
    if not ok:
        raise ConfigEntryNotReady(detail)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Card Lovelace: registrata una volta sola (no-op dal secondo veicolo in poi).
    await _async_register_card(hass)

    # Il monitor diagnostico va armato PRIMA del primo controllo sessione. È quel
    # controllo a decidere se aprire la riautenticazione, ed è esattamente l'evento che si
    # vuole rileggere dopo un riavvio. Armandolo dopo (com'era) il controllo d'avvio non
    # veniva mai registrato: verificato su 5 riavvii consecutivi, nel file diagnostico
    # restava un buco proprio nel momento più interessante.
    await coordinator.async_setup_diag()

    # stato sessione iniziale + avvio connessione MQTT all'auto
    await coordinator.async_check_session()
    # [H4] se QUALSIASI passo dell'avvio fallisce (connect MQTT, avvio timer, forward
    #      delle piattaforme) ripuliamo TUTTE le risorse già avviate — client paho e
    #      timer keepalive/poll — e togliamo il coordinator da hass.data, così non
    #      restano thread/timer orfani; poi rilanciamo → HA ritenta il setup.
    try:
        await coordinator.async_start()
        # keep-alive: refresh sessione periodico per non far scadere il token da fermi
        coordinator.async_start_keepalive()
        # poll telemetria periodico (sveglia + lettura); intervalli dalle opzioni
        coordinator.async_start_telemetry_poll()
        # battito di rilevamento marcia (sola lettura): fa partire il refresh automatico durante un
        # viaggio. No-op se l'interruttore "Aggiornamento automatico" è spento (lo riavvia lo switch).
        coordinator.async_start_drive_watch()
        coordinator.async_start_departure_scheduler()
        # ricarica l'entry quando l'utente cambia le opzioni (es. intervalli di poll)
        entry.async_on_unload(entry.add_update_listener(_async_options_updated))
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _async_register_services(hass)
        # backfill identità veicolo (nome device dinamico) per gli entry creati prima che il
        # config flow la salvasse: in background, così un eventuale reload avviene a setup finito.
        hass.async_create_background_task(
            coordinator.async_ensure_vehicle_identity(), "lepas_vehicle_identity")
    except Exception:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN):
            _async_unregister_services(hass)
        await hass.async_add_executor_job(coordinator.async_stop)
        raise
    return True


def _parse_time_minutes(raw: object) -> int:
    if isinstance(raw, datetime):
        raise ServiceValidationError(f"Invalid time value: {raw!r}")
    if isinstance(raw, dt_time):
        return raw.hour * 60 + raw.minute
    if isinstance(raw, str):
        match = re.fullmatch(r"(\d{1,2}):(\d{2})(?::(\d{2}))?", raw.strip())
        if not match:
            raise ServiceValidationError(f"Invalid time format (HH:MM or HH:MM:SS): {raw!r}")
        hh, mm, ss = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)
        if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
            raise ServiceValidationError(f"Time out of range: {raw!r}")
        return hh * 60 + mm
    raise ServiceValidationError(f"Unsupported time type: {type(raw).__name__}")


def _parse_bool(raw: object, field: str) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        norm = raw.strip().lower()
        if norm in ("true", "on", "yes", "1"):
            return True
        if norm in ("false", "off", "no", "0"):
            return False
    raise ServiceValidationError(f"Invalid boolean for {field}: {raw!r}")


def _parse_duration_hours(raw: object) -> int:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ServiceValidationError(f"duration_hours must be an integer 1..12, got {raw!r}")
    if isinstance(raw, float) and not raw.is_integer():
        raise ServiceValidationError(f"duration_hours must be an integer 1..12, got {raw!r}")
    dur = int(raw)
    if not 1 <= dur <= 12:
        raise ServiceValidationError(f"duration_hours out of range 1..12: {raw!r}")
    return dur


def _resolve_coordinator(hass: HomeAssistant, entry_id: object):
    entries = hass.data.get(DOMAIN) or {}
    if not entries:
        raise ServiceValidationError("No loaded Lepas vehicles")
    if entry_id is not None:
        if not isinstance(entry_id, str) or not entry_id.strip():
            raise ServiceValidationError(f"Invalid entry_id: {entry_id!r}")
        coord = entries.get(entry_id)
        if coord is None:
            raise ServiceValidationError(f"Unknown Lepas entry_id: {entry_id!r}")
        return coord
    if len(entries) > 1:
        raise ServiceValidationError("Multiple Lepas vehicles configured; entry_id is required")
    return next(iter(entries.values()))


def _async_register_services(hass: HomeAssistant) -> None:
    async def _handle_set_quick_departure(call: ServiceCall) -> None:
        coord = _resolve_coordinator(hass, call.data.get("entry_id"))
        minutes = _parse_time_minutes(call.data["time"]) if "time" in call.data else None
        enabled = _parse_bool(call.data["enabled"], "enabled") if "enabled" in call.data else True
        sync_charging = (
            _parse_bool(call.data["sync_charging"], "sync_charging")
            if "sync_charging" in call.data
            else None
        )
        apply_native = (
            _parse_bool(call.data["apply_native"], "apply_native")
            if "apply_native" in call.data
            else None
        )
        await coord.async_set_quick_departure(
            minutes,
            enabled=enabled,
            sync_charging=sync_charging,
            apply_native=apply_native,
        )

    async def _handle_set_charging_schedule(call: ServiceCall) -> None:
        coord = _resolve_coordinator(hass, call.data.get("entry_id"))
        start_min = _parse_time_minutes(call.data["start_time"]) if "start_time" in call.data else None
        dur_h = (
            _parse_duration_hours(call.data["duration_hours"])
            if "duration_hours" in call.data
            else None
        )
        days = None
        if "days" in call.data:
            try:
                days = parse_days_input(call.data["days"])
            except ValueError as err:
                raise ServiceValidationError(str(err)) from err
        apply_now = _parse_bool(call.data["apply"], "apply") if "apply" in call.data else True

        if apply_now:
            await coord.async_apply_charging_schedule(
                start_minutes=start_min,
                duration_hours=dur_h,
                days=days,
            )
            return

        if start_min is not None:
            coord.charge_start_minutes = start_min
        if dur_h is not None:
            coord.charge_duration_hours = dur_h
        if days is not None:
            coord.charge_days = days
        coord.notify_schedule_changed(sync_charge=False)

    async def _handle_set_departure_climate_extras(call: ServiceCall) -> None:
        coord = _resolve_coordinator(hass, call.data.get("entry_id"))
        try:
            await coord.async_set_departure_climate_extras(call.data["extras"])
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err

    async def _handle_set_battery_pack_heat(call: ServiceCall) -> None:
        coord = _resolve_coordinator(hass, call.data.get("entry_id"))
        enabled = _parse_bool(call.data["enabled"], "enabled") if "enabled" in call.data else None
        minutes = _parse_time_minutes(call.data["time"]) if "time" in call.data else None
        sync_to_dep = (
            _parse_bool(call.data["sync_to_departure"], "sync_to_departure")
            if "sync_to_departure" in call.data
            else None
        )
        if sync_to_dep is not None:
            coord.sync_battery_heat_to_departure = sync_to_dep
        if enabled is not None or (minutes is not None and coord.battery_heat_enabled):
            await coord.async_apply_battery_pack_heat(enabled=enabled, minutes=minutes)
            if sync_to_dep is True:
                coord.notify_schedule_changed(sync_battery=True)
        else:
            if minutes is not None:
                coord.battery_heat_minutes = minutes
            if minutes is not None or sync_to_dep is not None:
                coord.notify_schedule_changed(sync_battery=bool(sync_to_dep))

    async def _handle_disable_departure_schedule(call: ServiceCall) -> None:
        coord = _resolve_coordinator(hass, call.data.get("entry_id"))
        await coord.async_disable_departure_schedule()

    if not hass.services.has_service(DOMAIN, SERVICE_SET_QUICK_DEPARTURE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_QUICK_DEPARTURE,
            _handle_set_quick_departure,
            schema=_QUICK_DEPARTURE_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SET_CHARGING_SCHEDULE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_CHARGING_SCHEDULE,
            _handle_set_charging_schedule,
            schema=_CHARGING_SCHEDULE_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SET_DEPARTURE_CLIMATE_EXTRAS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_DEPARTURE_CLIMATE_EXTRAS,
            _handle_set_departure_climate_extras,
            schema=_DEPARTURE_CLIMATE_EXTRAS_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_SET_BATTERY_PACK_HEAT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_BATTERY_PACK_HEAT,
            _handle_set_battery_pack_heat,
            schema=_BATTERY_PACK_HEAT_SCHEMA,
        )
    if not hass.services.has_service(DOMAIN, SERVICE_DISABLE_DEPARTURE_SCHEDULE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_DISABLE_DEPARTURE_SCHEDULE,
            _handle_disable_departure_schedule,
            schema=_DISABLE_DEPARTURE_SCHEMA,
        )


def _async_unregister_services(hass: HomeAssistant) -> None:
    for svc in (
        SERVICE_SET_QUICK_DEPARTURE,
        SERVICE_SET_CHARGING_SCHEDULE,
        SERVICE_SET_DEPARTURE_CLIMATE_EXTRAS,
        SERVICE_SET_BATTERY_PACK_HEAT,
        SERVICE_DISABLE_DEPARTURE_SCHEDULE,
    ):
        if hass.services.has_service(DOMAIN, svc):
            hass.services.async_remove(DOMAIN, svc)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Ricarica l'entry SOLO se sono cambiate davvero le opzioni.

    `add_update_listener` scatta a ogni `async_update_entry`, anche quando a cambiare è
    `entry.data` e non le opzioni. Due conseguenze, entrambe reali:

    * il backfill dell'identità veicolo (task in background avviato dal setup) scrive in
      `entry.data` → l'entry appena avviata veniva **subito ricaricata**. Al primo avvio
      HA la caricava due volte, e se lo spegnimento arrivava mentre il reload era in volo
      il task restava appeso oltre la fase di chiusura (HA lo segnala: «Integrations
      should cancel non-critical tasks … to prevent delaying shutdown») lasciando l'entry
      in UNLOAD_IN_PROGRESS;
    * i percorsi che cambiano il PIN (Repair e riconfigura) si ricaricano **già da soli**
      in modo esplicito → il listener aggiungeva un secondo reload inutile.

    Chi ha davvero bisogno del reload è solo l'options flow (intervalli di poll, override
    del nome), che non ricarica per conto suo. Si confronta quindi con la fotografia delle
    opzioni applicate dal coordinator vivo. Se il coordinator non c'è (entry non ancora in
    `hass.data`) si ricarica, che è il comportamento prudente di prima.

    Si usa `async_schedule_reload` invece di attendere `async_reload`: il listener non
    resta appeso ad attendere il reload di se stesso, ed è HA a possedere e cancellare il
    task allo spegnimento.
    """
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is not None and dict(entry.options or {}) == coordinator.applied_options:
        return
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Scarica l'integrazione."""
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # [MED] solo se l'unload delle piattaforme è riuscito smontiamo il coordinator: se
    #       una piattaforma rifiuta l'unload (ok=False) HA considera l'entry ancora
    #       caricato → non distruggiamo il coordinator sotto entità ancora vive (stato
    #       coerente; HA ritenterà l'unload).
    if ok:
        coordinator = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if not hass.data.get(DOMAIN):
            _async_unregister_services(hass)
        if coordinator is not None:
            # async_stop è bloccante (loop_stop fa join del thread paho) → executor.
            await hass.async_add_executor_job(coordinator.async_stop)
        # P1-4/P2-6: in passato si ripulivano i segreti da `os.environ`, dove il
        # config flow li scriveva per passarli ai moduli core/. Non serve più — ed è la
        # garanzia più forte: con il contesto per-chiamata quei segreti nell'ambiente del
        # processo Home Assistant **non ci finiscono mai**, quindi non c'è nulla da
        # ripulire. (L'unico uso legittimo dell'ambiente resta quello EFFIMERO dei
        # sottoprocessi di login, che vive e muore con la singola chiamata.)
    return ok
