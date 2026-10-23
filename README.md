# Lepas Connect (custom_components/lepas)

## Home Assistant custom integration and async Python client for the **Lepas L8** connected vehicle platform (**Chery EU**, com.chery.eu.lepas).

> [!CAUTION]
> **Active Development & Use at Your Own Risk Disclaimer**
> This repository is under active, heavy development (Work in Progress / Experimental) and is an unofficial community project not affiliated with or endorsed by Chery International or Lepas. Using this software—including remote vehicle commands and cloud polling that may affect the 12V auxiliary battery—is strictly at your own risk. The authors and contributors assume no liability for any vehicle issues, battery drain, or account restrictions.

## Installation

### Option 1: HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=cavuminfundo&repository=Lepas-HA&category=integration)

1. Open your Home Assistant instance.
2. Navigate to the Home Assistant Community Store (HACS).
3. Click on the top-right menu (⋮).
4. Choose "Custom repositories."
5. Add `https://github.com/cavuminfundo/Lepas-HA` with the category "Integration."
6. Download the Lepas Connect integration.
7. Restart Home Assistant.

### Option 2: Manual Installation

1. Copy the `custom_components/lepas` directory from this repository into your Home Assistant configuration directory (`config_dir/custom_components/lepas`).
2. Restart Home Assistant.

### Configuration

1. Go to Settings -> Devices & Services.
2. Click on "Add Integration."
3. Search for "Lepas Connect."
4. Sign in with your Lepas Europe account.

## Overview & Key Capabilities

- **Telematics Sensors**: Monitor various vehicle metrics such as speed, fuel level, and engine temperature.
- **Vehicle Status Binary Sensors**: Track vehicle status indicators like door locks, engine running, and ignition state.
- **GPS Location via device_tracker**: Keep track of your vehicle's location using GPS.
- **Remote Commands**: Control your vehicle remotely, such as locking/unlocking doors and starting/stopping the engine.
- **12V Battery Preservation**: Features designed to minimize battery drain, ensuring your vehicle's auxiliary battery remains healthy.

## Repository Documentation Index

- [.agents/AGENTS.md](.agents/AGENTS.md)
- [.agents/memory/lessons.md](.agents/memory/lessons.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/roadmap.md](docs/roadmap.md)
- [docs/code-implementation.md](docs/code-implementation.md)

## Development & Quality Gates

To ensure the quality and reliability of the integration, we use the following tools:

- **pytest**: For running unit tests.
- **ruff**: For linting and code quality checks.

To run the tests and linting, use the following commands:

```bash
pytest
ruff .
```