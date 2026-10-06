"""Bluetti BT selects."""

from __future__ import annotations
import asyncio
from dataclasses import replace
import logging
import voluptuous as vol
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from bluetti_bt_lib import (
    build_device,
    BluettiDevice,
    FieldName,
)
from bluetti_bt_lib.enums import TimeSlotMode
from bluetti_bt_lib.fields import SelectField, TimeSlot, TimeSlotField

from .types import FullDeviceConfig, get_category
from . import device_info as dev_info, get_unique_id
from .const import DATA_COORDINATOR, DATA_LOCK, DOMAIN
from .coordinator import PollingCoordinator
from .utils import mac_loggable, unique_id_logable
from .time_slots import async_write_time_slot, current_slot
from .write import async_write_field

SERVICE_SET_TIME_SLOT = "set_time_slot"


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup select entities."""

    config = FullDeviceConfig.from_dict(entry.data)
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    lock = hass.data[DOMAIN][entry.entry_id][DATA_LOCK]

    logger = logging.getLogger(
        f"{__name__}.{mac_loggable(config.address).replace(':', '_')}"
    )

    if config is None or not isinstance(coordinator, PollingCoordinator):
        logger.error("No coordinator found")
        return None

    # Generate device info
    logger.info("Creating selects for device with address %s", config.address)
    device_info = dev_info(entry)

    # Add switches
    bluetti_device = build_device(config.name)

    switches_to_add = []
    switch_fields = bluetti_device.get_select_fields()
    for field in switch_fields:
        category = get_category(FieldName(field.name))

        switches_to_add.append(
            BluettiSelect(
                bluetti_device,
                config.address,
                coordinator,
                device_info,
                field,
                lock,
                config.use_encryption,
                category=category,
                logger=logger,
            )
        )

    for field in bluetti_device.get_time_slot_fields():
        switches_to_add.append(
            BluettiTimeSlotSelect(
                bluetti_device,
                config.address,
                coordinator,
                device_info,
                field,
                lock,
                config.use_encryption,
                logger=logger,
            )
        )

    async_add_entities(switches_to_add)

    # Set mode, start and end of a time slot in one write
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_SET_TIME_SLOT,
        {
            vol.Required("mode"): vol.In([m.name.lower() for m in TimeSlotMode]),
            vol.Required("start"): cv.time,
            vol.Required("end"): cv.time,
        },
        "async_set_time_slot",
    )


class BluettiSelect(CoordinatorEntity, SelectEntity):
    """Bluetti universal switch."""

    def __init__(
        self,
        bluetti_device: BluettiDevice,
        address: str,
        coordinator: PollingCoordinator,
        device_info: DeviceInfo,
        field: SelectField | TimeSlotField,
        lock: asyncio.Lock,
        use_encryption: bool = False,
        category: EntityCategory | None = None,
        logger: logging.Logger = logging.getLogger(),
    ):
        """Init entity."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._logger = logger

        e_name = f"{device_info.get('name')} {field.name}"
        self._bluetti_device = bluetti_device
        self._address = address
        self._use_encryption = use_encryption
        self._field = field
        self._response_key = field.name
        self._unavailable_counter = 5
        self._lock = lock
        self._attr_options = [e.name.lower() for e in self._enum()]

        self._attr_has_entity_name = True
        self._attr_device_info = device_info
        self._attr_translation_key = field.name
        self._attr_available = False
        self._attr_unique_id = get_unique_id(e_name)
        self._attr_entity_category = category

    def _enum(self):
        """Enum behind the options."""
        return self._field.e

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._attr_available

    def _set_available(self):
        """Set switch as available."""
        self._attr_available = True
        self._unavailable_counter = 0
        self._attr_extra_state_attributes = {}
        self.async_write_ha_state()

    def _set_unavailable(self, cause: str = "Unknown"):
        """Set switch as unavailable."""
        self._unavailable_counter += 1

        self._attr_extra_state_attributes = {
            "unavailable_counter": self._unavailable_counter,
            "unavailable_cause": cause,
        }

        if self._unavailable_counter >= 5:
            self._attr_available = False

        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        if self.coordinator.data is None:
            self._logger.debug(
                "Data from coordinator is None",
            )
            self._set_unavailable("Data is None")
            return

        self._logger.debug(
            "Updating state of %s", unique_id_logable(self._attr_unique_id)
        )
        if not isinstance(self.coordinator.data, dict):
            self._logger.debug(
                "Invalid data from coordinator (select.%s)",
                unique_id_logable(self._attr_unique_id),
            )
            self._set_unavailable("Invalid data")
            return

        response_data = self.coordinator.data.get(self._response_key)
        if response_data is None:
            self._set_unavailable("No data")
            return

        if not isinstance(response_data, self._field.e):
            self._logger.warning(
                "Invalid response data type from coordinator (select.%s): %s",
                unique_id_logable(self._attr_unique_id),
                response_data,
            )
            self._set_unavailable("Invalid data type")
            return

        self._set_available()
        self.current_option = response_data.name.lower()
        self.async_write_ha_state()

    async def async_select_option(self, option: str):
        """Set the entity to value."""
        self._logger.debug(
            "Set %s on %s to %s",
            self._response_key,
            mac_loggable(self._address),
            option,
        )
        await self.write_to_device(option)

    async def write_to_device(self, state: str):
        """Write to device and confirm by reading it back."""
        await async_write_field(
            self.coordinator,
            self._bluetti_device,
            self._address,
            self._use_encryption,
            self._lock,
            self._field,
            state.upper(),
            self._field.e[state.upper()],
            self._logger,
        )

    async def async_set_time_slot(self, mode: str, start, end):
        """Only time slot selects support this service."""
        raise HomeAssistantError(f"{self.entity_id} is not a time slot")


class BluettiTimeSlotSelect(BluettiSelect):
    """Mode of a time slot (off, charge, discharge, standby)."""

    def _enum(self):
        return TimeSlotMode

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        data = self.coordinator.data
        slot = data.get(self._response_key) if isinstance(data, dict) else None
        if not isinstance(slot, TimeSlot):
            self._set_unavailable("No data")
            return

        self._set_available()
        self.current_option = slot.mode.name.lower()
        self._attr_extra_state_attributes = {"start": slot.start, "end": slot.end}
        self.async_write_ha_state()

    async def async_select_option(self, option: str):
        """Change the mode, keep the times."""
        slot = current_slot(self.coordinator, self._field)
        await self._write_slot(replace(slot, mode=TimeSlotMode[option.upper()]))

    async def async_set_time_slot(self, mode: str, start, end):
        """Set mode, start and end in one write."""
        await self._write_slot(
            TimeSlot(
                TimeSlotMode[mode.upper()],
                start.strftime("%H:%M"),
                end.strftime("%H:%M"),
            )
        )

    async def _write_slot(self, slot: TimeSlot):
        self._logger.debug(
            "Set %s on %s to %s", self._response_key, mac_loggable(self._address), slot
        )
        await async_write_time_slot(
            self.coordinator,
            self._bluetti_device,
            self._address,
            self._use_encryption,
            self._lock,
            self._field,
            slot,
            self._logger,
        )
