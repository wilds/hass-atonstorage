# AtonStorage Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/wilds/hass-atonstorage.svg)](https://GitHub.com/wilds/hass-atonstorage/releases/)
![Installation Count](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.atonstorage.total)

This integration polls your AtonStorage inverter through the AtonStorage
cloud portal and splits the values it fetches into separate Home Assistant
sensors and binary sensors: battery state, instantaneous power flows, daily
energy counters, grid and string measurements, EV wallbox data (when present)
and alarm status.

## Requirements

- Home Assistant **2025.8.0** or newer
- Internet access: the integration is cloud-polling (`atonstorage.com`), the
  inverter does not need to be reachable from your LAN

## Installation

1. Install using [HACS](https://github.com/custom-components/hacs)
   (*Apps & integrations* → search for **AtonStorage**), or install manually by
   copying the `custom_components/atonstorage` folder into
   `<config_dir>/custom_components`
2. Restart Home Assistant
3. In the Home Assistant UI, navigate to `Settings` → `Devices & Services` and
   click **Add integration**. Select **AtonStorage** and fill in:
   - **Username** — your AtonStorage portal username
   - **Password** — your AtonStorage portal password
   - **Serial number** — the serial number of the inverter
   - **Scan interval (seconds)** — how often to poll the portal (10–3600,
     default 30)
   - **Sensors to create** — which sensors to expose; tick **BINARY SENSORS**
     to add the binary sensors

If the portal rejects the stored password at any point, Home Assistant asks
you to enter it again (re-authentication flow) instead of failing silently.

## Options

After setup you can change the scan interval and the sensor selection from
`Settings` → `Devices & Services` → *AtonStorage* → **Options**. Changes are
applied immediately — no restart needed.

## Sensors

All sensors are grouped under a single device named after the username.
The available categories:

| Category | Sensors |
| --- | --- |
| Battery | level, voltage, current, charged/discharged current, charged/discharged energy, BMS / inverter / Ah state of charge |
| Instant power | solar, user, battery, grid (plus grid and battery input/output split) |
| Daily energy | bought, sold, solar, consumed, self-consumed |
| Grid & utilities | voltage, frequency, current, utilities voltage/current |
| Solar strings | voltage and current for string 1 and 2 |
| Temperature | inverter temperature, temperature 2 |
| Derived | self sufficiency (%) |
| EV (wallbox plants only) | EV num, battery level, charge current, charge power, km/h, charged energy, km, charged percentage |
| Per phase (three-phase plants) | phase 1/2/3 power, grid phase 1/2/3 power |
| Alarms & diagnostics | active alarm count (with alarm names), last alarm, last update, board time, firmware versions, export limit |

Notes:

- EV sensors only report data when the plant has a wallbox; on other plants
  they show *unknown*
- Per-phase sensors read 0 on single-phase plants
- Daily counters reset to 0 at midnight, as reported by the plant

## Binary sensors

Enabled by ticking **BINARY SENSORS** during setup or in the options:

- Energy flows: grid→house, solar→battery, solar→grid, battery→house,
  solar→house, grid→battery, battery→grid
- EV status: off, on, charging, warning
- Connectivity: WiFi
- Problems: alarm active

## Development

```sh
pip install -r requirements-dev.txt
pytest                      # unit tests, no network access needed
pre-commit run --all-files  # black + flake8
```

## License

[MIT](LICENSE)
