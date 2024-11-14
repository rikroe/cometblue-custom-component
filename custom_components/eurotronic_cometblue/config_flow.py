"""Config flow for CometBlue."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cometblue.const import SERVICE
import voluptuous as vol

from homeassistant.components.bluetooth import async_discovered_service_info
from homeassistant.components.bluetooth.models import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_NAME, CONF_PIN, CONF_TIMEOUT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig

from .const import (
    CONF_DEVICE_NAME,
    CONF_RETRY_COUNT,
    DEFAULT_RETRY_COUNT,
    DEFAULT_TIMEOUT_SECONDS,
    DOMAIN,
)


DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PIN): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=99999999)
        ),
        vol.Optional(CONF_DEVICE_NAME): str,
        vol.Optional(CONF_TIMEOUT): NumberSelector(
            NumberSelectorConfig(min=10, max=60, step=5)
        ),
        vol.Optional(CONF_RETRY_COUNT): NumberSelector(
            NumberSelectorConfig(min=1, max=5, step=1)
        ),
    }
)


def name_from_discovery(discovery: BluetoothServiceInfoBleak | None) -> str:
    """Get the name from a discovery."""
    if discovery is None:
        raise ValueError("Discovery info not set")
    if discovery.name == str(discovery.address):
        return discovery.address
    return f"{discovery.name} {discovery.address}"


class CometBlueConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CometBlue."""

    VERSION = 1

    _existing_entry_data: Mapping[str, Any] | None = None

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device: str | None = None
        self._discovered_devices: list[str] = []

    def _create_entry(self, pin: int, device_name: str | None = None) -> FlowResult:
        """Create an entry for a discovered device."""

        if self._discovery_info is None or self._discovery_info.address is None:
            raise ValueError("Discovery info not set")

        return self.async_create_entry(
            title=name_from_discovery(self._discovery_info),
            data={
                CONF_ADDRESS: self._discovery_info.address,
                CONF_PIN: pin,
                CONF_DEVICE_NAME: device_name,
            },
            options={
                CONF_TIMEOUT: DEFAULT_TIMEOUT_SECONDS,
                CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT,
            },
        )

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user-confirmation of discovered device."""

        if user_input is not None:
            return self._create_entry(
                user_input[CONF_PIN], user_input.get(CONF_DEVICE_NAME)
            )

        try:
            device_name = name_from_discovery(self._discovery_info)
        except ValueError:
            device_name = None

        schema = self.add_suggested_values_to_schema(
            DATA_SCHEMA,
            {
                CONF_PIN: 0,
                CONF_DEVICE_NAME: device_name,
                CONF_TIMEOUT: DEFAULT_TIMEOUT_SECONDS,
                CONF_RETRY_COUNT: DEFAULT_RETRY_COUNT,
            }
            | self._existing_entry_data,
        )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                CONF_NAME: device_name,
            },
            data_schema=schema,
        )

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle a flow initialized by Bluetooth discovery."""
        self._discovery_info = discovery_info
        self._discovery_info.address = discovery_info.address

        await self.async_set_unique_id(format_mac(discovery_info.address))
        self._abort_if_unique_id_configured(
            updates={CONF_ADDRESS: discovery_info.address}
        )

        self.context["title_placeholders"] = {
            "name": name_from_discovery(self._discovery_info)
        }
        return await self.async_step_bluetooth_confirm()

    async def async_step_pick_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the step to pick discovered device."""

        if user_input is not None:
            address = user_input[CONF_ADDRESS]

            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            return self._create_entry(address)

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(
            self.hass, connectable=True
        ):
            if SERVICE in discovery_info.service_uuids:
                address = discovery_info.address
                if (
                    address not in current_addresses
                    and address not in self._discovered_devices
                ):
                    self._discovered_devices.append(address)

        addresses = {
            address
            for address in self._discovered_devices
            if address not in current_addresses
        }

        # Check if there is at least one device
        if not addresses:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="pick_device",
            data_schema=vol.Schema({vol.Required(CONF_ADDRESS): vol.In(addresses)}),
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""

        return await self.async_step_pick_device()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a reconfiguration flow initialized by the user."""
        self._existing_entry_data = self._get_reconfigure_entry().data
        return await self.async_step_bluetooth_confirm()
