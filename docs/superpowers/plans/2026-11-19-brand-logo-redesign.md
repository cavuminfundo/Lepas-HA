# Brand Logo & Icon Redesign (`v1.27.0`) Implementation Plan

## Dual-Gate Audit Matrix

| Gate | Model | Conversation ID | Verdetto | Note |
| --- | --- | --- | --- | --- |
| **Stage 1 (Domain & Archaeology Pre-Audit)** | `flash` | `3f5ac466-af62-43d7-b8d6-791ed863f820` | `PASS` | Cohesive Domain `brand_assets_and_release`, `AB-LEP-008`, `p[3] > 32` su `neon_cyan_pixels`, SHA-256 precedenti e gate HITL visivo integrati |
| **Stage 2 (Six-Pillars Sentinel Control Gate)** | `inherit` | `88696379-6211-491a-b774-f013836534bc` | `APPROVED` | Tutti i 6 pilastri `PASS` (Intent, Falsification, Cohesive Contract, BlastRadius/StateGraph, Security/VM110, Crash Antibodies) |

> **For agentic workers:** REQUIRED SUB-SKILL: Use `subagent-driven-development` to execute the approved tasks after user selection of the visual concept (A / B / C).

**Goal:** Sostituire gli 8 asset PNG RGBA in `custom_components/lepas/brand/` (attualmente scudo generico con bagliore ciano `#00D2FF`) con il nuovo brand emblem **leopardo stilizzato Matte Titanium + wordmark corsivo aerodinamico `Lepas` giallo-oro (`#FACC15` → `#F59E0B`)**, verificato con test falsificabili e rilasciato come `v1.27.0`.

**Architecture:** Generazione dell'emblema leopardo ad alta risoluzione tramite `local_llm_offload.py --task image-gen --image-model quality --remove-bg` su `pc-federico` (scelta utente tra i 3 concept A/B/C in scratch, con fallback `image-generator` solo su `CLOUD_FALLBACK_REQUIRED`), tracciatura/vettorializzazione nitida del wordmark corsivo `Lepas` (derivato da `official_lepas_logo.png` di `lepasinternational.com`) tramite Inkscape/Pillow con gradiente giallo-oro `#FACC15` → `#F59E0B`, e compositing RGBA (`Image.Resampling.LANCZOS`) nelle 8 risoluzioni Home Assistant Light/Dark senza background opachi. Allineamento finale SemVer `1.27.0` su manifest, pyproject, card JS, test e changelog.

**Tech Stack:** ComfyUI (`local_llm_offload.py --task image-gen`), Inkscape (`/usr/bin/inkscape`), Python 3.13 + Pillow `12.0.0`, pytest, Node 20 (`node --test`), Ruff.

**Spec:** `docs/superpowers/specs/2026-11-19-brand-logo-redesign-design.md`

---

## Global Constraints
- Tutti gli 8 file in `custom_components/lepas/brand/` (`icon.png`, `icon@2x.png`, `dark_icon.png`, `dark_icon@2x.png`, `logo.png`, `logo@2x.png`, `dark_logo.png`, `dark_logo@2x.png`) DEVONO essere PNG RGBA trasparenti con dimensioni esatte (`256×256`, `512×512`, `362×256`, `724×512`).
- Zero `#00D2FF` (neon ciano) e zero rettangoli opachi di sfondo.
- Wordmark corsivo `Lepas` nitido in giallo-oro (`#FACC15` → `#F59E0B`), mai testo distorto generato direttamente dal modello di diffusione.
- Sincronizzazione SemVer `1.27.0` obbligatoria in `custom_components/lepas/manifest.json`, `pyproject.toml`, `custom_components/lepas/lovelace/lepas-card.js` (`?v=1.27.0` + `CARD_VERSION`), `tests/test_lovelace_card.py`, `tests/lepas_card.test.mjs`, `CHANGELOG.md` e tag `v1.27.0` (`AB-LEP-008`).
- Nessun segreto/PII in chiaro; nessuna modifica a VM 110; rispetto `tests/test_repo_hygiene.py`.

---

## Domain Skills & Sub-Agent Roster

- **Dominio Coeso Unico (`brand_assets_and_release`):**
  - **Skill Primaria:** `antislop-ui` (`/home/federico/skills_library/antislop-ui/SKILL.md`)
  - **Companions:** `ponytail` (`/home/federico/skills_library/ponytail/SKILL.md`), `antislop-code` (`/home/federico/skills_library/antislop-code/SKILL.md`)
  - **Worker:** `lepas_brand_worker` (`Model: 'pro'` perché aggiorna `>=3` file interdipendenti inclusi `lepas-card.js` >600L e `tests/lepas_card.test.mjs` >600L; `Workspace: 'inherit'`).
  - **Nota esecuzione:** Gli script di composizione e le 8 PNG finali vengono prodotti solo dopo la scelta esplicita dell'utente tra i 3 concept visivi (A / B / C) generati in scratch.

---

## BlastRadius & StateGraph

### `BlastRadius` (da `codegraph_explore` + `--task archaeology`)
- `direct_files`:
  - `custom_components/lepas/brand/icon.png`
  - `custom_components/lepas/brand/icon@2x.png`
  - `custom_components/lepas/brand/dark_icon.png`
  - `custom_components/lepas/brand/dark_icon@2x.png`
  - `custom_components/lepas/brand/logo.png`
  - `custom_components/lepas/brand/logo@2x.png`
  - `custom_components/lepas/brand/dark_logo.png`
  - `custom_components/lepas/brand/dark_logo@2x.png`
  - `tests/test_brand_assets.py` (aggiunta check falsificabili su trasparenza alfa e assenza cyan `#00D2FF` / presenza pixel oro + SHA-256 scudo precedente)
  - `custom_components/lepas/manifest.json` (`L23`: `"1.26.0"` -> `"1.27.0"`)
  - `pyproject.toml` (`L3`: `"1.26.0"` -> `"1.27.0"`)
  - `custom_components/lepas/lovelace/lepas-card.js` (`L2, L14, L85-L91, L1480`: `1.26.0` -> `1.27.0`)
  - `tests/test_lovelace_card.py` (`L126, L129`: `1.26.0` -> `1.27.0`)
  - `tests/lepas_card.test.mjs` (`L921, L924, L930, L949`: `1.26.0` -> `1.27.0`)
  - `CHANGELOG.md` (`L19+`: nuova sezione `## v1.27.0 — 2026-11-19`)
- `transitively_affected`:
  - `tests/test_repo_hygiene.py` (`test_il_package_pubblicabile_e_completo`, `test_versione_sincronizzata_e_changelog_lepas`)
  - `.github/workflows/release.yml` (estrazione note release dal tag `v1.27.0`)
  - Integrazione live su Home Assistant (`192.168.88.231`)
- `uncertain`:
  - Caching browser/app companion Home Assistant sui PNG `brands` dopo `ha_restart`.

### `StateGraph` (`onSuccess:` / `onFailure:`)
- **Asset Generation & Atomic Swap (`custom_components/lepas/brand/*.png`):**
  - `onSuccess:` tutte e 8 le immagini vengono composte prima in una directory temporanea/scratch, validate per formato PNG, modalità RGBA, dimensioni esatte e canale alpha trasparente, e solo dopo copiate nei path finali.
  - `onFailure:` nessun file esistente in `custom_components/lepas/brand/` viene sovrascritto parzialmente; cleanup dei file temporanei in `try...finally`.
- **Home Assistant Live Deploy (`192.168.88.231`):**
  - `onSuccess:` copia atomica dei file aggiornati -> `ha_check_config` -> `ha_restart` -> verifica stato entità live.
  - `onFailure:` se `ha_check_config` fallisce, rollback immediato (`ha_git_rollback` o ripristino backup) senza riavviare HA.

---

## Tasks

### Task 1: Scelta Concept & Generazione delle 8 PNG RGBA (`custom_components/lepas/brand/`)

**Files:**
- Modify: `custom_components/lepas/brand/{icon,icon@2x,dark_icon,dark_icon@2x,logo,logo@2x,dark_logo,dark_logo@2x}.png`
- Reference (read-only): `/home/federico/.gemini/antigravity/brain/42f947d6-b4f6-4bc4-9459-ac070fcdbd04/scratch/official_lepas_logo.png` and user-chosen concept PNG in `/home/federico/.gemini/antigravity/brain/3f51151d-0c14-4367-95c6-6982a818f538/scratch/`

**Interfaces:**
- Produces: 8 valid RGBA PNG files in `custom_components/lepas/brand/` matching `BRAND_SPECS` (`256×256`, `512×512`, `362×256`, `724×512`) with transparent margins (`alpha == 0` at corners), zero neon-cyan glow, and crisp gold-yellow (`#FACC15`–`#F59E0B`) italic `Lepas` wordmark + Matte Titanium leopard emblem.

- [ ] **Step 1: Verify visual concept choice from user**
  Ensure user explicitly selected Concept A, B, or C (or refinement).
- [ ] **Step 2: Compose high-resolution Light & Dark master canvases with Pillow/Inkscape**
  Write a scratch generator script in `/home/federico/.gemini/antigravity/brain/3f51151d-0c14-4367-95c6-6982a818f538/scratch/build_brand_assets.py` (never committed to repo) using `try...finally` temp cleanup that:
  1. Loads the chosen transparent leopard emblem (`RGBA`) and creates Light variant (deep titanium `#181B20`–`#21252C` silhouette/accents) and Dark variant (light brushed titanium `#E5E7EB`–`#9CA3AF` with `#181B20` inner plate/outline for dark surfaces).
  2. Vectorizes/renders the official `Lepas` italic wordmark with `#FACC15` → `#F59E0B` warm gold gradient and subtle `#181B20` contrast shadow/outline on Light `logo.png` so it remains crisp on both white and dark HA backgrounds.
  3. Exports all 8 exact dimensions (`256×256`, `512×512`, `362×256`, `724×512`) with `Image.Resampling.LANCZOS`.
- [ ] **Step 3: Inspect generated assets visually & HITL preview gate**
  Run the scratch script, write to `custom_components/lepas/brand/`, and visually inspect `icon.png`, `dark_icon.png`, `logo.png`, `dark_logo.png` via `read_file` to confirm transparency, contrast, and zero text artifacts. Presentare all'utente l'anteprima delle 8 varianti finali composte per conferma visiva HITL (Spec §3) prima di finalizzare commit, tag e push `v1.27.0`.

---

### Task 2: Test Falsificabili per Redesign Brand (`tests/test_brand_assets.py`)

**Files:**
- Modify: `tests/test_brand_assets.py:22-86`

**Interfaces:**
- Consumes: `BRAND_SPECS` and `custom_components/lepas/brand/*.png`
- Produces: Falsifiable assertions verifying transparent background (`alpha` min == 0 at corners), non-empty opaque emblem content, presence of warm gold-yellow brand pixels (`R >= 180, G >= 120, B <= 90`), absence of neon-cyan (`#00D2FF`-like glow even semitrasparente `p[3] > 32`), and non-collision against previous shield SHA-256 hashes added to `LEGACY_OJ_SHA256`.

- [ ] **Step 1: Write failing tests (RED)**
  Add previous shield SHA-256 hashes to `LEGACY_OJ_SHA256` in `tests/test_brand_assets.py`:
  - `icon.png`, `dark_icon.png`: `"ec74facf70cfe94cd59098da3a12cfc6f5df6fec17c69c66a5ff7ea65fb60c4b"`
  - `icon@2x.png`, `dark_icon@2x.png`: `"80af4580822f9f865d0903feea3474000efce68f979fc4cd44b3b380501acf2a"`
  - `logo.png`, `dark_logo.png`: `"bdd41abca26eb29700162d191e275001e9c17c6075e97b6740563e96573579aa"`
  - `logo@2x.png`, `dark_logo@2x.png`: `"252e76e51e0cd061acf42505ed0cf5cb96ee191feab9ffebc3e1be17a1d6263e"`
  And add the pixel verification test:
  ```python
  @pytest.mark.parametrize("filename,width,height", BRAND_SPECS)
  def test_brand_png_has_transparent_corners_and_gold_brand_accent(filename, width, height):
      """Verify brand PNGs have transparent corners, visible artwork, and warm gold accent without neon cyan."""
      asset_path = Path(REPO) / "custom_components" / "lepas" / "brand" / filename
      with Image.open(asset_path) as img:
          rgba = img.convert("RGBA")
          w, h = rgba.size
          corners = [
              rgba.getpixel((0, 0))[3],
              rgba.getpixel((w - 1, 0))[3],
              rgba.getpixel((0, h - 1))[3],
              rgba.getpixel((w - 1, h - 1))[3],
          ]
          assert all(a == 0 for a in corners), f"{filename} must have transparent corners, got alpha {corners}"

          pixels = list(rgba.getdata())
          opaque = [p for p in pixels if p[3] > 200]
          assert len(opaque) > (w * h) * 0.05, f"{filename} appears nearly blank"

          gold_pixels = [p for p in opaque if p[0] >= 180 and p[1] >= 120 and p[2] <= 90]
          assert len(gold_pixels) >= 20, f"{filename} missing warm gold-yellow brand accent"

          neon_cyan_pixels = [p for p in pixels if p[3] > 32 and p[0] <= 40 and p[1] >= 180 and p[2] >= 220]
          assert len(neon_cyan_pixels) == 0, f"{filename} contains forbidden neon-cyan pixels"
  ```
  *Falsification check:* Against the current shield PNGs (which have opaque `#0D141E` rounded-rect corners or `#00D2FF` cyan glow and zero gold), this test FAILS (`RED`) until the new transparent leopard+gold assets replace them.
- [ ] **Step 2: Run targeted pytest to verify RED (before asset swap) or GREEN (after Task 1)**
  Run: `/home/federico/.local/bin/uv run --with pytest pytest tests/test_brand_assets.py -q --tb=short`
  Expected: FAIL on legacy shield assets; PASS on new leopard+gold RGBA assets.

---

### Task 3: Sincronizzazione SemVer `v1.27.0` & `CHANGELOG.md`

**Files:**
- Modify: `custom_components/lepas/manifest.json:23`
- Modify: `pyproject.toml:3`
- Modify: `custom_components/lepas/lovelace/lepas-card.js:2,14,85-91,1480`
- Modify: `tests/test_lovelace_card.py:126,129`
- Modify: `tests/lepas_card.test.mjs:921,924,930,949`
- Modify: `CHANGELOG.md:17-20`

**Interfaces:**
- Produces: Synchronized `1.27.0` version string across all manifest, card, test, and changelog files (required by `tests/test_repo_hygiene.py::test_versione_sincronizzata_e_changelog_lepas` and `AB-LEP-008`).

- [ ] **Step 1: Update test assertions first (RED)**
  Update `1.26.0` → `1.27.0` in `tests/test_lovelace_card.py:126,129` and `tests/lepas_card.test.mjs:921,924,930,949`.
- [ ] **Step 2: Update `manifest.json`, `pyproject.toml`, `lepas-card.js`, and `CHANGELOG.md` (GREEN)**
  - `custom_components/lepas/manifest.json`: `"version": "1.27.0"`
  - `pyproject.toml`: `version = "1.27.0"`
  - `custom_components/lepas/lovelace/lepas-card.js`: update header, `CARD_VERSION = "1.27.0"`, `HERO_IMAGES` `?v=1.27.0`, `DEFAULT_HERO` `?v=1.27.0`, and editor placeholder `?v=1.27.0`.
  - `CHANGELOG.md`: add `## v1.27.0 — 2026-11-19` directly under `## [Non rilasciato]` with `### 🇬🇧 English` and `### 🇮🇹 Italiano` sections.

---

### Task 4: Verifica Completa, Dual-Gate Audit Tier 3 & Rilascio (`v1.27.0`)

**Files:**
- Verify only (Master Agent): all modified/repo files.

- [ ] **Step 1: Run Master verification gates**
  - `/home/federico/.local/bin/uv run --with pytest pytest -q --tb=short --maxfail=2`
  - `node --test tests/lepas_card.test.mjs`
  - `/home/federico/.local/bin/uv run ruff check custom_components/ tests/ && /home/federico/.local/bin/uv run ruff format --check custom_components/ tests/`
- [ ] **Step 2: Run Tier 3 Audit**
  - Pass 1: `local_llm_offload.py --task review-hygiene --files ... --json`
  - Pass 2: Sentinel `Model: 'inherit'` (same CID `88696379-6211-491a-b774-f013836534bc` via `send_message`) + `APPROVED_TREE=$(git write-tree)`
- [ ] **Step 3: Graphify sync, Git commit/tag/push & HA live deploy**
  - `graphify update .`
  - Commit, `git tag -f v1.27.0`, `git push origin main && git push -f origin v1.27.0`
  - Deploy updated files to `192.168.88.231`, `ha_check_config`, `ha_restart`, verify live HA state.
