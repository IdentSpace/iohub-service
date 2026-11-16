from sqlmodel import SQLModel, create_engine, Session, select
import os
import sys
from datetime import datetime, timezone

def get_db_path(filename="data.db"):
    if os.name == "nt" and getattr(sys, "frozen", False):
        app_data = os.getenv("LOCALAPPDATA", os.path.expanduser("~/AppData/Local"))
        data_dir = os.path.join(app_data, "IOHub Service")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, filename)
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), filename)
    else:
        # Normales Skript: aktueller Ordner
        return os.path.abspath(filename)

db_path = get_db_path()

# DATABASE_URL = "sqlite:///./data.db"
DATABASE_URL = f"sqlite:///{db_path}"

sync_engine  = create_engine(DATABASE_URL, echo=False, pool_size=5, max_overflow=10, connect_args={"check_same_thread": False})

def get_session():
	return Session(sync_engine )

def default_data():
	with get_session() as session:
		from app.db.models import SysValues, DeviceType, DeviceDriver, User, KeyType

		# Insert default device types
		has_sys_values = session.exec(select(SysValues)).first()
		if has_sys_values is None:
			default = [
				SysValues(name="WEBHOOK_1", value=""),
			]
			session.add_all(default)

		# Add missing catalog entries on every startup; preserve existing IDs/data.
		device_types = {
			"base": "default device type",
			"lamp": "lamp",
			"machine": "machine like in a workshop",
			"door": "doors",
			"heater": "heater",
			"datascanner": "datascanner",
			"nfcreader": "Basic NFC reader",
			"parking_barrier": "Parking Barrier",
			"camera": "Camera snapshots and streaming",
		}
		existing_types = set(session.exec(select(DeviceType.name)).all())
		session.add_all([
			DeviceType(name=name, description=description, created_at=datetime.now(timezone.utc))
			for name, description in device_types.items() if name not in existing_types
		])

		from app.driver.driver_factory import DRIVERS
		descriptions = {
			"shelly_http": "Shelly devices via HTTP",
			"default_datascanner": "Default Data Scanner 1D / 2D",
			"default_nfcreader": "Default NFC Scanner",
			"hoptschuler_890": "RFID/NFC Reader from Hopt und Schuler",
			"as1620": "Parking Barrier from Automatic Systems",
			"feig_cpr0210": "FEIG CPR0210 NFC Reader",
			"feig_cpr46": "FEIG CPR46 NFC Reader",
			"gis_tshr": "TS-HR Reader from gis-net.de ",
			"hanwha_http": "Hanwha cameras via SUNAPI HTTP",
			"local_camera": "Local USB and notebook cameras via OpenCV",
		}
		existing_drivers = set(session.exec(select(DeviceDriver.name)).all())
		session.add_all([
			DeviceDriver(name=name, description=descriptions.get(name, driver.__name__),
			             created_at=datetime.now(timezone.utc))
			for name, driver in DRIVERS.items() if name not in existing_drivers
		])

		# Insert default user
		has_users = session.exec(select(User)).first()
		if has_users is None:
			default = [
				User(username="admin", password="admin", created_at=datetime.now(timezone.utc)),
			]
			session.add_all(default)

		# Insert default key types
		has_key_type = session.exec(select(KeyType)).first()
		if has_key_type is None:
			default = [
				KeyType(name="nfc_basic", description="basic nfc id from mifare classic etc.",
				        created_at=datetime.now(timezone.utc)),
			]
			session.add_all(default)

		session.commit()

def initialize_database():
	from . import models
	SQLModel.metadata.create_all(sync_engine )
	default_data()
	# if create, insert default data here
