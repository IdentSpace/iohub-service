"""In-process serial source; uses the real scanner read/parse/event pipeline."""

import math
import threading
from itertools import cycle
from urllib.parse import parse_qs, urlsplit

from app.driver.default_data_scanner import DefaultDataScanner
from app.driver.default_nfc_reader import DefaultNfcReader
from app.driver.types.device import DeviceState


class DummySerialConnection:
    SAMPLES = (b"DEMO-ARTIKEL-001\r\n", b"010401234567890110DEMO-LOT-01\r\n", b"DEMO-ARTIKEL-002\r\n")

    def __init__(self, interval, stop_event, samples=None):
        self.interval = interval
        self.stop_event = stop_event
        self.is_open = True
        self.samples = cycle(samples or self.SAMPLES)

    def readline(self):
        if not self.is_open or self.stop_event.wait(self.interval):
            return b""
        return next(self.samples)

    def close(self):
        self.is_open = False
        self.stop_event.set()


class DummySerialMixin:
    _active = {}
    _active_lock = threading.Lock()

    def __init__(self, args):
        super().__init__(args)
        self.port = args.get("port") or args.get("device_host", "")
        self.name = type(self).__name__
        address = urlsplit(self.port)
        if address.scheme != "dummy" or address.netloc != self.device_kind:
            raise ValueError(f"Dummy device requires dummy://{self.device_kind}/<name>?interval=3")
        self.interval = float(parse_qs(address.query).get("interval", ["3"])[0])
        if not math.isfinite(self.interval) or self.interval < 0.01:
            raise ValueError("Dummy interval must be finite and at least 0.01 seconds")

    def open_serial(self):
        return DummySerialConnection(self.interval, self._stop_event, self.samples)

    def listen_in_thread(self):
        if self.thread and self.thread.is_alive():
            return self
        self._stop_event.clear()
        super().listen_in_thread()
        with self._active_lock:
            self._active[str(self.id)] = self
        return self

    def close(self):
        super().close()
        with self._active_lock:
            if self._active.get(str(self.id)) is self:
                self._active.pop(str(self.id), None)

    def get_state(self):
        with self._active_lock:
            active = self._active.get(str(self.id))
            online = bool(active and active.thread and active.thread.is_alive() and not active._stop_event.is_set())
        return DeviceState(
            state=DeviceState.ONLINE if online else DeviceState.OFFLINE,
            message="Simulated serial device running" if online else "Simulated serial device stopped",
            raw_data={"simulated": True, "port": self.port, "interval": self.interval},
        )


class DummyDataScanner(DummySerialMixin, DefaultDataScanner):
    device_kind = "datascanner"
    samples = DummySerialConnection.SAMPLES


class DummyNfcReader(DummySerialMixin, DefaultNfcReader):
    device_kind = "nfcreader"
    samples = (b"04A1B2C3D4E580\r\n", b"DEADBEEF\r\n", b"04112233445566\r\n")
