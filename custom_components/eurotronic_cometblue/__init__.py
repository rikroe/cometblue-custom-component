"""Comet Blue Bluetooth integration."""
import logging

from bleak.exc import BleakError
from eurotronic_cometblue_ha import AsyncCometBlue

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_PIN, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import CometBlueConfigEntry, CometBlueDataUpdateCoordinator
from .services import async_setup_services

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
]
LOGGER = logging.getLogger(__name__)


@callback
def _async_migrate_options_if_missing(hass: HomeAssistant, entry: ConfigEntry) -> None:
    data = dict(entry.data)

    changed = False

    for k in entry.data:
        if k not in {CONF_ADDRESS, CONF_PIN}:
            _ = data.pop(k, None)
            changed = True
    if CONF_PIN in entry.data and isinstance(entry.data[CONF_PIN], int):
        data[CONF_PIN] = f"{entry.data[CONF_PIN]:06d}"
        changed = True

    if changed:
        hass.config_entries.async_update_entry(entry, data=data)


async def _async_migrate_entries(
    hass: HomeAssistant, config_entry: CometBlueConfigEntry
) -> bool:
    """Migrate old entry."""
    entity_registry = er.async_get(hass)

    @callback
    def update_unique_id(entry: er.RegistryEntry) -> dict[str, str] | None:
        new_unique_id = None
        if entry.domain == "climate" and entry.unique_id.endswith("-climate"):
            new_unique_id = entry.unique_id.replace("-climate", "")
        elif entry.domain == "number" and entry.unique_id.endswith("-target_temp_low"):
            new_unique_id = entry.unique_id.replace("-target_temp_low", "-eco_setpoint")
        elif entry.domain == "number" and entry.unique_id.endswith("-target_temp_high"):
            new_unique_id = entry.unique_id.replace("-target_temp_high", "-comfort_setpoint")
        else:
            return None
        LOGGER.debug(
            "Migrating entity '%s' unique_id from '%s' to '%s'",
            entry.entity_id,
            entry.unique_id,
            new_unique_id,
        )
        if existing_entity_id := entity_registry.async_get_entity_id(
            entry.domain, entry.platform, new_unique_id
        ):
            LOGGER.debug(
                "Cannot migrate to unique_id '%s', already exists for '%s'",
                new_unique_id,
                existing_entity_id,
            )
            return None
        return {
            "new_unique_id": new_unique_id,
        }

    await er.async_migrate_entries(hass, config_entry.entry_id, update_unique_id)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: CometBlueConfigEntry) -> bool:
    """Set up Eurotronic Comet Blue from a config entry."""

    _async_migrate_options_if_missing(hass, entry)

    await _async_migrate_entries(hass, entry)

    address = entry.data[CONF_ADDRESS]

    ble_device = async_ble_device_from_address(hass, entry.data[CONF_ADDRESS])

    if not ble_device:
        raise ConfigEntryNotReady(
            f"Couldn't find a nearby device for address: {entry.data[CONF_ADDRESS]}"
        )

    cometblue_device = AsyncCometBlue(
        device=ble_device,
        pin=int(entry.data[CONF_PIN]),
    )
    try:
        async with cometblue_device:
            ble_device_info = await cometblue_device.get_device_info_async()
            try:
                # Device only returns battery level if PIN is correct
                await cometblue_device.get_battery_async()
            except TimeoutError as ex:
                # This likely means PIN was incorrect on Linux and ESPHome backends
                raise ConfigEntryError(
                    "Failed to read battery level, likely due to incorrect PIN"
                ) from ex
    except BleakError as ex:
        raise ConfigEntryNotReady(
            f"Failed to get device info from '{cometblue_device.device.address}'"
        ) from ex

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, address)},
        name=f"{ble_device_info['model']} {cometblue_device.device.address}",
        manufacturer=ble_device_info["manufacturer"],
        model=ble_device_info["model"],
        sw_version=ble_device_info["version"],
    )

    coordinator = CometBlueDataUpdateCoordinator(
        hass,
        entry,
        cometblue_device,
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Eurotronic Comet Blue integration."""
    async_setup_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
