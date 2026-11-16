import asyncio
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v2.devices import CameraStreamResponse, router
from app.driver.types.camera import Camera, CameraTimeoutError


class CameraApiTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router, prefix="/api/v2")
        self.client = TestClient(app)
        self.base = f"/api/v2/devices/{uuid4()}"
        self.camera = Mock(spec=Camera)
        for target, value in (
            ("get_device", {"device_driver_name": "hanwha_http"}),
            ("runtime_devices.get_driver", self.camera),
        ):
            patcher = patch("app.devices.device_manager." + target, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_snapshot(self):
        self.camera.snapshot.return_value = b"jpeg"
        response = self.client.get(self.base + "/snapshot")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"jpeg")
        self.assertEqual(response.headers["content-type"], "image/jpeg")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_multipart_and_cleanup(self):
        closed = Mock()

        def frames():
            try:
                yield b"one"
                yield b"two"
            finally:
                closed()

        self.camera.stream.return_value = frames()
        response = self.client.get(self.base + "/stream")
        self.assertEqual(response.status_code, 200)
        self.assertIn("boundary=frame", response.headers["content-type"])
        self.assertIn(b"Content-Length: 3\r\n\r\none\r\n--frame", response.content)
        self.assertTrue(response.content.endswith(b"--frame--\r\n"))
        closed.assert_called_once()

    def test_errors(self):
        for error, status in ((RuntimeError("secret"), 502), (CameraTimeoutError("secret"), 504)):
            self.camera.snapshot.side_effect = error
            response = self.client.get(self.base + "/snapshot")
            self.assertEqual(response.status_code, status)
            self.assertNotIn("secret", response.text)

            def frames():
                raise error
                yield

            self.camera.stream.return_value = frames()
            self.assertEqual(self.client.get(self.base + "/stream").status_code, status)

    def test_missing_and_non_camera(self):
        with patch("app.devices.device_manager.get_device", return_value=None):
            self.assertEqual(self.client.get(self.base + "/snapshot").status_code, 404)
        with patch("app.devices.device_manager.runtime_devices.get_driver", return_value=object()):
            self.assertEqual(self.client.get(self.base + "/stream").status_code, 409)

    def test_disconnect_closes_prefetched_iterator(self):
        closed = Mock()

        def frames():
            try:
                yield b"first"
                while True:
                    yield b"next"
            finally:
                closed()

        async def exercise():
            iterator = frames()
            response = CameraStreamResponse(iterator, next(iterator))
            sent = asyncio.Event()

            async def send(message):
                if message["type"] == "http.response.body":
                    sent.set()
                await asyncio.sleep(0)

            async def receive():
                await sent.wait()
                return {"type": "http.disconnect"}

            await response({"type": "http", "asgi": {"spec_version": "2.0"}}, receive, send)

        asyncio.run(exercise())
        closed.assert_called_once()
