# Specifica Design — Popup Modale `<dialog>` & Stato Sintetico Ultimo Comando (`v1.22.0`)

**Data:** 2026-11-18
**Target:** `custom_components/lepas/lovelace/lepas-card.js`, `tests/lepas_card.test.mjs`, `tests/test_lovelace_card.py`, versioning (`manifest.json`, `pyproject.toml`, `CHANGELOG.md`)
**Classificazione:** Architectural (nuovo componente UI `<dialog>` modale + riscrittura UX conferme & esito comandi; include i due fix partenze della bozza v1.21.3 già verificati in locale)

---

## 1. Obiettivi & Vincoli
1. **Conferma modale esplicita (`<dialog>`)** per prevenire tocchi accidentali su:
   - Tutti i **comandi one-shot / stateless** (azioni `button` che non lasciano uno stato o un'icona accesa/animata nella card): `wake_car`, `refresh_location`, `refresh_full`, `locate_gps`, `flash_lights` / `sec_flash_lights`, `vent_windows`, `vent_sunroof`, `remote_start`, `apply_charging_schedule`, `apply_departure_schedule`.
   - Tutti i **5 comandi sensibili stateful** (`unlock` / `quick_unlock`, `trunk_open` / `quick_trunk_open`, `windows_open`, `sunroof_open`, `alarm_toggle`), sostituendo completamente il vecchio doppio tap inline da 4 secondi (`_confirmState`, `_confirmTimer`, `.is-confirming`, `.confirm-bar`).
   - Restano **immediati (1 tap)** tutti gli altri controlli stateful non distruttivi (switch clima/sedili/sbrinatori/ricarica/partenza rapida/giorni, `lock_now`, `trunk_close`, `windows_close`, `sunroof_close`, `climate_toggle`, `temp_down`/`temp_up`, selettori durata/orari/preset, tab).
2. **Badge sintetico "Ultimo comando"** al posto delle frasi di debug di `sensor.lepas_command_result`:
   - `sensor.lepas_command_result` nel backend Python (`coordinator.py`, `sensor.py`) resta invariato per preservare diagnostica, log e test backend esistenti.
   - Nella card (`cmdResultBadge`), le frasi raw del sensore sono mappate lato client in due soli stati chiari (IT/EN/NL) accompagnati dall'orario `HH:MM`:
     - **Successo / in corso**: `Ultimo comando · HH:MM ✓` / `Last command · HH:MM ✓` / `Laatste opdracht · HH:MM ✓` (classe `.is-emerald`).
     - **Errore / rifiuto / segnalazione guasto**: `Errore invio comando · HH:MM ✕` / `Command failed · HH:MM ✕` / `Opdracht mislukt · HH:MM ✕` (classe `.is-coral`).
   - Se un comando viene inviato dalla card e `callService` fallisce o risolve prima che `sensor.lepas_command_result` aggiorni `last_changed`, la card mostra immediatamente il feedback locale (`_lastCmdFeedback`) finché non arriva un `last_changed`/`last_updated` più recente dal sensore.
3. **Consolidamento `v1.21.3` → `v1.22.0`**:
   - Mantenere le migliorie partenze già implementate nel working tree (`formatCarNextDeparture`, `Prossima partenza: Attiva` quando HA è vuoto ma l'auto è attiva) e allineare tutto a SemVer `1.22.0`.
4. **Compatibilità WebView & Modern Web Guidance**:
   - Nessun `?.` o `??` (compatibilità Android System WebView).
   - `<dialog>` nativo nello Shadow DOM con `showModal()` (e fallback sicuro `setAttribute("open", "")` se `typeof dlg.showModal !== "function"`), `aria-labelledby`, `autofocus` sull'azione sicura (**Annulla**), `dialog:modal` + `::backdrop` (`overscroll-behavior: contain`, `overflow: hidden` sul backdrop), light-dismiss tramite `pointerdown`+`pointerup` fuori dal bounding rect (compatibile con Safari/WebView senza `closedby`), e reset `dlg.returnValue = ""` su `close`.

---

## 2. Architettura del Flusso di Conferma & Stato

### 2.1 Mappa Azioni con Modale (`CONFIRM_ACTIONS`)
Ogni voce registrata via `regAction(actionId, domain, service, data, needsConfirm, confirmKey, confirmLabel)` indica:
- `needsConfirm: true` per i 10 comandi stateless + i 5 sensibili stateful (`unlock`, `quick_unlock`, `trunk_open`, `quick_trunk_open`, `windows_open`, `sunroof_open`, `alarm_toggle`, `vent_windows`, `vent_sunroof`, `remote_start`, `wake_car`, `refresh_location`, `refresh_full`, `locate_gps`, `flash_lights`, `sec_flash_lights`, `apply_charging_schedule`, `apply_departure_schedule`).
- `confirmLabel`: titolo leggibile localizzato del comando mostrato nel modale (es. `"Stato completo"`, `"Sblocca"`, `"Applica su auto"`, `"Disattiva su auto"`).

### 2.2 Ciclo di Vita `<dialog data-bind="confirmDialog">`
1. Click su pulsante con `spec.needsConfirm === true` → apre `<dialog>` popolando titolo (`t.confirmModalTitle`), nome azione (`spec.confirmLabel`), ed evitando di inviare `callService`.
2. **Conferma** (`[data-dialog-action="confirm"]`): chiude il modale (`dlg.close("confirm")`), invia `this._callService(...)` con `_pendingKeys` attivo (il bottone resta disabilitato finché la Promise risolve/rigetta, evitando doppi invii).
3. **Annulla / Esc / Click esterno** (`[data-dialog-action="cancel"]`, `cancel`, backdrop click): chiude senza chiamare `callService`.
4. **Invariante anti-leak stato**: `this._pendingDialogAction` viene azzerato su `close`/`cancel` e su `disconnectedCallback()`. I `set hass()` esterni mentre il modale è aperto NON ricostruiscono lo Shadow DOM sopra `<dialog open>` (o ri-sincronizzano solo i binding senza chiudere/ricreare il nodo `<dialog>` perché `structKey` non cambia!).

### 2.3 Classificazione & Formattazione `cmdResultBadge`
Helper puro esportato `formatCommandOutcome(cmdStateObj, localFeedback, lang)`:
- Estrae timestamp `ts`: `localFeedback` (se più recente di `cmdStateObj.last_changed`/`last_updated`) oppure `cmdStateObj.last_changed || cmdStateObj.last_updated`. Formatta `HH:MM` via `formatTimestamp(ts, lang)`.
- Classifica errore (`isError`):
  - `true` se `localFeedback` ha `ok: false`, OPPURE se `state` contiene indicatori di guasto/rifiuto (`"❌"`, `"⚠️"`, `"rifiut"`, `"errore"`, `"error"`, `"fallit"`, `"failed"`, `"non riuscit"`, `"scadut"`, `"bloccat"`, `"eseguito solo in parte"`).
  - `false` altrimenti (es. `"✅"`, `"⏳"`, `"OK"`, `"inviato"`, `"Comando eseguito..."`, `"unica segnalazione"`).
- Restituisce `{ text, ok }` (es. `{ text: "Ultimo comando · 20:10 ✓", ok: true }` o `{ text: "Errore invio comando · 20:10 ✕", ok: false }`).

---

## 3. Strategia di Verifica
- **Unit & DOM Shadow DOM (`tests/lepas_card.test.mjs`)**:
  - Estendere `MiniElement` con supporto `<dialog>` (`showModal()`, `close()`, `open`, `returnValue`, evento `close`).
  - Test falsificabili per:
    1. Click su ogni comando stateless (`refresh_full`, `refresh_location`, `wake_car`, `flash_lights`, `locate_gps`, `apply_charging_schedule`, `apply_departure_schedule`) e sui 5 sensibili stateful (`unlock`, `trunk_open`, `windows_open`, `sunroof_open`, `alarm_toggle`) apre `<dialog>` SENZA chiamare `callService`; click su **Annulla** / `Esc` non chiama `callService`; click su **Invia** chiude il modale e chiama `callService` esattamente 1 volta.
    2. I comandi stateful non distruttivi (`lock_now`, `climate_toggle`, `temp_up`, `seat_driver_heat`, `quick_departure_toggle`, `day_chip`) restano 1-tap immediati.
    3. `formatCommandOutcome` & `cmdResultBadge`: zero testi debug grezzi in DOM, mostra `"Ultimo comando · HH:MM ✓"` su esito ok, `"Errore invio comando · HH:MM ✕"` su errore backend (`❌`/`⚠️`/rifiuto) o rigetto `callService` (IT/EN/NL).
    4. Assenza totale delle vecchie classi `.is-confirming` / `.confirm-bar` / `data-confirming`.
- **Integrazione Python (`tests/test_lovelace_card.py` + `.venv/bin/pytest`)**:
  - Verifica `?v=1.22.0` sincronizzato e assenza regressioni su tutti gli 810+ test esistenti.
