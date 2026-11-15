"""Compatibility entry points for application lifecycle and restart routes."""
import logging
from app.devices.device_manager import runtime_devices, get_devices_serial

logger = logging.getLogger(__name__)


async def start_threading():
    for config in get_devices_serial():
        try:
            runtime_devices.get_driver(config)
        except Exception:
            logger.exception("Could not start driver for %s", config.get("name"))


def stop_threading():
    runtime_devices.close_all()


def restart_threads():
    stop_threading()
