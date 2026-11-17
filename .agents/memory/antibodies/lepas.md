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
- **Invariant**: Normalizzare sempre `tUserId` tramite `wake._valid_tuserid()` (rifiutando `""`, `"None"`, `"0"`), normalizzare la firma BFF via `lepas_auth._normalize_sig_url()` (`/tsp/` e `/marketing/` -> `/v1/...`, lasciando `/auth/oauth2/token` invariato), risolvere via `GET /tsp/v1/app/auth/getTuserId` (`userId` obbligatorio); `checkPassword` usa `scene=0` come primo tentativo con un singolo fallback controllato a `scene=2` (default APK `RusApiService::checkPassword`) su `A00361`.
- **onFailure Mandate**: Se `tuid_str` è vuoto dopo `_resolve_tuserid`, sollevare subito `CommandError(..., reason="config")` PRIMA di `setVecDefault`/`checkPassword` (zero consumo lockout); su `A00361` con `tuid_source == "login"`, consentire al massimo 1 retry con `getTuserId` alternativo diverso, seguito da 1 fallback controllato con `scene=2` (default APK); loggare solo stato non-PII (`tuid_source`, `len`, `http`, `code`).
- **Forbidden Regex**: `if\s+not\s+tuid\s*:|headers_post\([^)]*method\s*=\s*["']GET["']`

## [AB-LEP-004] OAuth Refresh `user_id` Preservation & Atomic `token.json` Locking
- **Target Files**: `custom_components/lepas/core/wake.py`, `custom_components/lepas/{config_flow,diagnostics}.py`
- **Root Cause**: `/auth/oauth2/token?grant_type=refresh_token` restituisce `access_token`/`refresh_token` senza `user_id`; riscrivere `token.json` col solo JSON di risposta cancella `user_id`, rendendo impossibile chiamare `getTuserId`.
- **Invariant**: `_refresh_token_detail` deve copiare i metadati identitari (`user_id`, `userId`, `username`, `phone`, `email`) dal `token.json` esistente prima di riscrivere; se assente, recuperare `data.id` via `GET /marketing/v1/app/user` (`UserState::getUserInfo`) e persisterlo sotto `ctx.stato.lock_token` tramite `_write_token_atomic` (`0o600`, cleanup `.tmp`). In `config_flow.py` / `diagnostics.py`, ogni I/O su `token.json` o `_check_session` deve girare via `async_add_executor_job`.
- **onFailure Mandate**: Su fallimento HTTP/JSON di `getUserInfo`, loggare solo `type(err).__name__`/`http`/`code`/`has_id` a `DEBUG`, non modificare `token.json` e non chiamare `getTuserId` senza `userId`.
- **Forbidden Regex**: `json\.dump\(j,\s*f`

## [AB-LEP-005] Secondary Account Backend `A00361` Across TSP Microservices (`cpm/vmc/vac`) & HA Module Reload
- **Target Files**: `custom_components/lepas/core/commands.py`, `custom_components/lepas/core/permessi.py`
- **Root Cause**: Un account secondario (`authorizeType=1`) può ottenere `tUserId` da `auth/login` e `getTuserId`, `vmc/queryList` (`code=0`) e `vmc/setVecDefault` (`code=0`), ma ricevere comunque `A00361` ("User does not exist") su `cpm/checkPassword` (anche con header 1:1 APK `1.0.4`, `User-Agent: Dart/3.4 (dart:io)`, `scene=0/2` e `userId` alternativo), `vmc/queryVehicleAuthority` e `vac/queryAuthRemoteList`, e `A00120` su `vac/query`. L'app ufficiale (`RusCarCntrolViewModel::_refreshTaskIdIfInvalid`) evita la chiamata finché ha `taskId` in cache; su `eu-lepas`, senza registrazione/attivazione profilo TSP (`auth/register`) o con account diverso dal profilo registrato in CPM/VMC, il backend rifiuta il `tUserId` secondario. Inoltre `homeassistant.reload_config_entry` NON ricarica i moduli già importati in `custom_components/lepas/core/*.py`.
- **Invariant**: Loggare al fallimento di `checkPassword` solo metadati non-PII (`tuid_source`, `tuid_len`, `ql_code`, `auth_type`, `sv_code`, `scene`, `bff`, `ch`, `tenant`, `country`, `pin_len`, `pin_dig`, `cp_http`, `cp_key`, `ql_keys`) senza mai inventare chiamate HTTP extra né eludere `A00361` come errore PIN. Per test dal vivo su moduli `core/*.py` in HA è obbligatorio `ha_restart`.
- **onFailure Mandate**: Classificare `A00361` in `routing.py` come `reason="config"` senza incrementare il contatore di lockout PIN; evitare retry non deterministi e rimuovere sempre eventuali sonde prima di chiudere.
- **Forbidden Regex**: `probe_a|queryAuthRemoteList.*_LOGGER\.warning`

## [AB-LEP-006] Lepas EU `channelId: "6"` Alignment & ConfigEntry v1→v2 Migration
- **Target Files**: `custom_components/lepas/**/*.py`
- **Root Cause**: L'app ufficiale Lepas EU include `.env.prod` (`CHANNELID=1`), ma a runtime sovrascrive il canale interrogando `/tsp/v1/app/env/defaultEnv` che ritorna `channelId: 6`. Usare `"1"` provoca `A00361` ("User does not exist") su `cpm/checkPassword`, `vmc/queryVehicleAuthority` e `vac/queryAuthRemoteList`.
- **Invariant**: `PRESET_LEPAS_EU`, `DEFAULTS[CONF_CHANNEL_ID]`, `DEFAULT_CHANNEL_ID` e `CHANNEL_ID` devono restare `"6"`, con `LepasConfigFlow.VERSION >= 2` e `async_migrate_entry` per aggiornare le entry `v1` Lepas EU preservando `chery_eu` (`"2"`) e `custom`.
- **onFailure Mandate**: Su ricomparsa di `A00361`, verificare `GET /tsp/v1/app/env/defaultEnv` e `entry.data[CONF_CHANNEL_ID]` prima di toccare il flow PIN/lockout.
- **Forbidden Regex**: `PRESET_LEPAS_EU[^}]*CONF_CHANNEL_ID:\s*["']1["']`

## [AB-LEP-007] `/asr/manager/realtime` `META` Fields Propagation & `_state_lock` Non-Reentrancy
- **Target Files**: `custom_components/lepas/coordinator.py`
- **Root Cause**: Lepas L8 non invia push `5A02` spontanei su MQTT durante la marcia o l'apertura porte, ma `/asr/manager/realtime` restituisce già i campi `META` di stato fisico (`frontLeftDoor`, `doorLock`, `trunkDoor`, `sunroofState`, `sunroofMoveState`, ecc.); `_on_probe_data` aggiornava solo `patch["realtime"]` lasciando `self._fields` vuoto (`unknown` sulle entità non-realtime). Inoltre `self._state_lock` è un `threading.Lock` non rientrante usato anche da `_auto_e_sveglia()`.
- **Invariant**: In `_on_probe_data`, propagare in `self._fields` i campi `k in META` non `None` (esclusi `CMD_CONFIRM_META`, `"time"`, `GEO_KEYS`) senza emettere `msg_fields`; calcolare `awake = bool(self._last_msg_ts) and (time.time() - self._last_msg_ts) < self.awake_window` atomicamente dentro `with self._state_lock:` (senza mai chiamare `_auto_e_sveglia()` dentro il lock) e, se `awake` è `True`, riempire solo le chiavi assenti per non sovrascrivere un `5A02` live recente.
- **onFailure Mandate**: Se `data` non è un `dict`, saltare la propagazione senza sollevare né toccare `self._fields`; non chiamare mai `_auto_e_sveglia()` dentro `with self._state_lock:`.
- **Forbidden Regex**: `with\s+self\._state_lock:[^#]*self\._auto_e_sveglia\(`
