# Workspace Agent Router — Lepas

> **Lepas** (`custom_components/lepas`) is a Home Assistant custom integration and async Python client for the **Lepas L8** connected vehicle platform (**Chery EU**, `com.chery.eu.lepas`).

---

## 📖 [ALL AGENTS] Repository Documentation Index
Before starting any work, consult the relevant documentation files below:
- **Global Agent Guidelines & Safety:** Refer to `~/.gemini/config/AGENTS.md` for global execution rules.
- **System Architecture & Component Model:** Read [docs/architecture.md](file:///./docs/architecture.md).
- **Project Roadmap & Evolution Phases:** Read [docs/roadmap.md](file:///./docs/roadmap.md).
- **Low-Level Code Implementation & Security Bible:** Read [docs/code-implementation.md](file:///./docs/code-implementation.md).
- **Lessons Learned & Discovered Telemetry Context:** Read [.agents/memory/lessons.md](file:///./.agents/memory/lessons.md).

---

## 🧭 [ALL AGENTS] Golden Rules & Engineering Principles

### 1. Ponytail Ladder (Anti-Overengineering)
Stop at the first rung that holds:
1. **Does this need to exist at all?** Speculative need = skip it (YAGNI).
2. **Already in this codebase?** Reuse existing helpers, types, and constants.
3. **Stdlib does it?** Use Python standard library (`datetime`, `zoneinfo`, `dataclasses`, `enum`, `json`).
4. **Native platform feature covers it?** Use Home Assistant core helpers (`DataUpdateCoordinator`, `CoordinatorEntity`, `async_get_clientsession`, `ConfigEntryAuthFailed`).
5. **Already-installed dependency solves it?** Use `aiohttp` or existing HA dependencies. Never add external wheels without strict evaluation.
6. **Can it be one line?** One line.
7. **Only then:** The minimum code that works.

Code first. Then at most three short lines: what was skipped, when to add it. No unrequested abstractions, no speculative generic vehicle factory classes.

### 2. Antislop Comment Hygiene
- Modify comments only when working on code; never add decorative banners, box drawings, or ALL CAPS headers.
- Eliminate restating the obvious (`// Initialize coordinator` above coordinator setup).
- Eliminate step-by-step workflow narration (`// Step 1: get token`, `// Step 2: call endpoint`).
- Eliminate decorative emojis in comments and log strings.
- Keep comments strictly focused on non-obvious invariants: why, security rules, vehicle wake behavior, rate limits. Maximum 1-2 lines per comment.

### 3. Zero Plaintext Secrets Policy
- **Never commit credentials**: passwords, OAuth/JWT tokens, refresh tokens, API keys, or vehicle VINs must NEVER be hardcoded or checked into Git.
- **No plaintext `.env` in production**: Integration runtime configuration must be managed through Home Assistant `ConfigEntry` encrypted storage (`config_flow.py`).
- **Strict redaction in logs & diagnostics**: All VIN instances, bearer tokens, coordinates, and personal identifiers must be masked before writing diagnostics (`diagnostics.py`) or emitting debug logs.

### 4. Schema-Driven Development (SDD)
- All external API request/response payloads from `com.chery.eu.lepas` must be documented and typed using typed dataclasses or pydantic/msgspec models before writing entity bindings.
- Validate boundaries gracefully: handle missing keys, firmware variations, and offline vehicle states without crashing the coordinator.

### 5. Release, Versioning & Changelog Policy (Mandatory on Commit & Push)
Ad ogni `git commit` e `git push` su `main`, l'agente DEVE:
1. Incrementare la versione SemVer (`patch` per fix/asset/refactoring, `minor` per nuove feature/entità) in modo sincronizzato in `custom_components/lepas/manifest.json`, `pyproject.toml` e `?v=<version>` in `custom_components/lepas/lovelace/lepas-card.js`.
2. Compilare le note di rilascio in `CHANGELOG.md` subito sotto `## [Non rilasciato]` aggiungendo l'intestazione `## vX.Y.Z — YYYY-MM-DD` (con sezioni in inglese e italiano).
3. Aggiornare e pushare il tag Git corrispondente (`git tag -f vX.Y.Z && git push -f origin vX.Y.Z`) oltre a `origin/main`.

---

## 🧪 [ALL AGENTS] Mandatory Quality Gates
Automated verification standards for all changes:
- **Host Test Runner**: Python tests are run via `/home/federico/.local/bin/uv run --with pytest pytest -q --tb=short --maxfail=2` (or `.venv/bin/pytest`).
- **Code Style & Linting**: Run `uv run ruff check custom_components/ tests/` and `uv run ruff format --check custom_components/ tests/`.
- **🚫 Sub-Agents Test Ban**: Sub-Agents are strictly forbidden from executing global test suites. Only the Master Agent executes test runners.
- **🚫 No Task Polling**: Do NOT run polling loops or timer schedules (`schedule`) while waiting for tests or commands.

---

## 🏗️ [ALL AGENTS] Architectural Standards
- **Stack**: Python >=3.12, Home Assistant Core integration ecosystem, `aiohttp` async networking.
- **Async Safety**: Every I/O operation must be non-blocking and execute on the event loop with timeouts.
- **Session Lifecycle**: Always reuse Home Assistant's managed `aiohttp.ClientSession` via `async_get_clientsession(hass)`. Never instantiate unmanaged `ClientSession` objects.
- **Vehicle Battery Guard**: Adapt polling intervals based on vehicle power state (active driving/charging: 30-60s; parked/asleep: 15-30m) to prevent draining the 12V auxiliary battery.
