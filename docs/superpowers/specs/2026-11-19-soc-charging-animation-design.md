# Design Spec — Animazione Anello SoC & Distinzione Ricarica AC/DC (`v1.26.0`)

**Data:** 2026-11-19  
**Target Release:** `v1.26.0`  
**Classificazione:** `Architectural` (nuova micro-feature UI con animazione CSS GPU-composited, gestione accessibilità `prefers-reduced-motion`, semantica multi-lingua e rilevamento AC/DC su `custom_components/lepas/lovelace/lepas-card.js` `>600L`, test JS/Python e bump versione).

---

## 1. Obiettivo & Scelte Approvate dall'Utente

1. **Opzione A (Orbital Sweep + Vertical Slide):** rendere immediatamente leggibile a colpo d'occhio che il veicolo è in ricarica tramite un arco orbitale animato attorno al cerchietto SoC (`54×54 px`) e uno slide verticale interno che alterna la percentuale (`76%`) con l'indicazione del tipo di ricarica (**normale AC** vs **rapida DC**).
2. **Attivazione esclusiva a ricarica attiva:** a cavo collegato ma auto ferma in attesa (es. `Collegata` con `Non in ricarica` / `0 A` in attesa di fascia programmata), il cerchietto resta **completamente statico** (nessuna orbita, nessuno slide).

---

## 2. Architettura Segnali & Rilevamento Stato (`lepas-card.js`)

### 2.1 Rilevamento Ricarica Attiva (`isCharging`)
Oggi `isCharging` in `_applyBindingsInner` controlla `this._isOn(vm.chgSwitch) || /charg/i.test(vm.chgStatus.s.state)` (escludendo `/not/i`). Questo esclude lo stato italiano `"In ricarica"` (`CHARGE_STATE_MAP["1"]`).

Estrarre una funzione pura `resolveSocChargingState(vm, helpers)` (testabile in isolamento e usata sia per `heroStateBadge` sia per `socBtn` e `chgFlowTrack`):
- **Negazioni esplicite su `vm.chgStatus`** (se presente e non dead):
  - Se lo stato normalizzato (`trim().toLowerCase()`) corrisponde a `/^(?:non\s+in\s+ricaric|not\s+charg|ricarica\s+completat|charge\s+complet|complet|idle|off|0\b)/i`, `statusSaysOff = true`, `statusSaysOn = false`.
- **Conferme attive su `vm.chgStatus`**:
  - Se `not statusSaysOff` e lo stato corrisponde a `/^(?:in\s+ricarica|charging|opladen|1)$/i` oppure `/\bcharg(?:ing|e)\b/i`, `statusSaysOn = true`.
- **Ricarica attiva (`isCharging`)**:
  - `true` se `isOn(vm.chgSwitch)` oppure `statusSaysOn`, oppure (solo quando `chgStatus` è assente/`unknown`/`unavailable` e `not statusSaysOff`) se `chgPower` > `0.1` kW.
  - Quando `plug` (`charging_cable`) o `fastPort` sono `"Collegata"` ma `chgSwitch` è `off` e `chgStatus` è `"Non in ricarica"`, `isCharging` risulta **`false`** (nessuna animazione in attesa).

### 2.2 Distinzione Normale (AC) vs Rapida (DC) (`chargeMode`)
Quando `isCharging === false`: `chargeMode = "none"`.  
Quando `isCharging === true`:
1. **`chargeMode = "fast"`** se almeno una condizione è verificata:
   - `vm.fastPort` (`sensor.*_fast_charging_port`, `FAST_GUN_MAP`) è vivo e lo stato corrisponde a `/rapid|fast|quick|\b2\b|\bdc\b/i` (escludendo `/scolleg|disconnect|unplug|\b0\b/i`);
   - `vm.chgPower` è vivo e `>= 15` kW;
   - `vm.hvVolt` e `vm.hvCurr` sono entrambi vivi e `(hvVolt * Math.abs(hvCurr)) / 1000 >= 15` kW.
2. Altrimenti **`chargeMode = "normal"`**.

---

## 3. Design Visivo & Motion (`Matte Titanium` + `prefers-reduced-motion`)

### 3.1 Anello Esterno & Arco Orbitale
- Dentro `<svg class="soc-svg" viewBox="0 0 52 52">` si mantengono `.soc-ring-bg` e `.soc-ring-fg` (`r="21"`, `stroke-dasharray="131.95"`, arco SoC fisso e nitido al posto del precedente `lp-pulse-soft` quasi impercettibile).
- Si aggiunge un `<svg class="soc-svg-orbit hidden" data-bind="socOrbit" viewBox="0 0 52 52" aria-hidden="true">` sovrapposto (`position: absolute; inset: 2px; width: 48px; height: 48px;`) con `<circle class="soc-ring-orbit" cx="26" cy="26" r="21" stroke-dasharray="28 103.95"/>`: ruotando direttamente il nodo `<svg>` con `lp-spin` si evita ogni quirk di `transform-box` / `transform-origin` su elementi SVG interni in iOS Safari e Android WebView:
  - **Normale (AC)** (`.soc-btn.is-charging:not(.is-fast-charge)`): bordo `rgba(52, 211, 153, 0.55)`, orbita `--lp-emerald` (`#34D399`), animazione `lp-spin 2.4s linear infinite`.
  - **Rapida (DC)** (`.soc-btn.is-charging.is-fast-charge`): bordo `rgba(245, 158, 11, 0.65)`, orbita `--lp-amber` (`#F59E0B`), animazione `lp-spin 1.35s linear infinite`.
  - Nessun colore fuori palette (vietato `#00D2FF` come verificato da `test_lovelace_card.py`).

### 3.2 Slide Verticale Interna (`% ↔ Tipo Ricarica`)
- Struttura dentro `.soc-btn`:
  - `.soc-viewport` (`width: 38px; height: 22px; overflow: hidden; position: relative;`)
  - `.soc-track` (`display: flex; flex-direction: column; will-change: transform;`):
    - **Slide 1 (`.soc-slide`):** `<span class="soc-val num" data-bind="socText">—</span>` (`height: 22px`).
    - **Slide 2 (`.soc-slide.soc-mode-slide.hidden`, `data-bind="socModeSlide"`):** icona dedicata (`bolt` per AC in `--lp-emerald`, nuovo path SVG `fast_charge` a doppio fulmine per DC in `--lp-amber`, `12×12 px`) + micro-etichetta `<span class="soc-mode-lbl" data-bind="socModeLbl">AC|DC</span>` (`0.56rem`, `font-weight: 700`).
  - Mantenere `<span class="soc-chg-ico hidden" data-bind="socChgIco">` come fallback statico solo in `@media (prefers-reduced-motion: reduce)` (nascosto sotto `prefers-reduced-motion: no-preference`, visibile in `reduce` mentre `.soc-mode-slide` resta nascosto, così l'utente con moto ridotto vede sempre `76%` + icona AC/DC differenziata senza sovrapposizioni).
- Animazione `@keyframes lp-soc-slide` (solo dentro `@media (prefers-reduced-motion: no-preference)` e solo con `.soc-btn.is-charging`):
  - `0%, 40% { transform: translateY(0); }`
  - `48%, 88% { transform: translateY(-22px); }`
  - `96%, 100% { transform: translateY(0); }`
  - Durata `5.2s ease-in-out infinite` (esclusivamente proprietà `transform` su GPU compositor).
- Accessibilità: aggiornare `aria-label` su `socBtn` e `socProgress` con percentuale + stato localizzato (`it`, `en`, `nl`), es. `"76% · In carica (AC)"` / `"76% · In carica rapida (DC)"`.

---

## 4. Vincoli di Compatibilità, Testing & Rilascio

- **Sintassi Card:** zero `?.`, zero `??`, zero `import`/`export` top-level (`tests/test_lovelace_card.py`).
- **Test JS (`tests/lepas_card.test.mjs`):**
  - Verificare `isCharging === false` quando cavo/presa rapida collegati ma `chgStatus = "Non in ricarica"` e `chgSwitch = "off"` (nessuna classe `is-charging`, orbita e slide nascoste).
  - Verificare `isCharging === true` con `chgStatus = "In ricarica"` (italiano) e `"Charging"` (inglese), sia in modalità normale (`chargeMode === "normal"`, classe `is-charging` senza `is-fast-charge`, label `"AC"`) sia in modalità rapida (`fastPort = "Collegata (ricarica rapida)"` o `chgPower >= 15`, classe `is-fast-charge`, label `"DC"`).
  - Verificare transizione attiva → scollegato sullo stesso elemento DOM renderizzato (rimozione pulita di `is-charging`, `is-fast-charge` e ripristino `hidden`).
- **Versioning (`v1.26.0`):** aggiornamento sincronizzato in `custom_components/lepas/manifest.json`, `pyproject.toml`, `custom_components/lepas/lovelace/lepas-card.js` (`?v=1.26.0`), `tests/test_lovelace_card.py` e `CHANGELOG.md`.
