import unittest
from threading import Event, Thread
from unittest.mock import Mock, patch

from app.driver.driver_factory import driver_factory
from app.driver.types.camera import CameraTimeoutError
from app.driver.types.device import DeviceState


class LocalCameraTests(unittest.TestCase):
    def setUp(self):
        self.cv2 = Mock()
        self.capture = self.cv2.VideoCapture.return_value
        self.capture.isOpened.return_value = True
        self.capture.read.return_value = (True, object())
        self.cv2.imencode.return_value = (True, Mock(tobytes=Mock(return_value=b"jpeg")))
        patcher = patch.dict("sys.modules", {"cv2": self.cv2})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.camera = driver_factory("local_camera", args={"device_host": "0", "fps": 60,
                                                         "timeout": 0.5, "width": 640})
        self.addCleanup(self.camera.close)

    def test_shared_capture_snapshot_stream_and_restart(self):
        self.cv2.VideoCapture.assert_not_called()
        self.camera.start()
        self.camera.start()
        self.assertEqual(self.camera.snapshot(), b"jpeg")
        first, second = self.camera.stream(), self.camera.stream()
        self.assertEqual(next(first), b"jpeg")
        self.assertEqual(next(second), b"jpeg")
        self.assertEqual(next(first), b"jpeg")
        self.cv2.VideoCapture.assert_called_once_with(0)
        self.assertEqual(self.camera.get_state().state, DeviceState.ONLINE)
        first.close()
        self.assertEqual(self.camera.snapshot(), b"jpeg")
        self.camera.close()
        self.capture.release.assert_called_once()
        self.assertEqual(self.camera.get_state().state, DeviceState.OFFLINE)
        self.camera.start()
        self.assertEqual(self.camera.snapshot(), b"jpeg")
        self.assertEqual(list(second), [])
        self.assertEqual(self.cv2.VideoCapture.call_count, 2)

    def test_open_failure_releases_camera(self):
        self.capture.isOpened.return_value = False
        self.camera.start()
        with self.assertRaisesRegex(RuntimeError, "capture failed"):
            self.camera.snapshot()
        self.camera.close()
        self.capture.release.assert_called_once()

    def test_read_failure_sets_error_and_releases_camera(self):
        self.capture.read.return_value = (False, None)
        self.camera.start()
        with self.assertRaises(RuntimeError):
            self.camera.snapshot()
        self.assertEqual(self.camera.get_state().state, DeviceState.ERROR)
        self.camera.close()
        self.capture.release.assert_called_once()

    def test_slow_camera_times_out_and_releases_after_read_returns(self):
        unblock = Event()
        self.capture.read.side_effect = lambda: (unblock.wait(2), object())
        self.camera.timeout = 0.02
        self.camera.start()
        try:
            with self.assertRaises(CameraTimeoutError):
                self.camera.snapshot()
        finally:
            unblock.set()
            self.camera.close()
        self.capture.release.assert_called_once()

    def test_close_wakes_waiting_snapshot(self):
        self.camera._stop = Event()
        started = Event()
        errors = []

        def wait():
            started.set()
            try:
                self.camera.snapshot()
            except RuntimeError as exc:
                errors.append(exc)

        thread = Thread(target=wait)
        thread.start()
        started.wait(1)
        self.camera.close()
        thread.join(1)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)

    def test_numeric_options_are_validated(self):
        for key, value in (("fps", 0), ("timeout", -1), ("width", 1.5), ("fps", "nan")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                driver_factory("local_camera", args={key: value})
