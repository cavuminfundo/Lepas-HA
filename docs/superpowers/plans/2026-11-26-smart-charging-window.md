# Piano di Implementazione — Fase 2: Finestra di Ricarica Dinamica Smart (`Lepas`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Matrice Dual-Gate Audit (Pre-Presentazione)

| Stadio | Ruolo & Modello | Conversation ID | Verdetto | Esito & Integrazione |
|---|---|---|---|---|
| **Stage 1** (Domain & Archaeology Pre-Audit) | `domain_pre_auditor` (`Model: 'flash'`) | `5c37f7aa-81ea-4e03-b5fa-d2ce190f181b` | `CHANGES_REQUIRED` | Integrati tutti e **10 i rilievi** (decimal step `number.py`, lock `_departure_lock` `_locked`, `@property sync_charge_to_departure`, `fast_charging` in `ingest`, `ENTITY_FEATURE_MAP`, `CANON_ENTITY_ID`, `quick_expired` a `is_plugged=False`, `build_charge_appoint_plan` `ricarica_prog_off` completo, riuso `LepasScheduleSwitch`, verifica `commands.py` + `AB-LEP-008`/`016`). |
| **Stage 2** (Six-Pillars Sentinel Control Gate) | `sentinel_auditor` (`Model: 'inherit'`) | `d69001dd-13fa-4c50-a27c-e29ec1e2b134` | `APPROVED_WITH_NOTES` | Integrati tutti e **6 gli emendamenti obbligatori** (#1 `plug_in_home` con `chargeState == 1` post-bypass, #2 preservazione `charge_start_minutes` + flusso `_departure_tick_cb` su `charge_window_mode != "off"`, #3 boot-race restore in entrambi gli ordini + `AB-LEP-010`, #4 flush CC sul ramo `power_kw is None`, #5 fallback non-None `ricarica_prog_off` / event-loop boundary / cancel debounce completo / reset `_last_attempted_charge_sig`, #6 `self._attr_native_step` + clamp `[vmin, vmax]` + `_push` float). *(Stesso CID da riusare via `send_message` al Tier 3 Pass 2 Code Audit).* |

---

**Goal:** Implementare la finestra di ricarica dinamica smart Just-in-Time al 100% per Lepas L8 (modalità domestiche `off` / `fixed` / `smart_departure`, auto-apprendimento potenza AC/DC in fase CC, bypass fuori casa `at_home is False`, override da Partenza rapida `quick_departure`, giorni liberi `> 23h 45m` e `late_plug_in` → `ricarica_prog_off`, diagnostica non-PII e controlli in `lepas-card.js`).

**Architecture:** Motore energetico e decisionale puro in `scheduler.py` (`estimate_smart_charge_plan`, `resolve_desired_charge_schedule`) accoppiato all'apprendimento mediano/EMA AC-vs-DC retrocompatibile in `charging_stats.py` (`Store` v1). Il `LepasCoordinator` orchestra debounce di plug-in (`20s`), bypass fuori casa (`not car_in_use`), rete di sicurezza pre-carica e sync bidirezionale verso `select.lepas_charge_window_mode`, `switch.lepas_home_charge_power_auto`, `number.lepas_home_charge_power` e i sensori/card Lovelace.

**Tech Stack:** Python >= 3.12, Home Assistant Core (`DataUpdateCoordinator`, `RestoreEntity`, `SelectEntity`, `SwitchEntity`, `NumberEntity`, `Store`), `aiohttp`, Vanilla JS Web Components (`lepas-card.js`), `pytest`, `node --test`, `ruff`.

**Spec:** [`docs/superpowers/specs/2026-11-26-smart-charging-window-design.md`](file:///home/federico/Lepas/docs/superpowers/specs/2026-11-26-smart-charging-window-design.md)

## Global Constraints

- **Perimetro Fase 2:** solo `off`, `fixed`, `smart_departure`. Modalità `solar` rimandata a Fase 3 (zero opzioni disattive e zero codice morto in Fase 2).
- **Schema wire `chargeAppointControl`:** `startTime` in minuti UTC (`0..1439`, floor 15m via `CHARGE_START_STEP_MINUTES = 15`), `timeConsuming` in minuti, `cycleData` giorni ISO `1..7` UTC (`[1..7]` su Lepas L8 per `2131 = 0`), `switchStatus` `0/1`, `targetSoc` assente, `ricarica_start`/`stop` bloccato (`220 = 0`).
- **Crash Antibodies (`AB-LEP-001..019`):**
  - `AB-LEP-001`: zero polling/wake periodici a veicolo scollegato (`is_plugged is False`) o dormiente.
  - `AB-LEP-002`: entity ID con `ID_PREFIX = "lepas"` in `CANON_ENTITY_ID` (`naming.py`); zero PII in log, `Store` e `diagnostics.py`.
  - `AB-LEP-005`: test live su `core/*.py` richiedono `ha_restart` (non eseguito automaticamente).
  - `AB-LEP-007` / `AB-LEP-014`: mai annidare `_state_lock` / `_hv_lock` / `_charging_lock` attorno ad `await`, mai chiamare `_auto_e_sveglia()` dentro `_state_lock`; transizioni `plugged`/`car_in_use` e timer solo sull'event loop HA.
  - `AB-LEP-008` / `AB-LEP-016`: `window.customCards` senza prefisso `custom:`; `applyCarInUseState` non disabilita i controlli di configurazione ricarica (`charge_window_mode`, `home_charge_power_auto`, `home_charge_power`).
  - `AB-LEP-009` / `AB-LEP-019`: `resolve_tzinfo(hass)` + floor 15m; mai inferire lo schedule da `appointmentChargeState`; `CMD_PROBE` attivo su `CHARGE_PROBE_COMMANDS`.
  - `AB-LEP-010`: `async_update_listeners()` sempre guardato da `if not self._timers.closing:`.
- **Test Runner & Linting:** `/home/federico/.local/bin/uv run --with pytest pytest -q --tb=short --maxfail=2`, `node --test tests/lepas_card.test.mjs`, `uv run ruff check custom_components/ tests/`, `uv run ruff format --check custom_components/ tests/`. I Sub-Agenti non eseguono suite globali.

---

## Blast Radius & StateGraph

### `BlastRadius`
- **`direct_files` (20 file, partizione strettamente disgiunta tra i 4 worker):**
  - Round 1: `custom_components/lepas/scheduler.py`, `custom_components/lepas/charging_stats.py`, `tests/test_smart_charging.py` (new), `tests/test_charging_stats.py` (mod).
  - Round 2: `custom_components/lepas/const.py`, `custom_components/lepas/timers.py`, `custom_components/lepas/coordinator.py`, `custom_components/lepas/diagnostics.py`, `tests/test_smart_charge_coordinator.py` (new).
  - Round 3A: `custom_components/lepas/naming.py`, `custom_components/lepas/select.py`, `custom_components/lepas/switch.py`, `custom_components/lepas/number.py`, `custom_components/lepas/sensor.py`, `custom_components/lepas/translations/en.json`, `custom_components/lepas/translations/it.json`, `tests/test_smart_charge_entities.py` (new).
  - Round 3B: `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs` (mod), `tests/test_lovelace_card.py` (mod).
- **`transitively_affected`:**
  - `custom_components/lepas/__init__.py` (`async_apply_charging_schedule`, `notify_schedule_changed`)
  - `custom_components/lepas/button.py` (`LepasApplyChargingScheduleButton`)
  - `custom_components/lepas/time.py` (`charge_start_minutes` → `notify_schedule_changed`)
  - `custom_components/lepas/core/commands.py` (check read-only assenza vincoli su `timeConsuming`)
  - Test suite correlate: `tests/test_vin_features.py`, `tests/test_naming.py`, `tests/test_translations.py`, `tests/test_scheduler.py`, `tests/test_scheduled_charge_utc_probe.py`, `tests/test_config_ux.py`, `tests/test_native_departure_battery.py`, `tests/test_diagnostics.py`, `tests/test_timers_unit.py`, `tests/test_vehicle_color.py`, `tests/test_session.py`. *(Se test esistenti come `test_scheduler.py` / `test_native_departure_battery.py` / `test_config_ux.py` usano `position=None` dove il nuovo motore restituisce `at_home is None -> noop`, allineare le relative fixture con una posizione dentro `zone.home` senza alterare `at_home is None -> noop` in produzione).*
- **`uncertain`:**
  - Granularità `timeConsuming` lato backend `tspconsole-eu` (`15` vs `60` min): verifica preliminare read-only di `core/commands.py` / `core/permessi.py` in Task 1 + costante unica `CHARGE_DURATION_STEP_MINUTES = 15` (switchabile a `60` senza alterare la formula), da confermare dal vivo su HA dopo `ha_restart`.
  - Ordine di restore al boot tra `select.lepas_charge_window_mode` e `switch.lepas_sync_charge_to_departure`: gestito deterministicamente con `_charge_window_mode_restored` (solo su `last.state` valido) e riconciliazione bidirezionale.

### `StateGraph` (`onSuccess:` / `onFailure:`)
1. **Timer `CHARGE_PLUGIN_DEBOUNCE` (`20s` su `TimerRegistry`, esclusivamente su event loop HA):**
   - **Arm:** su transizione `plugged: False -> True` rilevata in `_ingest_charging_stats_on_loop` quando `charge_window_mode != "off"`, `at_home is True`, `not car_in_use`.
   - `onSuccess:` allo scadere dei `20s`, se `not self._timers.closing`, schedula task async `_async_sync_charge_desired(trigger="plug_in_home")` catturando/loggando eventuali eccezioni non-PII senza crash del loop.
   - `onFailure:` / cancel anticipato su `plugged: True -> False` (`< 20s`), `at_home is False`, passaggio a `charge_window_mode == "off"`, oppure `self._timers.close()` allo scaricamento (`unload`).
2. **Invio remoto `chargeAppointControl` (`ricarica_prog_on` / `ricarica_prog_off`) sotto `_departure_lock`:**
   - **Locking:** `_async_sync_charge_desired_locked(plan=..., trigger=...)` presume `self._departure_lock` già acquisito (chiamato da `async_set_quick_departure` e `_departure_tick_cb`); `_async_sync_charge_desired(...)` acquisisce `async with self._departure_lock:` (chiamato da `notify_schedule_changed`, `CHARGE_PLUGIN_DEBOUNCE` e transizioni `plugged` / `car_in_use`). Mai tenere `_state_lock`, `_hv_lock` o `_charging_lock` attraverso `await`.
   - **Guardia carica attiva (`chargeState == 1`):** blocca rinvii automatici su tick periodico, update SoC, cambio potenza e schedule già attivi; **eccezione mirata su `trigger == "plug_in_home"`** quando `plan.action == "enable"` e lo schedule dell'auto risulta spento (`not self._car_charge_schedule_is_on()` o `_last_synced_charge_sig` era `"disable"`), per garantire il ripristino post-`away_bypass` / `no_departure_24h` anche se l'auto avvia subito la carica entro i 20s di debounce.
   - **Payload `ricarica_prog_off` completo:** per `plan.action == "disable"` (`away_bypass`, `no_departure_24h`, `late_plug_in`), `build_charge_appoint_plan` riceve sempre parametri non-None (`local_start_minutes=self.charge_start_minutes`, `duration_hours=int(self.charge_duration_hours or 6)`, `local_days=self.effective_charge_days()`, `switch_status=0`).
   - `onSuccess:` `self._last_synced_charge_sig = sig`, `self._last_attempted_charge_sig = None`, `CMD_PROBE` armato da `async_send_command` (`AB-LEP-019`), `if not self._timers.closing: self.async_update_listeners()`.
   - `onFailure:` (`CommandError`, `HTTP >= 400`, timeout, rete): warning non-PII, `self._last_attempted_charge_sig = sig` (anti retry-storm 60s), `_last_synced_charge_sig` invariato, rilascio garantito di `_departure_lock`. `_last_attempted_charge_sig` viene azzerato su nuovo `plugged: False -> True`, cambio config utente o `async_apply_charging_schedule`.
3. **Salvataggio `Store` profili potenza (`_charging_store` v1):**
   - **Flush CC:** eseguito sia nel ramo `power_kw is None` (su `not plugged` oppure `odo_advanced`), sia nel ramo principale (su `(not plugged and not charging) or reset_cont`), sia su cambio `charge_kind` (`ac` ↔ `dc`).
   - `onSuccess:` `_schedule_charging_save` / `async_flush_charging_stats` persiste JSON senza PII.
   - `onFailure:` catturato con warning non-PII (`type(err).__name__`), stato in memoria preservato.

---

### Domain Skills & Sub-Agent Roster

| Round | Worker (`define_subagent`) | Model & Workspace | Skill Companion (1 call ciascuna) | Scope File Esclusivi (Single-Owner) |
|---|---|---|---|---|
| **Round 1** | `smart_engine_worker` | `Model: 'pro'`, `Workspace: 'inherit'` | `ponytail`, `antislop-code` | `scheduler.py`, `charging_stats.py`, `tests/test_smart_charging.py`, `tests/test_charging_stats.py` *(+ read-only check `core/commands.py`)* |
| **Round 2** | `coordinator_core_worker` | `Model: 'pro'`, `Workspace: 'inherit'` | `ponytail`, `antislop-code` | `const.py`, `timers.py`, `coordinator.py`, `diagnostics.py`, `tests/test_smart_charge_coordinator.py` |
| **Round 3A** | `ha_entities_worker` | `Model: 'pro'`, `Workspace: 'inherit'` | `ponytail`, `antislop-code` | `naming.py`, `select.py`, `switch.py`, `number.py`, `sensor.py`, `translations/en.json`, `translations/it.json`, `tests/test_smart_charge_entities.py` |
| **Round 3B** | `lovelace_card_worker` | `Model: 'pro'`, `Workspace: 'inherit'` | `antislop-ui`, `antislop-code` | `lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py` |

*(Ogni round usa `Model: 'pro'` perché tutti toccano moduli `>600L`, stato distribuito/lock o `>=3` file interdipendenti. I file condivisi sono zero e ogni round viene eseguito in ordine `1 → 2 → 3A → 3B` con spot-check e test Master tra i round).*

---

### Task 1: Motore Energetico Puro (`scheduler.py`) & Profili Potenza AC/DC (`charging_stats.py`)

**Files:**
- Modify: `custom_components/lepas/scheduler.py`
- Modify: `custom_components/lepas/charging_stats.py`
- Read-only verify: `custom_components/lepas/core/commands.py` (`CMD_MAP["ricarica_prog_on"]` / `"ricarica_prog_off"`)
- Create: `tests/test_smart_charging.py`
- Modify: `tests/test_charging_stats.py`

**Interfaces:**
- Consumes: `is_degraded_battery_frame` / `_safe_float` (`consumption.py`), `DEFAULT_BATTERY_CAPACITY_KWH` (`const.py`), `CHARGE_START_STEP_MINUTES`, `DepartureOccurrence`, `compute_next_occurrence`, `align_charge_start_minutes`, `shift_minutes` (`scheduler.py`).
- Produces (`scheduler.py`):
  - Costanti: `CHARGE_DURATION_STEP_MINUTES = 15`, `CHARGE_WINDOW_MODES = ("off", "fixed", "smart_departure")`, `SMART_AC_EFFICIENCY = 0.90`, `SMART_AC_CV_MARGIN_MIN = 25`, `SMART_DC_EFFICIENCY = 0.92`, `SMART_DC_CV_MARGIN_MIN = 30`, `SMART_MIN_DURATION_MIN = 30`, `DEFAULT_HOME_CHARGE_POWER_KW = 2.3`, `SMART_24H_WINDOW_MAX_MINUTES = 23 * 60 + 45`.
  - `SmartChargeEstimate(duration_minutes: int, raw_minutes: float, missing_kwh: float, fallback_used: bool, soc_used: float | None, charge_kind: str)`
  - `DesiredChargePlan(action: str, reason: str, start_minutes: int | None, duration_minutes: int | None, days: tuple[int, ...] | None, ref_date: date | None, target_key: str, estimated_duration_min: int | None, soc_used: float | None, charge_kind: str, effective_power_kw: float, power_source: str, fallback_used: bool, away_bypass_active: bool, quick_override_active: bool)`
  - `select_charge_departure_occurrence(now: datetime, weekly: Mapping[int, tuple[bool, int]] | None, quick_enabled: bool, quick_minutes: int, clima_duration_min: int) -> tuple[DepartureOccurrence | None, bool]`
  - `estimate_smart_charge_plan(*, soc_pct: float | None, degraded_battery: bool, capacity_kwh: float, power_kw: float, charge_kind: str, max_duration_hours: int, step_minutes: int = CHARGE_DURATION_STEP_MINUTES) -> SmartChargeEstimate`
  - `resolve_desired_charge_schedule(*, now: datetime, mode: str, at_home: bool | None, is_plugged: bool, charge_state: int | None, charge_start_minutes: int, charge_duration_hours: int, charge_days: Sequence[int], weekly: Mapping[int, tuple[bool, int]] | None, quick_enabled: bool, quick_minutes: int, clima_duration_min: int, soc_pct: float | None, degraded_battery: bool, capacity_kwh: float, power_kw: float, power_source: str, charge_kind: str, step_minutes: int = CHARGE_DURATION_STEP_MINUTES) -> DesiredChargePlan`
- Produces (`charging_stats.py`):
  - `classify_charge_kind(fast_charging: bool | None, power_kw: float | None) -> str` (`"ac"` / `"dc"`)
  - `select_effective_home_power(*, auto_enabled: bool, manual_kw: float, charge_kind: str, learned_ac_kw: float | None, learned_dc_kw: float | None) -> tuple[float, str]`
  - `ChargingStatsTracker.ingest(..., fast_charging: bool | None = None) -> bool` (retrocompatibile)
  - `ChargingStatsTracker.home_power_profile() -> dict[str, Any]` (`learned_ac_kw`, `learned_dc_kw`, `home_ac_sessions`, `home_dc_sessions`)

- [ ] **Step 1: Verifica read-only `core/commands.py` su `timeConsuming`**
  Controllare `CMD_MAP["ricarica_prog_on"]` e `CMD_MAP["ricarica_prog_off"]` in `custom_components/lepas/core/commands.py` per confermare che non esistano assert o vincoli hard-coded a multipli di 60 sul campo `timeConsuming`.

- [ ] **Step 2 (TDD RED): Scrivere test falsificabili in `tests/test_smart_charging.py` e `tests/test_charging_stats.py`**
  - In `tests/test_smart_charging.py`:
    - `test_estimate_ac_and_dc_durations`: `18.4 kWh`, `2.3 kW` AC (`eta=0.90`, `+25m`) su SoC `80%`, `50%`, `10%`, `99%` (`ceil` a step 15m, min 30m, cap `max_duration_hours * 60`); stessa verifica in DC (`eta=0.92`, `+30m`, `24.0 kW`).
    - `test_estimate_fallback_on_missing_or_degraded_soc`: `soc_pct=None`, `soc_pct=-5`, `degraded_battery=True` → `fallback_used=True` e `duration_minutes == max_duration_hours * 60`.
    - `test_select_charge_departure_quick_override_even_if_later`: `quick_enabled=True` alle `10:00` vince sulla settimanale delle `08:00` (`quick_override_active=True`); `quick_enabled=False` torna alla settimanale.
    - `test_resolve_desired_charge_schedule_all_branches`: `mode="off" -> noop`, `at_home=None -> noop`, `at_home=False -> disable (away_bypass)`, `fixed` normale (`fixed_home`), `fixed` + `quick_override`, `smart_departure` con `no_departure_24h` (`>23h45m` o `occ is None`) → `disable`, `late_plug_in` (`now >= smart_start_at` e `now < departure_at`) → `disable`, `already_charged` (`charge_state=2` o `soc>=99` plugged) → `noop`.
    - `test_smart_start_midnight_and_dst_alignment`: partenza `07:00` o `00:30` con calcolo `start_minutes` multiplo di `15` e `ref_date` coerente prima/dopo cambio ora legale.
  - In `tests/test_charging_stats.py`:
    - `test_home_cc_learning_ac_and_dc_separation`: AC `<85%` SoC a casa (`>=3` campioni, outlier filtrato da mediana) vs DC (`fast_charging=True` o `>11 kW`, `<75%` SoC), esclusione campioni CV (`>=85%` AC / `>=75%` DC), esclusione `in_home_zone=False/None`, `degraded_battery=True`, `<0.5 kW`, aggiornamento EMA `0.7/0.3` alla 2ª sessione.
    - `test_home_cc_learning_flush_on_mqtt_none_power_frame`: chiusura sessione tramite frame `power_kw=None` con `plugged=False` oppure `odo_advanced=True` finalizza correttamente il profilo AC/DC senza leak sulla sessione successiva (Emendamento Stage 2 #4).
    - `test_home_power_profile_backward_compatible_store_v1`: `from_dict` su payload v1 privo delle nuove chiavi resta valido con profili `None` / `0`.

- [ ] **Step 3: Eseguire test RED mirati**
  Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_smart_charging.py tests/test_charging_stats.py -q --tb=short`
  Expected: FAIL (`ImportError` / attributi mancanti).

- [ ] **Step 4 (GREEN): Implementare `scheduler.py` e `charging_stats.py`**
  - In `custom_components/lepas/scheduler.py`: implementare le dataclass e funzioni pure `select_charge_departure_occurrence`, `estimate_smart_charge_plan`, `resolve_desired_charge_schedule` rispettando `align_charge_start_minutes` e `shift_minutes`.
  - In `custom_components/lepas/charging_stats.py`: aggiungere `classify_charge_kind`, `select_effective_home_power`, buffer CC di sessione (max 120 campioni per evitare crescita illimitata), helper `_flush_cc_learning()` chiamato sia nel ramo `power_kw is None` su `(not plugged) or odo_advanced` sia nel ramo principale su `(not plugged and not charging) or reset_cont` e su cambio `charge_kind`, e serializzazione retrocompatibile in `to_dict()` / `from_dict()` (`version: 1`).

- [ ] **Step 5: Verificare GREEN**
  Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_smart_charging.py tests/test_charging_stats.py tests/test_scheduler.py -q --tb=short`
  Expected: PASS.

---

### Task 2: Integrazione Coordinator, Bypass Fuori Casa, Debounce 20s & Diagnostica (`const.py`, `timers.py`, `coordinator.py`, `diagnostics.py`)

**Files:**
- Modify: `custom_components/lepas/const.py`
- Modify: `custom_components/lepas/timers.py`
- Modify: `custom_components/lepas/coordinator.py`
- Modify: `custom_components/lepas/diagnostics.py`
- Create: `tests/test_smart_charge_coordinator.py`
- Conditional check/align: `tests/test_scheduler.py`, `tests/test_native_departure_battery.py`, `tests/test_config_ux.py` (solo se fixture `position=None` impattata da `at_home is None -> noop`).

**Interfaces:**
- Consumes: tutte le nuove API da `scheduler.py` e `charging_stats.py` (Task 1).
- Produces (`const.py` / `timers.py`):
  - `ENTITY_FEATURE_MAP` in `const.py`: aggiungere `("select", "charge_window_mode"): "scheduled_charging"`, `("switch", "home_charge_power_auto"): "scheduled_charging"`, `("number", "home_charge_power"): "scheduled_charging"`.
  - `CHARGE_PLUGIN_DEBOUNCE = "charge_plugin_debounce"` in `timers.py` e `GRUPPO_PARTENZA` / cleanup.
- Produces (`coordinator.py`):
  - Attributi stato su `LepasCoordinator`: `_charge_window_mode: str = "off"`, `_charge_window_mode_restored: bool = False`, `home_charge_power_auto: bool = True`, `home_charge_power_kw: float = DEFAULT_HOME_CHARGE_POWER_KW`, `_last_desired_charge_plan: DesiredChargePlan | None = None`, `_prev_charge_plugged_loop: bool | None = None`, `_prev_car_in_use_loop: bool | None = None`.
  - `@property def charge_window_mode(self) -> str` / `set_charge_window_mode(self, mode: str, *, from_restore: bool = False, sync_charge: bool = True) -> None`
  - `@property def sync_charge_to_departure(self) -> bool` + `@sync_charge_to_departure.setter` (`True -> "smart_departure"`, `False -> "fixed"` se era `"smart_departure"`).
  - `build_charge_appoint_plan(self, *, local_start_minutes: int, duration_hours: int | None = None, duration_minutes: int | None = None, local_days: Sequence[int], switch_status: int = 1, ref_date: date | None = None) -> dict` (valida che almeno uno tra `duration_minutes` e `duration_hours` sia non-None).
  - `evaluate_charge_plan(self, now: datetime | None = None) -> DesiredChargePlan` (legge in sicurezza SoC da `realtime`/`_fields` con `is_degraded_battery_frame`, `fastChargingGunStatus`, `chargingPower`, `chargeState`, `_safe_in_home_zone`, `_is_plugged`, `home_power_profile()`).
  - `async def _async_sync_charge_desired_locked(self, *, trigger: str, force: bool = False) -> bool` (richiede `_departure_lock` già acquisito) + `async def _async_sync_charge_desired(self, *, trigger: str, force: bool = False) -> bool` (acquisisce `_departure_lock`).
- Produces (`diagnostics.py`):
  - Sezione `diag["smart_charging"]` non-PII (`window_mode`, `home_charge_power_auto`, `home_charge_power_kw`, `learned_ac_kw`, `learned_dc_kw`, `home_ac_sessions`, `home_dc_sessions`, `last_plan_reason`).

- [ ] **Step 1 (TDD RED): Scrivere `tests/test_smart_charge_coordinator.py`**
  Test obbligatori falsificabili (mockando solo `async_send_command`, `Store`, `dt_util.now` — mai `resolve_desired_charge_schedule` né `build_charge_appoint_plan`):
  1. `test_plugin_home_debounce_20s_and_cancel_on_unplug`: `plugged False -> True` a casa arma `CHARGE_PLUGIN_DEBOUNCE`; scollegamento `< 20s` cancella il timer senza invii; allo scadere dei `20s` invia `ricarica_prog_on` con `startTime` UTC allineato a 15m e `timeConsuming` smart.
  2. `test_return_home_after_away_bypass_with_active_charging_state_1`: dopo `away_bypass` (`_last_synced_charge_sig` con `"disable"` / schedule auto spento), il plug-in a casa con `chargeState == 1` allo scadere dei 20s riesce comunque a inviare `ricarica_prog_on` una volta (Emendamento Stage 2 #1).
  3. `test_no_retrigger_while_charging_already_scheduled`: variazioni SoC (`80% -> 81% -> 82%`) mentre `chargeState == 1` e schedule attivo non inviano comandi.
  4. `test_away_bypass_on_park_and_plugin_never_while_car_in_use`: nessuna chiamata finché `car_in_use == True`; su `car_in_use: True -> False` fuori casa (o plug-in fuori casa) se schedule risulta ON invia `ricarica_prog_off` con payload completo (`mainSwitch=0`, `startTime` multiplo 15m, `cycleData` non vuoto, `timeConsuming > 0`, `switchStatus=0`) (Emendamento Stage 2 #5).
  5. `test_fixed_mode_quick_override_preserves_charge_start_minutes`: attiva `quick_departure` in `fixed` → invia smart verso rapida **senza** sovrascrivere `coord.charge_start_minutes`; su `quick_expired` con `is_plugged=True` ripristina `fixed`, con `is_plugged=False` aggiorna stato locale e azzera `_last_synced_charge_sig` senza wake 12V (Emendamento Stage 2 #2 + Stage 1 #8).
  6. `test_tick_safety_net_requires_plugged_and_resets_attempted_on_new_plugin`: tick a casa scollegata (`is_plugged=False`) non invia nulla; fallimento API salva `_last_attempted_charge_sig` (bloccando retry ogni 60s), poi un nuovo `plugged False -> True` azzera `_last_attempted_charge_sig` e riprova; nessuna deadlock su `_departure_lock` in `async_set_quick_departure` e `_departure_tick_cb`.
  7. `test_diagnostics_smart_charging_redacted_no_pii`: verifica sezione `smart_charging` e assenza VIN/lat/lon/token.

- [ ] **Step 2: Eseguire test RED**
  Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_smart_charge_coordinator.py -q --tb=short`
  Expected: FAIL.

- [ ] **Step 3 (GREEN): Implementare `const.py`, `timers.py`, `coordinator.py`, `diagnostics.py`**
  - `const.py`: aggiornare `ENTITY_FEATURE_MAP`.
  - `timers.py`: aggiungere `CHARGE_PLUGIN_DEBOUNCE` al set di timer gestiti e teardown.
  - `coordinator.py`:
    - Esporre `@property charge_window_mode`, `set_charge_window_mode`, `@property/@setter sync_charge_to_departure`.
    - Aggiornare `_ingest_charging_stats_on_loop`: passare `fast_charging = field_on(_pick_field(sources, "fastChargingGunStatus")) is True` a `_charging_tracker.ingest(...)`; rilevare esclusivamente sull'event loop HA le transizioni `plugged` (`chargeGunState` / `fastChargingGunStatus`) e `car_in_use` gestendo debounce `20s`, cancel su unplug/`away`/`off`, reset `_last_attempted_charge_sig` su `plugged: False -> True`, e trigger `away_bypass` su `car_in_use: True -> False` o plug-in fuori casa.
    - Aggiornare `build_charge_appoint_plan` per accettare `duration_minutes` o `duration_hours`.
    - Implementare `evaluate_charge_plan`, `_async_sync_charge_desired_locked` e `_async_sync_charge_desired` con tutti i punti dello `StateGraph` (incluso fallback non-None per `ricarica_prog_off`, eccezione `plug_in_home` con `chargeState == 1` post-bypass, log non-PII).
    - Aggiornare `notify_schedule_changed`, `async_set_quick_departure`, `async_apply_charging_schedule` (reset `_last_attempted_charge_sig = None`, parità tuple firma) e `_departure_tick_cb` (sostituire il blocco L1989 con il nuovo flusso `self.charge_window_mode != "off"`, nessuna mutazione di `self.charge_start_minutes` durante `fixed + quick_override`, e gestione `quick_expired` a `is_plugged=False`).
  - `diagnostics.py`: aggiungere blocco `smart_charging` privo di PII.

- [ ] **Step 4: Verificare GREEN & test transitivi**
  Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_smart_charge_coordinator.py tests/test_scheduler.py tests/test_scheduled_charge_utc_probe.py tests/test_native_departure_battery.py tests/test_config_ux.py tests/test_diagnostics.py tests/test_timers_unit.py tests/test_vin_features.py -q --tb=short`
  Expected: PASS (allineando prima eventuali fixture `position=None` nei test legacy che presupponevano `at_home` implicito).

---

### Task 3: Entità HA, Boot Migration Sicura, Sensori & Traduzioni (`naming.py`, `select.py`, `switch.py`, `number.py`, `sensor.py`, `translations/`)

**Files:**
- Modify: `custom_components/lepas/naming.py`
- Modify: `custom_components/lepas/select.py`
- Modify: `custom_components/lepas/switch.py`
- Modify: `custom_components/lepas/number.py`
- Modify: `custom_components/lepas/sensor.py`
- Modify: `custom_components/lepas/translations/en.json`
- Modify: `custom_components/lepas/translations/it.json`
- Create: `tests/test_smart_charge_entities.py`

**Interfaces:**
- Consumes: `LepasCoordinator` (`charge_window_mode`, `set_charge_window_mode`, `sync_charge_to_departure`, `home_charge_power_auto`, `home_charge_power_kw`, `evaluate_charge_plan`, `charging_stats` / `home_power_profile()`).
- Produces:
  - `naming.CANON_ENTITY_ID`: `("select", "charge_window_mode")`, `("switch", "home_charge_power_auto")`, `("number", "home_charge_power")`.
  - `select.LepasChargeWindowModeSelect` (`select.lepas_charge_window_mode`, opzioni `["off", "fixed", "smart_departure"]`, `RestoreEntity`).
  - `switch.LepasScheduleSwitch` esteso con `default: bool = False` per `home_charge_power_auto` (`switch.lepas_home_charge_power_auto`) e guard restore su `sync_charge_to_departure`.
  - `number.LepasConfigNumber` con `self._attr_native_step`, clamp `[min, max]`, decimal snapping per step `< 1` (`2.3` / `3.0` preservato float), `UnitOfPower.KILO_WATT`, voce `("Lepas Home charge power", "home_charge_power", "home_charge_power", 1.4, 40.0, 0.1, 2.3, UnitOfPower.KILO_WATT, "mdi:flash-auto")`.
  - `sensor.LepasScheduledChargingWindowSensor` (attributi estesi da `DesiredChargePlan` + `home_power_profile()`) e `sensor.LepasNextDepartureSensor` (`planned_charge_start` da `evaluate_charge_plan`).

- [ ] **Step 1 (TDD RED): Scrivere `tests/test_smart_charge_entities.py`**
  Test falsificabili:
  1. `test_boot_migration_both_setup_orders`:
     - First boot (`select` senza `last_state`): `switch` restaurato `ON` → `charge_window_mode == "smart_departure"` in **entrambi gli ordini** (`select` poi `switch` e `switch` poi `select`). Verifica che `select` con `last_state=None` NON imposti `_charge_window_mode_restored=True` e non sovrascriva `coord.charge_window_mode` (Emendamento Stage 2 #3).
     - Conflitto boot con `last_state` valido (`select="fixed"` vs `switch="on"`): vince `select` e chiama `async_update_listeners()` (`AB-LEP-010`) in entrambi gli ordini.
  2. `test_bidirectional_sync_select_and_legacy_switch`: toggle `switch.lepas_sync_charge_to_departure` aggiorna `select.lepas_charge_window_mode` (`smart_departure` ↔ `fixed`) e viceversa.
  3. `test_home_charge_power_number_decimal_snapping_and_clamp`: verifica `2.3`, `3.0` (resta `float`, non `int`), clamp `0.2 -> 1.4` e `99.0 -> 40.0`, `sync_charge=False` in `async_added_to_hass` vs `sync_charge=True` in `async_set_native_value` (Emendamento Stage 2 #6).
  4. `test_ice_vehicle_feature_gating_excludes_new_entities`: su veicolo ICE senza `"scheduled_charging"`, nessuna delle 3 entità viene creata.
  5. `test_window_sensor_attributes_and_next_departure_parity`: verifica tutti gli attributi su `LepasScheduledChargingWindowSensor` e parità `planned_charge_start` su `LepasNextDepartureSensor`.

- [ ] **Step 2: Eseguire test RED**
  Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_smart_charge_entities.py tests/test_naming.py tests/test_translations.py -q --tb=short`
  Expected: FAIL.

- [ ] **Step 3 (GREEN): Implementare entità, sensori, naming e traduzioni**
  - `naming.py`: aggiungere solo a `CANON_ENTITY_ID` le 3 nuove coppie (rispettando `ID_PREFIX = "lepas"`).
  - `select.py`: aggiungere `LepasChargeWindowModeSelect` seguendo esattamente l'Emendamento #3 e chiamando `set_charge_window_mode` (`from_restore=True` al boot, `sync_charge=True` su `async_select_option`).
  - `switch.py`: aggiungere parametro `default: bool = False` a `LepasScheduleSwitch` (riuso Ponytail), aggiungere riga `home_charge_power_auto` (`default=True`, `sync_mode="charge_power"` che chiama `notify_schedule_changed(sync_charge=True)`), e in `async_added_to_hass` per `attr == "sync_charge_to_departure"` saltare il restore se `getattr(self.coordinator, "_charge_window_mode_restored", False)` è `True`.
  - `number.py`: importare `UnitOfPower`, aggiungere entry `home_charge_power`, aggiornare `_snap_value` (clamp `[vmin, vmax]` + rounding decimali su `self._attr_native_step < 1`), `_push` (converti `int` solo se `self._attr_native_step >= 1`), e aggiungere `"home_charge_power"` ai rami `notify_schedule_changed` (`sync_charge=False` in `async_added_to_hass`, `sync_charge=True` in `async_set_native_value`).
  - `sensor.py`: aggiornare `LepasScheduledChargingWindowSensor` e `LepasNextDepartureSensor` tramite `coord.evaluate_charge_plan(...)` e `coord.charging_stats` / `home_power_profile()`.
  - `translations/en.json` & `translations/it.json`: aggiungere traduzioni complete (inclusi stati `off` / `fixed` / `smart_departure` per `select.charge_window_mode`).

- [ ] **Step 4: Verificare GREEN & naming/translations**
  Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_smart_charge_entities.py tests/test_naming.py tests/test_translations.py tests/test_vin_features.py -q --tb=short`
  Expected: PASS.

---

### Task 4: Card Lovelace (`lepas-card.js` & Test JS/Py)

**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js`
- Modify: `tests/lepas_card.test.mjs`
- Modify: `tests/test_lovelace_card.py`

**Interfaces:**
- Consumes: `select.lepas_charge_window_mode`, `switch.lepas_home_charge_power_auto`, `number.lepas_home_charge_power`, attributi `sensor.lepas_scheduled_charging_window` (`window_mode`, `effective_action`, `plan_reason`, `charge_kind`, `effective_power_kw`, `power_source`, `away_bypass_active`, `quick_override_active`).
- Produces: sezione Ricarica aggiornata in `lepas-card.js` con selettore modalità, badge contestuali, riga potenza Auto/Manuale + riepilogo `kW`, i18n IT/EN, invarianza `AB-LEP-008` (`window.customCards` senza `custom:`) e `AB-LEP-016` (`applyCarInUseState` non disabilita i controlli configurazione ricarica).

- [ ] **Step 1 (TDD RED): Aggiungere test in `tests/lepas_card.test.mjs` e `tests/test_lovelace_card.py`**
  Verificare rendering selettore `charge_window_mode`, chiamata servizio `select.select_option`, comparsa badge (`Bypass fuori casa`, `Override Partenza rapida`, `Ricarica immediata`), controlli `home_charge_power_auto` / `home_charge_power` + riepilogo `Auto AC · 2.2 kW`, assenza `custom:` in `window.customCards` (`AB-LEP-008`) e controlli ancora abilitati quando `car_in_use: true -> false` (`AB-LEP-016`).

- [ ] **Step 2: Eseguire test RED**
  Run: `node --test tests/lepas_card.test.mjs && /home/federico/.local/bin/uv run --with pytest pytest tests/test_lovelace_card.py -q --tb=short`
  Expected: FAIL.

- [ ] **Step 3 (GREEN): Aggiornare `custom_components/lepas/lovelace/lepas-card.js`**
  Implementare selettore modalità, badge contestuali, riga potenza domestica Auto/Manuale e dizionari IT/EN rispettando stile esistente e `AB-LEP-008`/`016`.

- [ ] **Step 4: Verificare GREEN**
  Run: `node --test tests/lepas_card.test.mjs && /home/federico/.local/bin/uv run --with pytest pytest tests/test_lovelace_card.py -q --tb=short`
  Expected: PASS.

---

### Verifica Finale & Dual-Gate Tier 3 (Master Agent)

- [ ] **Step 1: Suite completa + Linter + JS Tests**
  Run:
  ```bash
  /home/federico/.local/bin/uv run --with pytest pytest -q --tb=short --maxfail=2
  node --test tests/lepas_card.test.mjs
  /home/federico/.local/bin/uv run ruff check custom_components/ tests/
  /home/federico/.local/bin/uv run ruff format --check custom_components/ tests/
  ```
- [ ] **Step 2: Tier 3 Dual-Gate Audit**
  - **Pass 1:** `python3 /home/federico/skills_library/scripts/local_llm_offload.py --task review-hygiene --files ... --json` (con fallback `flash` su `lepas-card.js` UI).
  - **Pass 2 (Sentinel):** `send_message` su CID **`d69001dd-13fa-4c50-a27c-e29ec1e2b134`** verificando tutti i 6 pilastri e tutti e 6 gli emendamenti obbligatori, più lock `APPROVED_TREE=$(git write-tree)`.
- [ ] **Step 3: Graphify Sync & Release Gate (solo con conferma utente)**
  - Eseguire `graphify update .` e aggiornare `.agents/memory/antibodies/lepas.md` se emergono nuovi invarianti.
  - Bump SemVer (`minor`, es. `1.34.0`) in `manifest.json`, `pyproject.toml`, `lepas-card.js?v=...`, `CHANGELOG.md` bilingue, commit, tag e push **solo dopo conferma esplicita dell'utente** (e successivo `ha_restart` per test live anche su `timeConsuming` 15m vs 60m).
