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

## [AB-LEP-003] Secondary Account `tUserId == "0"` Normalization & GET Query Signing
- **Target Files**: `custom_components/lepas/core/{lepas_auth,wake,commands,provision,permessi}.py`, `custom_components/lepas/{config_flow,coordinator}.py`
- **Root Cause**: Sugli account secondari/condivisi `POST /tsp/v1/app/auth/login` restituisce `"tUserId": "0"` (truthy in Python) causando `A00361` in `checkPassword`, mentre le `GET` con query string richiedono firma `sha256(secret + nonce + path + ts + "[" + ",".join(vals) + "]")` e header `"keys"`.
- **Invariant**: Normalizzare sempre `tUserId` tramite `wake._valid_tuserid()` (rifiutando `""`, `"None"`, `"0"`), risolvere via `GET /tsp/v1/app/auth/getTuserId` con `A.headers_get` mantenendo `scene=0` invariato in `checkPassword`.
- **onFailure Mandate**: Su fallimento HTTP/JSON/`code` di `_resolve_tuserid`, loggare solo `type(err).__name__` a `DEBUG` (zero PII/token/userId/tUserId) e restituire `""`/`None` senza ciclare o consumare tentativi PIN (`A00361` -> `reason="config"`).
- **Forbidden Regex**: `if\s+not\s+tuid\s*:|headers_post\([^)]*method\s*=\s*["']GET["']`
