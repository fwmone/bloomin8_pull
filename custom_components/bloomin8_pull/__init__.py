from __future__ import annotations

import json
import os
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.util.json import load_json

from .const import (
    DOMAIN,
    CONF_IMAGE_DIR,
    CONF_PUBLISH_DIR,
    CONF_PUBLISH_WEBPATH,
    CONF_WAKE_UP_HOURS,
    CONF_ORIENTATION,
    DEFAULT_IMAGE_DIR,
    DEFAULT_PUBLISH_DIR,
    DEFAULT_PUBLISH_WEBPATH,
    DEFAULT_WAKE_UP_HOURS,
    DEFAULT_ORIENTATION,
    STATE_BATTERY,
    STATE_SUCCESS,
    STATE_LAST_SEEN,    
    STATE_FILE
)
from .view import (
    Bloomin8PullView,
    Bloomin8SignalView
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN): cv.string,
                vol.Optional(CONF_IMAGE_DIR, default=DEFAULT_IMAGE_DIR): cv.string,
                vol.Optional(CONF_PUBLISH_DIR, default=DEFAULT_PUBLISH_DIR): cv.string,
                vol.Optional(CONF_PUBLISH_WEBPATH, default=DEFAULT_PUBLISH_WEBPATH): cv.string,
                vol.Optional(CONF_WAKE_UP_HOURS, default=DEFAULT_WAKE_UP_HOURS): cv.string,
                vol.Optional(CONF_ORIENTATION, default=DEFAULT_ORIENTATION): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS = ["sensor", "binary_sensor"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    cfg = config.get(DOMAIN)
    if not cfg:
        return True

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["cfg"] = cfg
    hass.data[DOMAIN]["state"] = {
        STATE_BATTERY: None,
        STATE_SUCCESS: None,
        STATE_LAST_SEEN: None,
    }

    state = hass.data[DOMAIN]["state"]

    if os.path.isfile(STATE_FILE):
        try:
            saved = await hass.async_add_executor_job(load_json, STATE_FILE)
            state[STATE_BATTERY] = saved.get(STATE_BATTERY)
            state[STATE_SUCCESS] = saved.get(STATE_SUCCESS)
            state[STATE_LAST_SEEN] = saved.get(STATE_LAST_SEEN)
        except Exception:
            pass

    hass.data[DOMAIN]["entities"] = []  # This is where entities register so that we can push

    # register the HTTP endpoint
    hass.http.register_view(Bloomin8PullView(hass, cfg))
    hass.http.register_view(Bloomin8SignalView(hass, cfg))

    # Load platforms
    for platform in PLATFORMS:
        hass.async_create_task(async_load_platform(hass, platform, DOMAIN, {}, config))
    return True
