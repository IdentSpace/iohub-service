import unittest
from unittest.mock import Mock, patch

import requests

from app.driver.driver_factory import driver_factory
from app.driver.types.camera import Camera
from app.driver.types.camera import CameraTimeoutError
from app.driver.types.device import DeviceState


class HanwhaTests(unittest.TestCase):
    def setUp(self):
        self.driver = driver_factory("hanwha_http", args={
            "device_host": "https://camera.local", "username": "viewer",
            "password": "secret", "channel": 2,
        })
        self.response = Mock()
        self.jpeg = b"\xff\xd8image\xff\xd9"

    @patch("app.driver.hanwha.requests.get")
    def test_snapshot_uses_sunapi_digest_and_releases_response(self, get):
        get.return_value = self.response
        self.response.content = self.jpeg
        self.assertIsInstance(self.driver, Camera)
        self.assertEqual(self.driver.snapshot(), self.jpeg)
        kwargs = get.call_args.kwargs
        self.assertEqual(get.call_args.args[0], "https://camera.local/stw-cgi/video.cgi")
        self.assertEqual(kwargs["params"], {"msubmenu": "snapshot", "action": "view", "Channel": 2})
        self.assertEqual(kwargs["auth"].username, "viewer")
        self.response.close.assert_called_once()
        self.assertEqual(self.driver.get_state().state, DeviceState.ONLINE)

    @patch("app.driver.hanwha.requests.get")
    def test_stream_extracts_split_frames_and_closes_on_iterator_close(self, get):
        get.return_value = self.response
        self.response.iter_content.return_value = iter([
            b"--boundary\r\nContent-Type: image/jpeg\r\n\r\n\xff",
            b"\xd8image\xff", b"\xd9\r\n--boundary\r\n" + self.jpeg,
        ])
        frames = self.driver.stream()
        self.assertEqual(next(frames), self.jpeg)
        self.assertEqual(next(frames), self.jpeg)
        frames.close()
        self.response.close.assert_called_once()
        self.assertTrue(get.call_args.kwargs["stream"])

    @patch("app.driver.hanwha.requests.get")
    def test_close_stops_active_stream_even_after_restart(self, get):
        get.return_value = self.response
        self.response.iter_content.return_value = iter([self.jpeg, self.jpeg])
        frames = self.driver.stream()
        next(frames)
        self.driver.close()
        self.driver.start()
        self.assertEqual(list(frames), [])
        self.assertEqual(self.driver.get_state().state, DeviceState.OFFLINE)

    @patch("app.driver.hanwha.requests.get")
    def test_request_error_is_sanitized(self, get):
        get.side_effect = requests.ConnectionError("secret URL credentials")
        with self.assertRaisesRegex(RuntimeError, "^Camera request failed$"):
            self.driver.snapshot()
        self.assertEqual(self.driver.get_state().state, DeviceState.ERROR)

    @patch("app.driver.hanwha.requests.get")
    def test_request_and_stream_timeouts_remain_distinguishable(self, get):
        get.side_effect = requests.Timeout("secret")
        with self.assertRaises(CameraTimeoutError):
            self.driver.snapshot()
        get.side_effect = None
        get.return_value = self.response
        from urllib3.exceptions import ReadTimeoutError
        self.response.iter_content.side_effect = requests.ConnectionError(
            ReadTimeoutError(None, "/", "secret"))
        with self.assertRaises(CameraTimeoutError):
            next(self.driver.stream())
        self.response.close.assert_called_once()

    @patch("app.driver.hanwha.requests.get")
    def test_invalid_snapshot_is_rejected(self, get):
        get.return_value = self.response
        self.response.content = b"<html>login</html>"
        with self.assertRaises(RuntimeError):
            self.driver.snapshot()
        self.response.close.assert_called_once()
