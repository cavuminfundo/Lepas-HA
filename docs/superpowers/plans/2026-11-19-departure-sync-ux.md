# Departure Schedule Sync UX, Full-Plan Dirty Tracking & Disable Service — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendere il pulsante partenza della card Lovelace consapevole delle modifiche su **tutto** il piano settimanale/rapido (`has_pending_changes`) e dello stato dell'auto (`synced_with_ha`), attivare automaticamente l'avanzamento tra occorrenze (`native_departure_sync`) all'invio con **Applica su auto**, e introdurre **Disattiva piano** (`lepas.disable_departure_schedule`) per spegnere atomicamente auto, giorni/rapida HA e auto-sync.

**Architecture:** `LepasCoordinator` serializza tutte le mutazioni/sync di partenza sotto `self._departure_lock = asyncio.Lock()` e calcola una firma JSON canonica dell'intero piano (`departure_schedule_signature()`), esposta e ripristinata via `LepasDeparturePlan` (`sensor.lepas_scheduled_departure`). Le modifiche nella UI (`switch.py`/`time.py`) chiamano `notify_schedule_changed(..., sync_native=False)` restando bozze locali finché l'utente non preme **Applica su auto** (`enable_native_sync=True`) o non disattiva tramite `lepas.disable_departure_schedule` (fail-closed prima del reset HA). La card `LepasCard` in `lepas-card.js` implementa una macchina a 3 stati ES5 (`hidden` + `.hidden`, `Applica su auto`, `Disattiva piano`) guidata da `has_pending_changes`, `synced_with_ha`, `carActive` e `haHasActiveDep`.

**Tech Stack:** Python >=3.12, Home Assistant `DataUpdateCoordinator`, `RestoreSensor`, `asyncio.Lock`, JavaScript ES5 Web Component (`LepasCard`), `pytest`, `node --test`, `ruff`, `uv`.

**Spec:** [docs/superpowers/specs/2026-11-19-departure-sync-ux-design.md](file:///home/federico/Lepas/docs/superpowers/specs/2026-11-19-departure-sync-ux-design.md)

## Global Constraints
- Serializzazione obbligatoria con `self._departure_lock = asyncio.Lock()` tra `_async_apply_departure_schedule_locked`, `async_disable_departure_schedule`, `async_set_quick_departure`, e `_departure_tick_cb` (con early return `if self._timers.closing or self._departure_busy or self._departure_lock.locked(): return` nel tick).
- Nessun invio accidentale durante editing bozze: `LepasWeeklyDepartureSwitch`, `LepasTimeEntity` (`quick_departure_minutes`), `LepasWeeklyDepartureTime`, `LepasScheduleSwitch(sync_mode="departure")` passano `sync_native=False`; `_departure_tick_cb` usa `(not weekly_dirty or (quick_expired and occ is None))` per non inviare mai bozze settimanali non applicate.
- `async_set_quick_departure(apply_native=True)` passa `enable_native_sync=False` per preservare il contratto una-tantum `_quick_applied_native`.
- `async_disable_departure_schedule` invia `partenza_prog_off` **prima** di azzerare i giorni HA (`onFailure`: stato locale preservato); zero nuove entità HA (`test_entity_count.py` invariato).
- `lepas-card.js` resta compatibile ES5 (zero `?.`, zero `??`), usa `applyDepBtnEl.hidden = true/false` oltre a `.hidden` (`accessibility`), mantiene `vm.applyDepBtn` gating, e inizializza `sdRawAttrs` null-safe prima di leggere proprietà.
- Rispetto Crash Antibodies `AB-LEP-001`..`AB-LEP-013` (in particolare `AB-LEP-010`, `AB-LEP-012`, `AB-LEP-013`).
- Versioning sincronizzato a `1.24.0` (`manifest.json`, `pyproject.toml`, `lepas-card.js`, `tests/test_lovelace_card.py`, `tests/lepas_card.test.mjs`, `CHANGELOG.md`).

---

## Dual-Gate Audit Matrix (Pre-Execution)

| Gate | Sub-Agent Role | Model | Conversation ID | Verdict | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Stage 1 | Domain & Archaeology Pre-Audit | `flash` | `c517b59b-3b1a-4e42-8673-251c21701a26` | `FAIL -> Fixed` | Risolti: `_departure_lock`, `sdRawAttrs` + `btn.hidden = false`, guardia `quick_expired` su bozze dirty, `async_get_last_state()` su `LepasDeparturePlan`, rimozione dead call `_sync_battery_heat_start_local(None)`, `_async_unregister_services` |
| Stage 2 | Six-Pillars Sentinel Control Gate | `inherit` | `c51a768a-d17d-4dc1-ab20-710e40628708` | `REJECTED -> Fixed` | Risolti in spec & piano prima dell'esecuzione: (1) guardia tick `(not weekly_dirty or (quick_expired and occ is None))`, (2) `enable_native_sync=False` in `async_set_quick_departure(apply_native=True)`, (3) `car_active is True or (car_active is None and _applied_schedule_sig is not None)` in `has_pending_departure_changes()`, (4) `this._currentEntryId` + gating `vm.applyDepBtn` verificati |

---

### Domain Skills & Sub-Agent Roster

| Dominio Coeso | Skill Primaria & Companions (`lookup.py`) | Sub-Agente / Modello | File Assegnati (Contratto End-to-End) |
| :--- | :--- | :--- | :--- |
| **Backend Coordinator, Sensor Restore, Switches & Service** | `python-development` + `ponytail` + `antislop-code` | `lepas_backend_worker` (`Model: 'pro'`, file >600L + `asyncio.Lock` concorrente) | `custom_components/lepas/coordinator.py`, `custom_components/lepas/sensor.py`, `custom_components/lepas/switch.py`, `custom_components/lepas/time.py`, `custom_components/lepas/__init__.py`, `custom_components/lepas/services.yaml`, `tests/test_native_departure_battery.py` |
| **Lovelace Card 3-State UX & Release 1.24.0** | `modern-web-guidance` (`accessibility`) + `ponytail` + `antislop-code` | `lepas_card_worker` (`Model: 'flash'`) | `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`, `custom_components/lepas/manifest.json`, `pyproject.toml`, `CHANGELOG.md` |

---

## Blast Radius & StateGraph

### `BlastRadius` (da CodeGraph & `--task archaeology`)
- `direct_files`:
  - `custom_components/lepas/coordinator.py` (`__init__`, `departure_schedule_signature`, `_weekly_signature_part`, `has_active_departure_schedule`, `_is_car_departure_active`, `has_pending_departure_changes`, `restore_applied_schedule_sig`, `_async_apply_departure_schedule_locked`, `async_apply_departure_schedule`, `async_disable_departure_schedule`, `async_set_quick_departure`, `_async_sync_native_departure`, `_departure_tick_cb`)
  - `custom_components/lepas/sensor.py` (`LepasDeparturePlan.async_added_to_hass`, `extra_state_attributes`)
  - `custom_components/lepas/switch.py` (`LepasScheduleSwitch._SYNC_MODES["departure"]`, `LepasWeeklyDepartureSwitch._set_enabled`)
  - `custom_components/lepas/time.py` (`LepasTimeEntity.async_set_value`, `LepasWeeklyDepartureTime.async_set_value`)
  - `custom_components/lepas/__init__.py` (`SERVICE_DISABLE_DEPARTURE_SCHEDULE`, `_DISABLE_DEPARTURE_SCHEMA`, `_async_register_services`, `_async_unregister_services`)
  - `custom_components/lepas/services.yaml` (`disable_departure_schedule`)
  - `custom_components/lepas/lovelace/lepas-card.js` (`CONFIRM_ACTIONS`, `I18N`, `actions["disable_departure_schedule"]`, `_applyBindingsInner`, `CARD_VERSION`)
  - `tests/test_native_departure_battery.py`, `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`
  - Metadata release `1.24.0`: `custom_components/lepas/manifest.json`, `pyproject.toml`, `CHANGELOG.md`
- `transitively_affected`:
  - `custom_components/lepas/button.py` (`LepasActionButton` → `coord.async_apply_departure_schedule`)
  - `tests/test_config_ux.py`, `tests/test_scheduler.py`, `tests/test_entity_count.py`
- `uncertain`:
  - Nessun cambio al conteggio entità HA (`test_entity_count.py` invariato); eventuale presenza di vecchi test che chiamano switch settimanali aspettandosi invio automatico immediato prima di premere `Applica` (coperti in Task 1/2 e verificati sull'intera suite).

### `StateGraph` (`onSuccess:` / `onFailure:` & Concurrency)
1. **Local Edit (`switch.py`, `time.py`)**:
   - Mutates `departure_weekly[d]` or `quick_departure_*`, calls `notify_schedule_changed(..., sync_native=False)` -> updates `next_departure_occurrence` + listeners (`has_pending_changes == True`), **never** calls TSP `appointmentTravel`.
2. **`async_apply_departure_schedule()` -> `_async_apply_departure_schedule_locked(enable_native_sync=True)`**:
   - Acquires `self._departure_lock`.
   - Calls `await self.async_send_command(cmd_key, body)`.
     - `onFailure`: raises `CommandError`, leaves `_applied_schedule_sig`, `native_departure_sync`, and `_last_synced_native_dep_sig` untouched.
     - `onSuccess`: if `occ is not None`, sets `_applied_schedule_sig = departure_schedule_signature()` and (when `enable_native_sync=True`) `native_departure_sync = True`; if `occ is None`, clears `_applied_schedule_sig = None`, `native_departure_sync = False`, `_quick_applied_native = False`. Calls `async_update_listeners()`, `_async_refresh_travel_appoint_realtime()`, schedules `_post_settle_travel_refresh()`.
3. **`async_disable_departure_schedule()` (`lepas.disable_departure_schedule`)**:
   - Acquires `self._departure_lock`.
   - Builds `cmd_key, body, _ = self._build_native_departure_payload(None)` and calls `await self.async_send_command(cmd_key, body)` **before** clearing local HA schedule.
     - `onFailure`: propagates `CommandError`, preserves weekly/quick HA switches and `_applied_schedule_sig`.
     - `onSuccess`: disables `quick_departure_enabled`, all 7 `departure_weekly[d]`, `native_departure_sync = False`, `_applied_schedule_sig = None`, `_last_synced_native_dep_sig = None`, `_last_attempted_native_dep_sig = None`, `_quick_applied_native = False`; notifies listeners; if `sync_battery_heat_to_departure` calls `await self._async_sync_battery_for_occurrence(None)`; refreshes `realtime`.
4. **`_departure_tick_cb()`**:
   - Early return if `self._timers.closing or self._departure_busy or self._departure_lock.locked()`.
   - Acquires `self._departure_lock`.
   - Computes `weekly_dirty`. Only invokes `_async_sync_native_departure(occ)` when `(not weekly_dirty or (quick_expired and occ is None))` and `(self.native_departure_sync or (quick_expired and self._quick_applied_native))`.
   - Updates `_applied_schedule_sig` on `quick_expired` only if `_async_sync_native_departure` succeeded (`True` or already at `sig`); on failure keeps state for retry on next tick.

### `Test Falsification Mandate`
- Se `has_pending_departure_changes()` usasse solo `synced_with_ha`, modificare Venerdì con Giovedì sincronizzato non attiverebbe `Applica su auto` (test Python falserà).
- Se `LepasWeeklyDepartureSwitch` / `LepasWeeklyDepartureTime` chiamassero ancora `sync_native=True`, il test di modifica settimanale con `native_departure_sync=True` registrerebbe un comando TSP indesiderato (falserà).
- Se `async_disable_departure_schedule` azzerasse HA prima del comando e `async_send_command` fallisse, i test `onFailure` fallirebbero trovando i giorni spenti.
- Se `_departure_tick_cb` non avesse `_departure_lock` o la guardia `(not weekly_dirty or (quick_expired and occ is None))`, i test su bozza tutto-OFF o su race tick vs disable fallirebbero.
- Se `lepas-card.js` non gestisse `sdRawAttrs` null-safe o `btn.hidden = false`, i test JSDOM su entità assente o transizione hidden→visibile fallirebbero.

---

### Task 1: Coordinator Full-Plan Signature, Lock, Apply, Disable & Tick Guard (Backend TDD)

**Files:**
- Modify: `custom_components/lepas/coordinator.py:445-455`, `829-975`, `1128-1230`, `1420-1496`
- Modify: `custom_components/lepas/switch.py:864-870`, `1022-1030`
- Modify: `custom_components/lepas/time.py:143-154`, `198-206`
- Test: `tests/test_native_departure_battery.py`

**Interfaces:**
- Produces on `LepasCoordinator`:
  - `_departure_lock: asyncio.Lock`
  - `_applied_schedule_sig: str | None`
  - `departure_schedule_signature() -> str`
  - `has_active_departure_schedule() -> bool`
  - `has_pending_departure_changes() -> bool`
  - `restore_applied_schedule_sig(raw_sig: str | None) -> None`
  - `async_apply_departure_schedule() -> None` (delegates to `_async_apply_departure_schedule_locked(enable_native_sync=True)`)
  - `async_disable_departure_schedule() -> None`
  - `_async_sync_native_departure(occ: DepartureOccurrence | None) -> bool`

- [ ] **Step 1: Scrivere i test Python falsificabili in `tests/test_native_departure_battery.py` (RED)**

Aggiungere alla suite esistente test su contratto reale (`LepasCoordinator`, `LepasDeparturePlan`, `hass.services.async_call`):
1. `test_full_plan_dirty_tracking_friday_edit_while_thursday_synced`:
   - Imposta Gio `13:25` + Ven `06:00` + Sab `06:00`, invoca `coord.async_apply_departure_schedule()` (con realtime aggiornato a `travelTime=745`, `travelDate=[4]`).
   - Verifica `coord.native_departure_sync is True`, `coord.has_pending_departure_changes() is False`.
   - Modifica Ven `06:00 -> 07:30` via `LepasWeeklyDepartureTime` / `LepasWeeklyDepartureSwitch`: verifica **zero** chiamate `partenza_prog_on` immediate durante l'editing, `coord.has_pending_departure_changes() is True` anche se Giovedì sull'auto combacia ancora (`synced_with_ha` su Giovedì).
2. `test_tick_auto_advance_thursday_to_friday_saturday_and_draft_guard`:
   - Con Gio `13:25` + Ven `06:00` + Sab `06:00` applicati (`native_departure_sync=True`), avanza il clock alle `13:26` CET: `_departure_tick_cb` invia automaticamente `partenza_prog_on` per `06:00` su `[5, 6]` e aggiorna `realtime`.
   - Poi spegne in bozza tutti i giorni (`occ is None`, `weekly_dirty=True`): verifica che `_departure_tick_cb` **NON** invia `partenza_prog_off` a metà modifica della bozza!
3. `test_disable_departure_schedule_success_and_fail_closed`:
   - `async_disable_departure_schedule()` con successo: invia `partenza_prog_off`, spegne tutti i 7 giorni + `quick_departure_enabled` + `native_departure_sync = False`, azzera `_applied_schedule_sig = None`, aggiorna `realtime` (`mainSwitcher: 0`), `has_pending_departure_changes() is False`.
   - Se `async_send_command` solleva `CommandError`: i giorni attivi e `_applied_schedule_sig` e `native_departure_sync` restano intatti (fail-closed).
4. `test_quick_departure_service_apply_native_preserves_manual_sync_and_expiry`:
   - `set_quick_departure(apply_native=True)` con `native_departure_sync=False` lascia `native_departure_sync is False` e usa `_quick_applied_native=True`; alla scadenza (`quick_expired`) invia `partenza_prog_off` (o ripristina settimanale non-dirty) e su failure mantiene retry al tick successivo.
5. `test_departure_lock_prevents_tick_race_during_disable`:
   - Mentre `async_disable_departure_schedule()` è sospeso dentro `async_send_command`, una chiamata concorrente a `_departure_tick_cb()` ritorna subito senza inviare comandi fuori ordine.

- [ ] **Step 2: Eseguire pytest sui nuovi test per confermare RED**

Run: `.venv/bin/pytest tests/test_native_departure_battery.py -k "full_plan or auto_advance or disable_departure or lock_prevents" -q --tb=short`
Expected: FAIL (`AttributeError` / assertions mancanti).

- [ ] **Step 3: Implementare i metodi e le guardie in `coordinator.py`, `switch.py` e `time.py`**

1. In `custom_components/lepas/coordinator.py`:
   - Import `json` (già importato; verificare).
   - In `__init__`: aggiungere `self._departure_lock: asyncio.Lock = asyncio.Lock()` e `self._applied_schedule_sig: str | None = None`.
   - Aggiungere `departure_schedule_signature()`, `_weekly_signature_part(raw_sig)`, `has_active_departure_schedule()`, `_is_car_departure_active()`, `has_pending_departure_changes()`, `restore_applied_schedule_sig(raw_sig)`.
   - Refactor `async_apply_departure_schedule` → `_async_apply_departure_schedule_locked(*, enable_native_sync: bool = True)` protetto da `async with self._departure_lock:`.
   - Aggiungere `async_disable_departure_schedule()` protetto da `async with self._departure_lock:` (invio `partenza_prog_off` prima della mutazione stato HA; poi reset switch/quick/sync/sig + `async_sync_battery_for_occurrence(None)` se `sync_battery_heat_to_departure` + refresh realtime).
   - Proteggere `async_set_quick_departure` con `async with self._departure_lock:` usando `_async_apply_departure_schedule_locked(enable_native_sync=False)` quando `apply_native is True`, e aggiornando `_applied_schedule_sig` se `apply_native is None` e `_async_sync_native_departure` ha inviato con successo senza bozza settimanale dirty.
   - `_async_sync_native_departure(occ) -> bool`: ritorna `True` quando invia e schedula `_async_refresh_travel_appoint_realtime()` + `_post_settle_travel_refresh()`, `False` se skippato o in errore.
   - `_departure_tick_cb`: controllare `if self._timers.closing or self._departure_busy or self._departure_lock.locked(): return`, acquisire `async with self._departure_lock:`, applicare la guardia `(not weekly_dirty or (quick_expired and occ is None))` e gestire `quick_expired` su `sent_ok or sig == self._last_synced_native_dep_sig`.
2. In `custom_components/lepas/switch.py`:
   - In `LepasScheduleSwitch._SYNC_MODES["departure"]`: `{"sync_charge": en, "sync_native": False, "sync_battery": True}`.
   - In `LepasWeeklyDepartureSwitch._set_enabled`: `sync_native=False`.
3. In `custom_components/lepas/time.py`:
   - In `LepasTimeEntity.async_set_value` (`is_quick`): `sync_native=False`.
   - In `LepasWeeklyDepartureTime.async_set_value`: `sync_native=False`.

---

### Task 2: Sensor Restore/Attributes (`sensor.py`) & Service `lepas.disable_departure_schedule` (`__init__.py`, `services.yaml`)

**Files:**
- Modify: `custom_components/lepas/sensor.py:895-1016`
- Modify: `custom_components/lepas/__init__.py:30-35`, `370-515`
- Modify: `custom_components/lepas/services.yaml:120-132`
- Test: `tests/test_native_departure_battery.py`, `tests/test_entity_count.py`

**Interfaces:**
- Produces:
  - Service `lepas.disable_departure_schedule(entry_id: str | None = None)`
  - `sensor.lepas_scheduled_departure` attributes: `has_pending_changes: bool`, `applied_schedule_sig: str | None`

- [ ] **Step 1: Scrivere i test per restore attributi `LepasDeparturePlan` e servizio `lepas.disable_departure_schedule` (RED)**

Aggiungere a `tests/test_native_departure_battery.py`:
- `test_departure_plan_sensor_exposes_and_restores_applied_sig`: verifica `extra_state_attributes` prima di `realtime` (`has_pending_changes` + `applied_schedule_sig`) e restore via `async_get_last_state()` dopo riavvio.
- `test_disable_departure_schedule_service_registered_and_unregistered`: verifica chiamata `hass.services.async_call(DOMAIN, "disable_departure_schedule", ...)` e pulizia in `async_unload_entry`.

- [ ] **Step 2: Implementare `sensor.py`, `__init__.py` e `services.yaml`**

1. In `custom_components/lepas/sensor.py` (`LepasDeparturePlan`):
   - Aggiungere `async_added_to_hass`: chiamare `await super().async_added_to_hass()`, poi `last_state = await self.async_get_last_state()`, verificare `isinstance(last_state.attributes, Mapping)` e chiamare `restore_applied_schedule_sig(last_state.attributes.get("applied_schedule_sig"))` se `_applied_schedule_sig is None`.
   - In `extra_state_attributes`: includere `"has_pending_changes"` e `"applied_schedule_sig"` in tutti i rami (incluso boot prima di `realtime` quando `coord` espone `has_pending_departure_changes`).
2. In `custom_components/lepas/__init__.py`:
   - Definire `SERVICE_DISABLE_DEPARTURE_SCHEDULE = "disable_departure_schedule"` e `_DISABLE_DEPARTURE_SCHEMA = vol.Schema({vol.Optional("entry_id"): str})`.
   - Registrare `_handle_disable_departure_schedule` in `_async_register_services` e rimuovere `SERVICE_DISABLE_DEPARTURE_SCHEDULE` in `_async_unregister_services`.
3. In `custom_components/lepas/services.yaml`:
   - Documentare `disable_departure_schedule` con campo opzionale `entry_id`.

- [ ] **Step 3: Verificare test Python**

Run: `.venv/bin/pytest tests/test_native_departure_battery.py tests/test_config_ux.py tests/test_entity_count.py -q --tb=short`
Expected: PASS.

---

### Task 3: Lovelace Card 3-State Departure Button & Accessibility (`lepas-card.js`) + Bump `1.24.0`

**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js:1-15`, `95-115`, `255-265`, `422-432`, `590-600`, `2288-2305`, `2391-2405`, `3795-3825`
- Modify: `tests/lepas_card.test.mjs`
- Modify: `tests/test_lovelace_card.py`
- Modify: `custom_components/lepas/manifest.json`, `pyproject.toml`, `CHANGELOG.md`

**Interfaces:**
- Consumes: `sensor.lepas_scheduled_departure.attributes.{attiva, synced_with_ha, has_pending_changes}`, service `lepas.disable_departure_schedule`, `button.lepas_apply_departure_schedule`.
- Produces: ES5-safe `LepasCard` 3-state action (`apply_departure_schedule` / `disable_departure_schedule` / hidden with `btn.hidden`).

- [ ] **Step 1: Scrivere i test Node falsificabili in `tests/lepas_card.test.mjs` (RED)**

Aggiungere test JSDOM sul custom element `<lepas-card>`:
1. `has_pending_changes: true` (anche con `synced_with_ha: true`) + `haHasActiveDep: true` → pulsante visibile (`hidden === false`, no `.hidden`), testo `"Applica su auto"`, classe `"is-primary"`, `data-action-id === "apply_departure_schedule"`.
2. `has_pending_changes: false` + `synced_with_ha: true` + `carActive: true` + `haHasActiveDep: true` → pulsante trasformato in `"Disattiva piano"`, senza `"is-primary"`, `data-action-id === "disable_departure_schedule"`, click dopo conferma invoca `hass.callService("lepas", "disable_departure_schedule", { entry_id: ... })`.
3. `haHasActiveDep: false` + `carActive: false` → pulsante nascosto (`btn.hidden === true` e `.hidden`); poi attivando un giorno → riappare (`btn.hidden === false`, no `.hidden`).
4. `schedDep` assente o `unavailable` → nessun `TypeError` di runtime; fallback legacy preservato.

- [ ] **Step 2: Eseguire `node --test tests/lepas_card.test.mjs` per confermare RED**

- [ ] **Step 3: Implementare `lepas-card.js` (ES5 + a11y) e sincronizzare versione `1.24.0`**

1. In `custom_components/lepas/lovelace/lepas-card.js`:
   - `CARD_VERSION = "1.24.0"` + commento header `v1.24.0`.
   - `CONFIRM_ACTIONS`: aggiungere `disable_departure_schedule: true`.
   - `I18N`: aggiungere `disableDeparturePlan` (`"Disattiva piano"` / `"Disable schedule"` / `"Schema uitschakelen"`) e `departureStatus` (`"Stato"` / `"Status"` / `"Status"`).
   - In `dep-summary` (`L2948`), sostituire `t.nextDeparture` con `t.departureStatus` (mantenendo `t.nextDeparture` per il fallback `mOdoCard` in Overview `L3338`).
   - Inizializzare prima `var sdRawAttrs = (schedDep && schedDep.s && !this._dead(schedDep.s) && schedDep.s.attributes) ? schedDep.s.attributes : {};`.
   - In `if (applyDepBtn)`: registrare sia `apply_departure_schedule` che `disable_departure_schedule` (`"lepas"`, `"disable_departure_schedule"`, `this._currentEntryId ? { entry_id: this._currentEntryId } : {}`, `true`, `"disable_departure_schedule"`, `t.disableDeparturePlan`).
   - In `_applyBindingsInner` (dentro `if (applyDepBtnEl && vm.applyDepBtn)`): implementare la macchina a 3 stati con helper `showDepBtn(...)` che imposta `applyDepBtnEl.classList.remove("hidden"); applyDepBtnEl.hidden = false;` e ramo hidden che imposta `applyDepBtnEl.classList.add("hidden"); applyDepBtnEl.hidden = true;`. Zero `?.`, zero `??`.
2. Sincronizzare versione `1.24.0` in `custom_components/lepas/manifest.json`, `pyproject.toml`, `tests/test_lovelace_card.py`, `tests/lepas_card.test.mjs` e aggiungere sezione bilingue `## v1.24.0 — 2026-11-19` in `CHANGELOG.md`.

---

### Task 4: Verifica Completa, Dual-Gate Review (Pass 1 + Pass 2 Sentinel), Deploy & Test Live HA

- [ ] Eseguire `.venv/bin/pytest -q --tb=short --maxfail=2`, `node --test tests/lepas_card.test.mjs`, `node --check custom_components/lepas/lovelace/lepas-card.js` (+ check anti-`?.`/`??`), `/home/federico/.local/bin/uv run --no-project --with ruff ruff check --select F,E9 ...`.
- [ ] Eseguire Pass 1 (`local_llm_offload.py --task review-hygiene`) + Pass 2 Sentinel (`send_message` a `c51a768a-d17d-4dc1-ab20-710e40628708` con lock `APPROVED_TREE=$(git write-tree)`).
- [ ] Su approvazione utente, deploy su HA (`scp` + `ha_restart`) e test live: verifica stato 3 vie della card, cambio Venerdì/Sabato senza auto-invio intermedio, click **Applica su auto** (accende Auto-Sync), verifica passaggio automatico alle `13:25`, e test **Disattiva piano**.
