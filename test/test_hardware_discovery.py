import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v2.hardware import router
from app.devices.discovery import camera_devices, serial_devices


class HardwareDiscoveryTests(unittest.TestCase):
    def test_serial_port_metadata_without_opening_port(self):
        port = SimpleNamespace(device="COM3", description="USB Serial", manufacturer="Maker",
                               serial_number="123", vid=10, pid=20)
        with patch("app.devices.discovery.list_ports.comports", return_value=[port]):
            self.assertEqual(serial_devices()[0]["host"], "COM3")
            self.assertEqual(serial_devices()[0]["vid"], 10)

    def test_missing_opencv_is_explicit(self):
        with patch("app.devices.discovery.importlib.util.find_spec", return_value=None):
            result = camera_devices()
        self.assertFalse(result["available"])
        self.assertIn("requirements-camera.txt", result["message"])

    def test_probe_results_and_timeout(self):
        with patch("app.devices.discovery.importlib.util.find_spec", return_value=True), patch(
            "app.devices.discovery.sys.platform", "win32"), patch(
            "app.devices.discovery.subprocess.run", side_effect=[
                Mock(returncode=0, stdout="IOHUB_PROBE=true\n"),
                subprocess.TimeoutExpired("probe", 3),
                Mock(returncode=0, stdout="IOHUB_PROBE=false\n"),
            ]) as run:
            result = camera_devices(2)
        self.assertEqual([item["host"] for item in result["items"]], ["0"])
        self.assertEqual(result["issues"][0]["reason"], "probe_timeout")
        self.assertEqual(run.call_count, 3)
        self.assertEqual(run.call_args.kwargs["timeout"], 3)

    def test_api_and_index_validation(self):
        app = FastAPI()
        app.include_router(router, prefix="/api/v2")
        client = TestClient(app)
        with patch("app.devices.discovery.serial_devices", return_value=[]):
            self.assertEqual(client.get("/api/v2/hardware/serial").json(), {"items": []})
        with patch("app.devices.discovery.camera_devices", return_value={
            "available": False, "items": [], "issues": [], "message": "missing opencv"
        }) as discover:
            self.assertEqual(client.get("/api/v2/hardware/cameras").status_code, 200)
            discover.assert_called_once_with(4)
            self.assertEqual(client.get("/api/v2/hardware/cameras?max_index=99").status_code, 422)
