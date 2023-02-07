# AtonStorage Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/wilds/hass-atonstorage.svg)](https://GitHub.com/wilds/hass-atonstorage/releases/)
![Installation Count](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.atonstorage.total)

This integration splits out the various values that are fetched from your
AtonStorage inverter into separate HomeAssistant sensors.

## Installation

1. Install using [HACS](https://github.com/custom-components/hacs). Or install manually by copying `custom_components/atonstorage` folder into `<config_dir>/custom_components`
2. Restart Home Assistant.
3. In the Home Assistant UI, navigate to `Configuration` then `Integrations`. Click on the add integration button at the bottom right and select `AtonStorage`. Fill out the options and save.
   - Serial Number -The serial number of inverter.
   - Device Name - The name of the device that appears in Home Assistant.
   - Scan Interval - The scan interval in seconds to fetch data from AtonStorage API
