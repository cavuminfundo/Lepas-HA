"""Classificazione degli errori e invio comandi: quale RIMEDIO vede l'utente.

Il valore di questi test non è "il comando parte", ma: quando il backend rifiuta, il
componente propone la cosa giusta? Sbagliare qui ha conseguenze concrete —
mandare l'utente a cambiare un PIN sano (mentre il problema erano i permessi), o
non aprire la riautenticazione quando la sessione è davvero morta.

Sono anche la specifica eseguibile della tabella che P2-5 unificherà: le attese vivono
in `fixtures.CHECKPASSWORD_CODES`/`COMMAND_CODES`, quindi il refactor dovrà
riprodurre esattamente queste classificazioni.
"""
from __future__ import annotations

import pytest

import fixtures as FX


# ───────────────────────── checkPassword → reason ─────────────────────────
@pytest.mark.parametrize("code,atteso", sorted(FX.CHECKPASSWORD_CODES.items()))
def test_checkpassword_instrada_il_rimedio_giusto(core, cloud, ctx, code, atteso):
    """Ogni codice di checkPassword deve produrre il `reason` documentato.

    `reason` è ciò che il coordinator usa per decidere: Repair PIN, riautenticazione
    o semplice avviso. È la mappa che P1-2 ha corretto e che P2-5 dovrà preservare."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/cpm/checkPassword", {"code": code, "message": atteso["note"]})

    with pytest.raises(commands.CommandError) as err:
        commands._mint_taskid(ctx, FX.TUSERID)

    assert err.value.reason == atteso["reason"], (
        f"{code} ({atteso['note']}): atteso reason={atteso['reason']!r}, "
        f"ottenuto {err.value.reason!r}"
    )


@pytest.mark.parametrize("code,atteso", sorted(FX.CHECKPASSWORD_CODES.items()))
def test_solo_i_codici_pin_contano_per_il_lockout(core, cloud, ctx, code, atteso):
    """Il contatore anti-lockout si muove SOLO per i codici davvero imputabili al PIN.

    Contare un errore di permessi come "PIN errato" avvicinerebbe il blocco
    dell'account reale per una causa che col PIN non c'entra (bug P1-2)."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/cpm/checkPassword", {"code": code, "message": atteso["note"]})

    with pytest.raises(commands.CommandError):
        commands._mint_taskid(ctx, FX.TUSERID)

    atteso_n = 1 if atteso["counts_lockout"] else 0
    assert ctx.lockout.tentativi_falliti == atteso_n, (
        f"{code} ({atteso['note']}): anti-lockout a {ctx.lockout.tentativi_falliti}, "
        f"atteso {atteso_n}"
    )


def test_codice_sconosciuto_resta_sul_ramo_pin(core, cloud, ctx):
    """Default CONSERVATIVO voluto: un codice mai visto si tratta come PIN errato.

    È la scelta sicura — meglio proporre di ricontrollare il PIN che lasciare
    l'utente senza alcun rimedio. Il test la fissa perché è una decisione, non un caso."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/cpm/checkPassword", {"code": "A0XXXX", "message": "mai visto"})
    with pytest.raises(commands.CommandError) as err:
        commands._mint_taskid(ctx, FX.TUSERID)
    assert err.value.reason == "pin"


def test_il_codice_grezzo_finisce_nel_messaggio(core, cloud, ctx):
    """Il codice reale del backend deve restare visibile: è l'unico modo, dal campo,
    per distinguere un PIN errato da un rifiuto di altra natura."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/cpm/checkPassword", {"code": "A00285", "message": "password error"})
    with pytest.raises(commands.CommandError) as err:
        commands._mint_taskid(ctx, FX.TUSERID)
    assert "A00285" in str(err.value)


def test_checkpassword_code_1_con_a00361_in_message_non_conta_lockout(core, cloud, ctx):
    """Il BFF può avvolgere A00361 in code=1, message='A00361' (User does not exist):
    non è un errore di PIN, ritenta con scene=2 e non consuma tentativi anti-lockout."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/cpm/checkPassword", {"code": 1, "message": "A00361"})
    with pytest.raises(commands.CommandError) as err:
        commands._mint_taskid(ctx, FX.TUSERID)
    assert err.value.reason == "config"
    assert ctx.lockout.tentativi_falliti == 0
    assert cloud.count("checkPassword") == 2
    calls = cloud.calls_to("checkPassword")
    assert calls[0]["body"]["scene"] == 0
    assert calls[1]["body"]["scene"] == 2
    assert "A00361" in str(err.value)


def test_checkpassword_usa_tuserid_da_querylist_se_tuid_vuoto(core, cloud, ctx):
    """Se auth/login restituisce tuid vuoto, _checkpassword recupera tUserId da queryList."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/vmc/queryList", data=[{"vin": FX.VIN, "tUserId": "99887766"}])
    cloud.on("/tsp/v1/app/cpm/checkPassword", data={"taskId": FX.TASKID})
    tid = commands._mint_taskid(ctx, "")
    assert tid == FX.TASKID
    cp_call = cloud.calls_to("checkPassword")[0]["body"]
    assert cp_call["tUserId"] == "99887766"


# ───────────────────────── send() → esito ─────────────────────────
@pytest.mark.parametrize("code,atteso", sorted(FX.COMMAND_CODES.items()))
def test_esito_comando_per_codice(core, cloud, ctx, code, atteso):
    """Il backend risponde SEMPRE HTTP 200: l'esito vero è nel `code` del body.

    Distinguere accettato/rifiutato è ciò che impedisce alle entità ottimistiche di
    mostrare un finto "successo" quando l'auto ha in realtà rifiutato il comando."""
    commands = core["commands"]
    cloud.on("/asc/vehicleControl/lockControl", {"code": code})

    if atteso["ok"]:
        esito = commands.send(ctx, "blocca")
        assert code in esito
        return

    with pytest.raises(commands.CommandError) as err:
        commands.send(ctx, "blocca")
    assert err.value.code == code
    assert err.value.reason == atteso["reason"], f"{code}: reason inatteso"
    assert err.value.retryable is atteso["retryable"], (
        f"{code} ({atteso['note']}): retryable atteso {atteso['retryable']}"
    )


@pytest.mark.parametrize("code", FX.TASKID_INVALID_CODES)
def test_taskid_rifiutato_si_riconia_e_riprova_una_volta(core, cloud, ctx, code):
    """Un taskId scaduto non deve diventare un errore per l'utente: si riconia e si
    riprova UNA volta. Se anche il secondo giro fallisce ci si arrende (niente loop
    infinito che martella il backend e brucia tentativi PIN)."""
    commands = core["commands"]
    tentativi = {"n": 0}

    def risposta(path, body):
        tentativi["n"] += 1
        # primo invio: taskId rifiutato; secondo (dopo il riconio): accettato
        return {"code": code} if tentativi["n"] == 1 else {"code": "A00079"}

    cloud.on("/asc/vehicleControl/lockControl", risposta)
    esito = commands.send(ctx, "blocca")

    assert "A00079" in esito
    assert tentativi["n"] == 2, "doveva riprovare esattamente una volta"
    assert cloud.count("checkPassword") >= 1, "il taskId doveva essere ri-coniato"


def test_taskid_rifiutato_due_volte_si_arrende(core, cloud, ctx):
    """Il retry è UNO solo: al secondo rifiuto si solleva, non si insiste."""
    commands = core["commands"]
    cloud.on("/asc/vehicleControl/lockControl", {"code": "A00089"})
    with pytest.raises(commands.CommandError) as err:
        commands.send(ctx, "blocca")
    assert err.value.code == "A00089"
    assert cloud.count("/asc/vehicleControl/lockControl") == 2


def test_sessione_morta_chiede_riautenticazione(core, cloud, ctx):
    """Login BFF che non restituisce userToken = sessione morta → `reason="reauth"`,
    cioè la card «Riautentica» di HA, non il Repair del PIN (l'OTP non cambia il PIN)."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/auth/login", {"code": "A00000", "data": {}})
    cloud.on("/auth/oauth2/token", {"code": "A00000"})   # anche il refresh fallisce
    with pytest.raises(commands.CommandError) as err:
        commands.send(ctx, "blocca")
    assert err.value.reason == "reauth"


def test_conio_disattivato_non_e_colpa_del_pin(core, cloud, ctx):
    """P1-2 (#30): senza conio e senza taskId il PIN è irrilevante → `reason="config"`.
    Prima si diceva «PIN errato», mandando l'utente a riconfigurare un PIN sano."""
    commands = core["commands"]
    ctx.mint_taskid = False
    with pytest.raises(commands.CommandError) as err:
        commands.send(ctx, "blocca")
    assert err.value.reason == "config"
    assert cloud.count("checkPassword") == 0


def test_comando_sconosciuto_non_tocca_la_rete(core, cloud, ctx):
    commands = core["commands"]
    with pytest.raises(commands.CommandError):
        commands.send(ctx, "comando_inesistente")
    assert cloud.calls == []


def test_parametri_sovrascrivono_il_body_ma_non_i_campi_di_sistema(core, cloud, ctx):
    """I comandi parametrici (clima: temperatura/durata) devono poter cambiare il body,
    ma MAI i campi di sistema (vin/taskId/seq/clientType), che restano quelli coniati."""
    commands = core["commands"]
    cloud.on("/asc/vehicleControl/airControl", {"code": "A00079"})
    commands.send(ctx, "clima_on", params={"temperature": "24.0", "times": "30",
                                      "vin": "VIN_FASULLO", "taskId": "TASKID_FASULLO"})
    body = cloud.calls_to("airControl")[0]["body"]
    assert body["temperature"] == "24.0"
    assert body["times"] == "30"
    assert body["vin"] == FX.VIN, "il VIN di sistema è stato sovrascritto dai params"
    assert body["taskId"] == FX.TASKID, "il taskId di sistema è stato sovrascritto"


def test_errore_di_rete_non_diventa_un_falso_pin(core, cloud, ctx):
    """Un blip di rete durante l'invio non deve essere classificato come PIN errato:
    l'utente rifarebbe una riconfigurazione inutile."""
    commands = core["commands"]
    cloud.on("/asc/vehicleControl/lockControl", raises=OSError("rete giù"))
    with pytest.raises(commands.CommandError) as err:
        commands.send(ctx, "blocca")
    assert err.value.reason is None
    assert ctx.lockout.tentativi_falliti == 0


def test_checkpassword_ignora_tuid_zero_e_risolve_prima_di_checkpassword(core, cloud, ctx, token_file):
    """Verifica che tUserId '0' venga ignorato e risolto prima della chiamata a checkPassword."""
    import json

    commands = core["commands"]
    permessi = core["permessi"]

    tok = json.loads(token_file.read_text("utf-8"))
    tok["user_id"] = "u-sec-99"
    if isinstance(tok.get("data"), dict):
        tok["data"]["user_id"] = "u-sec-99"
    token_file.write_text(json.dumps(tok), encoding="utf-8")

    cloud.on("/tsp/v1/app/vmc/queryList", data=[{"vin": FX.VIN, "nickname": "Auto"}])
    cloud.on(
        "/tsp/v1/app/auth/getTuserId",
        {"code": "000000", "data": {"tUserId": "5544332211"}},
    )
    cloud.on("/tsp/v1/app/cpm/checkPassword", data={"taskId": FX.TASKID})

    tid = commands._mint_taskid(ctx, "0")
    assert tid == FX.TASKID
    cp_call = cloud.calls_to("checkPassword")[0]["body"]
    assert cp_call["tUserId"] == "5544332211"
    assert cp_call["scene"] == 0

    p = permessi.leggi(ctx, FX.USER_TOKEN, "0")
    assert p == permessi.IGNOTO
    assert cloud.count("queryVehicleAuthority") == 0
    assert cloud.count("queryPermissions") == 0


def test_checkpassword_blocca_se_tuserid_vuoto_senza_chiamare_backend(core, cloud, ctx, token_file):
    """Hard gate: se tUserId non è risolvibile, solleva CommandError(reason='config') prima di checkPassword."""
    import json
    commands = core["commands"]

    # token_file privo di user_id
    tok = json.loads(token_file.read_text("utf-8"))
    tok.pop("user_id", None)
    tok.pop("userId", None)
    if isinstance(tok.get("data"), dict):
        tok["data"].pop("user_id", None)
        tok["data"].pop("userId", None)
    token_file.write_text(json.dumps(tok), encoding="utf-8")

    cloud.on("/tsp/v1/app/vmc/queryList", data=[])
    cloud.on("/marketing/v1/app/user", {"code": 500, "data": {}}, status=500)

    with pytest.raises(commands.CommandError) as err:
        commands._mint_taskid(ctx, "0")

    assert err.value.reason == "config"
    assert "tUserId non disponibile" in str(err.value)
    assert ctx.lockout.tentativi_falliti == 0
    assert cloud.count("checkPassword") == 0
    assert cloud.count("setVecDefault") == 0


def test_checkpassword_a00361_con_tuid_login_ritenta_una_volta_con_getTuserId_diverso(core, cloud, ctx, token_file):
    """Se checkPassword dà A00361 con tuid_source='login', ritenta 1 sola volta se getTuserId è diverso."""
    import json
    commands = core["commands"]

    tok = json.loads(token_file.read_text("utf-8"))
    tok["user_id"] = "u-sec-99"
    if isinstance(tok.get("data"), dict):
        tok["data"]["user_id"] = "u-sec-99"
    token_file.write_text(json.dumps(tok), encoding="utf-8")

    def cp_cb(path, body):
        if body.get("tUserId") == "111":
            return {"code": 1, "message": "A00361"}
        if body.get("tUserId") == "222":
            return {"code": "000000", "data": {"taskId": FX.TASKID}}
        return {"code": "A00285"}

    cloud.on("/tsp/v1/app/cpm/checkPassword", cp_cb)
    cloud.on("/tsp/v1/app/auth/getTuserId", {"code": "000000", "data": {"tUserId": "222"}})

    tid = commands._mint_taskid(ctx, "111")
    assert tid == FX.TASKID
    assert cloud.count("checkPassword") == 2
    assert ctx.lockout.tentativi_falliti == 0

    # Secondo caso: getTuserId restituisce lo stesso "111" -> non ritenta con getTuserId, ritenta con scene=2
    cloud.reset_calls()
    cloud.on("/tsp/v1/app/auth/getTuserId", {"code": "000000", "data": {"tUserId": "111"}})

    with pytest.raises(commands.CommandError) as err:
        commands._mint_taskid(ctx, "111")

    assert err.value.reason == "config"
    assert cloud.count("checkPassword") == 2
    calls = cloud.calls_to("checkPassword")
    assert calls[0]["body"]["scene"] == 0
    assert calls[1]["body"]["scene"] == 2
    assert ctx.lockout.tentativi_falliti == 0


def test_checkpassword_a00361_con_scene0_ritenta_con_scene2_apk(core, cloud, ctx, token_file):
    """Su A00361 con scene=0, ritenta con il default APK scene=2 ed esce con successo se accettato."""
    import json
    commands = core["commands"]

    tok = json.loads(token_file.read_text("utf-8"))
    tok["user_id"] = "u-sec-99"
    if isinstance(tok.get("data"), dict):
        tok["data"]["user_id"] = "u-sec-99"
    token_file.write_text(json.dumps(tok), encoding="utf-8")

    cloud.on("/tsp/v1/app/auth/getTuserId", {"code": "000000", "data": {"tUserId": FX.TUSERID}})

    def cp_cb(path, body):
        if body.get("scene") == 0:
            return {"code": 1, "message": "A00361"}
        if body.get("scene") == 2:
            return {"code": "000000", "data": {"taskId": FX.TASKID}}
        return {"code": "A00285"}

    cloud.on("/tsp/v1/app/cpm/checkPassword", cp_cb)

    tid = commands._mint_taskid(ctx, FX.TUSERID)
    assert tid == FX.TASKID
    assert cloud.count("checkPassword") == 2
    calls = cloud.calls_to("checkPassword")
    assert calls[0]["body"]["scene"] == 0
    assert calls[1]["body"]["scene"] == 2
    assert ctx.lockout.tentativi_falliti == 0



