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

#### Prerequisites & Account Requirements

Before configuring the integration in Home Assistant, make sure you meet the following requirements:

1. **Active Lepas Europe Account**: An active account in the official Lepas / Chery Europe mobile app (`com.chery.eu.lepas`) with at least one paired vehicle.
2. **Account Password (Mandatory)**: Home Assistant connects exclusively via **Email (or Phone Number + International Country Code) and Password**.
   > [!IMPORTANT]
   > If you registered or normally sign in to the Lepas app using one-time verification codes (OTP email or SMS), you **must set an account password** in the official Lepas mobile app before setting up this integration (*Profile / Settings -> Account & Security -> Set Password*).
3. **Vehicle Security PIN**: The 4- or 6-digit PIN configured in your mobile app, required to execute remote vehicle commands (door locks, climate control, window venting, etc.).
4. **Security & Privacy**: Your password is encrypted and transmitted directly to the Chery/Lepas OAuth endpoint **only once** to mint an OAuth session token. Home Assistant **never stores your password**; subsequent requests use the rotating OAuth refresh token stored locally in your instance.

#### Step-by-Step Setup

1. In Home Assistant, go to **Settings** -> **Devices & Services**.
2. Click **Add Integration** in the bottom right corner.
3. Search for **Lepas Connect**.
4. Choose your region preset (defaults to **Lepas — Europe**; **Chery — Europe** is also available).
5. Enter your **Email or Phone Number**:
   - If using an email address, leave the country code as default.
   - If using a phone number, enter the number digits and specify your international country code (e.g. `39` for Italy) without `+` or spaces.
6. Enter your **Account Password** and your **Vehicle Security PIN**.
7. Submit the form. If multiple vehicles are linked to your account, choose the VIN you want to configure.

#### First Start & `unknown` Sensors

> [!NOTE]
> **Why do telemetry sensors show `unknown` immediately after configuration?**
> When the vehicle is parked and asleep, the onboard telematics module (T-Box) shuts off high-voltage polling to safeguard the 12V auxiliary battery.
> - Full telemetry (odometer, tire pressure, battery status) will populate automatically the first time the vehicle is turned on or driven.
> - You can immediately request status updates by pressing the **Wake car** (*Sveglia auto*) or **Refresh full status** (*Aggiorna stato completo*) buttons.
> - You can also enable **Automatic updates** in the integration options. Keep intervals reasonable (e.g., 60+ minutes while parked) to protect against 12V battery drain.

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