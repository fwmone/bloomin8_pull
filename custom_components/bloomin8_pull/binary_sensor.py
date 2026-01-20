from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, STATE_SUCCESS, STATE_LAST_SEEN


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([Bloomin8LastSuccessBinarySensor(hass)], True)


class Bloomin8LastSuccessBinarySensor(BinarySensorEntity):
    _attr_name = "Bloomin8 Last Pull Success"
    _attr_unique_id = "bloomin8_last_pull_success"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:check-circle"

    def __init__(self, hass):
        self.hass = hass

    @property
    def is_on(self):
        return self.hass.data[DOMAIN]["state"].get(STATE_SUCCESS)

    @property
    def extra_state_attributes(self):
        return {
            "last_seen": self.hass.data[DOMAIN]["state"].get(STATE_LAST_SEEN),
        }

    async def async_added_to_hass(self):
        self.hass.data[DOMAIN]["entities"].append(self)
        self.async_write_ha_state()
