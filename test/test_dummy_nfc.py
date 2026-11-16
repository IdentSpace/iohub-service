import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine

from app.api.device_routes import router
from app.devices.device_manager import get_devices_serial
from app.driver.dummy_serial import DummyNfcReader
from app.state.nfc import pop_latest_nfc_data
from generate_demo_data import generate_dummy_scanner


class DummyNfcTests(unittest.TestCase):
    def test_uid_events_webhook_latest_api_and_shutdown(self):
        received = threading.Event()
        events = []

        def enqueue(config, query):
            events.append((config, query))
            received.set()

        reader_id = str(uuid4())
        reader = DummyNfcReader({"port": "dummy://nfcreader/test?interval=0.01", "id": reader_id})
        observer = DummyNfcReader({"device_host": reader.port, "id": reader_id})
        pop_latest_nfc_data()
        try:
            with patch("app.state.nfc.enqueue_webhook", side_effect=enqueue):
                reader.listen_in_thread()
                self.assertEqual(observer.get_state().state, "online")
                self.assertTrue(received.wait(2))
                reader.close()
            self.assertEqual(observer.get_state().state, "offline")
            self.assertFalse(reader.thread.is_alive())
            self.assertEqual(events[0][0], "WEBHOOK_NFC")
            self.assertIn("UID=04A1B2C3D4E580", events[0][1])
            self.assertIn("device_id=" + reader_id, events[0][1])
            app = FastAPI()
            app.include_router(router, prefix="/api/device")
            with TestClient(app) as client:
                card = client.get("/api/device/nfc/latest").json()["data"]["nfc"]
                self.assertEqual(card["deviceId"], reader_id)
                self.assertIn(card["uid"], [line.decode().strip() for line in reader.samples])
                self.assertEqual(client.get("/api/device/nfc/latest").json()["data"]["nfc"], card)
        finally:
            reader.close()
            pop_latest_nfc_data()

    def test_repeatable_seed_and_startup_selection(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "demo.db"
            reader_id = generate_dummy_scanner(path, "nfcreader")
            self.assertEqual(generate_dummy_scanner(path, "nfcreader"), reader_id)
            engine = create_engine("sqlite:///" + path.as_posix())
            try:
                with patch("app.db.session.get_session", side_effect=lambda: Session(engine)):
                    devices = get_devices_serial()
                self.assertEqual(len(devices), 1)
                self.assertEqual(devices[0]["device_driver_name"], "dummy_nfcreader")
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
