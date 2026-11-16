import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from app.db.models import Device, DeviceDriver, DeviceType, User
from app.db.session import initialize_database
from app.driver.driver_factory import DRIVERS


class DatabaseCatalogTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool,
                                    connect_args={"check_same_thread": False})
        self.addCleanup(self.engine.dispose)
        patcher = patch("app.db.session.sync_engine", self.engine)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_existing_database_adds_missing_catalog_without_modifying_entries(self):
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            now = datetime.now(timezone.utc)
            driver = DeviceDriver(id=42, name="shelly_http", description="Custom description", created_at=now)
            custom = DeviceDriver(id=43, name="custom_driver", description="Keep me", created_at=now)
            device_type = DeviceType(id=12, name="lamp", description="Custom lamp", created_at=now)
            device = Device(device_host="localhost", device_driver="42", device_type="12",
                            created_at=now, updated_at=now)
            session.add_all([driver, custom, device_type, device,
                             User(username="owner", password="unchanged", created_at=now)])
            session.commit()
            device_id = device.id

        initialize_database()
        with Session(self.engine) as session:
            first_ids = {row.name: row.id for row in session.exec(select(DeviceDriver)).all()}
        initialize_database()
        with Session(self.engine) as session:
            drivers = session.exec(select(DeviceDriver)).all()
            self.assertEqual({row.name: row.id for row in drivers}, first_ids)
            self.assertEqual(set(first_ids), set(DRIVERS) | {"custom_driver"})
            self.assertEqual(session.get(DeviceDriver, 42).description, "Custom description")
            self.assertEqual(session.get(DeviceDriver, 43).description, "Keep me")
            self.assertEqual(session.get(DeviceType, 12).description, "Custom lamp")
            self.assertEqual(session.get(Device, device_id).device_driver, "42")
            self.assertEqual(session.get(Device, device_id).device_type, "12")
            self.assertIn("camera", session.exec(select(DeviceType.name)).all())
            self.assertEqual(session.exec(select(User.username)).all(), ["owner"])

    def test_new_database_and_future_factory_entries(self):
        with patch.dict(DRIVERS, {"future_driver": DRIVERS["default"]}):
            initialize_database()
            with Session(self.engine) as session:
                self.assertEqual(set(session.exec(select(DeviceDriver.name)).all()), set(DRIVERS))
                self.assertIn("camera", session.exec(select(DeviceType.name)).all())
