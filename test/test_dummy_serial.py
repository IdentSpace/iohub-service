import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, select

from app.api.device_routes import router
from app.db.models import Device
from app.driver.dummy_serial import DummyDataScanner
from app.state.dscanner import pop_latest_dscanner_data
from generate_demo_data import generate_dummy_scanner


class DummySerialTests(unittest.TestCase):
    def test_serial_lines_reach_parser_webhook_and_api_and_stop(self):
        delivered = threading.Event()
        queries = []

        def enqueue(config, query):
            queries.append((config, query))
            if len(queries) >= 2:
                delivered.set()

        scanner_id = str(uuid4())
        driver = DummyDataScanner({"port": "dummy://datascanner/test?interval=0.01", "id": scanner_id})
        pop_latest_dscanner_data()
        try:
            with patch("app.state.dscanner.enqueue_webhook", side_effect=enqueue):
                driver.listen_in_thread()
                first_thread = driver.thread
                driver.listen_in_thread()
                self.assertIs(driver.thread, first_thread)
                observer = DummyDataScanner({"device_host": driver.port, "id": scanner_id})
                self.assertEqual(observer.get_state().state, "online")
                self.assertTrue(delivered.wait(2), "No simulated scan events arrived")
                driver.close()
                self.assertFalse(driver.thread.is_alive())
                self.assertFalse(driver.serial.is_open)
                self.assertEqual(observer.get_state().state, "offline")
            self.assertEqual(queries[0][0], "WEBHOOK_DATASCANNER")
            self.assertIn("type=raw", queries[0][1])
            self.assertIn("type=dmgs1", queries[1][1])
            self.assertIn("scannerid=" + scanner_id, queries[1][1])
            self.assertIn("batch=DEMO-LOT-01", queries[1][1])
            app = FastAPI()
            app.include_router(router, prefix="/api/device")
            with TestClient(app) as client:
                scan = client.get("/api/device/scanner/latest").json()["data"]["scan"]
                self.assertEqual(scan["id"], scanner_id)
                self.assertEqual(client.get("/api/device/scanner/latest").json()["data"]["scan"], scan)
        finally:
            driver.close()
            pop_latest_dscanner_data()

    def test_invalid_dummy_configuration(self):
        for port in ("COM6", "dummy://other/test", "dummy://datascanner/test?interval=0", "dummy://datascanner/test?interval=nan"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                DummyDataScanner({"port": port})

    def test_dummy_seed_is_repeatable_and_selected_for_startup(self):
        from app.devices.device_manager import get_devices_serial

        with TemporaryDirectory() as directory:
            path = Path(directory) / "demo.db"
            device_id = generate_dummy_scanner(path)
            self.assertEqual(generate_dummy_scanner(path), device_id)
            engine = create_engine("sqlite:///" + path.as_posix())
            try:
                with Session(engine) as session:
                    self.assertEqual(len(session.exec(select(Device)).all()), 1)
                with patch("app.db.session.get_session", side_effect=lambda: Session(engine)):
                    devices = get_devices_serial()
                self.assertEqual(len(devices), 1)
                self.assertEqual(devices[0]["device_driver_name"], "dummy_datascanner")
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
