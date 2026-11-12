"""Serial validation through the real controller with an offline portal."""

import httpx
import pytest
from homeassistant.const import CONF_DEVICE_ID, CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.atonstorage import AtonStorageUpdateCoordinator
from custom_components.atonstorage.config_flow import FlowHandler
from custom_components.atonstorage.controller import Controller


@pytest.fixture
def portal_controller():
    """Build a controller with a successful login and configurable monitor body."""

    def make(monitor_body):
        requests = []

        def respond(request):
            requests.append(request)
            if request.url.path.endswith("index.php"):
                return httpx.Response(
                    200,
                    text="var idImpianto = 123;",
                    headers={"set-cookie": "PHPSESSID=test"},
                )
            if request.url.path.endswith("get_monitor.php"):
                return httpx.Response(200, text=monitor_body)
            return httpx.Response(200, json={})

        controller = Controller.__new__(Controller)
        controller._user = "user"
        controller._password = "password"
        controller._serial_number = "1234567890123456"
        controller._plant_id = None
        controller._opts = {}
        controller._session = None
        controller._alarm_descriptions_tried = True
        controller.monitor_data = {"serialNumber": "previous"}
        controller.energy_data = {"previous": "energy"}
        controller._async_client = httpx.AsyncClient(
            transport=httpx.MockTransport(respond)
        )
        return controller, requests

    return make


@pytest.mark.parametrize(
    ("body", "errors", "serial"),
    [
        ("null", {CONF_DEVICE_ID: "invalid_serial"}, None),
        ("{}", {CONF_DEVICE_ID: "invalid_serial"}, None),
        ('{"serialNumber": "APP123"}', {}, "APP123"),
        ("<html>Login</html>", {"base": "cannot_connect"}, None),
    ],
    ids=["null", "empty-dict", "valid", "html"],
)
async def test_validate_monitor(body, errors, serial, portal_controller, monkeypatch):
    """Missing plant data identifies the serial; persistent HTML stays a connection error."""
    controller, requests = portal_controller(body)
    monkeypatch.setattr(
        "custom_components.atonstorage.config_flow.AtonStorage",
        lambda *args: controller,
    )
    flow = FlowHandler()
    flow.hass = None

    assert await flow._async_validate(
        {
            CONF_USERNAME: "user",
            CONF_PASSWORD: "password",
            CONF_DEVICE_ID: "1234567890123456",
        }
    ) == (errors, serial)
    assert controller._async_client.is_closed
    logins = [request for request in requests if request.method == "POST"]
    assert len(logins) == (2 if body.startswith("<html>") else 1)
    if errors:
        assert controller.monitor_data == {"serialNumber": "previous"}
        assert controller.energy_data == {"previous": "energy"}


@pytest.mark.parametrize("body", ["null", "{}"])
async def test_invalid_serial_runtime_update_failed(body, portal_controller):
    """The coordinator wraps invalid serials and keeps both previous payloads."""
    controller, _ = portal_controller(body)
    coordinator = AtonStorageUpdateCoordinator.__new__(AtonStorageUpdateCoordinator)
    coordinator.bridge = controller
    coordinator.serial_number = controller._serial_number
    try:
        with pytest.raises(UpdateFailed) as raised:
            await coordinator._async_update_data()
        # Import here so the regression tests can also run against the old code.
        from custom_components.atonstorage.controller import InvalidSerialNumberError

        assert isinstance(raised.value.__cause__, InvalidSerialNumberError)
        assert controller.monitor_data == {"serialNumber": "previous"}
        assert controller.energy_data == {"previous": "energy"}
    finally:
        await controller.async_close()
