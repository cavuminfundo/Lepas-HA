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
