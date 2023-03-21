"""AtonStorage controller"""
import json
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

_BASEURL = "https://www.atonstorage.com/atonTC/"
_LOGIN_ENDPOINT = _BASEURL + "index.php"
_MONITOR_ENDPOINT = _BASEURL + "get_monitor.php?sn={serialNumber}"
_SET_REQUEST_ENDPOINT = (
    _BASEURL + "set_request.php?request=MONITOR&intervallo={interval}&sn={serialNumber}"
)
# _ENDPOINT = "https://www.atonstorage.com/atonTC/get_monitor.php?sn={serialNumber}&_={timestamp}"
# https://www.atonstorage.com/atonTC/set_request.php?sn=T19DE000868&request=MONITOR&intervallo=15&_={timestamp}
# https://www.atonstorage.com/atonTC/getAlarmDesc.php?sn=T19DE000868&_={timestamp}
# https://www.atonstorage.com/atonTC/hasExternalEV.php?id_impianto=151762966&_={timestamp}
# https://www.atonstorage.com/atonTC/get_monitorToday.php?&sn=T19DE000868&_={timestamp}
# https://www.atonstorage.com/atonTC/get_energy.php?anno=2022&mese=11&giorno=9&idImpianto=151762966&intervallo=d&potNom=3500&batNom=3500&sn=T19DE000868&_={timestamp}
# https://www.atonstorage.com/atonTC/get_vbib.php?anno=2022&mese=11&sn=T19DE000868&_={timestamp}
# https://www.atonstorage.com/atonTC/get_allarmi_oggi.php?sn=T19DE000868&idImpianto=151762966&tipoUtente=1&_={timestamp}
# https://www.atonstorage.com/atonTC/checkTShift.php?sn=T19DE000868&_={timestamp}
# https://www.atonstorage.com/atonTC/getTShift.php?sn=T19DE000868&_={timestamp}

_LOGGER = logging.getLogger(__name__)


class Controller:
    """Define a generic AtonStorage sensor."""

    _data = None
    _hass: HomeAssistant = None
    _async_client = None

    def __init__(self, hass: HomeAssistant, user, password, serial_number, opts):
        """Initialize."""

        if user is None or password is None:
            raise UsernameAndPasswordRequiredError

        if serial_number is None:
            raise SerialNumberRequiredError

        self._hass = hass

        self._user = user
        self._password = password
        self._serial_number = serial_number
        self._opts = opts
        self._session = None
        self._async_client = get_async_client(hass, verify_ssl=False)

    async def login(self) -> bool:
        """Login to Aton server."""
        login = await self._async_client.get(
            _LOGIN_ENDPOINT, timeout=60
        )  # get inital cookie

        login = await self._async_client.post(
            _LOGIN_ENDPOINT,
            timeout=60,
            data=f"username={self._user}&password={self._password}",
            cookies=login.cookies,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if login.headers is not None and login.headers["Set-Cookie"] is not None:
            self._session = login.cookies
            _LOGGER.info("Logged in")
            return True
        return False

    async def refresh(self) -> None:
        """Refresh data from server"""

        if self._session is None:
            login = await self.login()
            if not login:
                raise InvalidUsernameOrPasswordError

        try:
            set_interval = await self._async_client.get(
                _SET_REQUEST_ENDPOINT.format(
                    serialNumber=self._serial_number,
                    interval=self._opts["interval"] | 15,
                ),
                timeout=60,
                cookies=self._session,
            )
            if set_interval.content is None:
                _LOGGER.error("Unable to set refresh interval")
                raise AtonStorageConnectionError
            if set_interval.content == "Unauthorized":
                self._session = None
                raise AtonStorageConnectionError

            monitor = await self._async_client.get(
                _MONITOR_ENDPOINT.format(serialNumber=self._serial_number),
                timeout=60,
                cookies=self._session,
            )
            if monitor.content is None:
                _LOGGER.error("Unable to start fetching data")
                raise AtonStorageConnectionError
            if monitor.content == "Unauthorized":
                self._session = None
                raise AtonStorageConnectionError

            json_dict = monitor.content
            if json_dict is not None:
                try:
                    self._data = json.loads(json_dict)
                    _LOGGER.debug("Data fetched from resource: %s", json_dict)
                except ValueError:
                    _LOGGER.warning("REST result could not be parsed as JSON")
                    _LOGGER.debug("Erroneous JSON: %s", self._data)
                except Exception as exc:
                    _LOGGER.error(exc)
                    raise exc
            else:
                _LOGGER.warning("Empty reply found when expecting JSON data")
        except TypeError:
            _LOGGER.error("Unable to fetch data. Response: %s", monitor.content)
        except Exception as exc:
            _LOGGER.error(exc)
            raise exc

    def getRawData(self, __name: str):
        return self._data[__name]

    @property
    def serialNumber(self) -> str:
        """return the serial number"""
        return self._data["serialNumber"]

    @property
    def currentDate(self) -> str:
        return self._data["data"]

    @property
    def status(self) -> str:
        return self._data["status"]

    @property
    def statusMan(self) -> str:
        return self._data["statusMan"]

    @property
    def instantSolarPower(self) -> int:
        return int(self._data["pSolare"])

    @property
    def instantUserPower(self) -> int:
        return int(self._data["pUtenze"])

    @property
    def instantUserPowerReal(self) -> int:
        return int(self._data["pUtenzeReal"])

    @property
    def instantBatteryPower(self) -> int:
        return int(self._data["pBatteria"])

    @property
    def instantGridInputPower(self) -> int:
        return int(self._data["pReteIn"])

    @property
    def instantGridOutputPower(self) -> int:
        return int(self._data["pReteOut"])

    @property
    def instantGridPower(self) -> int:
        return int(self._data["pRete"])

    @property
    def instantGridPowerReal(self) -> int:
        return int(self._data["pReteReal"])

    @property
    def statusOfCharge(self) -> int:
        return int(self._data["soc"])

    @property
    def runMode(self) -> int:
        return int(self._data["runMode"])

    @property
    def string1Current(self) -> float:
        return float(self._data["string1I"])

    @property
    def string1Voltage(self) -> float:
        return float(self._data["string1V"])

    @property
    def string2Current(self) -> float:
        return float(self._data["string2I"])

    @property
    def string2Voltage(self) -> float:
        return float(self._data["string2V"])

    @property
    def userCurrent(self) -> float:
        return float(self._data["utenzeI"])

    @property
    def userVoltage(self) -> float:
        return float(self._data["utenzeV"])

    @property
    def batteryVoltage(self) -> float:
        return float(self._data["vb"])

    @property
    def batteryCurrent(self) -> float:
        return float(self._data["ib"])

    @property
    def fwScheda(self) -> str:
        return self._data["fwScheda"]

    @property
    def relInverter(self) -> str:
        return self._data["relInverter"]

    @property
    def relManager(self) -> str:
        return self._data["relManager"]

    @property
    def relCharger(self) -> str:
        return self._data["relCharger"]

    @property
    def relBIOS(self) -> str:
        return self._data["relBIOS"]

    @property
    def charged(self) -> int:
        return int(self._data["ahCaricati"])

    @property
    def discharge(self) -> int:
        return int(self._data["ahScaricati"])

    @property
    def maxSelledPower(self) -> int:
        return self._data["pMaxVenduta"]

    @property
    def maxPannelPower(self) -> int:
        return self._data["pMaxPannelli"]

    @property
    def maxBatteryPower(self) -> int:
        return self._data["pMaxBatteria"]

    @property
    def maxBoughtPower(self) -> int:
        return self._data["pMaxComprata"]

    @property
    def selledEnergy(self) -> int:
        return self._data["eVenduta"]

    @property
    def pannelEnergy(self) -> int:
        return self._data["ePannelli"]

    @property
    def batteryEnergy(self) -> int:
        return self._data["eBatteria"]

    @property
    def boughtEnergy(self) -> int:
        return self._data["eComprata"]

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
    def gridVoltage(self) -> float:
        return self._data["gridV"]

    @property
    def gridFrequency(self) -> float:
        return self._data["gridHz"]

    @property
    def gridPower(self) -> float:
        return self._data["pGrid"]

    # "string1IIN": "0",
    # "string1VIN": "0",
    # "string2IIN": "0",
    # "string2VIN": "0",

    @property
    def temperature(self) -> float:
        return self._data["temperatura"]

    @property
    def temperature2(self) -> float:
        return self._data["temperatura2"]

    # "dataAllarme": "07/11/2022 07:11:28",
    # "DiffDate": "829",
    # "timestampScheda": "07/11/2022 11:13:13",

    @property
    def vbScheda(self) -> str:
        return self._data["vbScheda"] | None

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

    # "SoC_EV": "0",
    # "potenza_EV": "-1",
    # "stato_EV": "-1",
    # "e_ciclo_EV": "-1",
    # "num_EV": "-1",
    # "setp_EV": "-1",

    # #"kmh": null,
    # #"km": null,
    # #"perc_carica": null,
    # "paese": "IT",
    # "scena": "0",
    # "qeps": "1",
    # "allertaMeteoAuto": "0",

    @property
    def batteryCount(self) -> int:
        return self._data["numBatterie"]


class AtonStorageConnectionError(Exception):
    """Unable to start fetching data."""


class UsernameAndPasswordRequiredError(Exception):
    """Error username and password required."""


class InvalidUsernameOrPasswordError(Exception):
    """Error invalid username or password."""


class SerialNumberRequiredError(Exception):
    """Error to serial number required."""
