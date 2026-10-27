from app.driver.driver_factory import driver_factory
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
import logging
import os
import sys

logger = logging.getLogger("uvicorn.error")

def get_db_path(filename="data.db"):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(os.path.dirname(sys.executable), filename)
    else:
        return os.path.abspath(filename)

db_path = get_db_path()

DATABASE_ASYNC_URL = f"sqlite+aiosqlite:///{db_path}"
async_engine = create_async_engine(DATABASE_ASYNC_URL, echo=False)

async_session_maker = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

def get_async_session() -> AsyncSession:
    return async_session_maker()


running_driver_threads = []

async def start_threading():
	async with get_async_session() as session:
		try:
			from app.devices.device_manager import get_devices_serial
			devices = get_devices_serial()
			logger.info(f"Found {len(devices)} serial devices configs from DB")

			for device in devices:
				try:
					logger.info("Starting driver %s (%s) on %s using %s", device['name'], device['device_type'], device['device_host'], device['device_driver_name'])
					driver = driver_factory(driver_type=device["device_driver_name"], args={'port': device["device_host"], 'baudrate': device["baudrate"], 'id': device["id"]})
					driver.listen_in_thread()
					running_driver_threads.append(driver)
				except Exception:
					logger.exception("Could not start driver for %s", device.get("name"))
		except Exception:
			logger.exception("Could not load serial device configurations")

def stop_threading():
	for driver in running_driver_threads:
		try:
			driver.close()
		except Exception:
			logger.exception("Error stopping driver %s", getattr(driver, "name", type(driver).__name__))
	running_driver_threads.clear()

def restart_threads():
	stop_threading()
