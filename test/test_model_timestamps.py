import unittest
from datetime import timedelta
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.db.models import Device, DeviceDriver, DeviceType
from app.devices.device_manager import register_device, update_device


class ModelTimestampTests(unittest.TestCase):
    def test_device_registration_and_update_with_default_timestamps(self):
        engine = create_engine("sqlite://", poolclass=StaticPool,
                               connect_args={"check_same_thread": False})
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            device_type = DeviceType(name="camera")
            driver = DeviceDriver(name="local_camera")
            for row in (device_type, driver):
                self.assertEqual(row.created_at.utcoffset(), timedelta(0))
            session.add_all([device_type, driver])
            session.commit()
            type_id, driver_id = device_type.id, driver.id

        with patch("app.db.session.sync_engine", engine):
            device = register_device(device_host="0", device_type=str(type_id),
                                     device_driver=str(driver_id), device_name="Cam")
            self.assertEqual(device.created_at.utcoffset(), timedelta(0))
            self.assertEqual(device.updated_at.utcoffset(), timedelta(0))
            updated = update_device(str(device.id), {"name": "USB Camera"})
            self.assertEqual(updated.name, "USB Camera")
            with Session(engine) as session:
                stored = session.get(Device, device.id)
                self.assertEqual(stored.device_host, "0")
                self.assertEqual(stored.name, "USB Camera")
