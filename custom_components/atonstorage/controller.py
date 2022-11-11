"""AtonStorage controller"""
import json
import logging

from homeassistant.components.rest.data import RestData
from homeassistant.core import HomeAssistant

_BASEURL = "https://www.atonstorage.com/atonTC/"
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

    data = None

    def __init__(self, hass: HomeAssistant, serialNumber, opts):
        """Initialize."""

        if serialNumber is None:
            raise SerialNumberRequiredError

        self._serialNumber = serialNumber
        self._opts = opts

        self._monitor = RestData(
            hass,
            "GET",
            _MONITOR_ENDPOINT.format(serialNumber=serialNumber),
            None,
            {},
            None,
            None,
            False,
            60,
        )

        self._set_interval = RestData(
            hass,
            "GET",
            _SET_REQUEST_ENDPOINT.format(
                serialNumber=serialNumber, interval=opts["interval"] | 15
            ),
            None,
            {},
            None,
            None,
            False,
            60,
        )

    async def refresh(self) -> None:
        try:
            await self._set_interval.async_update()  # set refresh interval
            if self._set_interval.data is None:
                _LOGGER.error("Unable to set refresh interval")
                raise AtonStorageConnectionError

            await self._monitor.async_update()

            if self._monitor.data is None:
                _LOGGER.error("Unable to start fetching data")
                raise AtonStorageConnectionError

            json_dict = self._monitor.data
            if json_dict is not None:
                try:
                    self.data = json.loads(json_dict)
                    _LOGGER.debug("Data fetched from resource: %s", json_dict)
                except ValueError:
                    _LOGGER.warning("REST result could not be parsed as JSON")
                    _LOGGER.debug("Erroneous JSON: %s", self.data)
                except Exception as exc:
                    _LOGGER.error(exc)
                    raise exc
            else:
                _LOGGER.warning("Empty reply found when expecting JSON data")
        except TypeError:
            _LOGGER.error("Unable to fetch data. Response: %s", self.rest.data)
        except Exception as exc:
            _LOGGER.error(exc)
            raise exc

    def getRawData(self, __name: str):
        return self.data[__name]

    @property
    def serialNumber(self) -> str:
        return self.data["serialNumber"]

    @property
    def currentDate(self) -> str:
        return self.data["data"]

    @property
    def status(self) -> str:
        return self.data["status"]

    @property
    def statusMan(self) -> str:
        return self.data["statusMan"]

    @property
    def instantSolarPower(self) -> int:
        return int(self.data["pSolare"])

    @property
    def instantUserPower(self) -> int:
        return int(self.data["pUtenze"])

    @property
    def instantUserPowerReal(self) -> int:
        return int(self.data["pUtenzeReal"])

    @property
    def instantBatteryPower(self) -> int:
        return int(self.data["pBatteria"])

    @property
    def instantGridInputPower(self) -> int:
        return int(self.data["pReteIn"])

    @property
    def instantGridOutputPower(self) -> int:
        return int(self.data["pReteOut"])

    @property
    def instantGridPower(self) -> int:
        return int(self.data["pRete"])

    @property
    def instantGridPowerReal(self) -> int:
        return int(self.data["pReteReal"])

    @property
    def statusOfCharge(self) -> int:
        return int(self.data["soc"])

    @property
    def runMode(self) -> int:
        return int(self.data["runMode"])

    @property
    def string1Current(self) -> float:
        return float(self.data["string1I"])

    @property
    def string1Voltage(self) -> float:
        return float(self.data["string1V"])

    @property
    def string2Current(self) -> float:
        return float(self.data["string2I"])

    @property
    def string2Voltage(self) -> float:
        return float(self.data["string2V"])

    @property
    def userCurrent(self) -> float:
        return float(self.data["utenzeI"])

    @property
    def userVoltage(self) -> float:
        return float(self.data["utenzeV"])

    @property
    def batteryVoltage(self) -> float:
        return float(self.data["vb"])

    @property
    def batteryCurrent(self) -> float:
        return float(self.data["ib"])

    @property
    def fwScheda(self) -> str:
        return self.data["fwScheda"]

    @property
    def relInverter(self) -> str:
        return self.data["relInverter"]

    @property
    def relManager(self) -> str:
        return self.data["relManager"]

    @property
    def relCharger(self) -> str:
        return self.data["relCharger"]

    @property
    def relBIOS(self) -> str:
        return self.data["relBIOS"]

    @property
    def charged(self) -> int:
        return int(self.data["ahCaricati"])

    @property
    def discharge(self) -> int:
        return int(self.data["ahScaricati"])

    @property
    def maxSelledPower(self) -> int:
        return self.data["pMaxVenduta"]

    @property
    def maxPannelPower(self) -> int:
        return self.data["pMaxPannelli"]

    @property
    def maxBatteryPower(self) -> int:
        return self.data["pMaxBatteria"]

    @property
    def maxBoughtPower(self) -> int:
        return self.data["pMaxComprata"]

    @property
    def selledEnergy(self) -> int:
        return self.data["eVenduta"]

    @property
    def oannelEnergy(self) -> int:
        return self.data["ePannelli"]

    @property
    def batteryEnergy(self) -> int:
        return self.data["eBatteria"]

    @property
    def boughtEnergy(self) -> int:
        return self.data["eComprata"]

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
        return self.data["gridV"]

    @property
    def gridFrequency(self) -> float:
        return self.data["gridHz"]

    @property
    def gridPower(self) -> float:
        return self.data["pGrid"]

    # "string1IIN": "0",
    # "string1VIN": "0",
    # "string2IIN": "0",
    # "string2VIN": "0",

    @property
    def temperature(self) -> float:
        return self.data["temperatura"]

    @property
    def temperature2(self) -> float:
        return self.data["temperatura2"]

    # "dataAllarme": "07/11/2022 07:11:28",
    # "DiffDate": "829",
    # "timestampScheda": "07/11/2022 11:13:13",

    @property
    def vbScheda(self) -> str:
        return self.data["vbScheda"] | None

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
        return self.data["numBatterie"]


class AtonStorageConnectionError(Exception):
    """Unable to start fetching data."""


class SerialNumberRequiredError(Exception):
    """Error to serial number address required."""
