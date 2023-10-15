"""Provides the DataUpdateCoordinator."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from bleak import BleakError
from cometblue import AsyncCometBlue

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

SCAN_INTERVAL = timedelta(minutes=5)
LOGGER = logging.getLogger(__name__)


class DeviceUnavailable(HomeAssistantError):
    """Raised if device can't be found."""


class CometBlueDataUpdateCoordinator(DataUpdateCoordinator[dict[str, bytes]]):
    """Class to manage fetching data."""

    def __init__(
        self,
        hass: HomeAssistant,
        cometblue: AsyncCometBlue,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize global data updater."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"Comet Blue {cometblue.client.address}",
            update_interval=SCAN_INTERVAL,
        )
        self.device: AsyncCometBlue = cometblue
        self.address = cometblue.client.address
        self.data: dict[str, Any] = {}
        self.device_info = device_info

    async def send_command(
        self, function: str, payload: dict[str, Any], caller_entity_id: str
    ) -> dict[str, Any] | None:
        """Send command to device."""

        LOGGER.debug("Updating device with '%s' from '%s'", caller_entity_id, payload)
        try:
            async with self.device:
                if not self.device.connected:
                    raise ConfigEntryNotReady(
                        f"Failed to connect to '{self.device.device.address}'"
                    )
                return await getattr(self.device, function)(**payload)
        except ValueError as err:
            raise HomeAssistantError(
                f"Invalid payload '{payload}' for '{caller_entity_id}': {err}"
            ) from err
        except BleakError as err:
            raise HomeAssistantError(
                f"Error sending command '{payload}' to '{caller_entity_id}': {err}"
            ) from err

    async def _async_update_data(self) -> dict[str, bytes]:
        """Poll the device."""
        data: dict = {}

        try:
            async with self.device:
                if not self.device.connected:
                    raise ConfigEntryNotReady(
                        f"Failed to connect to '{self.device.device.address}'"
                    )
                data = {
                    "battery": await self.device.get_battery_async(),
                    # "schedule": await self.device.get_weekday_async(),
                    "datetime": await self.device.get_datetime_async(),
                    # "holiday": await self.device.get_holiday_async(),
                    **await self.device.get_temperature_async(),
                }
        except Exception as ex:
            raise UpdateFailed(f"Unable to update data for due to {ex}") from ex
        LOGGER.debug("Received data: %s", data)
        return data


class CometBlueBluetoothEntity(CoordinatorEntity[CometBlueDataUpdateCoordinator]):
    """Coordinator entity for Gardena Bluetooth."""

    coordinator: CometBlueDataUpdateCoordinator
    _attr_has_entity_name = True

    def __init__(self, coordinator: CometBlueDataUpdateCoordinator) -> None:
        """Initialize coordinator entity."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.last_update_success
            and bluetooth.async_address_present(
                self.hass, self.coordinator.address, True
            )
            and self._attr_available
        )

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
