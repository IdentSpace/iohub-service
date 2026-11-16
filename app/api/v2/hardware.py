"""Hardware discovery on the machine running IOHub."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.devices import discovery

router = APIRouter(prefix="/hardware", tags=["Hardware v2"])


class SerialDevice(BaseModel):
    host: str
    description: str | None
    manufacturer: str | None
    serial_number: str | None
    vid: int | None
    pid: int | None


class SerialDevices(BaseModel):
    items: list[SerialDevice]


class CameraDevice(BaseModel):
    host: str
    description: str
    driver: str


class ProbeIssue(BaseModel):
    host: str
    reason: str


class CameraDevices(BaseModel):
    available: bool
    items: list[CameraDevice]
    issues: list[ProbeIssue]
    message: str


@router.get("/serial", response_model=SerialDevices)
def get_serial_devices():
    """List COM/TTY serial ports, including USB serial adapters, without opening them."""
    try:
        return {"items": discovery.serial_devices()}
    except Exception:
        raise HTTPException(503, detail={"code": "serial_discovery_failed",
                                         "message": "Could not enumerate serial ports"}) from None


@router.get("/cameras", response_model=CameraDevices)
def get_camera_devices(max_index: int = Query(4, ge=0, le=15)):
    """Probe camera indices 0..max_index, or /dev/video* on Linux.

    Opens each camera briefly in an isolated process (up to three seconds each).
    Busy or inaccessible cameras may not be listed. No background scan is run.
    """
    return discovery.camera_devices(max_index)
