from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.entity import EntityCategory

from .custom_components.bloomin8_pull.const import DOMAIN, STATE_BATTERY, STATE_LAST_SEEN


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([Bloomin8BatterySensor(hass)], True)


class Bloomin8BatterySensor(SensorEntity):
    _attr_name = "Bloomin8 Battery"
    _attr_unique_id = "bloomin8_battery"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_icon = "mdi:battery"

    def __init__(self, hass):
        self.hass = hass

    @property
    def native_value(self):
        return self.hass.data[DOMAIN]["state"].get(STATE_BATTERY)

    @property
    def extra_state_attributes(self):
        return {
            "last_seen": self.hass.data[DOMAIN]["state"].get(STATE_LAST_SEEN),
        }

    async def async_added_to_hass(self):
        # registrieren, damit der View später pushen kann
        self.hass.data[DOMAIN]["entities"].append(self)
        self.async_write_ha_state()
