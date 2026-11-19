# Top-Down Car OEM SVG Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Dual-Gate Plan Audit Matrix

| Stadio | Ruolo / Modello | Conversation ID | Verdetto | Note |
|---|---|---|---|---|
| **Stage 1 (Domain & Archaeology Pre-Audit)** | `stage1_plan_auditor` (`flash`) | `2c097c70-df64-4bac-8d96-fd6005e413a9` | `NEEDS_CHANGES -> RISOLTO` | Corretta direzione rotazione portiere (`+22deg` SX / `-22deg` DX + `transform-box: view-box`), ordine cascata `@container (max-width: 340px)`, firma `renderCarTopViewSvg(t)`, test su tutti i 5 `VALID_COLORS` e riferimento esplicito `AB-LEP-008` / `AB-LEP-014`. |
| **Stage 2 (Six-Pillars Sentinel Control Gate)** | `sentinel_auditor` (`inherit`) | `9d403987-d497-46f2-91ca-66057d01d5ee` | `APPROVED` | Verificati tutti i 6 pilastri dopo correzione larghezza minima `.bp-stage` (`236px` compatibile con cockpit 3 colonne `>=960px`), `.tpms-col { min-width: 0; }`, firma unificata `renderCarTopViewSvg(t)`, test live `hass` re-binding e transizione `.bp-sunroof-vent`. |

**Goal:** Sostituire lo schema rettangolare dell'auto dall'alto (`blueprintSvg`) in `custom_components/lepas/lovelace/lepas-card.js` con una vista SVG OEM multi-livello della Lepas L8 sincronizzata al colore veicolo, con 4 pneumatici legati agli alert TPMS e distinzione visiva tra tetto aperto e tetto in ventilazione/tilt.

**Architecture:** Tutto il rendering resta inline in `lepas-card.js` tramite una funzione dedicata `renderCarTopViewSvg(t)` (`viewBox="0 0 200 340"`) con gradienti CSS pilotati da `data-car-color` su `.bp-stage`, portiere sagomate incernierate sul profilo reale, 4 elementi `[data-bp-wheel]` sincronizzati al loop TPMS e stati differenziati su `[data-bp-part="sunroof"]` (`.is-open` vs `.is-tilted`). Nessun asset binario né modulo JS aggiuntivo; tutti i contratti `data-bp-part` e `data-bp-lock` esistenti restano invariati.

**Tech Stack:** Vanilla ES5/ES6 WebView-safe JavaScript (Custom Element + Shadow DOM), inline SVG, CSS Custom Properties & `@container` / `@media (prefers-reduced-motion)`, Node `node:test`, Python `pytest`.

**Spec:** `docs/superpowers/specs/2026-11-19-topdown-car-svg-design.md`

---

## Global Constraints

- **WebView Compatibility (`tests/test_lovelace_card.py`):** Vietati optional chaining (`?.`), nullish coalescing (`??`) e `:host-context` in `custom_components/lepas/lovelace/lepas-card.js`.
- **Matte Titanium & Contrast:** Rispettare i token `--lp-*` su `:host` (`--lp-canvas: #111317`, `--lp-surface: #181B20`, `--lp-elevated: #21252C`, `--lp-emerald: #34D399`, `--lp-glacier: #60A5FA`, `--lp-amber: #F59E0B`, `--lp-coral: #EF4444`); garantire contrasto >= 3:1 su tutte le varianti `data-car-color` (`grey`, `teal`, `violet`, `black`, `white`).
- **Accessibility & Motion:** `<svg role="img" aria-label="...">` localizzato in `it`/`en`/`nl`; tutte le transizioni/animazioni rispettano `@media (prefers-reduced-motion: no-preference)` e `@media (prefers-reduced-motion: reduce)`.
- **Backward Compatibility:** Conservare tutti i selettori `[data-bp-part="headlights|hood|sunroof|sunroof_blind|windows|front_left_door|front_right_door|rear_left_door|rear_right_door|trunk|tailgate_moving"]` e `[data-bp-lock]`, inclusa la presenza simultanea di `.is-open` e `.is-window-open` su `sunroof` quando aperto o in tilt.
- **Domain Crash Antibodies (`.agents/memory/antibodies/lepas.md`):**
  - `AB-LEP-008`: mantenere `type: "lepas-card"` (senza prefisso `custom:`) in `window.customCards` e `?v=1.27.0` coerente con `manifest.json`.
  - `AB-LEP-014`: preservare `btn.disabled = carInUse` sui controlli non-`_applyBtnState` in `_applyBindingsInner` senza alterare altre sezioni.
- **No Global Test Execution by Subagents:** I worker verificano solo la sintassi (`node --check`), mentre i test (`node --test` e `uv run --with pytest pytest`) vengono eseguiti esclusivamente dal Master Agent.

---

### Domain Skills & Sub-Agent Roster

| Dominio Coeso | Worker TypeName | Model | Skill & Companions (`lookup.py`) | File Assegnati (Contratto End-to-End) |
|---|---|---|---|---|
| **D1 — Lovelace Test Contract (RED)** | `lovelace_test_worker` | `'pro'` (`>600L`) | `antislop-code`, `ponytail` | `tests/lepas_card.test.mjs` |
| **D2 — Lovelace Top-Down SVG & CSS/Bindings** | `lovelace_svg_worker` | `'pro'` (`>600L`) | `antislop-ui`, `ponytail`, `antislop-code` | `custom_components/lepas/lovelace/lepas-card.js` |

*(Nota: i 2 worker sono sequenziali — Task 1 RED -> verifica Master -> Task 2 GREEN -> verifica Master — con `Workspace: 'inherit'` e 0 reuse per `'pro'`.)*

---

## Blast Radius & StateGraph (`onSuccess` / `onFailure`)

### `BlastRadius`
- `direct_files`:
  - `custom_components/lepas/lovelace/lepas-card.js` (CSS `.bp-stage`/`.bp-svg`/`.bp-wheel`/`.bp-sunroof`/`.bp-door-*`, `I18N.*.bpAriaLabel`, `renderCarTopViewSvg`, `_applyBindingsInner`)
  - `tests/lepas_card.test.mjs` (nuovi test unitari falsificabili per `viewBox="0 0 200 340"`, `[data-bp-wheel]`, `data-car-color`, `sunroof` open vs tilt)
- `transitively_affected`:
  - `tests/test_lovelace_card.py` (esegue `node --check`, controllo WebView compat e `node --test tests/lepas_card.test.mjs`)
  - `tests/test_lepas_card.py` (verifica statica compatibilità WebView, token Matte Titanium, container queries e a11y)
- `uncertain`:
  - Nessun effetto collaterale backend/Proxmox/SSH/HA Python: la card viene servita staticamente da `/lepas_card/lepas-card.js`. Verificare a fine task che `manifest.json`, `pyproject.toml`, `CHANGELOG.md` e `?v=` restino sincronizzati solo al momento del commit/push finale secondo `AGENTS.md` §5.

### `StateGraph`
- **Task 1 (`tests/lepas_card.test.mjs`)**:
  - `onSuccess`: i nuovi test esistono in `tests/lepas_card.test.mjs` e falliscono in modo esplicito (`RED`) alla successiva esecuzione Master di `node --test tests/lepas_card.test.mjs` perché `viewBox="0 0 200 340"`, `[data-bp-wheel]`, `data-car-color` e `.is-tilted` non sono ancora implementati.
  - `onFailure`: se `node --check tests/lepas_card.test.mjs` fallisce per errore di sintassi, il worker corregge immediatamente prima di restituire il report senza alterare `lepas-card.js`.
- **Task 2 (`custom_components/lepas/lovelace/lepas-card.js`)**:
  - `onSuccess`: `node --check custom_components/lepas/lovelace/lepas-card.js` passa con exit 0; tutti i test esistenti e nuovi (`node --test tests/lepas_card.test.mjs` + `uv run --with pytest pytest -q --tb=short --maxfail=2`) passano (`GREEN`).
  - `onFailure`: nessuna modifica parziale con syntax error o `?.`/`??` lasciata su disco; su fallimento di test nel Master Fix Loop, si isola il selettore/CSS fallito e si corregge in `lepas-card.js` mantenendo intatti i contratti `data-bp-part`.

### Test Falsification Mandate
- Ogni nuovo test aggiunto in `tests/lepas_card.test.mjs` verifica il DOM effettivamente renderizzato da `<lepas-card>` reale in JSDOM (zero mock della funzione di rendering):
  1. Se `renderCarTopViewSvg` non aggiornasse `viewBox="0 0 200 340"`, `role="img"` o `aria-label`, il test fallirebbe sul mismatch attributo.
  2. Se `data-car-color` non seguisse `cfg.color` / fallback `"grey"`, l'asserzione su `.bp-stage[data-car-color]` fallirebbe.
  3. Se `[data-bp-wheel="rear_right"]` non esistesse o non ricevesse `.is-alert` quando `binary_sensor.lepas_tire_warning_rear_right` è `"on"`, l'asserzione fallirebbe.
  4. Se `sunroof` in stato `tilt` (`cover` = `"closed"`, `sensor.lepas_sunroof_movement_state` = `"tilt"`) non applicasse `.is-tilted` (o applicasse `.is-tilted` anche quando `cover` = `"open"`), il test fallirebbe.

---

### Task 1: Aggiungere Test Falsificabili per Vista Auto OEM, Ruote TPMS, Vernice e Sunroof Tilt

**Files:**
- Modify: `tests/lepas_card.test.mjs:1323-1387`

**Interfaces:**
- Consumes: `makeFullHass`, `makeState`, `createCard` già presenti in `tests/lepas_card.test.mjs`.
- Produces: contratti DOM verificati dai test: `.bp-svg[viewBox="0 0 200 340"][role="img"][aria-label]`, `.bp-stage[data-car-color]`, `[data-bp-wheel="<pos>"].is-alert`, `[data-bp-part="sunroof"].is-tilted` vs non-tilted.

- [ ] **Step 1: Aggiungere il blocco di test falsificabili in `tests/lepas_card.test.mjs`**

Subito dopo il test `"Entity mapping: SVG blueprint, TPMS, ..."` (`L1386`), aggiungere:

```javascript
test("OEM top-down SVG: proportions, dynamic car color, TPMS wheels, and sunroof open vs tilt", () => {
  const openHass = makeFullHass({
    "cover.lepas_sunroof": makeState("cover.lepas_sunroof", "open"),
    "sensor.lepas_sunroof_movement_state": makeState("sensor.lepas_sunroof_movement_state", "open"),
    "binary_sensor.lepas_tire_warning_rear_right": makeState("binary_sensor.lepas_tire_warning_rear_right", "on"),
  }, "it");
  const openCard = createCard({ color: "teal" }, openHass);

  const stage = openCard.shadowRoot.querySelector(".bp-stage");
  assert.ok(stage);
  assert.equal(stage.getAttribute("data-car-color"), "teal");

  const svg = openCard.shadowRoot.querySelector(".bp-svg");
  assert.ok(svg);
  assert.equal(svg.getAttribute("viewBox"), "0 0 200 340");
  assert.equal(svg.getAttribute("role"), "img");
  assert.ok((svg.getAttribute("aria-label") || "").length > 5);

  // 4 corner wheels mirror TPMS alert state
  const wheels = openCard.shadowRoot.querySelectorAll("[data-bp-wheel]");
  assert.equal(wheels.length, 4);
  assert.ok(openCard.shadowRoot.querySelector('[data-bp-wheel="rear_right"].is-alert'));
  assert.equal(openCard.shadowRoot.querySelector('[data-bp-wheel="front_left"].is-alert'), null);

  // Sunroof full open has .is-open without .is-tilted
  const openSunroof = openCard.shadowRoot.querySelector('[data-bp-part="sunroof"]');
  assert.ok(openSunroof.classList.contains("is-open"));
  assert.equal(openSunroof.classList.contains("is-tilted"), false);

  // Sunroof tilt (ventilation) activates .is-tilted + .is-open
  const tiltHass = makeFullHass({
    "cover.lepas_sunroof": makeState("cover.lepas_sunroof", "closed"),
    "sensor.lepas_sunroof_movement_state": makeState("sensor.lepas_sunroof_movement_state", "tilt"),
  }, "en");
  const tiltCard = createCard({ color: "invalid-color" }, tiltHass);
  assert.equal(tiltCard.shadowRoot.querySelector(".bp-stage").getAttribute("data-car-color"), "grey");
  const tiltSunroof = tiltCard.shadowRoot.querySelector('[data-bp-part="sunroof"]');
  assert.ok(tiltSunroof.classList.contains("is-open"));
  assert.ok(tiltSunroof.classList.contains("is-window-open"));
  assert.ok(tiltSunroof.classList.contains("is-tilted"));

  // Closed sunroof baseline + live hass re-binding on the same card instances
  const closedHass = makeFullHass({
    "cover.lepas_sunroof": makeState("cover.lepas_sunroof", "closed"),
    "sensor.lepas_sunroof_movement_state": makeState("sensor.lepas_sunroof_movement_state", "closed"),
    "binary_sensor.lepas_tire_warning_rear_right": makeState("binary_sensor.lepas_tire_warning_rear_right", "off"),
  }, "it");
  tiltCard.hass = closedHass;
  const reboundSunroof = tiltCard.shadowRoot.querySelector('[data-bp-part="sunroof"]');
  assert.equal(reboundSunroof.classList.contains("is-open"), false);
  assert.equal(reboundSunroof.classList.contains("is-window-open"), false);
  assert.equal(reboundSunroof.classList.contains("is-tilted"), false);

  openCard.hass = closedHass;
  assert.equal(openCard.shadowRoot.querySelector('[data-bp-wheel="rear_right"].is-alert'), null);

  // All 5 VALID_COLORS propagate to .bp-stage[data-car-color]
  for (const col of ["grey", "teal", "violet", "black", "white"]) {
    const colCard = createCard({ color: col }, closedHass);
    assert.equal(colCard.shadowRoot.querySelector(".bp-stage").getAttribute("data-car-color"), col);
  }
});
```

- [ ] **Step 2: Verificare sintassi e stato RED (eseguito dal Master Agent)**

Worker verifica sintassi: `node --check tests/lepas_card.test.mjs` (exit 0).  
Master verifica RED: `node --test tests/lepas_card.test.mjs` -> atteso FAIL su `"OEM top-down SVG: proportions, dynamic car color, TPMS wheels, and sunroof open vs tilt"` (`stage.getAttribute("data-car-color")` è `null`, `viewBox` è `"0 0 160 250"`).

---

### Task 2: Implementare SVG OEM Lepas L8, CSS Paint Tokens e Binding Multi-Stato in `lepas-card.js`

**Files:**
- Modify: `custom_components/lepas/lovelace/lepas-card.js:222,401,580,866,1235-1258,1298,1317,3186-3213,4133-4176`

**Interfaces:**
- Consumes: `resolveColor(cfg.color)` (`L704-708`), `svgIcon` (`L862`), `escapeHtml`, `I18N` (`it`/`en`/`nl`), `vm.tpmsCorners`, `vm.sunroofCov`, `vm.sunroofMove`, `setBp`.
- Produces: `renderCarTopViewSvg(t)`, regole CSS `.bp-stage[data-car-color="..."]`, `.bp-wheel`, `.bp-sunroof-pane`, `.bp-sunroof-vent`, `.bp-mirror`, `.bp-taillight-bar`, e aggiornamenti binding in `_applyBindingsInner`.

- [ ] **Step 1: Aggiungere `bpAriaLabel` in `I18N` (`it`, `en`, `nl`)**

Subito dopo `blueprintTitle` in `I18N.it` (`L222`), `I18N.en` (`L401`), `I18N.nl` (`L580`):
- `it`: `bpAriaLabel: "Vista dall'alto dello stato chiusure e pneumatici Lepas L8",`
- `en`: `bpAriaLabel: "Top-down view of Lepas L8 closures and tire status",`
- `nl`: `bpAriaLabel: "Bovenaanzicht van sluitingen en bandenstatus Lepas L8",`

- [ ] **Step 2: Aggiornare gli stili CSS `.bp-*` e aggiungere i token `data-car-color` + `@container` responsive**

Sostituire le righe `.bp-stage` / `.bp-svg` / `.bp-body` / `.bp-part*` / `.bp-door-*` (`L1235-1236`, `L1244-1258`) in `lepas-card.js`:

```javascript
      ".bp-stage { display: grid; grid-template-columns: minmax(64px, 1fr) minmax(96px, 148px) minmax(64px, 1fr); gap: 6px; align-items: center; --lp-car-paint-hi: #6B7280; --lp-car-paint: #4B5563; --lp-car-paint-lo: #333A45; --lp-car-stroke: rgba(255, 255, 255, 0.30); }",
      ".bp-stage[data-car-color=\"teal\"] { --lp-car-paint-hi: #267B7B; --lp-car-paint: #195C5C; --lp-car-paint-lo: #103D3D; --lp-car-stroke: rgba(167, 243, 208, 0.30); }",
      ".bp-stage[data-car-color=\"violet\"] { --lp-car-paint-hi: #7A5899; --lp-car-paint: #593E73; --lp-car-paint-lo: #3B284E; --lp-car-stroke: rgba(221, 214, 254, 0.30); }",
      ".bp-stage[data-car-color=\"black\"] { --lp-car-paint-hi: #2D3340; --lp-car-paint: #1B1F27; --lp-car-paint-lo: #111419; --lp-car-stroke: rgba(255, 255, 255, 0.24); }",
      ".bp-stage[data-car-color=\"white\"] { --lp-car-paint-hi: #E5E7EB; --lp-car-paint: #C7CCD4; --lp-car-paint-lo: #9CA3AF; --lp-car-stroke: rgba(255, 255, 255, 0.54); }",
      ".tpms-col { min-width: 0; display: flex; flex-direction: column; justify-content: space-between; gap: 24px; }",
      // ... invariate .tpms-box .. .tpms-temp ...
      ".bp-svg { width: 100%; max-width: 152px; height: auto; display: block; margin: 0 auto; overflow: visible; }",
      ".bp-shadow { fill: rgba(0, 0, 0, 0.42); }",
      ".bp-body { fill: url(#lp-bp-paint-grad); stroke: var(--lp-car-stroke); stroke-width: 1.5; }",
      ".bp-trim { fill: rgba(17, 19, 23, 0.55); stroke: rgba(255, 255, 255, 0.16); stroke-width: 0.9; }",
      ".bp-mirror { fill: var(--lp-car-paint); stroke: var(--lp-car-stroke); stroke-width: 1.1; }",
      ".bp-crease { fill: none; stroke: rgba(255, 255, 255, 0.14); stroke-width: 1; stroke-linecap: round; }",
      ".bp-rail { fill: none; stroke: rgba(17, 19, 23, 0.78); stroke-width: 2.2; stroke-linecap: round; }",
      ".bp-wheel { fill: #16181D; stroke: rgba(255, 255, 255, 0.24); stroke-width: 1.2; }",
      ".bp-wheel.is-alert { fill: rgba(239, 68, 68, 0.38); stroke: var(--lp-coral); stroke-width: 1.6; }",
      ".bp-glass { fill: rgba(12, 14, 18, 0.84); stroke: rgba(255, 255, 255, 0.20); stroke-width: 1; }",
      ".bp-glass-glint { fill: rgba(255, 255, 255, 0.06); stroke: none; }",
      ".bp-part { fill: rgba(255, 255, 255, 0.06); stroke: rgba(255, 255, 255, 0.26); stroke-width: 1.25; }",
      ".bp-handle { stroke: rgba(255, 255, 255, 0.38); stroke-width: 1.2; stroke-linecap: round; }",
      ".bp-taillight-bar { fill: none; stroke: rgba(239, 68, 68, 0.52); stroke-width: 1.8; stroke-linecap: round; }",
      ".bp-part.is-open { fill: rgba(245, 158, 11, 0.34); stroke: var(--lp-amber); }",
      ".bp-part.is-window-open { fill: rgba(96, 165, 250, 0.32); stroke: var(--lp-glacier); }",
      ".bp-part.is-moving { fill: rgba(96, 165, 250, 0.45); stroke: var(--lp-glacier); }",
      ".bp-sunroof-pane { fill: rgba(17, 24, 39, 0.65); stroke: rgba(255, 255, 255, 0.28); stroke-width: 1.1; }",
      ".bp-sunroof.is-open .bp-sunroof-pane { fill: rgba(96, 165, 250, 0.34); stroke: var(--lp-glacier); }",
      ".bp-sunroof.is-open:not(.is-tilted) .bp-sunroof-pane { transform: translateY(22px); }",
      ".bp-sunroof-vent { opacity: 0; fill: rgba(96, 165, 250, 0.72); stroke: var(--lp-glacier); stroke-width: 1; }",
      ".bp-sunroof.is-tilted .bp-sunroof-vent { opacity: 1; }",
      ".bp-sunroof.is-tilted .bp-sunroof-pane { stroke: var(--lp-glacier); fill: rgba(96, 165, 250, 0.22); }",
      ".bp-light-beam { opacity: 0; fill: url(#lp-bp-beam-grad); stroke: none; }",
      ".bp-light-lens { fill: rgba(243, 244, 246, 0.20); stroke: rgba(243, 244, 246, 0.42); stroke-width: 1; }",
      ".bp-headlights.is-on .bp-light-beam { opacity: 1; }",
      ".bp-headlights.is-on .bp-light-lens { fill: rgba(245, 158, 11, 0.78); stroke: var(--lp-amber); }",
      ".bp-lock-ring { fill: rgba(17, 19, 23, 0.92); stroke: var(--lp-emerald); stroke-width: 1.4; }",
      ".bp-lock-shackle { fill: none; stroke: var(--lp-emerald); stroke-width: 1.4; stroke-linecap: round; }",
      ".bp-lock-body { fill: var(--lp-emerald); }",
      ".bp-lock-badge.is-unlocked .bp-lock-ring { stroke: var(--lp-amber); }",
      ".bp-lock-badge.is-unlocked .bp-lock-shackle { stroke: var(--lp-amber); transform: translateY(-1.8px); }",
      ".bp-lock-badge.is-unlocked .bp-lock-body { fill: var(--lp-amber); }",
      ".bp-door-fl { transform-box: view-box; transform-origin: 48px 124px; }",
      ".bp-door-fr { transform-box: view-box; transform-origin: 152px 124px; }",
      ".bp-door-rl { transform-box: view-box; transform-origin: 48px 188px; }",
      ".bp-door-rr { transform-box: view-box; transform-origin: 152px 188px; }",
      ".bp-door-fl.is-open, .bp-door-rl.is-open { transform: rotate(22deg); }",
      ".bp-door-fr.is-open, .bp-door-rr.is-open { transform: rotate(-22deg); }",
```

Subito dopo la fine dei blocchi `@container` esistenti (`L1298`, prima di `@supports not (container-type: inline-size)` a `L1299`), inserire il blocco compatto per larghezze strette:
```javascript
      "@container (max-width: 340px) { .bp-stage { grid-template-columns: minmax(60px, 1fr) minmax(92px, 120px) minmax(60px, 1fr); gap: 5px; } }",
```
E dentro `@media (prefers-reduced-motion: no-preference)` sostituire `L1317` con:
```javascript
      "  .bp-part, .bp-sunroof-pane, .bp-sunroof-vent, .bp-light-beam, .bp-wheel, .bp-lock-shackle { transition: opacity 0.2s ease, transform 0.25s ease-out, stroke 0.2s ease, fill 0.2s ease; }",
```

- [ ] **Step 3: Creare `renderCarTopViewSvg(t)` a livello di modulo (`L866`) e aggiornare `.bp-stage` in `lepas-card.js` (`L3186-3213`)**

Subito dopo `svgIcon` a livello di modulo (`L866`), definire `renderCarTopViewSvg(t)` usando `escapeHtml`:

```javascript
  function renderCarTopViewSvg(t) {
    var ariaLabel = escapeHtml((t && t.bpAriaLabel) ? t.bpAriaLabel : "Vehicle blueprint");
    return (
      '<svg class="bp-svg" viewBox="0 0 200 340" role="img" aria-label="' + ariaLabel + '">' +
        "<defs>" +
          '<linearGradient id="lp-bp-paint-grad" x1="0" y1="0" x2="1" y2="1">' +
            '<stop offset="0%" stop-color="var(--lp-car-paint-hi, #6B7280)"/>' +
            '<stop offset="52%" stop-color="var(--lp-car-paint, #4B5563)"/>' +
            '<stop offset="100%" stop-color="var(--lp-car-paint-lo, #333A45)"/>' +
          "</linearGradient>" +
          '<linearGradient id="lp-bp-beam-grad" x1="0" y1="1" x2="0" y2="0">' +
            '<stop offset="0%" stop-color="#F59E0B" stop-opacity="0.55"/>' +
            '<stop offset="100%" stop-color="#F59E0B" stop-opacity="0"/>' +
          "</linearGradient>" +
        "</defs>" +
        '<ellipse class="bp-shadow" cx="100" cy="172" rx="62" ry="152"/>' +
        '<g class="bp-headlights" data-bp-part="headlights">' +
          '<path class="bp-light-beam" d="M 54 32 L 34 2 L 78 2 L 70 28 Z M 146 32 L 166 2 L 122 2 L 130 28 Z"/>' +
          '<path class="bp-light-lens" d="M 52 38 Q 60 28 76 28 L 72 34 Q 61 35 55 43 Z M 148 38 Q 140 28 124 28 L 128 34 Q 139 35 145 43 Z"/>' +
        "</g>" +
        '<rect class="bp-wheel" data-bp-wheel="front_left" x="41" y="60" width="12" height="38" rx="4"/>' +
        '<rect class="bp-wheel" data-bp-wheel="front_right" x="147" y="60" width="12" height="38" rx="4"/>' +
        '<rect class="bp-wheel" data-bp-wheel="rear_left" x="41" y="232" width="12" height="38" rx="4"/>' +
        '<rect class="bp-wheel" data-bp-wheel="rear_right" x="147" y="232" width="12" height="38" rx="4"/>' +
        '<path class="bp-body" d="M 100 22 C 126 22 144 29 149 42 C 152 50 153 60 153 74 C 156 80 156 92 153 98 L 152 228 C 156 235 156 250 152 258 C 151 278 148 296 142 306 C 135 316 119 320 100 320 C 81 320 65 316 58 306 C 52 296 49 278 48 258 C 44 250 44 235 48 228 L 47 98 C 44 92 44 80 47 74 C 47 60 48 50 51 42 C 56 29 74 22 100 22 Z"/>' +
        '<path class="bp-trim" d="M 74 26 Q 100 23 126 26 L 122 30 Q 100 28 78 30 Z"/>' +
        '<g class="bp-part" data-bp-part="hood">' +
          '<path d="M 56 42 Q 100 32 144 42 L 138 96 Q 100 90 62 96 Z"/>' +
          '<path class="bp-crease" d="M 72 46 Q 74 68 70 90 M 128 46 Q 126 68 130 90"/>' +
        "</g>" +
        '<path class="bp-mirror" d="M 48 106 L 33 109 Q 29 111 31 117 Q 33 121 48 117 Z M 152 106 L 167 109 Q 171 111 169 117 Q 167 121 152 117 Z"/>' +
        '<path class="bp-glass" d="M 62 99 Q 100 92 138 99 L 133 134 Q 100 128 67 134 Z"/>' +
        '<path class="bp-glass-glint" d="M 72 103 L 88 100 L 80 128 L 68 130 Z"/>' +
        '<path class="bp-rail" d="M 60 132 L 62 252 M 140 132 L 138 252"/>' +
        '<rect class="bp-glass" x="65" y="136" width="70" height="114" rx="10"/>' +
        '<g class="bp-part bp-sunroof" data-bp-part="sunroof">' +
          '<rect class="bp-sunroof-pane" x="68" y="140" width="64" height="58" rx="7"/>' +
          '<path class="bp-sunroof-vent" d="M 72 197 L 128 197 L 124 204 L 76 204 Z"/>' +
        "</g>" +
        '<rect class="bp-part" data-bp-part="sunroof_blind" x="70" y="236" width="60" height="4" rx="2"/>' +
        '<path class="bp-part" data-bp-part="windows" d="M 52 122 L 58 124 L 58 242 L 52 246 Z M 148 122 L 142 124 L 142 242 L 148 246 Z"/>' +
        '<g class="bp-part bp-door-fl" data-bp-part="front_left_door"><path d="M 47 124 L 53 124 L 53 184 L 47 184 Z"/><line class="bp-handle" x1="49" y1="166" x2="49" y2="176"/></g>' +
        '<g class="bp-part bp-door-fr" data-bp-part="front_right_door"><path d="M 147 124 L 153 124 L 153 184 L 147 184 Z"/><line class="bp-handle" x1="151" y1="166" x2="151" y2="176"/></g>' +
        '<g class="bp-part bp-door-rl" data-bp-part="rear_left_door"><path d="M 47 188 L 53 188 L 53 246 L 48 246 Z"/><line class="bp-handle" x1="49" y1="226" x2="49" y2="236"/></g>' +
        '<g class="bp-part bp-door-rr" data-bp-part="rear_right_door"><path d="M 147 188 L 153 188 L 152 246 L 147 246 Z"/><line class="bp-handle" x1="151" y1="226" x2="151" y2="236"/></g>' +
        '<path class="bp-glass" d="M 66 254 Q 100 260 134 254 L 139 286 Q 100 293 61 286 Z"/>' +
        '<g class="bp-part" data-bp-part="trunk">' +
          '<path d="M 61 290 Q 100 296 139 290 L 143 310 Q 100 320 57 310 Z"/>' +
          '<path class="bp-taillight-bar" d="M 62 306 Q 100 313 138 306"/>' +
        "</g>" +
        '<rect class="bp-part" data-bp-part="tailgate_moving" x="76" y="317" width="48" height="5" rx="2.5"/>' +
        '<g class="bp-lock-badge" data-bp-lock transform="translate(100, 170)">' +
          '<circle class="bp-lock-ring" cx="0" cy="0" r="11"/>' +
          '<path class="bp-lock-shackle" d="M -3.5 -1 V -3.5 A 3.5 3.5 0 0 1 3.5 -3.5 V -1"/>' +
          '<rect class="bp-lock-body" x="-5" y="-1" width="10" height="7" rx="1.8"/>' +
        "</g>" +
      "</svg>"
    );
  }
```

E nel rendering di `blueprintHtml` (`L3186-3213`):
```javascript
      var blueprintSvg = renderCarTopViewSvg(t);
      var carColor = resolveColor(self._config && self._config.color);
      var blueprintHtml =
        '<div class="surface">' +
          '<div class="sec-hdr"><span class="sec-hdr-title">' + svgIcon("tire", "sec-ico") + "<span>" + self._h(t.blueprintTitle) + "</span></span></div>" +
          '<div class="bp-stage" data-car-color="' + self._h(carColor) + '">' +
            '<div class="tpms-col">' + tpmsCard(ctx.tpmsCorners[0]) + tpmsCard(ctx.tpmsCorners[2]) + "</div>" +
            blueprintSvg +
            '<div class="tpms-col">' + tpmsCard(ctx.tpmsCorners[1]) + tpmsCard(ctx.tpmsCorners[3]) + "</div>" +
          "</div>" +
        "</div>";
```

- [ ] **Step 4: Aggiornare `_applyBindingsInner` (`L4133-4176`)**

1. Aggiornare `data-car-color` su `.bp-stage` ad ogni binding pass:
   ```javascript
   var bpStage = root.querySelector(".bp-stage");
   if (bpStage) bpStage.setAttribute("data-car-color", resolveColor(this._config && this._config.color));
   ```
2. Aggiornare la logica `sunroof` per distinguere scorrimento vs tilt:
   ```javascript
   var sunMoveState = (vm.sunroofMove && vm.sunroofMove.s && vm.sunroofMove.s.state) ? String(vm.sunroofMove.s.state) : "";
   var sunCovOpen = Boolean(vm.sunroofCov && vm.sunroofCov.s && vm.sunroofCov.s.state === "open");
   var sunTilted = !sunCovOpen && /tilt/i.test(sunMoveState);
   var sunOpen = sunCovOpen || /open|mov|tilt/i.test(sunMoveState);
   setBp("sunroof", "is-open", sunOpen);
   setBp("sunroof", "is-window-open", sunOpen);
   setBp("sunroof", "is-tilted", sunTilted);
   ```
3. Nel loop `tpmsCorners`, sincronizzare `[data-bp-wheel="<pos>"]`:
   ```javascript
   var wheelEl = root.querySelector('[data-bp-wheel="' + tp.pos + '"]');
   if (wheelEl) wheelEl.classList.toggle("is-alert", isAlert);
   ```

- [ ] **Step 5: Verificare GREEN e qualità statica (eseguito dal Master Agent)**

1. `node --check custom_components/lepas/lovelace/lepas-card.js`
2. `node --test tests/lepas_card.test.mjs`
3. `/home/federico/.local/bin/uv run --with pytest pytest -q --tb=short --maxfail=2`
4. `/home/federico/.local/bin/uv run ruff check custom_components/ tests/ && /home/federico/.local/bin/uv run ruff format --check custom_components/ tests/`
5. `python3 /home/federico/skills_library/scripts/local_llm_offload.py --task review-hygiene --files custom_components/lepas/lovelace/lepas-card.js tests/lepas_card.test.mjs --json`
6. Pass 2 Sentinel (`Model: 'inherit'`, stesso CID dello Stage 2 via `send_message`) + `APPROVED_TREE=$(git write-tree)`.
