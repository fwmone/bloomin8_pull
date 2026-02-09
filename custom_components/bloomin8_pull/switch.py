from __future__ import annotations

import json
from pathlib import Path

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, STATE_BATTERY, STATE_SUCCESS, STATE_LAST_SEEN, STATE_ENABLED, STATE_FILE, DEFAULT_ENABLED, STATE_LAST_IMAGE_URL


def _write_json_sync(path: str, data: dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    async_add_entities([Bloomin8PullEnabledSwitch(hass)], True)


class Bloomin8PullEnabledSwitch(SwitchEntity):
    _attr_name = "BLOOMIN8 Pull Enabled"
    _attr_unique_id = "bloomin8_pull_enabled"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:sync"

    def __init__(self, hass):
        self.hass = hass

    @property
    def is_on(self) -> bool:
        return bool(self.hass.data[DOMAIN]["state"].get(STATE_ENABLED, DEFAULT_ENABLED))

    async def async_turn_on(self, **kwargs):
        self.hass.data[DOMAIN]["state"][STATE_ENABLED] = True
        await self._persist_state()
        self._push_update()

    async def async_turn_off(self, **kwargs):
        self.hass.data[DOMAIN]["state"][STATE_ENABLED] = False
        await self._persist_state()
        self._push_update()

    async def _persist_state(self):
        st = self.hass.data[DOMAIN]["state"]
        data = {
            STATE_BATTERY: st.get(STATE_BATTERY),
            STATE_SUCCESS: st.get(STATE_SUCCESS),
            STATE_LAST_SEEN: st.get(STATE_LAST_SEEN),
            STATE_ENABLED: st.get(STATE_ENABLED, DEFAULT_ENABLED),
            STATE_LAST_IMAGE_URL: st.get(STATE_LAST_IMAGE_URL),
        }
        await self.hass.async_add_executor_job(_write_json_sync, STATE_FILE, data)

    def _push_update(self):
        for ent in self.hass.data[DOMAIN].get("entities", []):
            ent.async_write_ha_state()
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        self.hass.data[DOMAIN]["entities"].append(self)
        self.async_write_ha_state()
