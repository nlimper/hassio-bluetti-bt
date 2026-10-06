"""Bluetti BT numbers."""

from __future__ import annotations
import asyncio
import logging
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from bluetti_bt_lib import (
    build_device,
    BluettiDevice,
    FieldName,
    get_unit,
)
from bluetti_bt_lib.fields import NumberField

from .types import FullDeviceConfig, get_category
from . import device_info as dev_info, get_unique_id
from .const import DATA_COORDINATOR, DATA_LOCK, DOMAIN
from .coordinator import PollingCoordinator
from .utils import mac_loggable, unique_id_logable
from .write import async_write_field


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Setup number entities."""

    config = FullDeviceConfig.from_dict(entry.data)
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    lock = hass.data[DOMAIN][entry.entry_id][DATA_LOCK]

    logger = logging.getLogger(
        f"{__name__}.{mac_loggable(config.address).replace(':', '_')}"
    )

    if config is None or not isinstance(coordinator, PollingCoordinator):
        logger.error("No coordinator found")
        return None

    logger.info("Creating numbers for device with address %s", config.address)
    device_info = dev_info(entry)

    bluetti_device = build_device(config.name)

    numbers_to_add = []
    for field in bluetti_device.get_number_fields():
        numbers_to_add.append(
            BluettiNumber(
                bluetti_device,
                config.address,
                coordinator,
                device_info,
                field,
                lock,
                config.use_encryption,
                category=get_category(FieldName(field.name)),
                logger=logger,
            )
        )

    async_add_entities(numbers_to_add)


class BluettiNumber(CoordinatorEntity, NumberEntity):
    """Bluetti universal number."""

    def __init__(
        self,
        bluetti_device: BluettiDevice,
        address: str,
        coordinator: PollingCoordinator,
        device_info: DeviceInfo,
        field: NumberField,
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

        self._attr_has_entity_name = True
        self._attr_device_info = device_info
        self._attr_translation_key = field.name
        self._attr_available = False
        self._attr_unique_id = get_unique_id(e_name)
        self._attr_entity_category = category
        self._attr_native_min_value = field.min
        self._attr_native_max_value = field.max
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = get_unit(FieldName(field.name))
        self._attr_mode = NumberMode.BOX

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._attr_available

    def _set_available(self):
        """Set number as available."""
        self._attr_available = True
        self._unavailable_counter = 0
        self._attr_extra_state_attributes = {}
        self.async_write_ha_state()

    def _set_unavailable(self, cause: str = "Unknown"):
        """Set number as unavailable."""
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

        if not isinstance(self.coordinator.data, dict):
            self._set_unavailable("Invalid data")
            return

        response_data = self.coordinator.data.get(self._response_key)
        if not isinstance(response_data, int) or isinstance(response_data, bool):
            self._logger.debug(
                "No valid data for number.%s: %s",
                unique_id_logable(self._attr_unique_id),
                response_data,
            )
            self._set_unavailable("No data")
            return

        self._set_available()
        self._attr_native_value = response_data
        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        """Set the value on the device."""
        if value != int(value):
            raise HomeAssistantError(f"{self._field.name} takes whole numbers only")
        target = int(value)

        data = self.coordinator.data if isinstance(self.coordinator.data, dict) else {}
        below = data.get(self._field.must_be_below) if self._field.must_be_below else None
        above = data.get(self._field.must_be_above) if self._field.must_be_above else None
        if isinstance(below, int) and target >= below:
            raise HomeAssistantError(
                f"{self._field.name} must stay below {self._field.must_be_below} ({below})"
            )
        if isinstance(above, int) and target <= above:
            raise HomeAssistantError(
                f"{self._field.name} must stay above {self._field.must_be_above} ({above})"
            )

        self._logger.debug(
            "Set %s on %s to %s", self._response_key, mac_loggable(self._address), target
        )
        await async_write_field(
            self.coordinator,
            self._bluetti_device,
            self._address,
            self._use_encryption,
            self._lock,
            self._field,
            target,
            target,
            self._logger,
        )
