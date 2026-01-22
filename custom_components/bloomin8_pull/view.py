from __future__ import annotations

import datetime as dt
import logging
import os
import random
import shutil
import json
from http import HTTPStatus
from pathlib import Path


from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from .const import DOMAIN, STATE_BATTERY, STATE_SUCCESS, STATE_LAST_SEEN, STATE_FILE

_LOGGER = logging.getLogger(__name__)

ALLOWED_EXT = (".jpg",".jpeg")

@property
def icon(self):
    return self._icon # You can use things like "mdi:calendar" etc

def _utc_iso_z(ts: dt.datetime) -> str:
    ts = ts.replace(tzinfo=dt.timezone.utc, microsecond=0)
    return ts.isoformat().replace("+00:00", "Z")


def clear_publish_dir(path: str) -> None:
    if not os.path.isdir(path):
        return

    for name in os.listdir(path):
        file_path = os.path.join(path, name)
        if os.path.isfile(file_path):
            os.remove(file_path)

def _write_json_sync(path: str, data: dict) -> None:
    """Write JSON to disk (sync). Called in executor."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)  # atomic on POSIX

def _publish_image_sync(publish_dir: str, src_path: str, dst_path: str) -> None:
    """Clear publish dir and copy the chosen image (sync). Called in executor."""
    os.makedirs(publish_dir, exist_ok=True)
    clear_publish_dir(publish_dir)
    shutil.copyfile(src_path, dst_path)

def _list_images_sync(image_dir: str, allowed_ext: tuple[str, ...]) -> list[str]:
    return [f for f in os.listdir(image_dir) if f.endswith(allowed_ext)]


class Bloomin8PullView(HomeAssistantView):
    """Implements GET /eink_pull for BLOOMIN8 devices."""

    url = "/eink_pull"
    name = "api:bloomin8_pull"
    requires_auth = False  # BLOOMIN8 uses X-Access-Token; we validate manually.

    def __init__(self, hass, cfg: dict) -> None:
        self.hass = hass
        self.cfg = cfg

    async def get(self, request: web.Request) -> web.Response:
        # --- Auth ---
        token = request.headers.get("X-Access-Token", "")
        expected = self.cfg["access_token"]
        if not expected or token != expected:
            return web.json_response(
                {"status": 401, "type": "ERROR", "message": "Unauthorized"},
                status=HTTPStatus.UNAUTHORIZED,
            )

        device_id = request.query.get("device_id")
        pull_id = request.query.get("pull_id")
        cron_time = request.query.get("cron_time")
        battery = request.query.get("battery")

        battery_val = None
        if battery is not None:
            try:
                battery_val = int(battery)
            except ValueError:
                battery_val = None
        self.hass.data[DOMAIN]["state"][STATE_BATTERY] = battery_val

        try:
            data = {
                STATE_BATTERY: self.hass.data[DOMAIN]["state"][STATE_BATTERY],
                STATE_SUCCESS: self.hass.data[DOMAIN]["state"][STATE_SUCCESS],
                STATE_LAST_SEEN: self.hass.data[DOMAIN]["state"][STATE_LAST_SEEN],
            }

            # nicht blocking im event loop
            await self.hass.async_add_executor_job(_write_json_sync, STATE_FILE, data)
        except Exception:
            pass

        # Push: alle registrierten Entities neu schreiben
        for ent in self.hass.data[DOMAIN].get("entities", []):
            ent.async_write_ha_state()

        _LOGGER.debug(
            "eink_pull request: device_id=%s pull_id=%s cron_time=%s battery=%s remote=%s",
            device_id, pull_id, cron_time, battery, request.remote
        )

        image_dir: str = self.cfg["image_dir"]
        publish_dir: str = self.cfg["publish_dir"]
        publish_webpath: str = self.cfg["publish_webpath"]
        interval_min: int = int(self.cfg["next_interval_minutes"])
        orientation: str = self.cfg["orientation"]

        # --- Choose a local image from cache ---
        try:
            files = await self.hass.async_add_executor_job(_list_images_sync, image_dir, ALLOWED_EXT)
        except FileNotFoundError:
            files = []

        if not files:
            return web.json_response(
                {
                    "status": 204,
                    "message": "No image available",
                    "data": {
                        "next_cron_time": _utc_iso_z(dt.datetime.utcnow() + dt.timedelta(minutes=interval_min))
                    }
                }                ,
                status=HTTPStatus.NO_CONTENT,
            )

        chosen = random.choice(files)
        src_path = os.path.join(image_dir, chosen)

        # --- Publish under /local/... (served from /config/www) ---
        os.makedirs(publish_dir, exist_ok=True)

        # We publish a stable filename to keep the device simple:
        # "current" + original extension, e.g. current.png
        basename, ext = os.path.splitext(chosen)
        ext = ext.lower() if ext else ".jpg"
        published_name = f"{basename}_{orientation}{ext}"
        dst_path = os.path.join(publish_dir, published_name)

        # Copy is safest across filesystems; very small overhead for e-ink cadence.
        try:
            await self.hass.async_add_executor_job(
                _publish_image_sync, publish_dir, src_path, dst_path
            )
        except Exception as err:
            _LOGGER.exception("Failed to publish image %s -> %s: %s", src_path, dst_path, err)
            return web.json_response(
                {"status": 500, "type": "ERROR", "message": "Failed to publish image"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

        # Build absolute base URL from the incoming request (works behind reverse proxy if headers are correct).
        # image_url must be absolute for BLOOMIN8.
        base = f"{request.scheme}://{request.host}"
        image_url = f"{base}{publish_webpath}/{published_name}"

        next_time = _utc_iso_z(dt.datetime.utcnow() + dt.timedelta(minutes=interval_min))

        return web.json_response(
            {
                "status": 200,
                "type": "SHOW",
                "message": "Image retrieved successfully",
                "data": {
                    "next_cron_time": next_time,
                    "image_url": image_url,
                },
            },
            status=HTTPStatus.OK,
        )

class Bloomin8SignalView(HomeAssistantView):
    """Implements GET /eink_signal for BLOOMIN8 devices."""

    url = "/eink_signal"
    name = "api:bloomin8_signal"
    requires_auth = False  # BLOOMIN8 uses X-Access-Token; we validate manually.

    def __init__(self, hass, cfg: dict) -> None:
        self.hass = hass
        self.cfg = cfg

    async def get(self, request: web.Request) -> web.Response:
        # --- Auth ---
        token = request.headers.get("X-Access-Token", "")
        expected = self.cfg["access_token"]
        if not expected or token != expected:
            return web.json_response(
                {"status": 401, "type": "ERROR", "message": "Unauthorized"},
                status=HTTPStatus.UNAUTHORIZED,
            )

        pull_id = request.query.get("pull_id")
        success = request.query.get("success")

        success_val = None
        if success is not None:
            success_val = str(success).strip() == "1"

        self.hass.data[DOMAIN]["state"][STATE_SUCCESS] = success_val
        self.hass.data[DOMAIN]["state"][STATE_LAST_SEEN] = (
            dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        )

        try:
            data = {
                STATE_BATTERY: self.hass.data[DOMAIN]["state"][STATE_BATTERY],
                STATE_SUCCESS: self.hass.data[DOMAIN]["state"][STATE_SUCCESS],
                STATE_LAST_SEEN: self.hass.data[DOMAIN]["state"][STATE_LAST_SEEN],
            }

            # nicht blocking im event loop
            await self.hass.async_add_executor_job(_write_json_sync, STATE_FILE, data)
        except Exception:
            pass

        # Push: alle registrierten Entities neu schreiben
        for ent in self.hass.data[DOMAIN].get("entities", []):
            ent.async_write_ha_state()

        _LOGGER.debug(
            "eink_signal request: pull_id=%s success=%s",
            pull_id, success, request.remote
        )

        return web.json_response(
            {
                "status": 200,
                "message": "Feedback recorded"
            },
            status=HTTPStatus.OK,
        )
