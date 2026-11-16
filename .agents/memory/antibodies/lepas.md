# Crash Antibodies — Lepas (Chery EU Connected Vehicle Integration)

## [AB-LEP-001] Chery EU Auth Token Refresh Serialization & 12V Battery Drain Guard
- **Target Files**: `custom_components/lepas/**/*.py`
- **Root Cause**: Richieste concorrenti di refresh del token OAuth Chery EU invalidano il refresh token attivo, e un polling forzato (`wake_up`) troppo frequente a veicolo spento scarica la batteria 12V.
- **Invariant**: Serializzare il refresh del token sotto `asyncio.Lock` nel `DataUpdateCoordinator` e rispettare rigorosamente il backoff passivo quando il veicolo è in stato `sleep`/parcheggiato.
- **onFailure Mandate**: Su errore `401/403` dopo 1 retry sotto lock, sollevare `ConfigEntryAuthFailed` senza ciclare in loop.
- **Forbidden Regex**: `while\s+True:\s*await\s+self\.async_refresh_token`

## [AB-LEP-002] `ID_PREFIX = "lepas"` Entity Registry Alignment & PII Redaction
- **Target Files**: `custom_components/lepas/**/*.py`
- **Root Cause**: L'uso di prefissi incoerenti (`chery_` vs `lepas_`) duplica le entità nel registro di Home Assistant, e il log raw dei payload API espone VIN, coordinate GPS e token.
- **Invariant**: Tutte le `unique_id` devono usare `ID_PREFIX = "lepas"` e i log diagnostici devono oscurare `vin`, `lat`, `lon`, `access_token` e `refresh_token`.
- **onFailure Mandate**: Filtrare i campi sensibili tramite `async_redact_data` prima di qualsiasi output di diagnostica o log.
- **Forbidden Regex**: `_LOGGER\.(?:info|warning|error)\([^)]*access_token`

## [AB-LEP-003] Secondary Account `tUserId == "0"` Normalization, APK URL Strip & Hard Gate
- **Target Files**: `custom_components/lepas/core/{lepas_auth,wake,commands,provision,permessi}.py`, `custom_components/lepas/{config_flow,coordinator,diagnostics}.py`
- **Root Cause**: Sugli account secondari/condivisi `POST /tsp/v1/app/auth/login` restituisce `"tUserId": "0"` (truthy in Python) causando `A00361` in `checkPassword`; `lepas_auth` firmava `/tsp/...` invece di `/v1/...` (APK `http_utils.dart:1207-1234` rimuove il primo segmento servizio), e `commands._checkpassword` chiamava `checkPassword` anche con `tUserId == ""`.
- **Invariant**: Normalizzare sempre `tUserId` tramite `wake._valid_tuserid()` (rifiutando `""`, `"None"`, `"0"`), normalizzare la firma BFF via `lepas_auth._normalize_sig_url()` (`/tsp/` e `/marketing/` -> `/v1/...`, lasciando `/auth/oauth2/token` invariato), risolvere via `GET /tsp/v1/app/auth/getTuserId` (`userId` obbligatorio) mantenendo `scene=0` invariato in `checkPassword`.
- **onFailure Mandate**: Se `tuid_str` è vuoto dopo `_resolve_tuserid`, sollevare subito `CommandError(..., reason="config")` PRIMA di `setVecDefault`/`checkPassword` (zero consumo lockout); su `A00361` con `tuid_source == "login"`, consentire al massimo 1 retry con `getTuserId` alternativo diverso; loggare solo stato non-PII (`tuid_source`, `len`, `http`, `code`).
- **Forbidden Regex**: `if\s+not\s+tuid\s*:|headers_post\([^)]*method\s*=\s*["']GET["']`

## [AB-LEP-004] OAuth Refresh `user_id` Preservation & Atomic `token.json` Locking
- **Target Files**: `custom_components/lepas/core/wake.py`, `custom_components/lepas/{config_flow,diagnostics}.py`
- **Root Cause**: `/auth/oauth2/token?grant_type=refresh_token` restituisce `access_token`/`refresh_token` senza `user_id`; riscrivere `token.json` col solo JSON di risposta cancella `user_id`, rendendo impossibile chiamare `getTuserId`.
- **Invariant**: `_refresh_token_detail` deve copiare i metadati identitari (`user_id`, `userId`, `username`, `phone`, `email`) dal `token.json` esistente prima di riscrivere; se assente, recuperare `data.id` via `GET /marketing/v1/app/user` (`UserState::getUserInfo`) e persisterlo sotto `ctx.stato.lock_token` tramite `_write_token_atomic` (`0o600`, cleanup `.tmp`). In `config_flow.py` / `diagnostics.py`, ogni I/O su `token.json` o `_check_session` deve girare via `async_add_executor_job`.
- **onFailure Mandate**: Su fallimento HTTP/JSON di `getUserInfo`, loggare solo `type(err).__name__`/`http`/`code`/`has_id` a `DEBUG`, non modificare `token.json` e non chiamare `getTuserId` senza `userId`.
- **Forbidden Regex**: `json\.dump\(j,\s*f`
