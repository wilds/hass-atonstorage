# AGENTS.md

Home Assistant custom integration (`custom_components/atonstorage`) for AtonStorage
solar+battery inverters. Cloud-polls the atonstorage.com PHP portal over httpx.
Single package, no build step, no frontend.

## Commands

- Tests: `pytest` (deps pinned in `requirements-dev.txt`; install with
  `pip install -r requirements-dev.txt`). `pytest.ini` sets `testpaths=tests`
  and `asyncio_mode=auto` (hence `pytest-asyncio`). Tests run offline: the
  Controller is instantiated without `__init__` and fed canned payloads.
- Lint: `pre-commit run --all-files` (black + flake8). flake8 config:
  max-line-length 127, only `E9,F63,F7,F82` selected.
- Version bump: `version` in `custom_components/atonstorage/manifest.json` plus a
  `vX.Y.Z` git tag. `hacs.json` holds the *minimum HA version* (2025.8.0), not the
  release version.

## Architecture

- `controller.py` — `Controller`: login + one refresh = 3 portal calls
  (`set_request` → `get_monitor` → `get_energy`) plus a one-time optional alarm
  table. Owns one private httpx client per config entry; re-logs in when the PHP
  session expires.
- `__init__.py` — config entry setup + `AtonStorageUpdateCoordinator`.
  `UPDATE_TIMEOUT` (90 s) must stay above 3 × `REQUEST_TIMEOUT` (30 s).
- `sensor.py` / `binary_sensor.py` — entity descriptions; each uses either
  `value_conversion_function` (raw payload key via `get_raw_data`) or
  `value_calc_function` (computed from the controller).
- `config_flow.py` — setup, reauth, and options flows (scan interval + sensor
  selection); changing options reloads the whole entry.
- Entities are selected by **display name** via `CONF_MONITORED_VARIABLES`
  (`AVAILABLE_SENSORS` in `const.py`); binary sensors are gated by the
  `"BINARY SENSORS"` option.
- Device identity: identifier `(DOMAIN, "AtonStorage " + username)`, device name =
  username, `sw_version` = `fw_Scheda`. New entities must reuse this.

## Portal / domain quirks

- Payloads are Italian (`pUtenze`, `ahCaricati`, `temperatura`, ...).
- Login success = `var idImpianto = ...` present in the login page; the portal
  hands out a session cookie even for wrong credentials. A non-JSON response
  means the session expired → drop session and re-login.
- `status` is a bitfield (1=grid→house, 2=solar→battery, 4=solar→grid, 8=battery→house,
  16=solar→house, 32=grid→battery, 64=battery→grid). `allarmi` is positional
  against the 128-entry `getAlarmDesc` table.
- Daily counters (`tot_*`) are reset to 0 by the plant at midnight: declare them
  `TOTAL_INCREASING`, never `TOTAL` (no `last_reset` is published).
- EV fields are absent on plants without a wallbox: `get_raw_data` returns None
  and `native_value` must return None (unknown), not crash.
- `monitor_data` and `energy_data` are published atomically — never publish one
  without the other.
- The energy endpoint date must be read once via `homeassistant.util.dt.now()`
  (HA timezone); separate `now()` calls can straddle midnight.

## Conventions

- Do not rename, remove, or re-unit existing entities — it would split their
  long-term statistics.
- Adding a sensor: add its display name to `AVAILABLE_SENSORS` (`const.py`) and
  matching keys to `strings.json` + `translations/en.json`. Translations use
  **literal strings** — `%key%` references are only resolved for core
  integrations.
- HA internal APIs are unstable: `IntegrationSensor.__init__` gained a required
  `hass` in 2025.8 and lost it again in 2026.8 (core PR #177596, not on the
  official breaking-changes list). When touching `homeassistant.components.*`
  internals, check the installed HA version.
- Untracked scratch files in the package dir (`controller copy.py`,
  `Untitled-1.p_y`) are not part of the integration — ignore them.
- The `lint` branch is a diverged experiment (removes `binary_sensor.py` and the
  tests); don't base work on it.
