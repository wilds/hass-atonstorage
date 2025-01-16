"""AtonStorage controller"""
import json
import logging
import re

from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client

_BASEURL = "https://www.atonstorage.com/atonTC/"
_LOGIN_ENDPOINT = _BASEURL + "index.php"
_MONITOR_ENDPOINT = _BASEURL + "get_monitor.php?sn={serial_number}"
_ENERGY_ENDPOINT = _BASEURL + "get_energy.php?idImpianto={id}&anno={year}&mese={month}&giorno={day}&intervallo=d"   #tot_pReteOut
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

_LOGGER = logging.getLogger(__name__)


class Controller:
    """Define a generic AtonStorage sensor."""

    _session = None
    data = None
    _hass: HomeAssistant = None
    _async_client = None
    _id_plant = None

    def __init__(self, hass: HomeAssistant, user, password, serial_number, opts):
        """Initialize."""

        # if user is None or password is None:
        #    raise UsernameAndPasswordRequiredError

        if serial_number is None:
            raise SerialNumberRequiredError

        self._hass = hass

        self._user = user
        self._password = password
        self._serial_number = serial_number
        # self._id_plant = serial_number    #TODO
        self._opts = opts
        self._session = None
        self._async_client = get_async_client(hass, verify_ssl=False)

    async def login(self) -> bool:
        """Login to Aton server."""

        login = await self._async_client.get(_LOGIN_ENDPOINT, timeout=60)

        login = await self._async_client.post(
            _LOGIN_ENDPOINT,
            timeout=60,
            data="username={user}&password={password}".format(
                user=self._user, password=self._password
            ),
            cookies=login.cookies,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if login.headers is not None and login.headers["Set-Cookie"] is not None:
            self._session = login.cookies
            _LOGGER.info("Logged in")

            # get plant id
            p = re.compile("var idImpianto = (.*);")
            result = p.search(login.content.decode("utf-8"))
            self._id_plant = result.group(1)
            _LOGGER.info("idImpianto=%s", self._id_plant)


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
                    serial_number=self._serial_number,
                    interval=self._opts["interval"] | 15,
                ),
                timeout=60,
                cookies=self._session,
            )
            if set_interval.content is None:
                _LOGGER.error("Unable to set refresh interval")
                raise AtonStorageConnectionError
            elif set_interval.content == "Unauthorized":
                self._session = None
                raise AtonStorageConnectionError

            monitor = await self._async_client.get(
                _MONITOR_ENDPOINT.format(serial_number=self._serial_number),
                timeout=60,
                cookies=self._session,
            )
            if monitor.content is None:
                _LOGGER.error("Unable to start fetching data")
                raise AtonStorageConnectionError
            elif monitor.content == "Unauthorized":
                self._session = None
                raise AtonStorageConnectionError

            json_dict = monitor.content
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



            # hack fix
            if self._id_plant is not None:
                energy = await self._async_client.get(
                    _ENERGY_ENDPOINT.format(id=self._id_plant, year=datetime.now().year, month=datetime.now().month, day=datetime.now().day),
                    timeout=60,
                    cookies=self._session,
                )
                if energy.content is None:
                    _LOGGER.error("Unable to start fetching data")
                    raise AtonStorageConnectionError
                elif energy.content == "Unauthorized":
                    self._session = None
                    raise AtonStorageConnectionError
                json_dict_energy = energy.content
                if json_dict_energy is not None:
                    try:
                        energy_data = json.loads(json_dict_energy)
                        _LOGGER.debug("Data fetched from resource: %s", json_dict_energy)

                        self.data["eVenduta"] = energy_data["tot_pReteOut"]

                    except ValueError:
                        _LOGGER.warning("REST result could not be parsed as JSON")
                        _LOGGER.debug("Erroneous JSON: %s", self.data)
                    except Exception as exc:
                        _LOGGER.error(exc)
                        raise exc
                else:
                    _LOGGER.warning("Empty reply found when expecting JSON data")




        except TypeError:
            _LOGGER.error("Unable to fetch data. Response: %s", self.data)
        except Exception as exc:
            _LOGGER.error(exc)
            raise exc

    def get_raw_data(self, __name: str):
        return self.data[__name]

    @property
    def grid_to_house(self) -> bool:
        return int(self.data["status"]) & 1 == 1

    @property
    def solar_to_battery(self) -> bool:
        return int(self.data["status"]) & 2 == 2

    @property
    def solar_to_grid(self) -> bool:
        return int(self.data["status"]) & 4 == 4

    @property
    def battery_to_house(self) -> bool:
        return int(self.data["status"]) & 8 == 8

    @property
    def solar_to_house(self) -> bool:
        return int(self.data["status"]) & 16 == 16

    @property
    def grid_to_battery(self) -> bool:
        return int(self.data["status"]) & 32 == 32

    @property
    def battery_to_grid(self) -> bool:
        return int(self.data["status"]) & 64 == 64

    @property
    def serial_number(self) -> str:
        return self.data["serialNumber"]

    @property
    def last_update(self) -> str:
        return self.data["data"]

    @property
    def status(self) -> str:
        return self.data["status"]

    @property
    def status_man(self) -> str:
        return self.data["statusMan"]

    @property
    def instant_solar_power(self) -> int:
        return int(self.data["pSolare"])

    @property
    def instant_user_power(self) -> int:
        return int(self.data["pUtenze"])

    @property
    def instant_user_power_real(self) -> int:
        return int(self.data["pUtenzeReal"])

    @property
    def instant_battery_power(self) -> int:
        return int(self.data["pBatteria"])

    @property
    def instant_grid_input_power(self) -> int:
        return int(self.data["pReteIn"])

    @property
    def instant_grid_output_power(self) -> int:
        return int(self.data["pReteOut"])

    @property
    def instant_grid_power(self) -> int:
        return int(self.data["pRete"])

    @property
    def instant_grid_power_real(self) -> int:
        return int(self.data["pReteReal"])

    @property
    def status_of_charge(self) -> float:
        return float(self.data["soc"])

    @property
    def run_mode(self) -> int:
        return int(self.data["runMode"])

    @property
    def string1_current(self) -> float:
        return float(self.data["string1I"])

    @property
    def string1_voltage(self) -> float:
        return float(self.data["string1V"])

    @property
    def string2_current(self) -> float:
        return float(self.data["string2I"])

    @property
    def string2_voltage(self) -> float:
        return float(self.data["string2V"])

    @property
    def user_current(self) -> float:
        return float(self.data["utenzeI"])

    @property
    def user_voltage(self) -> float:
        return float(self.data["utenzeV"])

    @property
    def battery_voltage(self) -> float:
        return float(self.data["vb"])

    @property
    def battery_current(self) -> float:
        return float(self.data["ib"])

    @property
    def fw_Scheda(self) -> str:
        return self.data["fwScheda"]

    @property
    def rel_inverter(self) -> str:
        return self.data["relInverter"]

    @property
    def rel_manager(self) -> str:
        return self.data["relManager"]

    @property
    def rel_charger(self) -> str:
        return self.data["relCharger"]

    @property
    def rel_bios(self) -> str:
        return self.data["relBIOS"]

    @property
    def charged(self) -> int:
        return int(self.data["ahCaricati"])

    @property
    def discharge(self) -> int:
        return int(self.data["ahScaricati"])

    @property
    def max_selled_power(self) -> int:
        return self.data["pMaxVenduta"]

    @property
    def max_pannel_power(self) -> int:
        return self.data["pMaxPannelli"]

    @property
    def max_battery_power(self) -> int:
        return self.data["pMaxBatteria"]

    @property
    def max_bought_power(self) -> int:
        return self.data["pMaxComprata"]

    @property
    def selled_energy(self) -> int:
        return self.data["eVenduta"]

    @property
    def pannel_energy(self) -> int:
        return self.data["ePannelli"]

    @property
    def self_consumed_energy(self) -> int:
        return self.data["eBatteria"]

    @property
    def bought_energy(self) -> int:
        return self.data["eComprata"]

    @property
    def consumed_energy(self) -> int:
        return int(self.bought_energy) + int(self.self_consumed_energy)

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
        return self.data["gridV"]

    @property
    def grid_frequency(self) -> float:
        return self.data["gridHz"]

    @property
    def grid_power(self) -> float:
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

    @property
    def update_delay(self) -> int:
        return self.data["DiffDate"]

    # "DiffDate": "829",
    # "timestampScheda": "07/11/2022 11:13:13",

    @property
    def vb_scheda(self) -> str:
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


    @property
    def ev_num(self) -> int:
        return int(self.data["num_EV"])

    @property
    def ev_status_of_charge(self) -> float:
        return float(self.data["SoC_EV"])

    @property
    def ev_status(self) -> int:
        return int(self.data["stato_EV"])   #

    #var firstNumber = (parseInt(_data.stato_EV)&0xf0)>>4;
    #var secondNumber = parseInt(_data.stato_EV)&0x0f;

    @property
    def ev_status_off(self) -> bool:
        return int(self.data["stato_EV"]) & 0xF0 >> 4 == 0 or (int(self.data["stato_EV"]) & 0xF0 >> 4 == 1 and int(self.data["stato_EV"]) & 0x0F != 3)

    @property
    def ev_status_on(self) -> bool:
        return int(self.data["stato_EV"]) & 0xF0 >> 4 == 1 and int(self.data["stato_EV"]) & 0x0F == 3

    @property
    def ev_status_charge(self) -> bool:
        return int(self.data["stato_EV"]) & 0xF0 >> 4 == 2

    @property
    def ev_status_warning(self) -> bool:
        return int(self.data["stato_EV"]) & 0xF0 >> 4 == 4 or int(self.data["stato_EV"]) & 0xF0 >> 4 == 5

    @property
    def ev_setp(self) -> float:
        return float(self.data["setp_EV"])  # in A

    @property
    def ev_power(self) -> int:
        return int(self.data["potenza_EV"]) #carica in W

    @property
    def ev_kmh(self) -> float:
        return float(self.data["kmh"])  #evCaricakmh km/h

    @property
    def ev_e_ciclo_(self) -> float:
        return float(self.data["e_ciclo_EV"])   #evScaricakWh

    @property
    def ev_km(self) -> float:
        return float(self.data["km"])  #evScaricakm km

    @property
    def ev_perc_carica(self) -> float:
        return float(self.data["perc_carica"])  #evCaricakmh %

    # "paese": "IT",
    # "scena": "0",
    # "qeps": "1",
    # "allertaMeteoAuto": "0",

    @property
    def battery_count(self) -> int:
        return self.data["numBatterie"]


class AtonStorageConnectionError(Exception):
    """Unable to start fetching data."""


class UsernameAndPasswordRequiredError(Exception):
    """Error username and password required."""


class InvalidUsernameOrPasswordError(Exception):
    """Error invalid username or password."""


class SerialNumberRequiredError(Exception):
    """Error to serial number required."""