# Design Spec — Redesign Logo & Icona Brand `Lepas` (Leopardo + Corsivo Giallo-Oro, `v1.27.0`)

**Data:** 2026-11-19  
**Target Release:** `v1.27.0`  
**Classificazione:** `Architectural` (rigenerazione degli 8 asset PNG RGBA in `custom_components/lepas/brand/` con pipeline `image-gen` + compositing vettoriale nitido, aggiornamento versioni e verifica `tests/test_brand_assets.py`).

---

## 1. Obiettivo & Direzione Approvata dall'Utente

Sostituire gli attuali asset con scudo generico e bagliore neon-ciano (`#00D2FF`) in `custom_components/lepas/brand/` con un'identità visiva ispirata al marchio ufficiale **LEPAS** (`com.chery.eu.lepas` / `lepasinternational.com`) adattata alla palette **Matte Titanium OEM**:
1. **Elemento Leopard ("Leopard Aesthetics"):** silhouette o profilo stilizzato di **leopardo** dinamico in balzo / scatto in stile automotive moderno (linee tese in titanio satinato `#181B20` / `#21252C` / `#F3F4F6`), che richiama direttamente il concept *Leap + Passion*.
2. **Scritta `Lepas` in corsivo giallo-oro:** ispirata al tratto calligrafico aerodinamico e inclinato del wordmark ufficiale `logo.svg` (`Lepas` con la `L` avvolgente), colorata in **giallo-oro caldo (`#FACC15` → `#F59E0B`)** come l'icona ufficiale dell'app mobile `com.chery.eu.lepas`, armonizzata con la palette scura/titanio dell'integrazione.

---

## 2. Specifiche Asset & Varianti Light/Dark (`tests/test_brand_assets.py`)

Tutti gli 8 file in `custom_components/lepas/brand/` DEVONO essere **PNG RGBA** con **sfondo trasparente** (niente rettangoli opachi attorno) e dimensioni esatte:

| File | Dimensioni | Tema HA | Composizione |
| --- | --- | --- | --- |
| `icon.png` / `icon@2x.png` | `256×256` / `512×512` | Light Mode | **Opzione 1 (Dark Titanium su trasparente)**: leopardo geometrico a fauci aperte con occhio ambra-oro che emerge dall'angolo sinistro sfumando in alfa + wordmark **`Lepas`** giallo-oro con leggero contorno `#181B20` per leggibilità su sfondo chiaro |
| `dark_icon.png` / `dark_icon@2x.png` | `256×256` / `512×512` | Dark Mode | **Opzione 1 Dark**: stessa composizione ottimizzata per sfondi scuri con leopardo in titanio scuro/argento sfumato da sinistra e wordmark **`Lepas`** giallo-oro (`#FACC15`–`#F59E0B`) |
| `logo.png` / `logo@2x.png` | `362×256` / `724×512` | Light Mode | **Opzione 1 (Dark Titanium su trasparente)**: composizione 362×256 / 724×512 con leopardo geometrico a fauci aperte incastonato da sinistra con dissolvenza alfa + wordmark corsivo **`Lepas`** giallo-oro con leggero contorno `#181B20` |
| `dark_logo.png` / `dark_logo@2x.png` | `362×256` / `724×512` | Dark Mode | **Opzione 1 Dark**: composizione speculare per Dark Mode con leopardo titanio da sinistra sfumato nello sfondo e wordmark corsivo **`Lepas`** giallo-oro (`#FACC15`–`#F59E0B`) |

---

## 3. Strategia di Generazione & Qualità Testo

- **Generazione grafica (`local_llm_offload.py --task image-gen`):**
  - Generare ad alta risoluzione su `pc-federico` (`--image-model quality --remove-bg`, fallback `image-generator` Cloud solo se `CLOUD_FALLBACK_REQUIRED`) la base dell'emblema leopardo in stile minimalista metallico/Matte Titanium (senza testo distorto da diffusione).
- **Wordmark corsivo nitido & export RGBA (`Pillow` / `cairosvg`):**
  - Per evitare testo corsivo corrotto dai modelli generativi, tracciare/renderizzare il wordmark corsivo **`Lepas`** (ispirato alle curve aerodinamiche di `logo.svg` in giallo-oro `#FACC15` → `#F59E0B`) e comporre con **Pillow** (`Image.Resampling.LANCZOS`) gli 8 file RGBA alle risoluzioni esatte (`256×256`, `512×512`, `362×256`, `724×512`), preservando `official_lepas_logo.png` come riferimento visivo in scratch e mai committando asset non ottimizzati.
- **Anteprima visiva HITL:** prima del commit finale `v1.27.0`, mostrare all'utente l'anteprima delle varianti generate per eventuale rifinitura estetica.

---

## 4. Verifica & Rilascio (`v1.27.0`)

- `tests/test_brand_assets.py` (tutte le 17 asserzioni su dimensioni, formato PNG, canale RGBA, SHA-256 non legacy) + suite completa `.venv/bin/pytest -q --tb=short --maxfail=2` e `node --test tests/lepas_card.test.mjs`.
- Sincronizzazione SemVer `1.26.0` → `1.27.0` (`manifest.json`, `pyproject.toml`, `lepas-card.js`, `tests/test_lovelace_card.py`, `tests/lepas_card.test.mjs`, `CHANGELOG.md`) al momento del commit/tag/push finale.
