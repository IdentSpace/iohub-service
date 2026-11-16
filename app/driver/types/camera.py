"""Common contract for camera drivers."""
from abc import abstractmethod
from collections.abc import Iterator

from app.driver.types.capabilities import DeviceCapabilities
from app.driver.types.device import DeviceBase


class CameraTimeoutError(TimeoutError):
    """A camera did not respond within its configured timeout."""


class Camera(DeviceBase):
    @abstractmethod
    def snapshot(self) -> bytes:
        """Capture one image and return its JPEG-encoded bytes."""
        pass

    @abstractmethod
    def stream(self) -> Iterator[bytes]:
        """Yield JPEG frames until stopped or closed.

        Frames contain image data only, without HTTP multipart boundaries.
        Implementations must release stream resources when the iterator is
        closed and stop active streams when the driver is closed.
        """
        pass

    @classmethod
    def get_capabilities(cls) -> DeviceCapabilities:
        return DeviceCapabilities(capabilities=("camera",))
