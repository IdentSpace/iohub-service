"""Shared reader lifecycle and thread-safe event subscriptions."""
from abc import abstractmethod
from collections.abc import Callable
from threading import RLock
from typing import Generic, TypeVar
import logging
from app.driver.types.device import DeviceBase

T = TypeVar("T")


class ReaderBase(DeviceBase, Generic[T]):
    def _init_events(self, device_id, legacy_sink: Callable[[T], None]):
        self.device_id = str(device_id) if device_id is not None else None
        self._event_lock = RLock()
        self._subscribers: list[Callable[[T], None]] = [legacy_sink]

    def subscribe(self, callback: Callable[[T], None]) -> None:
        """Callbacks run on the reader thread and should return quickly."""
        with self._event_lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[T], None]) -> None:
        with self._event_lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def _emit(self, event: T) -> None:
        with self._event_lock:
            callbacks = tuple(self._subscribers)
        for callback in callbacks:
            try:
                callback(event)
            except Exception:
                logging.getLogger(__name__).exception("Reader subscriber failed")

    @abstractmethod
    def listen(self):
        pass

    @abstractmethod
    def listen_in_thread(self):
        pass

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return
        self._stop_event.clear()
        self.listen_in_thread()

    def close(self) -> None:
        self._stop_event.set()
        if self.serial and self.serial.is_open:
            self.serial.close()
        if self.thread:
            self.thread.join(timeout=3)
            if self.thread.is_alive():
                raise RuntimeError("Reader thread did not stop")
