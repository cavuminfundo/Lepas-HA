#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""session.py — salute del token Lepas + login con password guidato da Home Assistant."""
import os, sys, subprocess, time, logging

HERE = os.path.dirname(os.path.abspath(__file__))
_LOGGER = logging.getLogger(__name__)

from . import wake  # riusa _bff_login / _refresh_token / TOKEN_PATH
from . import mask

_MOTIVO = "MOTIVO:"

PYEXE = sys.executable
_TIMEOUT = int(os.environ.get("LEPAS_LOGIN_TIMEOUT") or os.environ.get("LEPAS_OTP_TIMEOUT") or "120")

STATUS_OK = "OK"
STATUS_EXPIRED = "EXPIRED"
STATUS_NET_ERROR = "NET_ERROR"

_MOTIVO_FRESCO_S = 60.0
QUOTA_RINNOVO = 0.8


def check(ctx):
    """Ritorna (ok: bool, dettaglio: str, status: str).

    `status` è il marcatore stabile (STATUS_OK/EXPIRED/NET_ERROR): è ciò su cui il
    coordinator decide se aprire la riautenticazione. `dettaglio` è solo per l'utente."""
    try:
        ut, tu = wake._bff_login(ctx)
    except Exception as e:
        testo = str(e).strip()
        return (False,
                f"errore rete: {type(e).__name__}" + (f" - {testo[:160]}" if testo else ""),
                STATUS_NET_ERROR)
    if ut:
        return True, "Sessione attiva ✅", STATUS_OK
    try:
        motivo = ctx.stato.refresh_motivo or ""
        fresco = (time.time() - (ctx.stato.refresh_ts or 0.0)) < _MOTIVO_FRESCO_S
    except Exception:
        motivo, fresco = "", False
    if fresco and motivo.startswith("rete:"):
        return False, f"rinnovo non riuscito per la rete ({motivo[5:]})", STATUS_NET_ERROR
    return (False,
            "Sessione scaduta ❌ — riautentica da Home Assistant inserendo la password",
            STATUS_EXPIRED)


def refresh(ctx):
    """Rinnova l'access_token col refresh_token. True se rinnovato."""
    try:
        return bool(wake._refresh_token(ctx))
    except Exception:
        return False


def refresh_se_prossimo_a_scadere(ctx, quota: float = QUOTA_RINNOVO) -> tuple[bool, str]:
    """Rinnovo proattivo dell'access token."""
    try:
        eta, durata = wake._eta_token(ctx)
        if eta < 0 or durata <= 0:
            return False, "non_determinabile"
        if eta < durata * quota:
            return False, "non_serve"
        return wake._refresh_token_detail(ctx)
    except Exception as e:
        return False, f"rete:{type(e).__name__}"


def _timeout() -> int:
    try:
        return int(os.environ.get("LEPAS_LOGIN_TIMEOUT") or os.environ.get("LEPAS_OTP_TIMEOUT") or str(_TIMEOUT))
    except (TypeError, ValueError):
        return _TIMEOUT


def _subenv(ctx, **extra):
    """Ambiente effimero per il sottoprocesso di login."""
    env = dict(os.environ)
    deps = os.path.join(os.path.dirname(os.path.abspath(ctx.token_path)), "deps")
    if os.path.isdir(deps):
        env["PYTHONPATH"] = os.pathsep.join(
            [p for p in (env.get("PYTHONPATH", ""), deps) if p])
    env.update({
        "LEPAS_EMAIL": ctx.email,
        "LEPAS_PHONE": getattr(ctx, "phone", "") or "",
        "LEPAS_AREA": getattr(ctx, "area_code", "39") or "39",
        "LEPAS_TOKEN_PATH": ctx.token_path,
        "LEPAS_BFF": ctx.bff,
        "TSP_HOST": ctx.tsp_host,
        "CHANNEL_ID": ctx.channel_id,
        "LEPAS_COUNTRY_ID": ctx.country_id,
        "LEPAS_TENANT_CODE": ctx.tenant_code,
        "LEPAS_LANGUAGE": getattr(ctx, "language", "it-IT") or "it-IT",
        "VIN": ctx.vin,
        "TUSERID": ctx.tuserid,
    })
    env.update({k: str(v) for k, v in extra.items() if v is not None})
    return env


def _riga_utile(out: str, rc: int) -> str:
    """La riga dell'output del sottoprocesso che spiega davvero cos'è andato storto."""
    righe = [r.strip() for r in (out or "").strip().splitlines()
             if r.strip() and not r.strip().startswith("RESULT:")]
    motivi = [r[len(_MOTIVO):].strip() for r in righe if r.startswith(_MOTIVO)]
    if motivi:
        return motivi[-1]
    return righe[-1] if righe else f"rc={rc}"


def login_with_password(ctx, password, emit=lambda m: None):
    """Conia il token con username+password (ROPC), una volta sola."""
    if not (password or "").strip():
        return False, "nessuna password inserita"
    src_dir, timeout = ctx.src_dir, _timeout()
    emit("conio il token con la password…")
    try:
        r = subprocess.run([PYEXE, "prova_token.py"],
                           cwd=src_dir, capture_output=True, text=True, timeout=timeout,
                           env=_subenv(ctx, LEPAS_PASSWORD=password))
    except subprocess.TimeoutExpired:
        return False, "timeout conio token"
    out = (r.stdout or "") + (r.stderr or "")
    _LOGGER.debug("Lepas login: conio token via password rc=%s\n%s", r.returncode, out.strip())
    if r.returncode == 0 and "RESULT: OK" in out:
        ok, dettaglio, stato = check(ctx)
        if ok:
            return True, "Sessione ripristinata ✅"
        return False, f"password accettata, ma il login al gateway e' fallito: {dettaglio} [{stato}]"
    return False, f"password rifiutata: {_riga_utile(out, r.returncode)[:120]}"


if __name__ == "__main__":
    from .context import ctx_da_environ
    print("check:", check(ctx_da_environ()))
