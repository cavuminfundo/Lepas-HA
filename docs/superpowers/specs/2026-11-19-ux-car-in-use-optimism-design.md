# Design Spec — UX Partenze, Rilevamento "Auto in uso", Annullamento Ottimismo su `reason` e Esito in Tab Clima (`v1.25.0`)

**Data:** 2026-11-19  
**Target Release:** `v1.25.0`  
**Scope Classification:** Architectural (`>= 3` file interdipendenti tra backend coordinator/entità e frontend Lovelace, con contratto end-to-end tra telemetria/conferme MQTT, attributi HA e disabilitazione/rendering UI).

---

## 1. Contesto ed Evidenze Empiriche

1. **Bug sedile riscaldato (`11:13:03Z`, auto reale in uso):**
   - Con vettura attiva/in uso (`hVoltageState=1`, `frontHVACState=1`, `23 °C`), l'utente ha premuto `switch.lepas_driver_seat_heating`.
   - Il backend ha risposto `HTTP 200 A00079`, quindi `LepasOptimisticMixin._run_command` ha mantenuto `_opt_value = True`.
   - 1,4 s dopo (`11:13:05.232Z`), l'auto ha inviato via MQTT una conferma con `reason: [{"modelId": "0", "code": "95"}, {"modelId": "4", "code": "95"}]` senza includere `dSeatHeatingState` nei `msg_fields`.
   - **Bug A (Backend):** `LepasOptimisticMixin._verita_arrivata()` azzera `_opt_value` solo se `dSeatHeatingState` compare in `msg_fields` o dopo `OPT_MAX_S = 900s`. Lo switch è rimasto finto `on` per ~2m30s fino allo spegnimento manuale.
   - **Bug B (Frontend):** `cmdResultBadge` (`lepas-card.js`) esiste solo nella tab **Plancia (Overview)**, non nella tab **Clima**.

2. **Spike `/asr/manager/realtime` su auto reale (97 chiavi catturate):**
   - Non esistono campi `accState`, `keyStatus`, `readyState` o `gearPos`.
   - Segnali disponibili: `hVoltageState`, `engineState`, `vehicleSpeed`, `chargeGunState`, `frontHVACState`, `doorLock`, `frontLeftDoor`/`frontRightDoor`/`backLeftDoor`/`backRightDoor`, `odometer`, `onlineStatus`, più i push di conferma `reason` (es. `4:95`).

3. **UX Partenze (Opzione 1 approvata dall'utente):**
   - Nella sezione Partenze programmate di `lepas-card.js`, le due righe di riepilogo (`nextDep` e `schedDep`) devono distinguere chiaramente il piano **Prossima partenza** (stato calcolato da HA) da **Su auto** (stato sincronizzato/pendente sul veicolo).

---

## 2. Architettura & Contratti

### 2.1 Annullamento istantaneo ottimismo su rifiuto centralina (`reason`)
- **Mappa moduli (`coordinator.py`):**
  - Introdurre `REASON_FIELD_MAP` allineata a `REASON_MODULI`:
    - `"4"` → `("dSeatHeatingState",)`
    - `"5"`, `"6"`, `"8"` → `("pSeatHeatingState", "lSeatHeatingState2", "rSeatHeatingState2")`
    - `"9"` → `("dSeatVentilateState",)`
    - `"10"`, `"11"`, `"13"` → `("pSeatVentilateState", "lSeatVentilateState2", "rSeatVentilateState2")`
  - **Invariante `_solo_clima` (`0:95`):** Se `reason` soddisfa `_solo_clima(reason)` (solo `modelId == "0"`), NON produce alcun rifiuto (`cmd_rejected_fields = frozenset()`, `cmd_rejected_other = False`), preservando il comportamento esistente su comandi clima/spegnimento.
  - Se `is_confirmation` è `True` e `reason` è valorizzato e `not self._solo_clima(reason)`:
    - Mappare i `modelId` presenti in `REASON_FIELD_MAP` dentro `rejected_fields: set[str]`.
    - Se compare un `modelId != "0"` non presente in `REASON_FIELD_MAP` (es. `"15"`, `"16"`, o struttura non-lista/non-dict), impostare `cmd_rejected_other = True`.
    - Per `modelId == "0"` in presenza di un altro modulo fallito: NON aggiungere `"frontHVACState"` se `code == "95"`; aggiungerlo solo se `code != "95"` **e** `result not in ("1", "2", "5")`.
  - Su messaggi non di conferma (es. `5A02` puro), azzerare `cmd_rejected_fields = frozenset()` e `cmd_rejected_other = False` nel `patch`.
  - Inoltre, se `is_confirmation` porta un rifiuto (`rejected_fields` o `cmd_rejected_other`), delegare al loop HA tramite `@callback _schedule_probe_on_loop()` (`self.hass.loop.call_soon_threadsafe(...)`) che verifica sul loop `not self._timers.closing and self.poll_enabled and not self._poll_busy`, imposta `self._poll_busy = True` **sincronamente** nel `@callback` (con rollback in `except` se `async_create_task` fallisce) e avvia `_run_guarded_probe()` (`try: await self.async_probe(force=True) finally: self._poll_busy = False`) per riallineare subito `hVoltageState`/`vehicleSpeed`/`frontHVACState`.
- **Mixin (`entity.py`):**
  - `LepasOptimisticMixin._verita_arrivata()`: oltre a `any(k in msg for k in self._opt_keys)`, restituisce `True` quando `last_seen != self._opt_anchor` e:
    - `any(k in (data.get("cmd_rejected_fields") or ()) for k in self._opt_keys)`, oppure
    - `bool(data.get("cmd_rejected_other"))` (solo quando `self._opt_keys` è non vuoto).
- **Mutua esclusione (`switch.py`):**
  - In `LepasComfortSwitch`: se `_handle_coordinator_update` annulla l'ottimismo a seguito di un rifiuto (`_rifiuto_arrivato()`), azzera anche l'eventuale `_exclusive._opt_value` se questo aveva lo stesso `_opt_anchor` (o è stato impostato nell'istante della chiamata rifiutata), evitando che il gemello (es. sedile ventilato) resti bloccato su un falso `False` ottimistico.
  - `LepasClimaMacroSwitch`: invariato sul rifiuto parziale dei soli sedili (perché il clima della macro può comunque essere partito), mantenendo la correzione unidirezionale `_spento_dall_auto` via `msg_fields`.
- **Clima (`climate.py`):**
  - `LepasClimate._handle_coordinator_update`: azzera `_opt_on` anche quando `last_seen != self._opt_anchor` e (`CAMPO_CLIMA in (data.get("cmd_rejected_fields") or ())` or `bool(data.get("cmd_rejected_other"))`).

### 2.2 Rilevamento `is_car_in_use()` e Sondaggio HV / `DRIVE_WATCH`
- **Stato di sessione HV (`coordinator.py`):**
  - Campi in `LepasCoordinator.__init__`:
    - `self._hv_lock: threading.Lock = threading.Lock()` (dedicato, mai annidato dentro `self._state_lock` per rispettare `AB-LEP-007`)
    - `self._hv_session_in_use: bool = False`
    - `self._hv_session_start_odo: float | None = None`
    - `self.data["car_in_use"] = False`
  - Funzione `_evaluate_car_in_use(self, rt: dict | None, fields: dict | None, *, msg_fields: dict | None = None, comfort_rejected: bool = False) -> bool` (protetta da `with self._hv_lock:` esclusivamente intorno a lettura/mutazione di `_hv_session_in_use` e `_hv_session_start_odo`, senza mai chiamare `_auto_e_sveglia()` né acquisire `_state_lock`):
    - Legge `hVoltageState`, `engineState`, `vehicleSpeed`, `chargeGunState`, `frontHVACState`, `frontLeftDoor`/`frontRightDoor`/`backLeftDoor`/`backRightDoor`, `odometer`:
      - nel path `_on_probe_data`: precedenza `rt` > `fields` (`msg_fields=None`);
      - nel path `_on_car_message` (push `5A02`/ack): precedenza `msg_fields` > `rt` > `fields`, così un `realtime` stantio non maschera mai un `engineState="1"` o una porta aperta appena arrivati via MQTT.
    - `hv_on = field_on(hv_val)` (`True`, `False`, `None`); `eng_on = field_on(eng_val) is True`; `speed_pos = float(speed_val) > 0` (safe float).
    - **Reset:** se `hv_on is False` e `not eng_on` e `not speed_pos`: resetta `_hv_session_in_use = False`, `_hv_session_start_odo = None` e restituisce `False`.
    - **Sessione HV attiva** (`hv_on is True or eng_on or speed_pos`):
      - Registra `_hv_session_start_odo` alla prima lettura positiva di `odometer`.
      - Attiva il latch `self._hv_session_in_use = True` se si verifica almeno una condizione:
        1. `eng_on` (`engineState == 1`)
        2. `speed_pos` (`vehicleSpeed > 0`)
        3. `not plugged and not hvac_on` (`hVoltageState == 1` senza ricarica né clima remoto)
        4. `any_door_open` (una delle 4 porte aperta mentre HV attivo)
        5. `odo_increased` (`odometer` attuale > `_hv_session_start_odo`)
        6. `comfort_rejected` (rifiuto `reason` non-`_solo_clima` ricevuto durante sessione HV attiva)
      - Nota anti-falso-positivo: `doorLock == 1` (sbloccata) da solo NON attiva il latch, così chi pre-climatizza l'auto sbloccata in garage privato non viene bloccato.
    - **Sconosciuto (`hv_on is None`):** mantiene `self._hv_session_in_use` (inizialmente `False`).
  - Metodo pubblico `is_car_in_use(self) -> bool`: legge `bool(self._hv_session_in_use)` sotto `with self._hv_lock:` (in modo sincrono e deterministico, mentre `patch["car_in_use"]` mantiene sincronizzato `self.data["car_in_use"]`).
  - **Sondaggio HV / `DRIVE_WATCH`:**
    - `_hv_followup_cb`: verifica `if self._timers.closing or not self.poll_enabled: return`; se `self._poll_busy`, riarma `self._arm_hv_followup()` e ritorna senza sovrapporsi; altrimenti imposta `self._poll_busy = True` in `try ... finally: self._poll_busy = False` ed esegue `await self.async_probe(force=True)`.
    - `@callback _schedule_probe_on_loop`: esegue sul loop HA la guardia `if self._timers.closing or not self.poll_enabled or self._poll_busy: return`, imposta `self._poll_busy = True` sincronamente prima di `self.hass.async_create_task(self._run_guarded_probe())` (rollback in `except`, rilascio in `finally`).
- **Esposizione attributo `car_in_use` (zero nuove entità HA):**
  - `custom_components/lepas/binary_sensor.py` (`LepasRealtimeBinary`): per `self._field == "hVoltageState"`, esporre `@property def extra_state_attributes(self) -> dict[str, object] | None` con `{"car_in_use": bool(fn())}`.
  - `custom_components/lepas/climate.py` (`LepasClimate`): esporre `@property def extra_state_attributes(self) -> dict[str, object] | None` con `{"car_in_use": bool(fn())}`.

### 2.3 Frontend `lepas-card.js` — Tab Clima & UX Partenze (Opzione 1)
1. **Tab Clima (`panel[data-panel="climate"]`):**
   - `carInUse`: letto da `climate.s.attributes.car_in_use === true || hvActive.s.attributes.car_in_use === true` (`hvActive = this._findDomain(items, "binary_sensor", "high_voltage_active", "rt_alta_tensione")`).
   - Banner esplicativo `data-bind="carInUseBanner"` (`role="status"`, visibile quando `carInUse === true`, nascosto altrimenti con `.hidden` e `.hidden = true/false`).
   - Disabilitazione (`disabled = carInUse`, `aria-disabled = carInUse ? "true" : "false"`, classe `.is-car-in-use`) di tutti i comandi comfort nella tab Clima: `climateToggleBtn`, `temp_down`, `temp_up`, `[data-action-id="climate_duration"]`, `coolAllBtn`, `heatAllBtn`, `[data-defrost-btn]`, `[data-seat-btn]`. In `_handleClick` / `_triggerAction`, ignorare click su bottoni `disabled`. CSS: separare `.ctrl-btn:disabled` (`opacity: 0.55; cursor: not-allowed;`) da `.ctrl-btn.is-pending` (`opacity: 0.58; cursor: wait;`), aggiungere `.chip-btn:disabled`, e su `.is-car-in-use` renderizzare un overlay `::after` traslucido (`rgba(17, 19, 23, 0.72)`) con simbolo di stop `⊘` + etichetta breve localizzata `t.inUseShort` (`Auto in uso` / `Car in use` / `In gebruik`, via attributo `data-in-use-label`) sui bottoni larghi (`climateToggleBtn`, macro, sbrinamenti) e il solo simbolo `⊘` sui controlli stretti (stepper `+/-`, chip durata, pulsanti sedili) per evitare troncamenti.
   - **`cmdResultBadge` in Tab Clima:** aggiungere un `<span class="badge hidden" data-bind="cmdResultBadge"></span>` nella tab Clima (barra stato dedicata compatta) e aggiornare `root.querySelectorAll('[data-bind="cmdResultBadge"]')` così sia Plancia sia Clima mostrino lo stesso esito comando in tempo reale.
2. **UX Partenze (Opzione 1):**
   - Riga 1 (`nextDep`): etichetta `t.nextDeparture` (`Prossima partenza` / `Next departure` / `Volgend vertrek`), valore `vm.nextDep.s.state` (es. `Oggi 13:25 (clima 13:10)` oppure `Disattivata`).
   - Riga 2 (`schedDep`): etichetta `t.onCar` (`Su auto` / `On car` / `In auto`):
     - `carActive && !hasPending && isSynced === true` → `Sincronizzata` / `Synced` / `Gesynchroniseerd` (verde `.is-emerald`, senza ripetere l'orario).
     - `hasPending || isSynced === false` → `Da applicare (auto: <orario|spenta>)` / `To apply (car: <time|off>)` / `Toepassen (auto: <tijd|uit>)` (ambra `.is-amber`).
     - Tutto spento (`!carActive && !hasPending && isSynced !== false`) → `Disattivata` / `Disabled` / `Uitgeschakeld`.
     - Fallback legacy (`hasPending === null` e `carActive === true`) → `formatCarNextDeparture(...)`.

### 2.4 Release & Versioning
- Aggiornare in modo sincronizzato a `1.25.0`: `custom_components/lepas/manifest.json`, `pyproject.toml`, `custom_components/lepas/lovelace/lepas-card.js`, `CHANGELOG.md` (IT + EN).
- Zero nuove entità HA (`tests/test_entity_count.py` invariato).
- `lepas-card.js` resta compatibile ES5 (zero `?.`, zero `??`, zero top-level `import`/`export`).
