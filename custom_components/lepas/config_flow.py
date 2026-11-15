"""Config flow Lepas Connect — login con username (email o telefono) + password."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    DOMAIN, CONF_EMAIL, CONF_PIN, CONF_VIN, CONF_TUSERID,
    CONF_PHONE, CONF_AREA_CODE, DEFAULT_AREA_CODE,
    CONF_PASSWORD, CONF_LOGIN_METHOD, LOGIN_METHOD_PASSWORD,
    CONF_LANGUAGE, DEFAULT_LANGUAGE, LANGUAGES,
    CONF_BFF, CONF_TSP_HOST, CONF_CERTS_SRC, CONF_CHANNEL_ID,
    CONF_CAR_MQTT_HOST, CONF_CAR_MQTT_PORT, DEFAULTS,
    CONF_TENANT_CODE, CONF_COUNTRY_ID,
    CONF_PRESET, PRESETS, DEFAULT_PRESET,
    PRESET_LEPAS_EU, PRESET_CHERY_EU, PRESET_CUSTOM,
    CONF_POLL_NORMAL, CONF_POLL_CHARGING,
    DEFAULT_POLL_NORMAL_MIN, DEFAULT_POLL_CHARGING_MIN,
    CONF_VEHICLE_NAME,
)

_LOGGER = logging.getLogger(__name__)

_CORE = os.path.join(os.path.dirname(__file__), "core")


def _clear_pin_lockout(hass: HomeAssistant, entry_id: str) -> None:
    """Azzera anti-lockout PIN + taskId in cache del veicolo interessato."""
    coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
    if coordinator is not None:
        coordinator.ctx.reset_pin_lockout()


def _pending_token_path(hass: HomeAssistant) -> str:
    """Path temporaneo dove conia il token finché non si conosce il VIN."""
    return hass.config.path(f"{DOMAIN}_pending_token.json")


def _reason_line(detail: str | None) -> str:
    """Riga col motivo del fallimento, mostrata sotto il form (vuota se non c'è)."""
    detail = (detail or "").strip()
    return f"\n\n⚠️ Motivo: {detail}" if detail else ""


_ACCESSO_INTERNAZIONALE = "00"
_MAX_CIFRE_PREFISSO = 3


def _normalizza_telefono(numero: str | None, prefisso: str | None) -> tuple[str, str]:
    """Ripulisce numero e prefisso. Ritorna ("", "") se non validi."""
    solo_cifre = lambda s: "".join(ch for ch in str(s or "") if ch.isdigit())

    scritto = str(prefisso or "").strip()
    if not scritto:
        pref = DEFAULT_AREA_CODE
    else:
        pref = solo_cifre(scritto).lstrip("0")
        if not 1 <= len(pref) <= _MAX_CIFRE_PREFISSO:
            return "", ""

    grezzo = str(numero or "").strip()
    num = solo_cifre(grezzo)
    internazionale = grezzo.startswith("+") or num.startswith(_ACCESSO_INTERNAZIONALE)
    if num.startswith(_ACCESSO_INTERNAZIONALE):
        num = num[len(_ACCESSO_INTERNAZIONALE):]
    if internazionale and num.startswith(pref):
        num = num[len(pref):]

    num = num.lstrip("0")
    if not 6 <= len(num) <= 15 - len(pref):
        return "", ""
    return num, pref


def _ctx_del_flow(hass: HomeAssistant, data: dict, token_path: str | None = None):
    """CoreCtx per i passi del config flow."""
    from .core.context import CoreCtx

    return CoreCtx(
        vin=data.get(CONF_VIN, ""),
        tuserid=data.get(CONF_TUSERID, ""),
        pin=data.get(CONF_PIN, ""),
        email=data.get(CONF_EMAIL, ""),
        phone=data.get(CONF_PHONE, ""),
        area_code=str(data.get(CONF_AREA_CODE, DEFAULT_AREA_CODE) or DEFAULT_AREA_CODE),
        token_path=token_path or _pending_token_path(hass),
        src_dir=_CORE,
        tsp_host=data.get(CONF_TSP_HOST, DEFAULTS[CONF_TSP_HOST]),
        bff=data.get(CONF_BFF, DEFAULTS[CONF_BFF]),
        channel_id=str(data.get(CONF_CHANNEL_ID, DEFAULTS[CONF_CHANNEL_ID])),
        tenant_code=str(data.get(CONF_TENANT_CODE, DEFAULTS[CONF_TENANT_CODE])),
        country_id=str(data.get(CONF_COUNTRY_ID, DEFAULTS[CONF_COUNTRY_ID])),
        language=str(data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE),
    )


def _mint_password(hass: HomeAssistant, data: dict, password: str) -> tuple[bool, str]:
    """Conia il token con username+password (executor) → core.session.login_with_password."""
    from .core import session as SESSION
    return SESSION.login_with_password(_ctx_del_flow(hass, data), password)


def _discover(hass: HomeAssistant, data: dict) -> tuple[bool, str, list[str], str]:
    """Scoperta veicoli post-login."""
    try:
        import requests
        from .core import lepas_auth as A
        from .core import wake
        ctx = _ctx_del_flow(hass, data, token_path=_pending_token_path(hass))
        _ut, tu = wake._bff_login(ctx)
        if not tu:
            return False, "", [], "login backend non riuscito"
        access = wake._access_token(ctx)
        headers = A.headers_post("/tsp/v1/app/vmc/queryList", ctx=ctx, extra={
            "Authorization": f"Bearer {access}",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json, text/plain, */*"})
        r = requests.post(ctx.bff + "/tsp/v1/app/vmc/queryList",
                          data=json.dumps({}), headers=headers, timeout=25)
        j = r.json()
        lst = j.get("data")
        vins: list[str] = []
        if isinstance(lst, list):
            for v in lst:
                if isinstance(v, dict) and v.get("vin"):
                    vins.append(str(v["vin"]))
        return True, str(tu), vins, ("ok" if vins else "nessun veicolo trovato")
    except Exception as e:
        return False, "", [], f"errore scoperta veicoli: {type(e).__name__}"


def _finalize_token(hass: HomeAssistant, vin: str) -> bool:
    """Sposta il token 'pending' nella token-path per-VIN definitiva."""
    pend = _pending_token_path(hass)
    dest = hass.config.path(f"{DOMAIN}_{vin}_token.json")
    try:
        if os.path.isfile(pend):
            os.replace(pend, dest)
        return os.path.isfile(dest)
    except OSError as e:
        _LOGGER.error("Lepas: impossibile spostare il token in %s: %s", dest, e)
        return False


def _cleanup_pending(hass: HomeAssistant) -> None:
    """Rimuove un eventuale *_pending_token.json orfano."""
    pend = _pending_token_path(hass)
    try:
        if os.path.isfile(pend):
            os.remove(pend)
    except OSError as e:
        _LOGGER.debug("Lepas: cleanup pending token fallito: %s", e)


class LepasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Gestisce il config flow dell'integrazione Lepas Connect."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._tuserid: str = ""
        self._vins: list[str] = []
        self._reauth_reason: str = ""
        self._pending_login_step: str = ""
        self._pending_password: str = ""

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "LepasOptionsFlow":
        return LepasOptionsFlow(config_entry)

    def _region_fields(self) -> dict:
        """Preset di regione/marchio e lingua di comunicazione."""
        return {
            vol.Optional(CONF_PRESET, default=DEFAULT_PRESET): SelectSelector(
                SelectSelectorConfig(
                    mode=SelectSelectorMode.DROPDOWN,
                    options=[
                        SelectOptionDict(value=PRESET_LEPAS_EU,
                                         label="Lepas — Europe"),
                        SelectOptionDict(value=PRESET_CHERY_EU,
                                         label="Chery — Europe"),
                        SelectOptionDict(value=PRESET_CUSTOM,
                                         label="Custom / other region (next step)"),
                    ],
                )
            ),
            vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): SelectSelector(
                SelectSelectorConfig(
                    mode=SelectSelectorMode.DROPDOWN,
                    options=[SelectOptionDict(value=v, label=lbl) for v, lbl in LANGUAGES.items()],
                )
            ),
        }

    def _custom_region_schema(self) -> vol.Schema:
        """Parametri tecnici di connessione per regioni o marchi non coperti da preset."""
        return vol.Schema({
            vol.Optional(CONF_BFF, default=DEFAULTS[CONF_BFF]): str,
            vol.Optional(CONF_TENANT_CODE, default=DEFAULTS[CONF_TENANT_CODE]): str,
            vol.Optional(CONF_COUNTRY_ID, default=DEFAULTS[CONF_COUNTRY_ID]): str,
            vol.Optional(CONF_CHANNEL_ID, default=DEFAULTS[CONF_CHANNEL_ID]): str,
            vol.Optional(CONF_TSP_HOST, default=DEFAULTS[CONF_TSP_HOST]): str,
            vol.Optional(CONF_CAR_MQTT_HOST, default=DEFAULTS[CONF_CAR_MQTT_HOST]): str,
            vol.Optional(CONF_CAR_MQTT_PORT, default=DEFAULTS[CONF_CAR_MQTT_PORT]): vol.Coerce(int),
            vol.Optional(CONF_CERTS_SRC, default=""): str,
        })

    def _password_schema(self) -> vol.Schema:
        return vol.Schema({
            vol.Required(CONF_EMAIL): str,
            vol.Optional(CONF_AREA_CODE, default=DEFAULT_AREA_CODE): str,
            vol.Required(CONF_PIN): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Required(CONF_PASSWORD): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            **self._region_fields(),
        })

    @staticmethod
    def _apply_preset(data: dict) -> None:
        """Applica i valori del preset e rimuove CONF_PRESET dai dati."""
        preset = data.pop(CONF_PRESET, DEFAULT_PRESET)
        values = PRESETS.get(preset)
        if values:
            data.update(values)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Punto d'ingresso: login con password."""
        return await self.async_step_login_password(user_input)

    async def _complete_password_login(
        self,
        password: str,
        step_id: str,
        schema: vol.Schema,
        user_input: dict[str, Any],
    ):
        """Conia il token con grant ROPC e scopre il veicolo."""
        ok, msg = await self.hass.async_add_executor_job(
            _mint_password, self.hass, self._data, password)
        if ok:
            d_ok, tu, vins, detail = await self.hass.async_add_executor_job(
                _discover, self.hass, self._data)
            if not d_ok or not vins:
                await self.hass.async_add_executor_job(_cleanup_pending, self.hass)
                self._pending_password = ""
                _LOGGER.warning("Lepas: scoperta veicolo (password) fallita: %s", detail)
                reason = _reason_line(detail)
                if step_id == "custom_region":
                    err_schema = self.add_suggested_values_to_schema(
                        self._custom_region_schema(),
                        {k: v for k, v in user_input.items() if k not in (CONF_PIN, CONF_PASSWORD)})
                    return self.async_show_form(
                        step_id="custom_region",
                        data_schema=err_schema,
                        errors={"base": "no_vehicle"},
                        description_placeholders={"reason": reason},
                    )
                err_schema = self.add_suggested_values_to_schema(
                    schema, {k: v for k, v in user_input.items() if k not in (CONF_PIN, CONF_PASSWORD)})
                return self.async_show_form(
                    step_id=step_id,
                    data_schema=err_schema,
                    errors={"base": "no_vehicle"},
                    description_placeholders={"reason": reason},
                )
            self._pending_password = ""
            self._tuserid = tu
            self._vins = vins
            self._data[CONF_LOGIN_METHOD] = LOGIN_METHOD_PASSWORD
            if len(vins) == 1:
                return await self._create_entry(vins[0])
            return await self.async_step_select_vehicle()

        await self.hass.async_add_executor_job(_cleanup_pending, self.hass)
        self._pending_password = ""
        _LOGGER.warning("Lepas: login password fallito: %s", msg)
        reason = _reason_line(msg)
        if step_id == "custom_region":
            suggested = {k: v for k, v in self._data.items() if k not in (CONF_PIN, CONF_PASSWORD)}
            err_schema = self.add_suggested_values_to_schema(self._password_schema(), suggested)
            return self.async_show_form(
                step_id="login_password",
                data_schema=err_schema,
                errors={"base": "password_invalid"},
                description_placeholders={"reason": reason},
            )
        err_schema = self.add_suggested_values_to_schema(
            schema, {k: v for k, v in user_input.items() if k not in (CONF_PIN, CONF_PASSWORD)})
        return self.async_show_form(
            step_id=step_id,
            data_schema=err_schema,
            errors={"base": "password_invalid"},
            description_placeholders={"reason": reason},
        )

    async def async_step_login_password(self, user_input: dict[str, Any] | None = None):
        """Login con e-mail o telefono + password (ROPC)."""
        schema = self._password_schema()
        if user_input is not None:
            val = str(user_input.get(CONF_EMAIL) or "").strip()
            area_code = str(user_input.get(CONF_AREA_CODE) or DEFAULT_AREA_CODE).strip()
            password = str(user_input.get(CONF_PASSWORD) or "")
            self._pending_password = password

            suggested = {k: v for k, v in user_input.items() if k not in (CONF_PIN, CONF_PASSWORD)}

            if "@" in val:
                local, _, domain = val.partition("@")
                if not local or not domain or "." not in domain or domain.startswith(".") or domain.endswith(".") or " " in val:
                    self._pending_password = ""
                    return self.async_show_form(
                        step_id="login_password",
                        data_schema=self.add_suggested_values_to_schema(schema, suggested),
                        errors={"base": "email_invalid"},
                        description_placeholders={"reason": ""},
                    )
                self._data[CONF_EMAIL] = val
                self._data[CONF_PHONE] = ""
            else:
                numero, area = _normalizza_telefono(val, area_code)
                if not numero:
                    self._pending_password = ""
                    return self.async_show_form(
                        step_id="login_password",
                        data_schema=self.add_suggested_values_to_schema(schema, suggested),
                        errors={"base": "phone_invalid"},
                        description_placeholders={"reason": ""},
                    )
                self._data[CONF_PHONE] = numero
                self._data[CONF_AREA_CODE] = area
                self._data[CONF_EMAIL] = ""

            self._data.update({
                k: v for k, v in user_input.items()
                if k not in (CONF_PASSWORD, CONF_EMAIL, CONF_PHONE, CONF_AREA_CODE)
            })

            preset = user_input.get(CONF_PRESET, DEFAULT_PRESET)
            if preset == PRESET_CUSTOM:
                self._pending_login_step = "login_password"
                return await self.async_step_custom_region()
            self._apply_preset(self._data)
            return await self._complete_password_login(password, "login_password", schema, user_input)

        return self.async_show_form(step_id="login_password", data_schema=schema,
                                    description_placeholders={"reason": ""})

    async def async_step_custom_region(self, user_input: dict[str, Any] | None = None):
        """Configurazione parametri tecnici per regioni o marchi personalizzati."""
        schema = self._custom_region_schema()
        if user_input is not None:
            self._data.update(user_input)
            self._data.pop(CONF_PRESET, None)
            pwd = self._pending_password
            return await self._complete_password_login(
                pwd, "custom_region", schema, user_input
            )

        custom_keys = (
            CONF_BFF,
            CONF_TENANT_CODE,
            CONF_COUNTRY_ID,
            CONF_CHANNEL_ID,
            CONF_TSP_HOST,
            CONF_CAR_MQTT_HOST,
            CONF_CAR_MQTT_PORT,
            CONF_CERTS_SRC,
        )
        prefill = {k: self._data[k] for k in custom_keys if k in self._data}
        if prefill:
            schema = self.add_suggested_values_to_schema(schema, prefill)
        return self.async_show_form(
            step_id="custom_region",
            data_schema=schema,
            description_placeholders={"reason": ""},
        )

    async def async_step_select_vehicle(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return await self._create_entry(user_input[CONF_VIN])
        schema = vol.Schema({vol.Required(CONF_VIN): vol.In(self._vins)})
        return self.async_show_form(step_id="select_vehicle", data_schema=schema)

    async def _create_entry(self, vin: str):
        await self.async_set_unique_id(vin)
        try:
            self._abort_if_unique_id_configured()
        except AbortFlow:
            await self.hass.async_add_executor_job(_cleanup_pending, self.hass)
            self._pending_password = ""
            raise
        self._data[CONF_VIN] = vin
        self._data[CONF_TUSERID] = self._tuserid
        ok = await self.hass.async_add_executor_job(_finalize_token, self.hass, vin)
        if not ok:
            await self.hass.async_add_executor_job(_cleanup_pending, self.hass)
            self._pending_password = ""
            return self.async_abort(reason="token_move_failed")
        self._pending_password = ""
        return self.async_create_entry(title=f"Lepas ({vin})", data=self._data)

    def _entry_da_riconfigurare(self):
        return self.hass.config_entries.async_get_entry(self.context["entry_id"])

    def _applica_riconfigurazione(self, entry, dati: dict):
        """Scrive i dati nuovi e ricarica l'integrazione."""
        from homeassistant.helpers import issue_registry as ir
        ir.async_delete_issue(self.hass, DOMAIN, f"pin_wrong_{entry.entry_id}")
        _clear_pin_lockout(self.hass, entry.entry_id)
        return self.async_update_reload_and_abort(entry, data=dati)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Menu di «Configura»: cosa si vuole correggere."""
        entry = self._entry_da_riconfigurare()
        if entry is None:
            return self.async_abort(reason="reconfigure_no_entry")
        return self.async_show_menu(
            step_id="reconfigure",
            menu_options=["reconfigure_pin"],
        )

    async def async_step_reconfigure_pin(self, user_input: dict[str, Any] | None = None):
        """Cambia il PIN a 4 cifre dei comandi remoti."""
        entry = self._entry_da_riconfigurare()
        errors: dict[str, str] = {}
        if entry is None:
            return self.async_abort(reason="reconfigure_no_entry")
        if user_input is not None:
            new_pin = (user_input.get(CONF_PIN) or "").strip()
            if not new_pin:
                errors["base"] = "pin_required"
            else:
                return self._applica_riconfigurazione(
                    entry, {**entry.data, CONF_PIN: new_pin})
        return self.async_show_form(
            step_id="reconfigure_pin", errors=errors,
            data_schema=vol.Schema({
                vol.Required(CONF_PIN): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            }))

    async def async_step_reauth(self, entry_data: dict[str, Any] | None = None):
        """Punto d'ingresso della reauth (HA mostra la card "Riautentica")."""
        self._reauth_reason = ""
        return await self.async_step_reauth_confirm()

    def _reauth_targets(self):
        """(entry, coordinator) del veicolo da riautenticare, (None, None) se spariti."""
        entry_id = self.context.get("entry_id", "")
        return (self.hass.config_entries.async_get_entry(entry_id),
                self.hass.data.get(DOMAIN, {}).get(entry_id))

    @staticmethod
    def _login_identity(entry) -> str:
        """Identità per i dialoghi di riautenticazione (mascherata)."""
        from .core import mask
        phone = entry.data.get(CONF_PHONE, "")
        if phone:
            return mask.numero_con_prefisso(
                phone, entry.data.get(CONF_AREA_CODE, DEFAULT_AREA_CODE))
        return mask.indirizzo_email(entry.data.get(CONF_EMAIL, ""))

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None):
        """Punto d'ingresso della riautenticazione: instrada sempre a reauth_password."""
        entry, coordinator = self._reauth_targets()
        if entry is None or coordinator is None:
            return self.async_abort(reason="reauth_no_entry")
        return await self.async_step_reauth_password()

    async def async_step_reauth_password(self, user_input: dict[str, Any] | None = None):
        """Reauth: re-inserire la password conia un token nuovo."""
        entry, coordinator = self._reauth_targets()
        if entry is None or coordinator is None:
            return self.async_abort(reason="reauth_no_entry")
        errors: dict[str, str] = {}
        if user_input is not None:
            password = (user_input.get(CONF_PASSWORD) or "").strip()
            if not password:
                errors["base"] = "password_required"
            else:
                ok, detail = await self.hass.async_add_executor_job(
                    coordinator._login_with_password, password)
                if ok:
                    new_data = {**entry.data, CONF_LOGIN_METHOD: LOGIN_METHOD_PASSWORD}
                    return self.async_update_reload_and_abort(entry, data=new_data)
                self._reauth_reason = _reason_line(detail)
                errors["base"] = "password_invalid"
                _LOGGER.warning("Lepas: reauth password fallita: %s", detail)
        return self.async_show_form(
            step_id="reauth_password",
            data_schema=vol.Schema({
                vol.Required(CONF_PASSWORD): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            }),
            errors=errors,
            description_placeholders={"email": self._login_identity(entry),
                                      "reason": self._reauth_reason})


class LepasOptionsFlow(config_entries.OptionsFlow):
    """Opzioni: i due intervalli (minuti) del poll telemetria. 0 = disattiva."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict | None = None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        opt = self._entry.options or {}
        cur_name = opt.get(CONF_VEHICLE_NAME) or self._entry.data.get(CONF_VEHICLE_NAME) or ""
        schema = vol.Schema({
            vol.Optional(
                CONF_POLL_NORMAL,
                default=opt.get(CONF_POLL_NORMAL, DEFAULT_POLL_NORMAL_MIN),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=1440)),
            vol.Optional(
                CONF_POLL_CHARGING,
                default=opt.get(CONF_POLL_CHARGING, DEFAULT_POLL_CHARGING_MIN),
            ): vol.All(vol.Coerce(int), vol.Range(min=0, max=1440)),
            vol.Optional(
                CONF_VEHICLE_NAME,
                description={"suggested_value": cur_name},
            ): str,
        })
        return self.async_show_form(step_id="init", data_schema=schema)
