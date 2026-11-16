"""Config flow, riautenticazione e Repair del PIN — flusso password-only."""
from __future__ import annotations

import pytest
from homeassistant import config_entries, data_entry_flow

import fixtures as FX
from custom_components.lepas.config_flow import LepasConfigFlow
from custom_components.lepas.const import (
    CONF_AREA_CODE,
    CONF_BFF,
    CONF_CAR_MQTT_HOST,
    CONF_CAR_MQTT_PORT,
    CONF_CERTS_SRC,
    CONF_CHANNEL_ID,
    CONF_COUNTRY_ID,
    CONF_EMAIL,
    CONF_LANGUAGE,
    CONF_LOGIN_METHOD,
    CONF_PASSWORD,
    CONF_PHONE,
    CONF_PIN,
    CONF_PRESET,
    CONF_TENANT_CODE,
    CONF_TSP_HOST,
    CONF_VIN,
    DEFAULT_PRESET,
    DEFAULT_VEHICLE_NAME,
    DEFAULTS,
    DOMAIN,
    LOGIN_METHOD_PASSWORD,
    PRESET_CUSTOM,
    PRESET_LEPAS_EU,
    PRESET_CHERY_EU,
)


@pytest.fixture
def flusso_ok(monkeypatch):
    """Backend che coopera: password accettata, token coniato, un veicolo trovato."""
    from custom_components.lepas import config_flow as cf

    monkeypatch.setattr(cf, "_mint_password", lambda hass, data, password: (True, "token ok"))
    monkeypatch.setattr(cf, "_discover",
                        lambda hass, data: (True, FX.TUSERID, [FX.VIN], "ok"))
    monkeypatch.setattr(cf, "_finalize_token", lambda hass, vin: True)
    monkeypatch.setattr(cf, "_cleanup_pending", lambda hass: None)
    return cf


DATI_UTENTE = {CONF_EMAIL: FX.EMAIL, CONF_PASSWORD: "secret_password", CONF_PIN: FX.PIN}
DATI_TELEFONO = {CONF_EMAIL: FX.PHONE, CONF_AREA_CODE: FX.AREA_CODE, CONF_PASSWORD: "secret_password", CONF_PIN: FX.PIN}


async def _init_login_password(hass):
    """Init del flow utente: mostra direttamente il form 'login_password'."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["step_id"] == "login_password"
    return result


def _forza_blocco(coordinator) -> None:
    """Porta l'anti-lockout del veicolo allo stato 'bloccato', come dopo N PIN errati."""
    lockout = coordinator.ctx.lockout
    for _ in range(lockout.max_fail):
        with lockout.attempt() as tentativo:
            tentativo.fallito()
    assert lockout.is_locked(), "prerequisito: l'anti-lockout doveva essere scattato"


async def test_configurazione_completa(hass, flusso_ok):
    """Il percorso normale con email: login_password → entry creato col VIN scoperto."""
    result = await _init_login_password(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], DATI_UTENTE)
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_VIN] == FX.VIN
    assert result["data"][CONF_EMAIL] == FX.EMAIL
    assert result["data"][CONF_PHONE] == ""
    assert result["data"][CONF_LOGIN_METHOD] == LOGIN_METHOD_PASSWORD
    assert CONF_PASSWORD not in result["data"]


async def test_configurazione_via_telefono(hass, flusso_ok):
    """Login con numero di telefono e prefisso internazionale."""
    result = await _init_login_password(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], DATI_TELEFONO)
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_VIN] == FX.VIN
    assert result["data"][CONF_PHONE] == FX.PHONE
    assert result["data"][CONF_AREA_CODE] == FX.AREA_CODE
    assert result["data"][CONF_EMAIL] == ""
    assert result["data"][CONF_LOGIN_METHOD] == LOGIN_METHOD_PASSWORD
    assert CONF_PASSWORD not in result["data"]


async def test_setup_telefono_con_prefisso_popola_campi(hass, flusso_ok):
    """Setup con telefono e prefisso internazionale popola phone, area_code e svuota email."""
    result = await _init_login_password(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: "3331234567",
            CONF_AREA_CODE: "39",
            CONF_PASSWORD: "secret_password",
            CONF_PIN: FX.PIN,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PHONE] == "3331234567"
    assert result["data"][CONF_AREA_CODE] == "39"
    assert result["data"][CONF_EMAIL] == ""
    assert result["data"][CONF_LOGIN_METHOD] == LOGIN_METHOD_PASSWORD
    assert CONF_PASSWORD not in result["data"]


@pytest.mark.parametrize("valore,area,errore", [
    ("non-una-email@", "39", "email_invalid"),
    ("utente@dominio", "39", "email_invalid"),
    ("12", "39", "phone_invalid"),
    ("", "39", "phone_invalid"),
])
async def test_identita_invalida_blocca_prima_di_mint_password(hass, monkeypatch, valore, area, errore):
    """Un'identità non valida (email o telefono) blocca prima di _mint_password e non salva la password."""
    from custom_components.lepas import config_flow as cf

    chiamate_mint = []
    monkeypatch.setattr(
        cf, "_mint_password", lambda h, d, p: (chiamate_mint.append(p) or True, "ok")
    )

    result = await _init_login_password(hass)
    flow = hass.config_entries.flow._progress[result["flow_id"]]

    payload = {CONF_EMAIL: valore, CONF_AREA_CODE: area, CONF_PIN: FX.PIN}
    payload[CONF_PASSWORD] = FX.PIN
    result = await hass.config_entries.flow.async_configure(result["flow_id"], payload)
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "login_password"
    assert result["errors"]["base"] == errore
    assert len(chiamate_mint) == 0, "_mint_password non deve essere chiamata su identità invalida"
    assert flow._pending_password == "", "la password pendente deve essere azzerata"


async def test_login_password_fallito_mostra_errore(hass, monkeypatch):
    """Se _mint_password fallisce, il form torna su login_password con errore e azzera pending_password."""
    from custom_components.lepas import config_flow as cf

    pulizie = {"n": 0}
    monkeypatch.setattr(cf, "_mint_password", lambda h, d, p: (False, "credenziali errate"))
    monkeypatch.setattr(cf, "_cleanup_pending", lambda h: pulizie.__setitem__("n", pulizie["n"] + 1))

    result = await _init_login_password(hass)
    flow = hass.config_entries.flow._progress[result["flow_id"]]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], DATI_UTENTE)
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "login_password"
    assert result["errors"]["base"] == "password_invalid"
    assert "credenziali errate" in result["description_placeholders"]["reason"]
    assert pulizie["n"] == 1
    assert flow._pending_password == ""


async def test_piu_veicoli_chiede_quale(hass, flusso_ok, monkeypatch):
    """Account con più auto: si deve poter scegliere, non prendere la prima."""
    altro = "LZZBBBBBB9Z8Y7X6W"     # VIN_PLACEHOLDER: sintetico
    monkeypatch.setattr(flusso_ok, "_discover",
                        lambda hass, data: (True, FX.TUSERID, [FX.VIN, altro], "ok"))

    result = await _init_login_password(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], DATI_UTENTE)
    assert result["step_id"] == "select_vehicle"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_VIN: altro})
    assert result["data"][CONF_VIN] == altro


async def test_stesso_veicolo_non_si_configura_due_volte(hass, flusso_ok, config_entry):
    """Il VIN è l'identità univoca: un secondo entry darebbe due set di entità in conflitto."""
    result = await _init_login_password(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], DATI_UTENTE)

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_token_non_spostabile_fa_fallire_il_flow(hass, flusso_ok, monkeypatch):
    """Senza token in posizione il coordinator non potrebbe autenticarsi."""
    monkeypatch.setattr(flusso_ok, "_finalize_token", lambda hass, vin: False)

    result = await _init_login_password(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], DATI_UTENTE)

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "token_move_failed"


# ───────────────────────── riconfigurazione PIN ─────────────────────────
async def test_riconfigura_pin_azzera_sempre_il_lockout(hass, integrazione_avviata):
    """P0-2: il reset dell'anti-lockout deve avvenire ANCHE reinserendo lo STESSO PIN."""
    coord = hass.data[DOMAIN][integrazione_avviata.entry_id]
    _forza_blocco(coord)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE,
                 "entry_id": integrazione_avviata.entry_id})
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "reconfigure_pin"})
    assert result["step_id"] == "reconfigure_pin"

    await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PIN: FX.PIN})
    await hass.async_block_till_done()

    assert coord.ctx.lockout.tentativi_falliti == 0, \
        "lockout ancora attivo dopo la riconfigurazione"


async def test_form_pin_non_mostra_il_pin_attuale(hass, integrazione_avviata):
    """P1-5 (sicurezza): il PIN è una credenziale. Non deve comparire pre-riempito nel form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE,
                 "entry_id": integrazione_avviata.entry_id})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "reconfigure_pin"})

    schema = result["data_schema"].schema
    campo = next(k for k in schema if str(k) == CONF_PIN)
    assert getattr(campo, "default", None) in (None, vol_undefined()), \
        "il form ripropone il PIN attuale come default"

    selettore = schema[campo]
    assert "password" in str(selettore.config).lower()


def vol_undefined():
    import voluptuous as vol
    return vol.UNDEFINED


async def test_pin_vuoto_rifiutato(hass, integrazione_avviata):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE,
                 "entry_id": integrazione_avviata.entry_id})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "reconfigure_pin"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PIN: "   "})
    assert result["errors"]["base"] == "pin_required"


# ───────────────────────── Repair «PIN comandi errato» ─────────────────────────
async def test_repair_pin_sblocca_e_applica(hass, integrazione_avviata):
    """Il Repair deve scrivere il nuovo PIN E azzerare il blocco."""
    from custom_components.lepas import repairs

    coord = hass.data[DOMAIN][integrazione_avviata.entry_id]
    _forza_blocco(coord)

    flow = await repairs.async_create_fix_flow(
        hass, f"pin_wrong_{integrazione_avviata.entry_id}",
        {"entry_id": integrazione_avviata.entry_id})
    flow.hass = hass

    result = await flow.async_step_init()
    assert result["step_id"] == "pin"

    result = await flow.async_step_pin({CONF_PIN: "1234"})
    await hass.async_block_till_done()

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert integrazione_avviata.data[CONF_PIN] == "1234"
    coord_dopo = hass.data[DOMAIN][integrazione_avviata.entry_id]
    assert coord_dopo.ctx.lockout.tentativi_falliti == 0


async def test_repair_senza_entry_si_interrompe(hass):
    """Entry già rimosso mentre l'avviso era aperto: si abortisce senza esplodere."""
    from custom_components.lepas import repairs

    flow = await repairs.async_create_fix_flow(hass, "pin_wrong_x",
                                               {"entry_id": "non_esiste"})
    flow.hass = hass
    result = await flow.async_step_init()
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "entry_not_found"


# ───────────────────── riautenticazione con password ─────────────────────
async def _apri_reauth(hass, entry):
    """Apre la riautenticazione come fa Home Assistant quando la sessione muore."""
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=dict(entry.data),
    )


async def test_reauth_instrada_subito_a_reauth_password(hass, integrazione_avviata):
    """La riautenticazione instrada direttamente a reauth_password richiedendo la password."""
    result = await _apri_reauth(hass, integrazione_avviata)
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_password"
    keys = _schema_keys(result["data_schema"])
    assert CONF_PASSWORD in keys


async def test_reauth_password_riuscita_fa_backfill_login_method(
        hass, integrazione_avviata, monkeypatch):
    """Reauth con password corretta conia il token e aggiorna CONF_LOGIN_METHOD nell'entry."""
    coord = hass.data[DOMAIN][integrazione_avviata.entry_id]
    monkeypatch.setattr(coord, "_login_with_password",
                        lambda pwd: (True, "Sessione ripristinata ✅"))

    result = await _apri_reauth(hass, integrazione_avviata)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "nuova_password"})
    await hass.async_block_till_done()

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert integrazione_avviata.data.get(CONF_LOGIN_METHOD) == LOGIN_METHOD_PASSWORD


async def test_reauth_password_errata_mostra_errore(
        hass, integrazione_avviata, monkeypatch):
    """Password errata in reauth mostra errore password_invalid e il motivo."""
    coord = hass.data[DOMAIN][integrazione_avviata.entry_id]
    monkeypatch.setattr(coord, "_login_with_password",
                        lambda pwd: (False, "credenziali non valide"))

    result = await _apri_reauth(hass, integrazione_avviata)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "password_sbagliata"})

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_password"
    assert result["errors"]["base"] == "password_invalid"
    assert "credenziali non valide" in result["description_placeholders"]["reason"]


async def test_reauth_password_vuota_richiesta(hass, integrazione_avviata):
    """Password vuota in reauth è rifiutata con password_required."""
    result = await _apri_reauth(hass, integrazione_avviata)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_PASSWORD: "   "})

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "reauth_password"
    assert result["errors"]["base"] == "password_required"


async def test_reauth_senza_entry_abortisce(hass):
    """Reauth senza entry valida abortisce con reauth_no_entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": "non_esiste"},
        data={},
    )
    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reauth_no_entry"


# ───────────────────────── Preset e parametri di regione ─────────────────────────
def test_domain_and_defaults_lepas():
    """Verifica il dominio nativo lepas e i parametri predefiniti di connessione."""
    assert DOMAIN == "lepas"
    assert DEFAULT_VEHICLE_NAME == "Lepas"
    assert PRESET_LEPAS_EU == "lepas_eu"
    assert DEFAULT_PRESET == PRESET_LEPAS_EU
    assert DEFAULTS[CONF_BFF] == "https://eu-lepas.cheryinternational.com/api"
    assert DEFAULTS[CONF_TENANT_CODE] == "3000011"
    assert DEFAULTS[CONF_CHANNEL_ID] == "6"
    assert DEFAULTS[CONF_COUNTRY_ID] == "1"


def test_apply_preset_lepas_eu():
    """Verifica l'applicazione esplicita del preset Lepas Europe."""
    flow = LepasConfigFlow()
    data = {CONF_PRESET: PRESET_LEPAS_EU}
    res = flow._apply_preset(data)
    target = res if isinstance(res, dict) else data
    assert CONF_PRESET not in target
    assert target[CONF_BFF] == "https://eu-lepas.cheryinternational.com/api"
    assert target[CONF_TENANT_CODE] == "3000011"
    assert target[CONF_CHANNEL_ID] == "6"
    assert target[CONF_COUNTRY_ID] == "1"


def test_apply_preset_default_fallback():
    """Verifica il fallback automatico su Lepas Europe in assenza di preset."""
    flow = LepasConfigFlow()
    data = {}
    res = flow._apply_preset(data)
    target = res if isinstance(res, dict) else data
    assert CONF_PRESET not in target
    assert target[CONF_BFF] == "https://eu-lepas.cheryinternational.com/api"
    assert target[CONF_TENANT_CODE] == "3000011"
    assert target[CONF_CHANNEL_ID] == "6"
    assert target[CONF_COUNTRY_ID] == "1"


def test_apply_preset_chery_eu():
    """Verifica il preset Chery Europe."""
    flow = LepasConfigFlow()
    data = {CONF_PRESET: PRESET_CHERY_EU}
    res = flow._apply_preset(data)
    target = res if isinstance(res, dict) else data
    assert CONF_PRESET not in target
    assert target[CONF_BFF] == "https://eu-chery.cheryinternational.com/api"
    assert target[CONF_TENANT_CODE] == "300001"
    assert target[CONF_CHANNEL_ID] == "2"
    assert target[CONF_COUNTRY_ID] == "2"


def test_apply_preset_custom():
    """Verifica che i parametri custom non vengano sovrascritti."""
    flow = LepasConfigFlow()
    data = {
        CONF_PRESET: PRESET_CUSTOM,
        CONF_BFF: "https://custom-gateway.example.com/api",
        CONF_TENANT_CODE: "999999",
        CONF_CHANNEL_ID: "42",
        CONF_COUNTRY_ID: "99",
    }
    res = flow._apply_preset(data)
    target = res if isinstance(res, dict) else data
    assert CONF_PRESET not in target
    assert target[CONF_BFF] == "https://custom-gateway.example.com/api"
    assert target[CONF_TENANT_CODE] == "999999"
    assert target[CONF_CHANNEL_ID] == "42"
    assert target[CONF_COUNTRY_ID] == "99"


async def test_login_password_applica_preset_lepas(hass, flusso_ok, monkeypatch):
    """Verifica che il login via password invochi _apply_preset garantendo i default Lepas."""
    flow = LepasConfigFlow()
    flow.hass = hass
    flow.context = {"source": "user"}
    flow._data = {CONF_PRESET: PRESET_LEPAS_EU}

    chiamate_apply = []
    original_apply = flow._apply_preset

    def spy_apply(data):
        chiamate_apply.append(dict(data))
        return original_apply(data)

    monkeypatch.setattr(flow, "_apply_preset", spy_apply)

    await flow.async_step_login_password(
        {CONF_EMAIL: FX.EMAIL, CONF_PASSWORD: "secret_password"}
    )
    assert len(chiamate_apply) >= 1
    assert flow._data.get(CONF_BFF) == "https://eu-lepas.cheryinternational.com/api"
    assert flow._data.get(CONF_TENANT_CODE) == "3000011"


CAMPI_TECNICI = (
    CONF_BFF,
    CONF_TENANT_CODE,
    CONF_COUNTRY_ID,
    CONF_CHANNEL_ID,
    CONF_TSP_HOST,
    CONF_CAR_MQTT_HOST,
    CONF_CAR_MQTT_PORT,
    CONF_CERTS_SRC,
)


def _schema_keys(schema) -> list[str]:
    """Estrae i nomi effettivi delle chiavi da uno schema voluptuous."""
    return [k.schema if hasattr(k, "schema") else k for k in schema.schema.keys()]


async def test_login_forms_nascondono_campi_tecnici(hass):
    """Verifica che il form di login_password mostri solo preset e lingua, nascondendo gli 8 campi tecnici."""
    result = await _init_login_password(hass)
    keys = _schema_keys(result["data_schema"])
    assert CONF_PRESET in keys
    assert CONF_LANGUAGE in keys
    for campo in CAMPI_TECNICI:
        assert campo not in keys

    for marker, selector in result["data_schema"].schema.items():
        name = marker.schema if hasattr(marker, "schema") else marker
        if name == CONF_PRESET:
            options = getattr(selector, "config", {}).get("options", [])
            custom_opt = next((o for o in options if (o.get("value") if isinstance(o, dict) else getattr(o, "value", None)) == PRESET_CUSTOM), None)
            assert custom_opt is not None
            lbl = custom_opt.get("label") if isinstance(custom_opt, dict) else getattr(custom_opt, "label", None)
            assert lbl == "Custom / other region (next step)"


async def test_custom_preset_instrada_a_custom_region_email(hass, flusso_ok, monkeypatch):
    """Selezionando PRESET_CUSTOM in login_password con email, il flow va a custom_region prima di coniare il token."""
    from custom_components.lepas import config_flow as cf

    chiamate_mint = []
    monkeypatch.setattr(
        cf,
        "_mint_password",
        lambda h, d, p: (chiamate_mint.append((dict(d), p)) or True, "token ok"),
    )

    result = await _init_login_password(hass)
    flow = hass.config_entries.flow._progress[result["flow_id"]]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: FX.EMAIL, CONF_PIN: FX.PIN, CONF_PASSWORD: "secret_password", CONF_PRESET: PRESET_CUSTOM},
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "custom_region"
    assert len(chiamate_mint) == 0
    assert CONF_PASSWORD not in flow._data
    assert flow._pending_password == "secret_password"

    keys = _schema_keys(result["data_schema"])
    for campo in CAMPI_TECNICI:
        assert campo in keys

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BFF: "https://custom-gateway.example.com/api",
            CONF_TENANT_CODE: "999999",
        },
    )

    assert len(chiamate_mint) == 1
    data_ricevuto, pwd_ricevuta = chiamate_mint[0]
    assert pwd_ricevuta == "secret_password"
    assert data_ricevuto[CONF_BFF] == "https://custom-gateway.example.com/api"
    assert data_ricevuto[CONF_TENANT_CODE] == "999999"
    assert flow._pending_password == ""
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert CONF_PASSWORD not in result["data"]


async def test_custom_preset_instrada_a_custom_region_phone(hass, flusso_ok, monkeypatch):
    """Selezionando PRESET_CUSTOM in login_password con telefono, il flow normalizza il telefono e va a custom_region."""
    from custom_components.lepas import config_flow as cf

    chiamate_mint = []
    monkeypatch.setattr(
        cf,
        "_mint_password",
        lambda h, d, p: (chiamate_mint.append((dict(d), p)) or True, "token ok"),
    )

    result = await _init_login_password(hass)
    flow = hass.config_entries.flow._progress[result["flow_id"]]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: "340 123 4567",
            CONF_AREA_CODE: "+39",
            CONF_PIN: FX.PIN,
            CONF_PASSWORD: "secret_password",
            CONF_PRESET: PRESET_CUSTOM,
        },
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "custom_region"
    assert len(chiamate_mint) == 0
    assert flow._data[CONF_PHONE] == "3401234567"
    assert flow._data[CONF_AREA_CODE] == "39"
    assert flow._data[CONF_EMAIL] == ""
    assert flow._pending_password == "secret_password"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BFF: "https://custom-phone.example.com/api"},
    )

    assert len(chiamate_mint) == 1
    data_ricevuto, pwd_ricevuta = chiamate_mint[0]
    assert pwd_ricevuta == "secret_password"
    assert data_ricevuto[CONF_PHONE] == "3401234567"
    assert data_ricevuto[CONF_AREA_CODE] == "39"
    assert data_ricevuto[CONF_BFF] == "https://custom-phone.example.com/api"
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PHONE] == "3401234567"
    assert result["data"][CONF_AREA_CODE] == "39"
    assert result["data"][CONF_EMAIL] == ""
    assert CONF_PASSWORD not in result["data"]


async def test_custom_region_failure_branches(hass, monkeypatch):
    """Verifica la gestione degli errori e il rispetto delle credenziali nei rami di fallimento di custom_region."""
    from custom_components.lepas import config_flow as cf

    # (a) _mint_password fallito in custom_region: torna a login_password, azzera pending_password, preserva custom fields in self._data
    monkeypatch.setattr(cf, "_mint_password", lambda h, d, p: (False, "password.invalid"))
    monkeypatch.setattr(cf, "_cleanup_pending", lambda h: None)

    result = await _init_login_password(hass)
    flow = hass.config_entries.flow._progress[result["flow_id"]]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: FX.EMAIL,
            CONF_PIN: FX.PIN,
            CONF_PASSWORD: "wrong_password",
            CONF_PRESET: PRESET_CUSTOM,
        },
    )
    assert result["step_id"] == "custom_region"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BFF: "https://fail-pwd.example.com/api"},
    )
    assert result["step_id"] == "login_password"
    assert result["errors"]["base"] == "password_invalid"
    assert "password.invalid" in result["description_placeholders"]["reason"]
    assert flow._pending_password == ""

    # Verifica Crash Antibodies AB-LEP-001/002: mai PIN o password nei suggested values
    for marker in result["data_schema"].schema:
        name = marker.schema if hasattr(marker, "schema") else marker
        if name in (CONF_PIN, CONF_PASSWORD):
            desc = marker.description if hasattr(marker, "description") else {}
            assert (isinstance(desc, dict) and "suggested_value" not in desc) or not isinstance(desc, dict)

    # I campi custom sono preservati in self._data: inviando di nuovo con PRESET_CUSTOM, custom_region è precompilato
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: FX.EMAIL,
            CONF_PIN: FX.PIN,
            CONF_PASSWORD: "retry_password",
            CONF_PRESET: PRESET_CUSTOM,
        },
    )
    assert result["step_id"] == "custom_region"
    bff_marker = next(
        m for m in result["data_schema"].schema
        if (m.schema if hasattr(m, "schema") else m) == CONF_BFF
    )
    desc = bff_marker.description if hasattr(bff_marker, "description") else {}
    assert isinstance(desc, dict) and desc.get("suggested_value") == "https://fail-pwd.example.com/api"

    # (b) _discover fallito in custom_region: mostra no_vehicle su custom_region e preserva pending_password
    monkeypatch.setattr(cf, "_mint_password", lambda h, d, p: (True, "token ok"))
    monkeypatch.setattr(cf, "_discover", lambda h, d: (False, "", [], "no_vehicle_found"))

    result = await _init_login_password(hass)
    flow = hass.config_entries.flow._progress[result["flow_id"]]

    await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_EMAIL: FX.EMAIL,
            CONF_PIN: FX.PIN,
            CONF_PASSWORD: "valid_password",
            CONF_PRESET: PRESET_CUSTOM,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_BFF: "https://fail-discover.example.com/api"},
    )
    assert result["step_id"] == "custom_region"
    assert result["errors"]["base"] == "no_vehicle"
    assert "no_vehicle_found" in result["description_placeholders"]["reason"]
    assert flow._pending_password == ""


def test_discover_authorized_control_car_list_e_tuserid_zero(hass, cloud):
    """_discover estrae VIN da authorizedControlCarList e risolve tUserId 0 via getTuserId."""
    from custom_components.lepas import config_flow as cf

    cloud.on(
        "/tsp/v1/app/auth/login",
        {"code": "000000", "data": {"userToken": FX.USER_TOKEN, "tUserId": "0"}},
    )
    cloud.on(
        "/marketing/v1/app/user",
        {"code": 200, "data": {"id": "u-discover-1"}},
    )
    cloud.on(
        "/tsp/v1/app/auth/getTuserId",
        {"code": "000000", "data": {"tUserId": "7766554433"}},
    )
    cloud.on(
        "/tsp/v1/app/vmc/queryList",
        {"code": "000000", "data": {"authorizedControlCarList": [{"vin": FX.VIN}]}},
    )

    data = {CONF_EMAIL: FX.EMAIL, CONF_PIN: FX.PIN}
    res = cf._discover(hass, data)
    assert res == (True, "7766554433", [FX.VIN], "ok")


async def test_migrate_entry_v1_lepas_eu_aggiorna_channel_a_6(hass):
    """Entry v1 Lepas EU con channel_id='1' viene migrata a v2 con channel_id='6'."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.lepas import async_migrate_entry
    from custom_components.lepas.const import (
        CONF_BFF, CONF_CHANNEL_ID, CONF_COUNTRY_ID, CONF_TENANT_CODE, CONF_VIN, DOMAIN,
    )

    assert LepasConfigFlow.VERSION == 2
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id=FX.VIN,
        data={
            CONF_VIN: FX.VIN,
            CONF_BFF: "https://eu-lepas.cheryinternational.com/api",
            CONF_TENANT_CODE: "3000011",
            CONF_COUNTRY_ID: "1",
            CONF_CHANNEL_ID: "1",
        },
    )
    entry.add_to_hass(hass)

    ok = await async_migrate_entry(hass, entry)
    assert ok is True
    assert entry.version == 2
    assert entry.data[CONF_CHANNEL_ID] == "6"


async def test_migrate_entry_v1_legacy_senza_campi_regione_imposta_6(hass):
    """Entry v1 storica senza bff/tenant_code/channel_id o con channel_id=None riceve channel_id='6'."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.lepas import async_migrate_entry
    from custom_components.lepas.const import CONF_CHANNEL_ID, CONF_VIN, DOMAIN

    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id=FX.VIN,
        data={CONF_VIN: FX.VIN},
    )
    entry_none = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id="LZZNONECORRECT001",
        data={CONF_VIN: "LZZNONECORRECT001", CONF_CHANNEL_ID: None},
    )
    entry.add_to_hass(hass)
    entry_none.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is True
    assert entry.version == 2
    assert entry.data[CONF_CHANNEL_ID] == "6"

    assert await async_migrate_entry(hass, entry_none) is True
    assert entry_none.version == 2
    assert entry_none.data[CONF_CHANNEL_ID] == "6"


async def test_migrate_entry_v1_preserva_chery_eu_e_custom(hass):
    """Entry v1 Chery EU ('2') o custom ('42') mantengono il proprio channel_id avanzando a v2."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.lepas import async_migrate_entry
    from custom_components.lepas.const import (
        CONF_BFF, CONF_CHANNEL_ID, CONF_COUNTRY_ID, CONF_TENANT_CODE, CONF_VIN, DOMAIN,
    )

    chery = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id="LZZCHERY000000001",
        data={
            CONF_VIN: "LZZCHERY000000001",
            CONF_BFF: "https://eu-chery.cheryinternational.com/api",
            CONF_TENANT_CODE: "300001",
            CONF_COUNTRY_ID: "2",
            CONF_CHANNEL_ID: "2",
        },
    )
    custom = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        unique_id="LZZCUSTOM00000002",
        data={
            CONF_VIN: "LZZCUSTOM00000002",
            CONF_BFF: "https://eu-lepas.cheryinternational.com/api",
            CONF_TENANT_CODE: "3000011",
            CONF_CHANNEL_ID: "42",
        },
    )
    chery.add_to_hass(hass)
    custom.add_to_hass(hass)

    assert await async_migrate_entry(hass, chery) is True
    assert chery.version == 2
    assert chery.data[CONF_CHANNEL_ID] == "2"

    assert await async_migrate_entry(hass, custom) is True
    assert custom.version == 2
    assert custom.data[CONF_CHANNEL_ID] == "42"


async def test_migrate_entry_downgrade_rifiutato(hass):
    """Una entry con version > 2 non viene degradata e ritorna False."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.lepas import async_migrate_entry
    from custom_components.lepas.const import CONF_CHANNEL_ID, CONF_VIN, DOMAIN

    future = MockConfigEntry(
        domain=DOMAIN,
        version=3,
        unique_id=FX.VIN,
        data={CONF_VIN: FX.VIN, CONF_CHANNEL_ID: "99"},
    )
    future.add_to_hass(hass)

    assert await async_migrate_entry(hass, future) is False
    assert future.version == 3
    assert future.data[CONF_CHANNEL_ID] == "99"

