# Specifica Design — Retry Automatico Protetto con Sveglia su `A07900` (`v1.23.0`)

**Data:** 2026-11-19
**Target:** `custom_components/lepas/const.py`, `custom_components/lepas/coordinator.py`, `tests/test_a07900_wake_retry.py`, docs & versioning (`1.23.0`)
**Classificazione:** Architectural (sincronizzazione cross-thread `paho` ↔ `asyncio`, macchina a stati `async_send_command`, lock `_cmd_gate` / `_state_lock`, test falsificabili di concorrenza)

---

## 1. Contesto & Obiettivi
Quando l'auto è a riposo e l'utente o un'automazione invia un comando diretto (`async_send_command`), `tspconsole-eu` risponde con `CommandError(code="A07900")` (*auto a riposo*). Oggi il comando fallisce immediatamente costringendo l'utente a premere prima *Sveglia/Localizza* e attendere manualmente.

L'obiettivo è introdurre un **retry automatico protetto (massimo 1 volta)** dentro `LepasCoordinator.async_send_command`, sincronizzato con l'effettivo risveglio MQTT dell'auto (`_on_car_message` → `asyncio.Event`), senza deadlock su `_cmd_gate`, senza tempeste di sveglie (`A07900_WAKE_COOLDOWN_S = 60`), e senza consumare tentativi PIN (`taskId` già in cache).

---

## 2. Architettura & Componenti

### 2.1 Costante Anti-Tempesta (`custom_components/lepas/const.py`)
- Aggiungere `A07900_WAKE_COOLDOWN_S = 60` (secondi minimi tra due sveglie automatiche innescate da `A07900`).
- Importare `A07900_WAKE_COOLDOWN_S` in `custom_components/lepas/coordinator.py`.

### 2.2 Sincronizzazione Cross-Thread `paho` ↔ `asyncio` (`coordinator.py`)
In `LepasCoordinator.__init__`:
- `self._last_a07900_wake_ts: float = 0.0` (clock `time.monotonic()`; `0.0` = nessuna sveglia A07900 ancora eseguita).
- `self._mqtt_msg_event: asyncio.Event = asyncio.Event()`

In `LepasCoordinator._on_car_message`:
- Dopo l'aggiornamento atomico di `self._last_msg_ts = now` sotto `with self._state_lock:` e l'accodamento di `self._update(patch)`, notificare il loop asyncio dal thread paho:
  ```python
  self.hass.loop.call_soon_threadsafe(self._mqtt_msg_event.set)
  ```

In `LepasCoordinator.async_stop`:
- Subito dopo `self._timers.close()`, svegliare un'eventuale `_wait_for_car_wake` in corso (protetto da `try ... except RuntimeError: pass` se il loop è già chiuso) per evitare attese fino a 25 s in fase di unload.

In `LepasCoordinator._wait_for_car_wake(self, baseline_ts: float, timeout: float = POLL_WAKE_WAIT) -> bool`:
- Attende fino a `timeout` secondi (default `POLL_WAKE_WAIT = 25`) che arrivi un messaggio MQTT con `self._last_msg_ts > baseline_ts`.
- Schema anti-race (nessuna perdita di segnale tra check e `clear()`):
  1. Se `self._timers.closing`: `return False`.
  2. Controlla `self._last_msg_ts > baseline_ts` sotto `with self._state_lock:` → se `True`, `return True`.
  3. Chiama `self._mqtt_msg_event.clear()`.
  4. Ricontrolla `self._last_msg_ts > baseline_ts` sotto `with self._state_lock:` → se `True`, `return True`.
  5. Attende `await asyncio.wait_for(self._mqtt_msg_event.wait(), timeout=remaining)` in loop fino a `deadline` (gestendo risvegli spuri o chiusura).
  6. Su `asyncio.TimeoutError`, esegue un ultimo check sotto `with self._state_lock:` e ritorna `(not self._timers.closing) and (self._last_msg_ts > baseline_ts)`.

### 2.3 Flusso in `async_send_command` (`coordinator.py`)
Firma:
```python
async def async_send_command(
    self,
    key: str,
    params: dict | None = None,
    *,
    _allow_wake_retry: bool = True,
) -> str:
```
Nota di compatibilità: `_sveglia_una_volta()` continua a chiamare `await self.async_send_command("localizza")` senza parametri aggiuntivi (preservando la compatibilità con tutti i test che monkeypatchano `async_send_command(self, key, params=None)`).

Helper `_should_wake_retry_on_a07900(self, key: str, err: Exception, allow_wake_retry: bool) -> bool`:
Restituisce `True` **solo** se tutte le condizioni seguenti sono soddisfatte:
1. `getattr(err, "code", None) == "A07900"`
2. `allow_wake_retry is True`
3. `key != "localizza"`
4. `not self._timers.closing`
5. `not self.auto_sveglia`
6. `self._last_a07900_wake_ts == 0.0 or (time.monotonic() - self._last_a07900_wake_ts) >= A07900_WAKE_COOLDOWN_S`

Transizioni su `CommandError` idoneo:
1. Nel blocco `except Exception as err:` del tentativo 1, se `_should_wake_retry_on_a07900(...)` è `True`:
   - Cattura `wake_err = err`, `err_note_cmd = list(self._note_cmd)`, `err_note_cmd_at = self._note_cmd_at` e `err_cmd_status` (stato pubblicato dal tentativo 1 se aggiornato, altrimenti `str(err)[:STATO_MAX]`).
   - **Non** registra ancora `_diag.record(ok=False)` e **non** chiama ancora `_instrada_rimedio(err)`.
   - Esce dal blocco `try ... finally`: il `finally` rilascia `self._cmd_gate` (`if not consegnato: self._cmd_gate.release()`) **prima** della sveglia → **zero deadlock** quando `async_assicura_sveglia()` acquisisce `_cmd_gate` per inviare `"localizza"`.
2. Fuori dal `try ... finally` (con `_cmd_gate` libero):
   - Imposta `self._last_a07900_wake_ts = time.monotonic()`.
   - Cattura `with self._state_lock: baseline_ts = self._last_msg_ts` **prima** di `await self.async_assicura_sveglia()` (cattura anche eventuali push MQTT arrivati durante l'HTTP di `localizza`).
   - Esegue `await self.async_assicura_sveglia()`.
   - Attende `woke = (not self._timers.closing) and await self._wait_for_car_wake(baseline_ts, timeout=POLL_WAKE_WAIT)`.
3. Se `woke is True`:
   - Esegue `return await self.async_send_command(key, params, _allow_wake_retry=False)` (riusa `taskId` già in cache senza consumare PIN).
4. Se `woke is False` (timeout o `closing`):
   - Registra `self._diag.record("command", key=key, ok=False, ...)` se `self._diag is not None`.
   - Ripristina `self._note_cmd`, `self._note_cmd_at` e `self._apply_update({"cmd_status": err_cmd_status})`.
   - Chiama `self._instrada_rimedio(wake_err)` e rilancia `raise wake_err`.
5. Se `asyncio.CancelledError` colpisce `async_assicura_sveglia()` o `_wait_for_car_wake()`, `_cmd_gate` è già stato rilasciato dal `finally` del tentativo 1 e resta libero.

---

## 3. Strategia di Verifica TDD (`tests/test_a07900_wake_retry.py`)
Tutti i test devono esercitare il `LepasCoordinator.async_send_command` reale (nessun mock della funzione sotto test), verificando il contratto su `_send_command`, `_on_car_message`, `_cmd_gate`, `cmd_status`, `_instrada_rimedio` e `taskId` cache:
1. **Risveglio MQTT OK + Retry riuscito**: tentativo 1 riceve `A07900`, `_cmd_gate` viene rilasciato prima di `localizza`, push MQTT sveglia `_wait_for_car_wake`, tentativo 2 riesce riusando `taskId` dalla cache (`checkPassword` chiamato una sola volta / zero chiamate extra).
2. **Timeout MQTT → nessun retry e stato originale preservato**: `localizza` viene inviato e aggiorna temporaneamente `cmd_status`, `_wait_for_car_wake` va in timeout, il comando originale non viene ritentato, `cmd_status` torna al messaggio dell'errore `A07900` originale, `_instrada_rimedio(err)` viene chiamato e viene rilanciato l'errore `A07900` originale.
3. **Cooldown 60s attivo**: con `_last_a07900_wake_ts` recente (`< 60s`), nessuna sveglia e nessun retry; `A07900` rilanciato subito.
4. **`auto_sveglia == True`**: con `_last_msg_ts` recente, nessuna sveglia e nessun retry; `A07900` rilanciato subito.
5. **`key == "localizza"`**: un `A07900` su `"localizza"` non innesca ricorsione né retry.
6. **Doppio `A07900`**: anche il retry (`_allow_wake_retry=False`) riceve `A07900` → esattamente 1 sveglia e 1 retry (2 invii comando + 1 `localizza`), poi rilancia `A07900`.
7. **`CancelledError` durante attesa MQTT/sveglia**: cancellando il task durante `_wait_for_car_wake`, `coord._cmd_gate.locked()` è `False` e nessun secondo invio parte.
8. **Anti-race push durante sveglia & sblocco su `async_stop()`**: un messaggio MQTT arrivato mentre `async_assicura_sveglia()` è ancora in corso fa tornare `True` immediatamente da `_wait_for_car_wake`; `async_stop()` durante attesa sblocca subito `_wait_for_car_wake` ritornando `False`.
