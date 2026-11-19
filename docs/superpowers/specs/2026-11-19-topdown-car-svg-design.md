# Specifica di Design — Vista Auto dall'Alto OEM (`lepas-card.js`)

**Data:** 2026-11-19  
**Stato:** Bozza in revisione utente  
**Scope:** Sostituzione della vista schematica dell'auto dall'alto (`blueprintSvg`) nella tab *Sicurezza* (`Stato chiusure e TPMS`) di `custom_components/lepas/lovelace/lepas-card.js`.

---

## 1. Obiettivo e Vincoli

Riprogettare la vista dall'alto dell'auto dentro `.bp-stage` affinché rappresenti fedelmente le proporzioni di un SUV **Lepas L8** con qualità visiva OEM coerente con il tema *Matte Titanium* della card, mantenendo:

- **Zero nuovi asset binari o file JS esterni:** tutto il rendering resta inline in `custom_components/lepas/lovelace/lepas-card.js` (compatibilità WebView senza `?.` / `??`, nessun carico di rete aggiuntivo, nitidezza a qualsiasi DPI).
- **Compatibilità retroattiva dei contratti DOM:** tutti gli attributi `data-bp-part` e `data-bp-lock` esistenti devono restare presenti e funzionali.
- **Accessibilità:** `<svg role="img" aria-label="...">` con descrizione localizzata (`it`, `en`, `nl`), contrasto >= 3:1 per gli indicatori di stato e rispetto di `@media (prefers-reduced-motion: reduce)`.

---

## 2. Layout e Proporzioni Stage (`.bp-stage`)

Nel pannello *Stato chiusure e TPMS*, la colonna centrale attuale (`108px–124px`, `max-width: 130px`) comprime eccessivamente la sagoma tra i 4 riquadri TPMS.

- **Griglia `.bp-stage`:**
  - `grid-template-columns: minmax(64px, 1fr) minmax(96px, 148px) minmax(64px, 1fr);`
  - `gap: 6px; align-items: center;` (minimo ~236px compatibile con la colonna 1 del layout cockpit a 3 colonne `min-width: 960px`, fino a `148px` centrali su mobile/tab singola)
- **Dimensione `.bp-svg`:**
  - `width: 100%; max-width: 152px; height: auto; display: block; margin: 0 auto;`
  - `viewBox="0 0 200 340"` (rapporto ~1:1.70 coerente con un SUV di medie/grandi dimensioni).
- **Resa su container stretti:** tramite container query esistenti (`@container (max-width: 340px)`), la colonna centrale si adatta senza sovrapporsi ai box TPMS (`min-width: 0` su `.tpms-col`).

---

## 3. Architettura SVG Multi-Livello (`renderCarTopViewSvg(t)`)

Il markup viene generato da una funzione helper dedicata `renderCarTopViewSvg(t)` a livello di modulo in `lepas-card.js` e organizzato nei seguenti layer ordinati dal fondo al primo piano:

1. **Ombra sotto-scocca e fasci fari anteriori:**
   - Ellisse morbida sotto la scocca per staccare il veicolo dal piano della card.
   - `[data-bp-part="headlights"]`: gruppi ottici anteriori sottili a L/DRL sui due angoli frontali + coni luminosi anteriori visibili quando `.is-on` (`flash_lights` attivo).
2. **Pneumatici nei passaruota (novità TPMS):**
   - 4 ruote sagomate sporgenti leggermente ai 4 angoli (`[data-bp-wheel="front_left"]`, `front_right`, `rear_left`, `rear_right`).
   - Stato normale neutro scuro; quando il rispettivo angolo TPMS è in `.is-alert`, la ruota assume classe `.is-alert` con bordo e riempimento rosso corallo (`#EF4444`).
3. **Scocca principale SUV (`.bp-body`):**
   - Profilo completo con calandra frontale sagomata, passaruota svasati anteriore/posteriore, fiancate affusolate verso il montante posteriore e spoiler sul portellone.
   - Riempimento con gradiente lineare `<defs>` pilotato dai CSS token della vernice (`--lp-car-paint-hi`, `--lp-car-paint`, `--lp-car-paint-lo`) per dare tridimensionalità alle superfici.
4. **Cofano anteriore (`[data-bp-part="hood"]`):**
   - Sagoma cofano scolpita con due nervature longitudinali simmetriche (`power domes`); evidenziazione `.is-open` in ambra (`#F59E0B`).
5. **Vetri fissi e specchietti:**
   - Parabrezza anteriore ampio con curvatura panoramica e lunotto posteriore (`.bp-glass`) in nero fumé semi-trasparente con leggero riflesso diagonale.
   - Specchietti retrovisori sinistro e destro sagomati sul montante anteriore (`.bp-mirror`), verniciati in tinta carrozzeria.
6. **Portiere laterali sagomate:**
   - `[data-bp-part="front_left_door"]`, `[data-bp-part="front_right_door"]`, `[data-bp-part="rear_left_door"]`, `[data-bp-part="rear_right_door"]` (classi `.bp-door-fl`, `.bp-door-fr`, `.bp-door-rl`, `.bp-door-rr`).
   - Ogni portiera include pannello porta, linea di cintura e maniglia a filo; `transform-origin` ancorato al montante anteriore di ciascuna portiera in coordinate `0..200 x 0..340` (`transform-box: view-box`) per una rotazione realistica verso l'esterno (`rotate(22deg)` lato sinistro, `rotate(-22deg)` lato destro, senza traslazioni artificiali staccate dalla scocca) quando `.is-open`.
7. **Finestrini laterali (`[data-bp-part="windows"]`):**
   - Tracciato integrato dei cristalli laterali lungo le portiere SX e DX; `.is-open` / `.is-window-open` in blu ghiaccio (`#60A5FA`).
8. **Tetto panoramico, mancorrenti e multi-stato (`sunroof` + `sunroof_blind`):**
   - Barre longitudinali nere sul tetto ai lati della superficie vetrata.
   - `[data-bp-part="sunroof"]`: pannello tetto panoramico apribile con tre stati visivi distinti:
     - **Chiuso:** vetro fumé uniforme integrato nel tetto.
     - **Aperto a scorrimento (`.is-open`):** pannello evidenziato con cornice blu ghiaccio e apertura nella parte anteriore.
     - **Ventilazione / Tilt (`.is-tilted`):** bordo posteriore sollevato/evidenziato a fessura luminosa (mantenendo compatibilità con la rilevazione `/tilt/i` di `sunroofMove`).
   - `[data-bp-part="sunroof_blind"]`: barra/cursore della tendina parasole interna al tetto (`.is-open`).
9. **Portellone posteriore e barra LED:**
   - `[data-bp-part="trunk"]`: portellone posteriore con firma luminosa a barra LED continua a tutta larghezza; `.is-open` in ambra.
   - `[data-bp-part="tailgate_moving"]`: indicatore di movimento portellone elettrico (`.is-moving` blu ghiaccio con pulsazione dolce disattivata su `prefers-reduced-motion: reduce`).
10. **Badge Lucchetto (`[data-bp-lock]`):**
    - Gruppo grafico compatto centrato sul tetto (`translate(100, 170)`) con icona lucchetto vettoriale nitida all'interno di un medaglione circolare scuro: bordo verde smeraldo (`#34D399`) se bloccata, ambra (`#F59E0B`) se sbloccata (`.is-unlocked`).

---

## 4. Sistema Vernice Dinamico (`data-car-color`)

La funzione `resolveColor(cfg.color)` restituisce uno dei 5 valori in `VALID_COLORS` (`grey`, `teal`, `violet`, `black`, `white`).  
Il container `.bp-stage` riceve l'attributo `data-car-color="<color>"` (aggiornato anche durante `_applyBindingsInner` al cambio configurazione), e il CSS imposta le variabili di verniciatura senza stili inline:

| Colore | `--lp-car-paint-hi` | `--lp-car-paint` | `--lp-car-paint-lo` | `--lp-car-stroke` |
|---|---|---|---|---|
| `grey` (default) | `#6B7280` | `#4B5563` | `#333A45` | `rgba(255, 255, 255, 0.30)` |
| `teal` | `#267B7B` | `#195C5C` | `#103D3D` | `rgba(167, 243, 208, 0.30)` |
| `violet` | `#7A5899` | `#593E73` | `#3B284E` | `rgba(221, 214, 254, 0.30)` |
| `black` | `#2D3340` | `#1B1F27` | `#111419` | `rgba(255, 255, 255, 0.24)` |
| `white` | `#E5E7EB` | `#C7CCD4` | `#9CA3AF` | `rgba(255, 255, 255, 0.54)` |

Le sfumature sono calibrate sul fondo scuro della card (`#181B20`) affinché anche la variante `black` resti leggibile nei contorni e la variante `white` non crei abbagliamento eccessivo rispetto agli indicatori ambra/blu/rosso.

---

## 5. Logica di Binding (`_applyBindingsInner`)

In `_applyBindingsInner`:

- **Colore auto:** aggiorna `bpStage.setAttribute("data-car-color", resolveColor(this._config && this._config.color))`.
- **Tetto apribile (`sunroof`):**
  - `sunSlideOpen`: `vm.sunroofCov && vm.sunroofCov.s && vm.sunroofCov.s.state === "open"`, oppure `vm.sunroofMove` con stato corrispondente ad apertura scorrevole (`/open|mov/i` escluso `tilt`).
  - `sunTilted`: `!sunSlideOpen && vm.sunroofMove && vm.sunroofMove.s && /tilt/i.test(vm.sunroofMove.s.state)`.
  - Applica `is-open` e `is-window-open` su `[data-bp-part="sunroof"]` quando `sunSlideOpen || sunTilted` (preservando la retrocompatibilità con i test esistenti su `sunroof.is-open`) e aggiunge `.is-tilted` quando `sunTilted` è vero.
- **Ruote TPMS (`[data-bp-wheel="<pos>"]`):**
  - Nel ciclo già esistente sui 4 angoli (`front_left`, `front_right`, `rear_left`, `rear_right`), sincronizza `.is-alert` sull'elemento `[data-bp-wheel="<pos>"]` dell'SVG in base a `alert`.
- **Restanti parti (`headlights`, `hood`, `trunk`, `tailgate_moving`, `sunroof_blind`, `windows`, portiere, `[data-bp-lock]`):** comportamento invariato sui rispettivi selettori `data-bp-part` / `data-bp-lock`.

---

## 6. Strategia di Verifica

- **`tests/lepas_card.test.mjs`:**
  - Verifica presenza del nuovo `viewBox="0 0 200 340"`, `role="img"` e `aria-label`.
  - Verifica presenza dei 4 elementi `[data-bp-wheel]` e propagazione di `.is-alert` al superamento soglia TPMS.
  - Verifica propagazione di `data-car-color` per tutti i valori `VALID_COLORS` (`grey`, `teal`, `violet`, `black`, `white`).
  - Verifica distinzione tra `sunroof` aperto (`cover` = `open` -> `.is-open` senza `.is-tilted`) e ventilazione/tilt (`sunroof_movement_state` = `tilt` con `cover` = `closed` -> `.is-tilted` + `.is-open`).
  - Mantenimento di tutti i test esistenti su portiere, cofano, baule, finestrini, tendina, fari e lucchetto.
- **`tests/test_lovelace_card.py` e `tests/test_lepas_card.py`:**
  - Verifica compatibilità sintattica WebView (`node --check`, assenza `?.`/`??`), assenza `:host-context`, presenza token *Matte Titanium* ed esecuzione completa via `uv run --with pytest pytest -q --tb=short --maxfail=2`.
