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

from collections import deque
from homeassistant.helpers.storage import Store

from datetime import datetime, timedelta
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STATE_BATTERY, STATE_SUCCESS, STATE_LAST_SEEN, STATE_FILE

def calc_recent_max(n_files: int) -> int:
    # 50% of files, minimum 5, maximum 50
    return max(5, min(50, int(round(n_files * 0.5))))

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

def parse_wake_up_hours(raw: str | list[int] | None) -> list[int]:
    if raw is None:
        return []
    if isinstance(raw, list):
        hours = raw
    else:
        parts = [p.strip() for p in str(raw).split(",") if p.strip()]
        hours = [int(p) for p in parts]
    for h in hours:
        if h < 0 or h > 23:
            raise ValueError(f"wake_up_hours hour out of range: {h}")
    return sorted(set(hours))

def next_wake_time_local(hours: list[int], now_local=None):
    if now_local is None:
        now_local = dt_util.now()

    today = now_local.date()
    candidates = [
        dt_util.as_local(datetime(today.year, today.month, today.day, h, 0, 0))
        for h in hours
    ]
    candidates = sorted(candidates)

    for c in candidates:
        if c > now_local:
            return c

    tomorrow = today + timedelta(days=1)
    first = dt_util.as_local(datetime(tomorrow.year, tomorrow.month, tomorrow.day, hours[0], 0, 0))
    return first

def next_wake_time_local_windowed(
    hours: list[int],
    now_local: datetime | None = None,
    drift_window: timedelta = timedelta(minutes=30),
) -> datetime:
    """Return next scheduled local time.
    If we're within `drift_window` BEFORE the next slot, skip that slot and return the following one.
    """
    if not hours:
        raise ValueError("No wake_up_hours configured")

    if now_local is None:
        now_local = dt_util.now()

    first = next_wake_time_local(hours, now_local=now_local)

    # If the device calls shortly before the next slot (drift), don't schedule that same slot again.
    delta = first - now_local
    if timedelta(0) < delta <= drift_window:
        # Next slot after `first`
        return next_wake_time_local(hours, now_local=first + timedelta(seconds=1))

    return first

async def choose_varied(hass, files: list[str], store_key: str = "recent_images") -> str:
    RECENT_MAX = calc_recent_max(len(files))

    store = Store(hass, 1, f"bloomin8_pull_{store_key}")

    data = await store.async_load() or {}
    recent = deque(data.get("recent", []), maxlen=RECENT_MAX)

    # Remove files from recent (dynamic image selection)
    files_set = set(files)
    recent = deque([f for f in recent if f in files_set], maxlen=RECENT_MAX)

    # Candidates: anything that is not “recent”
    recent_set = set(recent)
    candidates = [f for f in files if f not in recent_set]

    # Fallback: if everything is in recent, take from all again
    chosen = random.choice(candidates or files)

    # update recent
    recent.append(chosen)
    await store.async_save({"recent": list(recent)})

    return chosen


_LOGGER = logging.getLogger(__name__)
ALLOWED_EXT = (".jpg",)


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

            # don't block the event loop
            await self.hass.async_add_executor_job(_write_json_sync, STATE_FILE, data)
        except Exception:
            pass

        # Push: rewrite all registered entities
        for ent in self.hass.data[DOMAIN].get("entities", []):
            ent.async_write_ha_state()

        _LOGGER.debug(
            "eink_pull request: device_id=%s pull_id=%s cron_time=%s battery=%s remote=%s",
            device_id, pull_id, cron_time, battery, request.remote
        )

        image_dir: str = self.cfg["image_dir"]
        publish_dir: str = self.cfg["publish_dir"]
        publish_webpath: str = self.cfg["publish_webpath"]

        hours = parse_wake_up_hours(self.cfg["wake_up_hours"])
        now_local = dt_util.now()
        next_local = next_wake_time_local_windowed(
            hours,
            now_local=now_local,
            drift_window=timedelta(minutes=30),
        )
        next_utc = dt_util.as_utc(next_local)

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
                        "next_cron_time": next_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
                    }
                }                ,
                status=HTTPStatus.NO_CONTENT,
            )

        chosen = await choose_varied(self.hass, files)
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

        return web.json_response(
            {
                "status": 200,
                "type": "SHOW",
                "message": "Image retrieved successfully",
                "data": {
                    "next_cron_time": next_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
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

            # don't block the event loop
            await self.hass.async_add_executor_job(_write_json_sync, STATE_FILE, data)
        except Exception:
            pass

        # Push: rewrite all registered entities
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
