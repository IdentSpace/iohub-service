"""Hanwha SUNAPI snapshot and MJPEG streaming driver."""
from threading import Event, RLock
from urllib.parse import urlsplit

import requests
from requests.auth import HTTPDigestAuth

from app.driver.types.camera import Camera, CameraTimeoutError
from app.driver.types.device import DeviceState, UnsupportedCommandError


class Hanwha(Camera):
    def __init__(self, args: dict):
        host = args.get("device_host") or ""
        self.base_url = (host if "://" in host else f"http://{host}").rstrip("/")
        self.auth = HTTPDigestAuth(args.get("username") or "admin", args.get("password") or "")
        self.channel = int(args.get("channel") or 0)
        self.timeout = float(args.get("timeout") or 5)
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")
        self._lock = RLock()
        self._stop = Event()
        self._responses = set()
        self._state = DeviceState(state=DeviceState.OFFLINE)

    def start(self) -> None:
        with self._lock:
            if self._stop.is_set():
                self._stop = Event()

    def close(self) -> None:
        with self._lock:
            self._stop.set()
            responses = tuple(self._responses)
            self._responses.clear()
            self._state = DeviceState(state=DeviceState.OFFLINE)
        for response in responses:
            response.close()

    def _request(self, submenu: str, streaming: bool = False):
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("device_host must be an HTTP(S) camera host")
        with self._lock:
            stop = self._stop
            if stop.is_set():
                raise RuntimeError("Camera is closed; call start() before use")
        response = None
        try:
            response = requests.get(
                f"{self.base_url}/stw-cgi/video.cgi", auth=self.auth,
                params={"msubmenu": submenu, "action": "view", "Channel": self.channel},
                stream=streaming, timeout=self.timeout,
            )
            response.raise_for_status()
            with self._lock:
                if stop.is_set():
                    raise RuntimeError("Camera was closed during request")
                self._responses.add(response)
            return response, stop
        except (requests.RequestException, RuntimeError) as exc:
            if response is not None:
                response.close()
            with self._lock:
                if not stop.is_set():
                    self._state = DeviceState(state=DeviceState.ERROR, message="Camera request failed")
            if isinstance(exc, requests.Timeout):
                raise CameraTimeoutError("Camera request timed out") from None
            raise RuntimeError("Camera request failed") from None

    def _release(self, response):
        with self._lock:
            self._responses.discard(response)
        response.close()

    def snapshot(self) -> bytes:
        response, stop = self._request("snapshot")
        try:
            image = response.content
            if not image.startswith(b"\xff\xd8") or not image.endswith(b"\xff\xd9"):
                raise RuntimeError("Camera did not return a JPEG image")
            with self._lock:
                if stop.is_set():
                    raise RuntimeError("Camera is closed")
                self._state = DeviceState(state=DeviceState.ONLINE)
            return image
        except RuntimeError:
            with self._lock:
                if not stop.is_set():
                    self._state = DeviceState(state=DeviceState.ERROR, message="Camera snapshot failed")
            raise
        finally:
            self._release(response)

    def stream(self):
        response, stop = self._request("stream", streaming=True)
        buffer = bytearray()
        try:
            for chunk in response.iter_content(chunk_size=4096):
                if stop.is_set():
                    break
                buffer.extend(chunk)
                while True:
                    start = buffer.find(b"\xff\xd8")
                    if start < 0:
                        buffer[:] = buffer[-1:]
                        break
                    if start:
                        del buffer[:start]
                    end = buffer.find(b"\xff\xd9", 2)
                    if end < 0:
                        break
                    frame = bytes(buffer[:end + 2])
                    del buffer[:end + 2]
                    with self._lock:
                        if stop.is_set():
                            return
                        self._state = DeviceState(state=DeviceState.ONLINE)
                    yield frame
                if len(buffer) > 16 * 1024 * 1024:
                    raise RuntimeError("Camera stream frame exceeds 16 MiB")
            if not stop.is_set():
                raise RuntimeError("Camera stream ended")
        except (requests.RequestException, RuntimeError) as exc:
            if not stop.is_set():
                with self._lock:
                    self._state = DeviceState(state=DeviceState.ERROR, message="Camera stream failed")
                # requests wraps streaming read timeouts in ConnectionError.
                from urllib3.exceptions import ReadTimeoutError
                if isinstance(exc, requests.Timeout) or (
                    isinstance(exc, requests.ConnectionError)
                    and exc.args and isinstance(exc.args[0], ReadTimeoutError)
                ):
                    raise CameraTimeoutError("Camera stream timed out") from None
                raise RuntimeError("Camera stream failed") from None
        finally:
            self._release(response)

    def get_state(self) -> DeviceState:
        """Return the last observed connection state without fetching an image."""
        with self._lock:
            return self._state

    def raw_command(self):
        raise UnsupportedCommandError("raw_command")

    def execute_command(self, cmd, arg=None):
        raise UnsupportedCommandError(cmd)
