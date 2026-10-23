# Lepas (`custom_components/lepas`)

Home Assistant custom integration and async Python client for the **Lepas L8** connected vehicle platform (**Chery EU**, `com.chery.eu.lepas`).

---

## Overview

This repository provides an asynchronous Python API client and Home Assistant integration enabling real-time telematics monitoring and remote vehicle control for the Lepas L8 PHEV/SUV on the European Chery connected vehicle infrastructure.

### Key Capabilities
- **Telematics Sensors**: High-voltage battery state of charge (SoC), estimated electric and fuel range, odometer, 12V auxiliary battery health, and tire pressures.
- **Vehicle Status Binary Sensors**: Door, trunk, hood, window, and charging cable status.
- **Vehicle Location**: GPS tracking via Home Assistant `device_tracker`.
- **Remote Commands**: Door lock/unlock, climate pre-conditioning, window defrost, and charging controls.
- **Battery Preservation**: Adaptive polling cadences to protect the vehicle's 12V auxiliary battery.

---

## Repository Documentation Index
- **Agent Router & Golden Rules**: [.agents/AGENTS.md](.agents/AGENTS.md)
- **Lessons & Telemetry Invariants**: [.agents/memory/lessons.md](.agents/memory/lessons.md)
- **System Architecture**: [docs/architecture.md](docs/architecture.md)
- **Roadmap & Phases**: [docs/roadmap.md](docs/roadmap.md)
- **Implementation & Security Details**: [docs/code-implementation.md](docs/code-implementation.md)

---

## Development & Quality Gates

### Running Tests
Automated verification is executed using `uv` or local virtualenv:
```bash
uv run --with pytest pytest -q --tb=short --maxfail=2
```

### Code Formatting & Linting
```bash
uv run ruff check .
uv run ruff format --check .
```
