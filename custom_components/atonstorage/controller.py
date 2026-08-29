"""AtonStorage controller"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import create_async_httpx_client
from homeassistant.util import dt as dt_util

_BASEURL = "https://www.atonstorage.com/atonTC/"
_LOGIN_ENDPOINT = _BASEURL + "index.php"
_MONITOR_ENDPOINT = _BASEURL + "get_monitor.php?sn={serial_number}"
_ENERGY_ENDPOINT = (
    _BASEURL
    + "get_energy.php?idImpianto={id}&anno={year}&mese={month}&giorno={day}&intervallo=d"
)  # tot_pReteOut
_SET_REQUEST_ENDPOINT = (
    _BASEURL
    + "set_request.php?request=MONITOR&intervallo={interval}&sn={serial_number}"
)
# _ENDPOINT = "https://www.atonstorage.com/atonTC/get_monitor.php?sn={serialNumber}&_={timestamp}"
# https://www.atonstorage.com/atonTC/set_request.php?sn={serialNumber}&request=MONITOR&intervallo=15&_={timestamp}
# https://www.atonstorage.com/atonTC/getAlarmDesc.php?sn={serialNumber}&_={timestamp}
# https://www.atonstorage.com/atonTC/hasExternalEV.php?id_impianto=151762966&_={timestamp}
# https://www.atonstorage.com/atonTC/get_monitorToday.php?&sn={serialNumber}&_={timestamp}
# https://www.atonstorage.com/atonTC/get_energy.php?anno=2022&mese=11&giorno=9&idImpianto=151762966&intervallo=d&potNom=3500&batNom=3500&sn={serialNumber}&_={timestamp}
# https://www.atonstorage.com/atonTC/get_vbib.php?anno=2022&mese=11&sn={serialNumber}&_={timestamp}
# https://www.atonstorage.com/atonTC/get_allarmi_oggi.php?sn={serialNumber}&idImpianto=151762966&tipoUtente=1&_={timestamp}
# https://www.atonstorage.com/atonTC/checkTShift.php?sn={serialNumber}&_={timestamp}
# https://www.atonstorage.com/atonTC/getTShift.php?sn={serialNumber}&_={timestamp}

# Per request timeout. A full refresh performs three of these calls, so it has
# to stay well below the coordinator's own timeout.
REQUEST_TIMEOUT = 30

_PLANT_ID_RE = re.compile(r"var idImpianto = (.*);")
_UNAUTHORIZED = b"Unauthorized"

_LOGGER = logging.getLogger(__name__)


class Controller:
    """Define a generic AtonStorage sensor."""

    def __init__(self, hass: HomeAssistant, user, password, serial_number, opts):
        """Initialize."""

        if serial_number is None:
            raise SerialNumberRequiredError

        if not user or not password:
            raise UsernameAndPasswordRequiredError

        self._hass = hass

        self._user = user
        self._password = password
        self._serial_number = serial_number
        self._plant_id = None
        self._opts = opts
        self._session = None

        # A private client, so the PHP session cookie is not shared with every
        # other httpx based integration, nor with a second AtonStorage account.
        # Closed again by async_close(); auto_cleanup is off because it would
        # register one more stop listener on every reload of the config entry.
        self._async_client = create_async_httpx_client(
            hass, auto_cleanup=False, follow_redirects=True
        )

        # data dicts
        self.monitor_data = None
        self.energy_data = None

    async def async_close(self) -> None:
        """Close the http client owned by this controller."""
        await self._async_client.aclose()

    async def login(self) -> bool:
        """Login to Aton server."""

        try:
            landing = await self._async_client.get(
                _LOGIN_ENDPOINT, timeout=REQUEST_TIMEOUT
            )
            login = await self._async_client.post(
                _LOGIN_ENDPOINT,
                timeout=REQUEST_TIMEOUT,
                # Pass a dict and let httpx url-encode it: a hand built body
                # breaks on passwords containing &, =, + or non ascii characters.
                data={"username": self._user, "password": self._password},
                cookies=landing.cookies,
            )
        except httpx.HTTPError as err:
            raise AtonStorageConnectionError(f"Login request failed: {err}") from err

        if login.is_error:
            raise AtonStorageConnectionError(f"Login returned HTTP {login.status_code}")

        # The portal hands out a session cookie even when the credentials are
        # wrong, so the only reliable success marker is the plant id embedded in
        # the page that comes back.
        result = _PLANT_ID_RE.search(login.text)
        if result is None:
            _LOGGER.debug("No plant id in the login response, credentials rejected")
            return False

        self._plant_id = result.group(1)
        self._session = login.cookies or landing.cookies
        _LOGGER.info("Logged in, plant id %s", self._plant_id)

        return True

    async def _async_get(self, url: str, description: str) -> httpx.Response:
        """Perform an authenticated GET, raising on anything that is not usable."""

        try:
            response = await self._async_client.get(
                url, timeout=REQUEST_TIMEOUT, cookies=self._session
            )
        except httpx.HTTPError as err:
            raise AtonStorageConnectionError(f"{description} failed: {err}") from err

        # Note the b prefix: response.content is bytes, comparing it to a str
        # silently never matched.
        if (
            response.status_code in (401, 403)
            or response.content.strip() == _UNAUTHORIZED
        ):
            self._session = None
            raise AtonStorageSessionExpiredError(f"{description} was refused")

        if response.is_error:
            raise AtonStorageConnectionError(
                f"{description} returned HTTP {response.status_code}"
            )

        if not response.content:
            raise AtonStorageConnectionError(f"{description} returned an empty body")

        return response

    async def _async_get_json(self, url: str, description: str) -> Any:
        """Perform an authenticated GET and decode the JSON payload."""

        response = await self._async_get(url, description)

        try:
            data = json.loads(response.content)
        except ValueError as err:
            # A body that is not JSON is almost always the HTML login page, i.e.
            # the PHP session expired. Drop the session so the caller can log in
            # again, instead of silently serving yesterday's values forever.
            self._session = None
            _LOGGER.debug("Erroneous JSON for %s: %s", description, response.content)
            raise AtonStorageSessionExpiredError(
                f"{description} did not return JSON"
            ) from err

        _LOGGER.debug("Data fetched from resource: %s", response.content)

        return data

    async def refresh(self) -> None:
        """Refresh data from server, logging in again if the session expired."""

        for attempt in (1, 2):
            if self._session is None:
                if not await self.login():
                    raise InvalidUsernameOrPasswordError

            try:
                await self._async_refresh_once()
            except AtonStorageSessionExpiredError as err:
                if attempt == 2:
                    raise AtonStorageConnectionError(str(err)) from err
                _LOGGER.info("AtonStorage session expired, logging in again")
                continue

            return

    async def _async_refresh_once(self) -> None:
        """Run one full fetch cycle with the session currently held."""

        await self._async_get(
            _SET_REQUEST_ENDPOINT.format(
                serial_number=self._serial_number,
                interval=self._opts.get("interval", 15),
            ),
            "set_request",
        )

        monitor_data = await self._async_get_json(
            _MONITOR_ENDPOINT.format(serial_number=self._serial_number),
            "get_monitor",
        )

        # Read the clock once, in Home Assistant's configured timezone: three
        # separate now() calls can straddle midnight and build a date whose
        # year/month/day come from different days.
        now = dt_util.now()
        energy_data = await self._async_get_json(
            _ENERGY_ENDPOINT.format(
                id=self._plant_id,
                year=now.year,
                month=now.month,
                day=now.day,
            ),
            "get_energy",
        )

        # Publish both payloads only once both have been fetched, so a partial
        # refresh can never mix fresh monitor data with stale energy data.
        self.monitor_data = monitor_data
        self.energy_data = energy_data

    def get_raw_data(self, key: str):
        """Return a raw value from either payload, or None when unavailable."""

        if self.monitor_data and key in self.monitor_data:
            return self.monitor_data[key]

        if self.energy_data and key in self.energy_data:
            return self.energy_data[key]

        # Debug and not warning: a plant without an EV lacks a whole set of keys
        # and would log on every single poll.
        _LOGGER.debug("Key %s not found in monitor_data or energy_data", key)
        return None

    def _status_bit(self, mask: int) -> bool:
        """Return a single bit of the status bitfield."""
        return int(self.monitor_data.get("status") or 0) & mask == mask

    @property
    def grid_to_house(self) -> bool:
        return self._status_bit(1)

    @property
    def solar_to_battery(self) -> bool:
        return self._status_bit(2)

    @property
    def solar_to_grid(self) -> bool:
        return self._status_bit(4)

    @property
    def battery_to_house(self) -> bool:
        return self._status_bit(8)

    @property
    def solar_to_house(self) -> bool:
        return self._status_bit(16)

    @property
    def grid_to_battery(self) -> bool:
        return self._status_bit(32)

    @property
    def battery_to_grid(self) -> bool:
        return self._status_bit(64)

    @property
    def serial_number(self) -> str:
        return self.monitor_data["serialNumber"]

    @property
    def last_update(self) -> str:
        return self.monitor_data["data"]

    @property
    def status(self) -> str:
        return self.monitor_data["status"]

    @property
    def status_man(self) -> str:
        return self.monitor_data["statusMan"]

    @property
    def instant_solar_power(self) -> int:
        return int(self.monitor_data["pSolare"])

    @property
    def instant_user_power(self) -> int:
        return int(self.monitor_data["pUtenze"])

    @property
    def instant_user_power_real(self) -> int:
        return int(self.monitor_data["pUtenzeReal"])

    @property
    def instant_battery_power(self) -> int:
        return int(self.monitor_data["pBatteria"])

    @property
    def instant_grid_input_power(self) -> int:
        return int(self.monitor_data["pReteIn"])

    @property
    def instant_grid_output_power(self) -> int:
        return int(self.monitor_data["pReteOut"])

    @property
    def instant_grid_power(self) -> int:
        return int(self.monitor_data["pRete"])

    @property
    def instant_grid_power_real(self) -> int:
        return int(self.monitor_data["pReteReal"])

    @property
    def status_of_charge(self) -> float:
        return float(self.monitor_data["soc"])

    @property
    def run_mode(self) -> int:
        return int(self.monitor_data["runMode"])

    @property
    def string1_current(self) -> float:
        return float(self.monitor_data["string1I"])

    @property
    def string1_voltage(self) -> float:
        return float(self.monitor_data["string1V"])

    @property
    def string2_current(self) -> float:
        return float(self.monitor_data["string2I"])

    @property
    def string2_voltage(self) -> float:
        return float(self.monitor_data["string2V"])

    @property
    def user_current(self) -> float:
        return float(self.monitor_data["utenzeI"])

    @property
    def user_voltage(self) -> float:
        return float(self.monitor_data["utenzeV"])

    @property
    def battery_voltage(self) -> float:
        return float(self.monitor_data["vb"])

    @property
    def battery_current(self) -> float:
        return float(self.monitor_data["ib"])

    @property
    def fw_Scheda(self) -> str:
        return self.monitor_data["fwScheda"]

    @property
    def rel_inverter(self) -> str:
        return self.monitor_data["relInverter"]

    @property
    def rel_manager(self) -> str:
        return self.monitor_data["relManager"]

    @property
    def rel_charger(self) -> str:
        return self.monitor_data["relCharger"]

    @property
    def rel_bios(self) -> str:
        return self.monitor_data["relBIOS"]

    @property
    def battery_charged(self) -> int:
        return int(self.monitor_data["ahCaricati"])

    @property
    def battery_discharged(self) -> int:
        return int(self.monitor_data["ahScaricati"])

    @property
    def battery_energy_charged(self) -> float:
        return float(self.energy_data["tot_pBatteria"])

    @property
    def battery_energy_discharged(self) -> float:
        return float(self.energy_data["tot_pBatteriaB"])

    @property
    def max_selled_power(self) -> int:
        return self.monitor_data["pMaxVenduta"]

    @property
    def max_pannel_power(self) -> int:
        return self.monitor_data["pMaxPannelli"]

    @property
    def max_battery_power(self) -> int:
        return self.monitor_data["pMaxBatteria"]

    @property
    def max_bought_power(self) -> int:
        return self.monitor_data["pMaxComprata"]

    @property
    def sold_energy(self) -> float:
        return float(self.energy_data["tot_pReteOut"])

    @property
    def bought_energy(self) -> float:
        return float(self.energy_data["tot_pReteIn"])

    @property
    def pannel_energy(self) -> int:
        return self.monitor_data["ePannelli"]

    @property
    def consumed_energy(self) -> float:
        return self.bought_energy + self.battery_energy_discharged

    # "ingressi1": "0",
    # "ingressi2": "160",
    # "ingressi3": "0",
    # "ingressi4": "0",
    # "ingressi5": "0",
    # "ingressi6": "0",
    # "ingressi7": "0",
    # "ingressi8": "0",
    # "uscite1": "0",
    # "uscite2": "10",
    # "uscite3": "0",
    # "uscite4": "0",
    # "uscite5": "0",
    # "uscite6": "0",
    # "iac1": "0",
    # "iac2": "0",
    # "iac3": "0",
    # "allarmi1": "0",
    # "allarmi2": "0",
    # "allarmi3": "0",
    # "allarmi4": "0",
    # "allarmi5": "0",
    # "allarmi6": "0",
    # "allarmi7": "0",
    # "allarmi8": "0",
    # "allarmi9": "0",
    # "allarmi10": "0",
    # "allarmi11": "0",
    # "allarmi12": "32",
    # "allarmi13": "0",
    # "allarmi14": "0",
    # "allarmi15": "0",
    # "allarmi16": "0",

    @property
    def grid_voltage(self) -> float:
        return self.monitor_data["gridV"]

    @property
    def grid_frequency(self) -> float:
        return self.monitor_data["gridHz"]

    @property
    def grid_power(self) -> float:
        return self.monitor_data["pGrid"]

    # "string1IIN": "0",
    # "string1VIN": "0",
    # "string2IIN": "0",
    # "string2VIN": "0",

    @property
    def temperature(self) -> float:
        return self.monitor_data["temperatura"]

    @property
    def temperature2(self) -> float:
        return self.monitor_data["temperatura2"]

    # "dataAllarme": "07/11/2022 07:11:28",

    @property
    def update_delay(self) -> int:
        return self.monitor_data["DiffDate"]

    # "DiffDate": "829",
    # "timestampScheda": "07/11/2022 11:13:13",

    @property
    def vb_scheda(self) -> str:
        return self.monitor_data.get("vbScheda")

    # "flagProgrammazione": "128",
    # "flagProgrammazione3": "72",
    # "wifi": "1",
    # "exportLimit": "0",

    # "pL1": "0",
    # "pL2": "0",
    # "pL3": "0",
    # "pReteL1": "0",
    # "pReteL2": "0",
    # "pReteL3": "0",

    @property
    def ev_num(self) -> int:
        return int(self.monitor_data["num_EV"])

    @property
    def ev_status_of_charge(self) -> float:
        return float(self.monitor_data["SoC_EV"])

    @property
    def ev_status(self) -> int:
        return int(self.monitor_data["stato_EV"])

    # var firstNumber = (parseInt(_data.stato_EV)&0xf0)>>4;
    # var secondNumber = parseInt(_data.stato_EV)&0x0f;

    @property
    def _ev_status_high(self) -> int:
        """High nibble of stato_EV.

        Mind the parentheses: in Python >> binds tighter than &, so writing
        "x & 0xF0 >> 4" silently means "x & 0x0F" instead.
        """
        return (int(self.monitor_data.get("stato_EV") or 0) & 0xF0) >> 4

    @property
    def _ev_status_low(self) -> int:
        """Low nibble of stato_EV."""
        return int(self.monitor_data.get("stato_EV") or 0) & 0x0F

    @property
    def ev_status_off(self) -> bool:
        return self._ev_status_high == 0 or (
            self._ev_status_high == 1 and self._ev_status_low != 3
        )

    @property
    def ev_status_on(self) -> bool:
        return self._ev_status_high == 1 and self._ev_status_low == 3

    @property
    def ev_status_charge(self) -> bool:
        return self._ev_status_high == 2

    @property
    def ev_status_warning(self) -> bool:
        return self._ev_status_high in (4, 5)

    @property
    def ev_setp(self) -> float:
        return float(self.monitor_data["setp_EV"])  # in A

    @property
    def ev_power(self) -> int:
        return int(self.monitor_data["potenza_EV"])  # carica in W

    @property
    def ev_kmh(self) -> float:
        return float(self.monitor_data["kmh"])  # evCaricakmh km/h

    @property
    def ev_e_ciclo_(self) -> float:
        return float(self.monitor_data["e_ciclo_EV"])  # evScaricakWh

    @property
    def ev_km(self) -> float:
        return float(self.monitor_data["km"])  # evScaricakm km

    @property
    def ev_perc_carica(self) -> float:
        return float(self.monitor_data["perc_carica"])  # evCaricakmh %

    # "paese": "IT",
    # "scena": "0",
    # "qeps": "1",
    # "allertaMeteoAuto": "0",

    @property
    def battery_count(self) -> int:
        return self.monitor_data["numBatterie"]


class AtonStorageConnectionError(Exception):
    """Unable to start fetching data."""


class AtonStorageSessionExpiredError(AtonStorageConnectionError):
    """The server refused the session cookie, a new login is needed."""


class UsernameAndPasswordRequiredError(Exception):
    """Error username and password required."""


class InvalidUsernameOrPasswordError(Exception):
    """Error invalid username or password."""


class SerialNumberRequiredError(Exception):
    """Error to serial number required."""
