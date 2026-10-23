# Specifica Architetturale: Full Clean Sweep dei Riferimenti Omoda / Jaecoo

**Data:** 2026-10-23
**Stato:** Approvato (Brainstorming L1)
**Autore:** Antigravity Master Agent

## 1. Obiettivo
Rimuovere integralmente dal repository `Lepas` ogni riferimento residuale ai marchi **Omoda** e **Jaecoo** (nelle traduzioni UI di Home Assistant, nei preset di configurazione `config_flow.py`/`const.py`, nel codice Python del componente e del core `custom_components/lepas/`, nelle variabili d'ambiente `OMODA_*`, nei servizi legacy `legacy.py` e nella suite di test `tests/`), rendendo l'integrazione 100% nativa per **Lepas / Chery EU** (`com.chery.eu.lepas`).

## 2. Requisiti e Invarianti Globali
1. **Zero Occorrenze in Codice, Traduzioni e Test**: Nessun match case-insensitive per `omoda` o `jaecoo` deve rimanere in `custom_components/lepas/**` e `tests/**`.
2. **Preset di Configurazione**: `const.py` e `config_flow.py` devono esporre esclusivamente `PRESET_LEPAS_EU` (`lepas_eu`, default), `PRESET_CHERY_EU` (`chery_eu`) e `PRESET_CUSTOM` (`custom`). `PRESET_OMODA_JAECOO_EU` viene rimosso.
3. **Traduzioni UI (`strings.json`, `en.json`, `it.json`, `nl.json`)**:
   - Tutti i testi di login/reauth/cambio telefono devono riferirsi a `"Lepas account"` / `"account Lepas"` / `"Lepas-account"`.
   - Le descrizioni del campo `preset` devono citare esclusivamente `"Lepas (Europe) and Chery (Europe)"` / `"Lepas (Europa) e Chery (Europa)"`.
   - Rimozione della issue legacy `entity_id_migrated_v115` dalle traduzioni e da `repairs.py`.
4. **Rimozione Sottosistema Legacy**:
   - Eliminazione del file `custom_components/lepas/legacy.py` e dei servizi `adotta_entita_legacy` e `recupera_statistiche_legacy` da `__init__.py` e `services.yaml`.
   - Rimozione del fallback sul prefisso `omoda9_` in `__init__.py` (`_async_migrate_entity_ids`) e `entity.py`.
5. **Standardizzazione Variabili d'Ambiente Core (`LEPAS_*`)**:
   - Tutte le variabili d'ambiente interne usate da `core/session.py`, `core/login_lepas.py`, `core/context.py`, `core/commands.py`, `core/prova_token.py`, `core/captcha_solver.py`, `core/wake.py`, `core/provision.py`, `core/lepas.py`, `core/lepas_auth.py`, `core/tls_client.py` e `coordinator.py` passano dal prefisso `OMODA_*` al prefisso `LEPAS_*` (es. `LEPAS_EMAIL`, `LEPAS_PHONE`, `LEPAS_AREA`, `LEPAS_TOKEN_PATH`, `LEPAS_BFF`, `LEPAS_COUNTRY_ID`, `LEPAS_TENANT_CODE`, `LEPAS_LANGUAGE`, `LEPAS_OTP_TIMEOUT`, `LEPAS_PIN`, `LEPAS_MINT_TASKID`, `LEPAS_RETRY_REFRESH`, `LEPAS_TLS_CLIENT`).
   - Rimozione dell'URL fallback `legend-oj.omodaauto.nl` in favore di `https://eu-lepas.cheryinternational.com/api`.
6. **Allineamento Suite di Test e Gate Automatico**:
   - Rimozione di `tests/test_migrazione_entity_id.py` e `tests/test_adozione_legacy.py` (o riconversione di `test_migrazione_entity_id.py` per testare unicamente l'idempotenza su `lepas_`).
   - Pulizia degli alias `omoda` / `login_omoda` in `tests/core_loader.py` e `tests/conftest.py`.
   - Aggiornamento di `tests/test_repo_hygiene.py` con un test di regressione che fallisce se compaiono match case-insensitive di `omoda` o `jaecoo` in `custom_components/lepas/` o `tests/`.
7. **Allineamento Istanza Live Home Assistant**:
   - Copia dei file aggiornati di `custom_components/lepas/` su `/config/custom_components/lepas/` (e rimozione di `/config/custom_components/lepas/legacy.py`) affinché la UI di Home Assistant mostri immediatamente le nuove traduzioni e opzioni.

## 3. Partizionamento dei Domini (N-Domain Mapping)
1. **Dominio 1 — HA Integration Layer & UI Translations (`python-development`)**:
   - File: `custom_components/lepas/strings.json`, `custom_components/lepas/translations/*.json`, `custom_components/lepas/const.py`, `custom_components/lepas/config_flow.py`, `custom_components/lepas/__init__.py`, `custom_components/lepas/coordinator.py`, `custom_components/lepas/entity.py`, `custom_components/lepas/legacy.py` (delete), `custom_components/lepas/services.yaml`, `custom_components/lepas/diagnostics.py`, `custom_components/lepas/diag.py`, `custom_components/lepas/climate.py`, `custom_components/lepas/sensor.py`, `custom_components/lepas/repairs.py`, `custom_components/lepas/certs/store.json`.
2. **Dominio 2 — Core Async Client & CLI Engine (`python-pro`)**:
   - File: `custom_components/lepas/core/*.py` (`session.py`, `login_lepas.py`, `context.py`, `commands.py`, `prova_token.py`, `captcha_solver.py`, `permessi.py`, `wake.py`, `provision.py`, `lepas.py`, `lepas_auth.py`, `tls_client.py`, `probe.py`, `codes.py`).
3. **Dominio 3 — Test Suite, Repo Hygiene & Ancillary Files (`pytest-skill`)**:
   - File: `tests/**`, `NOTICE`, `.github/ISSUE_TEMPLATE/**`, `tools/**`, `docs/roadmap.md`, `docs/superpowers/specs/2026-10-23-lepas-chery-connect-design.md`.
