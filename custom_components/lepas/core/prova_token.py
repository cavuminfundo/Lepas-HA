"""prova_token.py — chiama auth/oauth2/token via password (ROPC) replicando l'app."""
import os, sys, json, requests
try:
    from . import lepas_auth as A
    from . import mask
except ImportError:
    import lepas_auth as A
    import mask

# dove salvare il token coniato (per-account); il bridge/coordinator legge lo stesso path
_TOKEN_OUT = os.environ.get("LEPAS_TOKEN_PATH", "token.json")

TOKEN_PATH = "/auth/oauth2/token"


def _dept(area):
    """`DEPT-ID` da mandare nelle intestazioni, ricavato dal prefisso internazionale."""
    cifre = "".join(ch for ch in str(area or "") if ch.isdigit()).lstrip("0")
    return {"dept_id": cifre} if cifre else {}


def build_params_password(username, password, is_phone=False, area="39"):
    """ROPC (grant_type=password): login con USERNAME + PASSWORD.

    `username` è l'identificatore grezzo (e-mail oppure numero). La password è cifrata AES-128-CBC (`A.aes_cbc_password`) e va nel
    BODY con `needDecode=1`: il server la decifra. Verificato dal vivo (2026-08-24): conia il
    token dell'account REALE, lo stesso del login e-mail.

    ⚠️ La password è una CREDENZIALE: cifrata prima di partire (mai in chiaro nei parametri), mai
    in un log (solo la sua lunghezza) né in entry.data. Si conia il token UNA volta e da lì la
    sessione vive sul refresh_token — la password non viene conservata."""
    p = {"username": username, "password": A.aes_cbc_password(password), "grant_type": "password",
         "scope": "server", "needDecode": "1"}
    if is_phone:
        p["loginType"] = "mobile"
        p["areaCode"] = area
    else:
        p["loginType"] = "email"
    return p


def call_password(username, password, is_phone=False, area="39", verbose=True):
    """Conia il token via ROPC (username+password). Ritorna (status, json, token)."""
    params = build_params_password(username, password, is_phone, area)
    H = A.headers_post(TOKEN_PATH, secret=A.SIGN_SECRET, **_dept(area))
    try:
        r = requests.post(A.BFF + TOKEN_PATH, data=params, headers=H, timeout=20)
    except requests.RequestException as e:
        if verbose:
            print(f"[login password pwd_len={len(password)}] errore di rete: {type(e).__name__}")
        return 0, {"key": "network.error",
                   "msg": f"errore di rete durante il login ({type(e).__name__})"}, None
    try:
        j = r.json()
    except Exception:
        j = {"_raw": r.text[:300]}
    tok = j.get("access_token") or (j.get("data") or {}).get("access_token")
    if verbose:
        who = mask.numero_con_prefisso(username, area) if is_phone else mask.indirizzo_email(username)
        print(f"[login password user={who} pwd_len={len(password)}] HTTP {r.status_code}")
        print("  resp:", json.dumps(_redact(j), ensure_ascii=False)[:400])
    return r.status_code, j, tok


def _redact(obj):
    """Copia con access_token/refresh_token oscurati (per le stampe che vanno in HA)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ("access_token", "refresh_token") and v:
                out[k] = f"<{len(str(v))}ch redatto>"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LEPAS_EMAIL", "")
    phone = os.environ.get("LEPAS_PHONE", "")
    area = os.environ.get("LEPAS_AREA", "39")
    password = os.environ.get("LEPAS_PASSWORD", "")
    if not password:
        print("MOTIVO: manca la password per il login (LEPAS_PASSWORD)")
        print("RESULT: FAIL")
        sys.exit(1)
    is_phone = bool(phone)
    username = phone if is_phone else email
    if not username:
        print("MOTIVO: manca l'identità (numero o e-mail) per il login con password")
        print("RESULT: FAIL")
        sys.exit(1)
    sc, j, tok = call_password(username, password, is_phone=is_phone, area=area)
    if tok:
        tmp = _TOKEN_OUT + ".tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(j, fh, indent=2, ensure_ascii=False)
        os.chmod(tmp, 0o600)
        os.replace(tmp, _TOKEN_OUT)
        print(f"\n✅ LOGIN OK — token salvato in {_TOKEN_OUT}")
        print("RESULT: OK")
        sys.exit(0)
    print("RESULT: FAIL")
    sys.exit(1)
