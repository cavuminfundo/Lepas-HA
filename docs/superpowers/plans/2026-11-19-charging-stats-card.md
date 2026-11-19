# Card Dedicata "Statistiche Lepas" (Ricarica + Consumi Medi) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Dual-Gate Plan Audit Matrix (Empirical Proof)

| Stage | Role / Model | Conversation ID | Verdict | Summary |
|---|---|---|---|---|
| Pre-Audit & Archaeology | Local Offload (`qwen2.5:3b`) | `task-8`, `task-73` | `OK` (`exit 0`) | Analisi simboli, `try/finally`, e anticorpi su `consumption.py`, `sensor.py`, `coordinator.py`, `__init__.py`, `button.py`, `lepas-card.js`. |
| Stage 1 (Domain & Archaeology) | `plan_auditor` (`flash`) | `da07cc27-cd95-411d-ab99-387c98cb41b3` | `CHANGES_REQUIRED` → Risolto | Individuati 3 gap: filtro `patch` in `_apply_update`, `async_delay_save` fuori `_charging_lock` + `dt_util.utcnow().timestamp()` + mock `hass.states`, regole baseline `LepasChargedEnergy`. Tutti integrati. |
| Stage 2 (Six-Pillars Sentinel) | `sentinel_auditor` (`inherit`) | `4b85af27-77c4-4c82-9814-7b0a7cfd94ef` | `APPROVED` (re-audit) | Verificati tutti i 6 Pilastri: integrata semantica `power_kw=None`, precedenza `AB-LEP-014` `msg_fields > fields`, guardie `LepasChargedEnergy` (`rt is self._ultimo_rt`), `escapeHtml` XSS & test JS/Python. |

---

**Goal:** Introdurre il motore persistente `charging_stats.py` con integratore ibrido (`chargingPower` trapezoidale `<= 300s` + riconciliazione delta SoC `> 300s`), migliorare `LepasChargedEnergy`, esporre 4 sensori periodici (`today`, `month`, `year`, `from_start`) + 1 pulsante di reset, e registrare la seconda card `lepas-stats-card` (Ricarica + Consumi medi) nel bundle `lepas-card.js` rimuovendo `Consumi medi` da `LepasCard`.

**Architecture:** Un nuovo modulo puro Python `custom_components/lepas/charging_stats.py` ospita `compute_charge_delta_kwh(...)` (condiviso con `LepasChargedEnergy`) e `ChargingStatsTracker` (bucket locali `today`/`month`/`year`/`from_start`, serie compatte `30g`/`12m`, rollover su lettura e su ingest). `LepasCoordinator` gestisce `Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.charging_stats")` sotto `_charging_lock` dedicato ed esegue `_ingest_charging_stats_on_loop(patch)` in `_apply_update(patch)` sul loop eventi HA (solo se `"realtime"` o `"fields"` è in `patch`, unificando `_on_probe_data` e `_on_car_message` senza mai riusare `realtime.chargingPower` stantio su push MQTT `fields`-only, usando `now_ts = dt_util.utcnow().timestamp()`). Sul frontend, `lepas-card.js` rimuove `consSection` da `LepasCard` e registra `LepasStatsCard` (`type: "lepas-stats-card"` in `window.customCards` con guardia anti-duplicazione, zero `?.`/`??`, Matte Titanium, SVG bar chart `7g/30g/12m`, toggle `Tutte|Casa|Fuori` e reset con dialog di conferma).

**Tech Stack:** Python >=3.12, Home Assistant Core (`Store`, `RestoreSensor`, `SensorDeviceClass.ENERGY`, `SensorStateClass.TOTAL` / `TOTAL_INCREASING`, `dt_util`), Vanilla JS Web Components (IIFE CJS-safe, Shadow DOM, SVG), `pytest`, `node --test`, `ruff`.

**Spec:** [2026-11-19-charging-stats-card-design.md](file:///home/federico/Lepas/docs/superpowers/specs/2026-11-19-charging-stats-card-design.md)

## Global Constraints
- Zero segreti, VIN o coordinate GPS persistiti in chiaro nello `Store` o nei log.
- Lock isolation (`AB-LEP-007`, `AB-LEP-014`): `self._charging_lock` non deve MAI essere annidato con `_state_lock`, `_hv_lock` o `_consumption_lock`; `async_delay_save(self._charging_snapshot, 30)` va chiamato **fuori** da `with self._charging_lock:` (perché `_charging_snapshot()` riacquisisce il lock non rientrante).
- Threading safety & timestamp source: `in_zona_casa(self.hass, pos)` e `dt_util.as_local(...)` vanno eseguiti sul loop eventi HA (`_apply_update`), mai nei thread paho/executor; `now_ts` usa sempre `dt_util.utcnow().timestamp()` (mai `time.time()`).
- `LepasChargedEnergy` mantiene `unique_id`, `entity_id`, `SensorStateClass.TOTAL_INCREASING`, `RestoreSensor` e `available = bool(poll_enabled)` (recupera buchi di polling a runtime; la continuità cross-riavvio HA è gestita da `ChargingStatsTracker` + `Store`).
- `LepasChargingStatsSensor` usa `SensorStateClass.TOTAL` (permette azzeramento a fine periodo / reset `from_start`) e resta disponibile anche a `poll_enabled=False`.
- JS (`lepas-card.js`): zero `?.` e zero `??` ovunque (inclusi commenti), zero `import`/`export` top-level, zero `:host-context`, zero `#00D2FF`, registrazione `window.customCards` con `type: "lepas-stats-card"` (senza prefisso `custom:`, `AB-LEP-008`) e guardia anti-duplicazione `!customElements.get(...)` / `!window.customCards.some(...)`, escaping HTML/SVG obbligatorio con `escapeHtml(...)` (o `.textContent` / `.value`) su `config.title`, etichette serie e valori dinamici interpolati, e versione `?v=X.Y.Z` sincronizzata con `manifest.json` e `pyproject.toml`.

---

## Domain Skills & Cohesive Roster

| Domain | Worker | Model | Workspace | Primary & Companion Skills (`lookup.py`) | Exclusive Cohesive Files |
|---|---|---|---|---|---|
| 1. Charging Stats Backend & HA Integration | `charging_backend_worker` | `'pro'` | `'inherit'` (Seq Round 1) | `python-testing-patterns` + `ponytail` + `antislop-code` | `custom_components/lepas/charging_stats.py`, `custom_components/lepas/coordinator.py`, `custom_components/lepas/__init__.py`, `custom_components/lepas/sensor.py`, `custom_components/lepas/button.py`, `custom_components/lepas/strings.json`, `custom_components/lepas/translations/{en,it,nl}.json`, `tests/test_charging_stats.py`, `tests/test_energia_ricarica.py`, `tests/test_entity_count.py` |
| 2. Lovelace Stats Card & Main Card Cleanup | `lovelace_ui_worker` | `'pro'` | `'inherit'` (Seq Round 2) | `ui-component` + `antislop-ui` + `antislop-code` | `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py` |
| 3. Verification, Dual-Gate Review & Release | Master Agent | — | `'inherit'` | `verification-before-completion`, `requesting-code-review` | `manifest.json`, `pyproject.toml`, `CHANGELOG.md`, `lepas-card.js` (`?v=X.Y.Z`), `.agents/memory/antibodies/lepas.md` (se applicabile) |

*(Nota: entrambi i worker usano `Model: 'pro'` fin dal Round 1 perché toccano file `>600L` — `coordinator.py` 3309L, `sensor.py` 1339L, `lepas-card.js` 4566L, `lepas_card.test.mjs` 3350L — oltre a lock di stato e contratti multi-file).*

---

## Blast Radius & StateGraph

### `BlastRadius`
- **`direct_files`**:
  - Create: `custom_components/lepas/charging_stats.py`, `tests/test_charging_stats.py`
  - Modify: `custom_components/lepas/coordinator.py`, `custom_components/lepas/__init__.py`, `custom_components/lepas/sensor.py`, `custom_components/lepas/button.py`, `custom_components/lepas/strings.json`, `custom_components/lepas/translations/{en,it,nl}.json`, `custom_components/lepas/lovelace/lepas-card.js`, `tests/test_energia_ricarica.py`, `tests/test_entity_count.py`, `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`, `manifest.json`, `pyproject.toml`, `CHANGELOG.md`
- **`transitively_affected`**:
  - `tests/test_consumption.py`, `tests/test_sensors.py`, `tests/test_traduzioni_complete.py`, `tests/test_translation_key_declared.py`, `tests/test_car_in_use_optimism.py`
  - `custom_components/lepas/naming.py` (verifica generazione `object_id` e `translation_key` — `LepasEntity` usa `object_id=f"{ID_PREFIX}_{key}"` e `translation_key=key` come `LepasConsumptionSensor`, zero modifiche necessarie a `naming.py`)
  - Home Assistant Energy Dashboard (`sensor.lepas_home_charging_energy`, `sensor.lepas_away_charging_energy`)
- **`uncertain`**:
  - Comportamento dei test esistenti che chiamano `coordinator._on_probe_data(...)` con mock parziali di `hass.loop` / `hass.states` (verificato in `_apply_update`: gestire con fallback sicuro se `self.hass` o `self.hass.states` è assente nei mock).

### `StateGraph` (`onSuccess:` / `onFailure:`)
1. **Store Load (`async_load_charging_stats` in `async_start`)**:
   - `onSuccess:` deserializza tramite `ChargingStatsTracker.from_dict(raw)` e assegna sotto `with self._charging_lock:`.
   - `onFailure:` catch `Exception`, log `WARNING` con solo `type(err).__name__`, mantiene tracker vuoto di default senza bloccare `async_start()`.
2. **Ingestione Event Loop (`_ingest_charging_stats_on_loop(patch)` in `_apply_update(patch)`)**:
   - `onSuccess:` ritorna subito (no-op) se né `"realtime"` né `"fields"` sono presenti in `patch` (evitando re-ingestione su `cmd_status`, `restore_position`, `wake_status`). Se `"realtime"` è in `patch`, legge `sources = (patch["realtime"], self.data.get("fields") or {})`, `power_kw = _safe_float(_pick_field(sources, "chargingPower"))` e `degraded = is_degraded_battery_frame(patch["realtime"])`; su push MQTT `fields`-only (`"realtime" not in patch`), per `AB-LEP-014` usa `sources = (patch.get("msg_fields") or {}, patch.get("fields") or {})` (`msg_fields > fields`, MAI `self.data.get("realtime")` stantio!) con `power_kw = None` e `degraded = False`. Valuta `in_zona_casa(self.hass, pos)` con guard difensivo su `hass`/`hass.states`/attributi numerici reali di `zone.home` (fallback `None` se `hass.states` è mockato/assente), `now_dt = dt_util.utcnow()`, `now_ts = now_dt.timestamp()`, `local_date = dt_util.as_local(now_dt).date().isoformat()`, esegue `self._charging_tracker.ingest(...)` sotto `with self._charging_lock:` (`try...finally` garantito dal context manager `with`), e **fuori** dal lock schedula `self._charging_store.async_delay_save(self._charging_snapshot, 30)` se `changed and not self._timers.closing`.
   - `onFailure:` se `self._timers.closing` è True, no-op; frame degradati (`is_degraded_battery_frame(rt)`) scartati prima di toccare i baseline; eccezioni di I/O su `async_delay_save` loggate senza interrompere `async_set_updated_data`.
3. **Store Flush (`async_flush_charging_stats` in `async_unload_entry`)**:
   - `onSuccess:` cattura `snapshot = self._charging_snapshot()` sotto `_charging_lock` ed esegue `await self._charging_store.async_save(snapshot)`.
   - `onFailure:` catch `Exception`, log `WARNING` senza far fallire l'unload dell'entry.
4. **Reset `From Start` (`async_reset_charging_from_start`)**:
   - `onSuccess:` azzera `_from_start` sotto `_charging_lock`, esegue `await self._charging_store.async_save(snapshot)` e chiama `self.async_update_listeners()` se `not self._timers.closing`.
   - `onFailure:` catch `Exception` sul save, log `WARNING`, notifica comunque i listener così la UI riflette l'azzeramento in memoria.
5. **UI Reset Dialog (`LepasStatsCard`)**:
   - `onSuccess:` tap su pulsante reset -> apre dialog di conferma -> conferma disabilita temporaneamente il bottone (lock anti-doppio-click in volo) e chiama `hass.callService("button", "press", { entity_id })` -> in `finally`/then-catch riabilita bottone, chiude dialog e pulisce `_pendingDialogAction`; su `disconnectedCallback()` ripulisce listener e dialog.
   - `onFailure:` annullamento / Escape / click esterno chiude dialog senza chiamare `callService`; errore di rete in `callService` gestito senza lasciare il dialog bloccato né il bottone disabilitato.

---

## Tasks

### Task 1: Pure Python Engine `charging_stats.py` & Shared Hybrid Integrator

**Files:**
- Create: `custom_components/lepas/charging_stats.py`
- Test: `tests/test_charging_stats.py`

**Interfaces:**
- Consumes: `CHARGE_ENERGY_MAX_GAP` (`const.py`), `_safe_float` / `is_degraded_battery_frame` (`consumption.py` o helper locale coerente), `DEFAULT_BATTERY_CAPACITY_KWH` (`const.py`).
- Produces:
  - `compute_charge_delta_kwh(prev_ts: float | None, prev_power_kw: float, prev_soc_pct: float | None, prev_odo_km: float | None, prev_charging: bool, *, now_ts: float, power_kw: float, soc_pct: float | None, odo_km: float | None, charging: bool, plugged: bool, degraded_battery: bool, battery_capacity_kwh: float, max_gap_s: float = CHARGE_ENERGY_MAX_GAP) -> tuple[float, bool]` (`(delta_kwh, reset_continuity)`)
  - `ChargingStatsTracker` con:
    - `ingest(now_ts: float, local_date: str, *, power_kw: float | None, charge_state: object, plugged: bool, soc_pct: float | None, odometer: float | None, in_home_zone: bool | None, degraded_battery: bool, battery_capacity_kwh: float) -> bool`
    - `period_stats(period: str, current_local_date: str) -> dict[str, Any]` (`period in ("today", "month", "year", "from_start")`)
    - `reset_from_start() -> None`
    - `to_dict() -> dict[str, Any]`
    - `from_dict(cls, raw: dict | None) -> ChargingStatsTracker`

- [ ] **Step 1: Write failing tests in `tests/test_charging_stats.py`**
  - **Test Falsification Mandate**: ogni test asserisce calcoli esatti (nessun mock della funzione sotto test); se `compute_charge_delta_kwh` sommasse entrambi trapezio e SoC, o ignorasse `degraded_battery`, o non azzerasse al rollover di `local_date`, i test falliscono immediatamente.
  - Casi da coprire:
    1. `test_trapezoidal_within_max_gap`: 2.0 kW per 120s -> `0.06667 kWh`, no doppio conteggio anche se `soc_pct` sale nello stesso intervallo.
    2. `test_gap_reconciles_with_soc_delta`: gap `> 300s` (es. 1800s) con auto collegata e SoC `30% -> 50%` su `18.4 kWh` -> recupera esattamente `3.68 kWh`; se SoC invariato (`30% -> 30%`) -> `0.0 kWh`.
    3. `test_degraded_battery_frame_ignored`: frame con `degraded_battery=True` non produce kWh e non sovrascrive `prev_soc`.
    4. `test_odometer_advance_resets_continuity`: avanzamento odometro `> 0.1 km` tra due letture azzera la continuità ed evita recupero SoC spurio.
    5. `test_period_rollover_ingest_and_read`: cambio giorno/mese/anno azzera `today`/`month`/`year` sia su nuovo `ingest` sia su `period_stats(..., current_local_date)` in sola lettura, preservando `from_start`.
    6. `test_zone_attribution_and_none_preserves_total`: `in_home_zone=True` -> `home_kwh` + `total_kwh`; `False` -> `away_kwh` + `total_kwh`; `None` -> solo `total_kwh`.
    7. `test_sessions_count_and_series_pruning`: conteggio sessioni su carica continua senza duplicati, potatura a 30 giorni (`daily_series`) e 12 mesi (`monthly_series`).
    8. `test_reset_from_start_and_resilient_from_dict`: `reset_from_start()` azzera solo `from_start`; `from_dict` tollera JSON corrotti/NaN/negativi.
    9. `test_unplugged_soc_drift_ignored`: con `prev_charging=False, charging=False, plugged=False` e `dt_s > 300s`, un aumento di SoC (es. `50% -> 52%`) produce `delta_kwh == 0.0`.
    10. `test_gap_recovered_session_counted`: un buco `> 300s` con `plugged=True` e salto SoC `30% -> 50%` (anche con `charging=False` sul frame finale) incrementa `sessions_count` di `1` oltre ai kWh.
    11. `test_trapezoidal_requires_prev_charging_and_positive_dt`: primo campione `charging=True` con `prev_charging=False` produce `0.0`; `dt_s <= 0` produce `0.0`; `soc_pct` fuori `[0, 100]` o `battery_capacity_kwh <= 0` fail-closed (`0.0`).
    12. `test_fields_only_power_none_preserves_trapezoid`: con `_prev_charging=True` e `power_kw=None` (push MQTT `fields`-only): (a) se `plugged=True` / `charge_state == 1`, NON sovrascrive `_prev_ts`/`_prev_power_kw`/`_prev_charging` così il campione `realtime` successivo continua correttamente il trapezio (ed esegue riconciliazione SoC se `dt_s > 300s`); (b) se `not plugged` o `charge_state == 0` o odometro avanzato (`> 0.1 km`), azzera `_prev_charging=False` e `_prev_power_kw=0.0` chiudendo la continuità.

- [ ] **Step 2: Run failing tests**
  - Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_charging_stats.py -q` (Expected: `ModuleNotFoundError` / FAIL).

- [ ] **Step 3: Implement `custom_components/lepas/charging_stats.py`**
  - Riutilizza `_safe_float` da `.consumption`, `CHARGE_ENERGY_MAX_GAP` e `DEFAULT_BATTERY_CAPACITY_KWH` da `.const`.
  - Implementa `compute_charge_delta_kwh`, `_Bucket`, e `ChargingStatsTracker`.
  - Semantica esplicita di `ChargingStatsTracker.ingest(..., power_kw=None)`: quando `power_kw is None` (push `fields`-only senza nuovo `realtime`), se `not plugged` o `charge_state == 0` o odometro avanzato (`> 0.1 km`) azzera `_prev_charging = False, _prev_power_kw = 0.0` (e aggiorna `_prev_ts`/`_prev_soc`); se `plugged` (o `charge_state == 1`) è ancora `True`, preserva `_prev_ts`, `_prev_power_kw` e `_prev_charging` per il segmento trapezoidale successivo (eseguendo comunque eventuale riconciliazione delta SoC se `dt_s > 300s`).

- [ ] **Step 4: Run tests to verify PASS**
  - Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_charging_stats.py -q` (Expected: PASS).

---

### Task 2: Coordinator Store Lifecycle & `LepasChargedEnergy` Hybrid Upgrade

**Files:**
- Modify: `custom_components/lepas/coordinator.py` (around `__init__` L459-465, `async_start` L680-686, `_apply_update` L2268-2275, plus new charging stats methods right after `_ingest_consumption` L678)
- Modify: `custom_components/lepas/__init__.py:565-568` (`async_unload_entry` flush)
- Modify: `custom_components/lepas/sensor.py:622-717` (`LepasChargedEnergy._campiona`)
- Modify: `tests/test_energia_ricarica.py`

**Interfaces:**
- Consumes: `ChargingStatsTracker`, `compute_charge_delta_kwh` (`charging_stats.py`), `in_zona_casa` (`entity.py`), `dt_util` (`homeassistant.util.dt`).
- Produces:
  - `LepasCoordinator.async_load_charging_stats() -> None`
  - `LepasCoordinator.async_flush_charging_stats() -> None`
  - `LepasCoordinator.charging_stats(period: str) -> dict[str, object]`
  - `LepasCoordinator.async_reset_charging_from_start() -> None`
  - `LepasCoordinator._ingest_charging_stats_on_loop(patch: dict) -> None`

- [ ] **Step 1: Update & add failing tests**
  - Aggiornare `tests/test_energia_ricarica.py`:
    - `test_buco_lungo_senza_soc_non_inventa_energia`: gap `> CHARGE_ENERGY_MAX_GAP` senza salto SoC resta `0.0`.
    - `test_buco_lungo_recupera_da_delta_soc`: gap `> CHARGE_ENERGY_MAX_GAP` con `dumpEnergy` da `30` a `70` e `battery_capacity_kwh=18.4` recupera `7.36 kWh` nella zona attiva, mantenendo monotonicità.
    - `test_degraded_e_cambio_zona_non_inquinano_baseline`: `degraded_battery=True` non altera `_ultimo_soc`; cambio zona (`True -> False`) resetta continuità senza attribuire energia alla zona sbagliata; `a_casa is None` non avanza `_ultimo_soc` finché l'odometro resta invariato; `cmd_status` o listener update non-realtime (`rt is self._ultimo_rt`) non ri-integra.
  - Aggiungere in `tests/test_charging_stats.py` test coordinator `Store`: `load`, `delay_save` (con mock che invoca subito `snapshot_fn()` per verificare assenza deadlock su `_charging_lock`), `flush`, `async_reset_charging_from_start`, `_apply_update({"cmd_status": "ok"})` / `{"position": ...}` no-op, push MQTT `fields`-only che non riusa un vecchio `realtime.chargingPower`, e `hass.states` mockato con `MagicMock` gestito senza errori.
  - **Test Falsification Mandate**: asserire i valori numerici reali di `LepasChargedEnergy.native_value` e del `Store` mockato/persistito; se `_campiona` non chiamasse `compute_charge_delta_kwh`, o `_ingest_charging_stats_on_loop` re-ingerisse su `cmd_status`, o `async_delay_save` fosse chiamato dentro `_charging_lock`, il test fallisce immediatamente.

- [ ] **Step 2: Run tests to verify FAIL**
  - Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_energia_ricarica.py tests/test_charging_stats.py -q`

- [ ] **Step 3: Implement Coordinator & `LepasChargedEnergy`**
  - `coordinator.py`: aggiungere `self._charging_lock`, `self._charging_tracker`, `self._charging_store`, `async_load_charging_stats`, `_charging_snapshot`, `_schedule_charging_save`, `async_flush_charging_stats`, `charging_stats`, `async_reset_charging_from_start`, `_ingest_charging_stats_on_loop(patch)` invocato in `_apply_update(patch)`. Rispettare rigorosamente: `now_ts = dt_util.utcnow().timestamp()`, filtro `"realtime" not in patch and "fields" not in patch`, precedenza `sources = (patch["realtime"], self.data.get("fields") or {})` se `"realtime" in patch` vs `(patch.get("msg_fields") or {}, patch.get("fields") or {})` (`AB-LEP-014`, `power_kw = None`, `degraded_battery = False`) se `"realtime" not in patch`, `async_delay_save` **fuori** da `with self._charging_lock:`, e helper difensivo per `in_zona_casa` quando `hass`/`hass.states` è mockato nei test.
  - `__init__.py`: chiamare `await coordinator.async_flush_charging_stats()` in `async_unload_entry`.
  - `sensor.py`: aggiornare `LepasChargedEnergy.__init__` / `_campiona` usando `now_ts = dt_util.utcnow().timestamp()`, leggendo `soc` (`dumpEnergy`), `odo` (`odometer`) e `plugged` (`chargeGunState`/`fastChargingGunStatus`) da `(rt, fields)` (con `rt = data.get("realtime")`, `fields = data.get("fields") or {}`), tracciando `_ultimo_soc`, `_ultimo_odo`, e riferimento `_ultimo_rt = None` (salva riferimento oggetto `rt`, non `id(rt)` intero riciclabile dopo GC: salta la re-integrazione quando `rt is self._ultimo_rt` su aggiornamenti listener non-realtime come `cmd_status`, `set_poll_enabled`, `async_reset_charging_from_start`), e delegando il calcolo delta a `compute_charge_delta_kwh(..., battery_capacity_kwh=getattr(self.coordinator, "battery_capacity_kwh", DEFAULT_BATTERY_CAPACITY_KWH))` (continuità a runtime; cross-restart gestito da `ChargingStatsTracker` + `Store`). Regole esatte di aggiornamento baseline in `_campiona()`:
    1. Se `rt is self._ultimo_rt`: ritorna subito (nessuna doppia integrazione su notifiche non-realtime).
    2. Se `is_degraded_battery_frame(rt)`: aggiorna `self._ultimo_rt = rt` e ritorna senza toccare `_energia_wh` né i baseline (`_ultimo_ts`, `_ultima_potenza`, `_ultimo_soc`, `_ultimo_odo`, `_era_attivo`).
    3. Se `a_casa is None`: aggiorna `self._ultimo_rt = rt`; se `self._ultimo_odo is not None and odo is not None and odo > self._ultimo_odo + 0.1`, resetta continuità (`_ultimo_ts = None`, `_era_attivo = False`, `_ultima_potenza = 0.0`, `_ultimo_odo = odo`, `_ultimo_soc = soc`); altrimenti non avanzare `_ultimo_soc` né `_ultimo_ts` per non perdere il recupero delta SoC al ritorno del fix GPS.
    4. Se `a_casa != self._home` (altra zona): resetta continuità (`_era_attivo = False`, `_ultimo_ts = None`, `_ultima_potenza = 0.0`) e aggiorna `self._ultimo_rt = rt`, `_ultimo_soc = soc`, `_ultimo_odo = odo` così il cambio zona `casa <-> fuori` non travasa energia tra contatori.
    5. Se `a_casa == self._home`: calcola `delta_kwh, reset_cont = compute_charge_delta_kwh(...)`; se `delta_kwh > 0`, incrementa `self._energia_wh += delta_kwh * 1000.0`; aggiorna `self._ultimo_rt = rt`, `_ultimo_ts = now_ts`, `_ultima_potenza = 0.0 if reset_cont else potenza`, `_ultimo_soc = soc`, `_ultimo_odo = odo`, `_era_attivo = False if reset_cont else carica`.

- [ ] **Step 4: Run tests to verify PASS**
  - Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_energia_ricarica.py tests/test_charging_stats.py -q`

---

### Task 3: New HA Entities (4 Sensors + 1 Reset Button) & Translations

**Files:**
- Modify: `custom_components/lepas/sensor.py` (add `_CHARGING_STATS_SPECS`, `LepasChargingStatsSensor`, instantiate in `async_setup_entry`)
- Modify: `custom_components/lepas/button.py` (add `reset_charging_from_start` `LepasActionButton` + `_ICONS`)
- Modify: `custom_components/lepas/strings.json`, `custom_components/lepas/translations/{en,it,nl}.json`
- Modify: `tests/test_entity_count.py` (`sensor: 50 -> 54`, `button: 16 -> 17`, `TOTALE_ATTESO: 142 -> 147`)

**Interfaces:**
- Consumes: `LepasCoordinator.charging_stats(period)`, `LepasCoordinator.async_reset_charging_from_start()`.
- Produces:
  - `sensor.lepas_charging_energy_today` (attr: `home_kwh`, `away_kwh`, `sessions_count`, `period_key`, `daily_series`)
  - `sensor.lepas_charging_energy_month` (attr: `home_kwh`, `away_kwh`, `sessions_count`, `period_key`)
  - `sensor.lepas_charging_energy_year` (attr: `home_kwh`, `away_kwh`, `sessions_count`, `period_key`, `monthly_series`)
  - `sensor.lepas_charging_energy_from_start` (attr: `home_kwh`, `away_kwh`, `sessions_count`, `period_key`)
  - `button.lepas_reset_charging_from_start`

- [ ] **Step 1: Add failing entity & translation tests**
  - Aggiornare `tests/test_entity_count.py` a `sensor: 54`, `button: 17`, `TOTALE_ATTESO = 147`.
  - Aggiungere test in `tests/test_charging_stats.py` per `LepasChargingStatsSensor` (`state_class == TOTAL`, `device_class == ENERGY`, attributi `home_kwh`/`away_kwh`/`daily_series`/`monthly_series`) e `reset_charging_from_start` button press.

- [ ] **Step 2: Run tests to verify FAIL**
  - Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_entity_count.py tests/test_traduzioni_complete.py tests/test_translation_key_declared.py tests/test_charging_stats.py -q`

- [ ] **Step 3: Implement Sensors, Button, and Translations (`strings.json`, `en`, `it`, `nl`)**
  - `LepasChargingStatsSensor` replica il pattern di `LepasConsumptionSensor` (`object_id=f"{ID_PREFIX}_{spec.key}"`, `translation_key=spec.key`) ed è istanziato per tutti i veicoli (BEV e PHEV).

- [ ] **Step 4: Run tests to verify PASS**
  - Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_entity_count.py tests/test_traduzioni_complete.py tests/test_translation_key_declared.py tests/test_charging_stats.py tests/test_sensors.py -q`

---

### Task 4: Lovelace Main Card Cleanup (`LepasCard`) & New `LepasStatsCard` + `LepasStatsCardEditor`

**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js`
- Modify: `tests/lepas_card.test.mjs`
- Modify: `tests/test_lovelace_card.py`

**Interfaces:**
- Consumes HA entities: `sensor.*charging_energy_{today,month,year,from_start}`, `button.*reset_charging_from_start`, `sensor.*average_energy_consumption`, `sensor.*ev_consumption_{100km,1000km,from_start}`, `sensor.*average_fuel_consumption`, `sensor.*hybrid_consumption_{100km,1000km,from_start}`, `button.*reset_consumption_from_start`.
- Produces in `lepas-card.js`:
  - `LepasCard` senza `consSection` in *Panoramica*
  - `LepasStatsCard` (`<lepas-stats-card>`) + `LepasStatsCardEditor` (`<lepas-stats-card-editor>`)
  - `window.customCards.push({ type: "lepas-stats-card", name: "Lepas Stats Card", preview: true, description: "..." })`
  - `I18N` `it`, `en`, `nl` completi per titoli, periodi (`Oggi/Mese/Anno/Da inizio`), scope (`Tutte/Casa/Fuori`), grafici (`7g/30g/12m`), reset e conferme.

- [ ] **Step 1: Update & add failing JS & Python contract tests**
  - Aggiornare `tests/lepas_card.test.mjs`:
    - Verificare che `LepasCard` non renderizzi più `.cons-section` nella tab Overview e migrare su `LepasStatsCard` tutti i test esistenti di *Consumi medi* (mantenendo tutte le 4 celle EV + 4 Ibrida, incluso `50 km` via `average_energy_consumption` / `average_fuel_consumption`, e il caso BEV che nasconde Ibrido).
    - Testare `LepasStatsCard`: registrazione `window.customCards` (`type: "lepas-stats-card"` con guardia anti-duplicazione, `getStubConfig().type === "custom:lepas-stats-card"`), render KPI `Oggi/Mese/Anno/Da inizio`, click sulle celle KPI/consumi -> emissione evento `hass-more-info` con `entityId`, switch `Tutte | Casa | Fuori` che cambia i valori mostrati dai rispettivi attributi, grafico SVG `7g | 30g | 12m` (barre impilate `Casa` + `Fuori` + stato vuoto), click su entrambe le icone reset -> apertura dialog conferma -> conferma (con lock anti-doppio-click in volo) chiama `hass.callService("button", "press", ...)`, annullamento non chiama `callService`, `show_reset_buttons: false` (o entità button assente) nasconde le icone reset, editor `LepasStatsCardEditor` (`show_charging`, `show_consumption`, `show_chart`, `show_reset_buttons`, `default_scope`, `default_chart`), escape XSS su `config.title` (es. `<img src=x onerror=alert(1)>` reso come testo sicuro senza iniezione HTML/SVG), localizzazione `it`/`en`/`nl`.
  - Aggiornare `tests/test_lovelace_card.py`: verificare registrazione `'type: "lepas-stats-card"'` in `window.customCards` oltre ai controlli statici già presenti (`?.`, `??`, `#00D2FF`, `:host-context`).

- [ ] **Step 2: Run JS & Python tests to verify FAIL**
  - Run: `node --test tests/lepas_card.test.mjs` and `/home/federico/.local/bin/uv run --with pytest pytest tests/test_lovelace_card.py -q`

- [ ] **Step 3: Implement `lepas-card.js` changes**
  - Rimuovere `consSection` e i relativi binding da `LepasCard`.
  - Estrarre/condividere helper leggeri in scope IIFE (`collectIntegrationItems`, `findDomainEntity`, `formatMetric`, `openConfirmDialog` / CSS condivisi) per evitare duplicazione.
  - Implementare `LepasStatsCardEditor` e `LepasStatsCard` rispettando tutti i vincoli (`?.`/`??` assenti ovunque, Zero `#00D2FF`, Zero `:host-context`, `container-type: inline-size`, Matte Titanium tokens, SVG puro per grafico a barre `7g/30g/12m`, uso rigoroso di `escapeHtml(...)` o `.textContent`/`.value` su ogni stringa/etichetta/attributo utente o serie interpolata in HTML/SVG).

- [ ] **Step 4: Run JS & Python tests to verify PASS**
  - Run: `node --check custom_components/lepas/lovelace/lepas-card.js && node --test tests/lepas_card.test.mjs`
  - Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_lovelace_card.py -q`

---

### Task 5: Full Verification, Dual-Gate Audit, SemVer Release (`v1.30.0`) & Graph Sync

**Files:**
- Modify: `custom_components/lepas/manifest.json`, `pyproject.toml`, `custom_components/lepas/lovelace/lepas-card.js` (`CARD_VERSION` + `?v=1.30.0`), `CHANGELOG.md`, `tests/test_lovelace_card.py` (aggiornare assertion `?v=1.30.0`), `docs/architecture.md` / `.agents/memory/antibodies/lepas.md` (se necessario)

- [ ] **Step 1: Bump SemVer `1.30.0` (minor feature) & update `CHANGELOG.md` (IT + EN)**
- [ ] **Step 2: Run full test suite & linters**
  - `/home/federico/.local/bin/uv run --with pytest pytest -q --tb=short --maxfail=2`
  - `node --test tests/lepas_card.test.mjs`
  - `/home/federico/.local/bin/uv run ruff check custom_components/ tests/`
  - `/home/federico/.local/bin/uv run ruff format --check custom_components/ tests/`
- [ ] **Step 3: Tier 3 Dual-Gate Review & `git write-tree` lock**
  - Pass 1: `local_llm_offload.py --task review-hygiene --files ... --json` (+ auditor `flash` per UI).
  - Pass 2: Sentinel `inherit` (riuso CID `4b85af27-77c4-4c82-9814-7b0a7cfd94ef` via `send_message`) con sigillo `APPROVED_TREE=$(git write-tree)`.
- [ ] **Step 4: `graphify update .` & `codegraph sync`, Commit, Tag `v1.30.0`, Push (solo su conferma Push Gate utente se richiesta)**
