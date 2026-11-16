"""Shared local USB/notebook camera capture, loaded without importing OpenCV."""
import math
from threading import Condition, Event, RLock, Thread
from time import monotonic

from app.driver.types.camera import Camera, CameraTimeoutError
from app.driver.types.device import DeviceState, UnsupportedCommandError


class LocalCamera(Camera):
    def __init__(self, args: dict):
        source = args.get("device_host")
        self.source = 0 if source is None or source == "" else source
        if isinstance(self.source, str) and self.source.isdecimal():
            self.source = int(self.source)
        self.width = self._positive(args.get("width"), "width", integer=True)
        self.height = self._positive(args.get("height"), "height", integer=True)
        self.fps = self._positive(args.get("fps", 15), "fps")
        self.timeout = self._positive(args.get("timeout", 5), "timeout")
        self._condition = Condition()
        self._lifecycle = RLock()
        self._stop = Event()
        self._stop.set()
        self._thread = None
        self._frame = None
        self._sequence = 0
        self._captured = 0
        self._error = None
        self._users = 0

    @staticmethod
    def _positive(value, name, integer=False):
        if value is None and name in ("width", "height"):
            return None
        number = float(value)
        if not math.isfinite(number) or number <= 0 or (integer and not number.is_integer()):
            raise ValueError(f"{name} must be positive" + (" and integral" if integer else ""))
        return int(number) if integer else number

    def start(self) -> None:
        # Registering a driver or reading its state must not reserve hardware.
        pass

    def _acquire(self):
        with self._lifecycle:
            self._start_capture()
            self._users += 1
            return self._stop

    def _release(self, stop):
        with self._lifecycle:
            # An iterator from before close() must not stop a newer capture.
            if stop is not self._stop or self._users == 0:
                return
            self._users -= 1
            if self._users == 0:
                self.close()

    def _start_capture(self) -> None:
        with self._lifecycle:
            if self._thread and self._thread.is_alive():
                if self._stop.is_set():
                    raise RuntimeError("Previous camera capture has not stopped")
                return
            try:
                import cv2
            except ImportError:
                raise RuntimeError("Local cameras require opencv-python-headless") from None
            with self._condition:
                self._stop = Event()
                self._frame = None
                self._error = None
                self._thread = Thread(target=self._capture, args=(cv2, self._stop),
                                      name="local-camera", daemon=True)
                self._thread.start()

    def close(self) -> None:
        with self._lifecycle:
            self._users = 0
            with self._condition:
                self._stop.set()
                self._frame = None
                self._condition.notify_all()
            if self._thread:
                self._thread.join(timeout=3)
                if self._thread.is_alive():
                    raise RuntimeError("Local camera capture did not stop within three seconds")

    def _capture(self, cv2, stop):
        capture = None
        try:
            capture = cv2.VideoCapture(self.source)
            if not capture.isOpened():
                raise RuntimeError("Could not open local camera")
            for prop, value in ((cv2.CAP_PROP_FRAME_WIDTH, self.width),
                                (cv2.CAP_PROP_FRAME_HEIGHT, self.height),
                                (cv2.CAP_PROP_FPS, self.fps)):
                if value is not None:
                    capture.set(prop, value)
            while not stop.is_set():
                began = monotonic()
                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError("Could not read local camera")
                ok, jpeg = cv2.imencode(".jpg", frame)
                if not ok:
                    raise RuntimeError("Could not encode local camera image")
                with self._condition:
                    if stop.is_set():
                        break
                    self._frame = jpeg.tobytes()
                    self._captured = monotonic()
                    self._sequence += 1
                    self._condition.notify_all()
                stop.wait(max(0, 1 / self.fps - (monotonic() - began)))
        except Exception:
            with self._condition:
                self._error = "Local camera capture failed"
                self._frame = None
                self._condition.notify_all()
        finally:
            try:
                if capture is not None:
                    capture.release()
            finally:
                with self._condition:
                    self._condition.notify_all()

    def _wait_frame(self, stop, after=None):
        deadline = monotonic() + self.timeout
        with self._condition:
            while True:
                if stop.is_set():
                    raise RuntimeError("Local camera is closed")
                if self._error:
                    raise RuntimeError(self._error)
                if (self._frame is not None and monotonic() - self._captured < self.timeout
                        and (after is None or self._sequence > after)):
                    return self._sequence, self._frame
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise CameraTimeoutError("Local camera frame timed out")
                self._condition.wait(remaining)

    def snapshot(self) -> bytes:
        stop = self._acquire()
        try:
            return self._wait_frame(stop)[1]
        finally:
            self._release(stop)

    def stream(self):
        stop = self._acquire()
        sequence = None
        try:
            while not stop.is_set():
                try:
                    sequence, image = self._wait_frame(stop, sequence)
                except RuntimeError:
                    if stop.is_set():
                        return
                    raise
                yield image
        finally:
            self._release(stop)

    def get_state(self) -> DeviceState:
        with self._condition:
            if self._error:
                return DeviceState(state=DeviceState.ERROR, message=self._error)
            if self._stop.is_set():
                return DeviceState(state=DeviceState.OFFLINE, message="Camera idle")
            if self._frame is not None and monotonic() - self._captured < self.timeout:
                return DeviceState(state=DeviceState.ONLINE)
            return DeviceState(state=DeviceState.OFFLINE, message="Waiting for camera frame")

    def raw_command(self):
        raise UnsupportedCommandError("raw_command")

    def execute_command(self, cmd, arg=None):
        raise UnsupportedCommandError(cmd)
