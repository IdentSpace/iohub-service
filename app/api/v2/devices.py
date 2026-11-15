"""Versioned device discovery, state and command API."""
import logging
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.devices import device_manager
from app.driver.driver_factory import get_driver_capabilities
from app.driver.types.capabilities import DeviceCapabilities
from app.driver.types.commands import DeviceCommand, CommandArgument
from app.driver.types.device import UnsupportedCommandError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["Devices v2"])


class DeviceSummary(BaseModel):
    id: UUID
    name: str | None
    type: str | None
    driver: str | None
    capabilities: DeviceCapabilities | None
    configuration_error: str | None = None


class DeviceList(BaseModel):
    items: list[DeviceSummary]


class DeviceStateResponse(BaseModel):
    device_id: UUID
    connection: Literal["online", "offline", "error", "unknown"]
    values: dict[str, Any]
    message: str
    observed_at: datetime


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cmd: DeviceCommand
    arg: CommandArgument | None = None


class CommandResponse(BaseModel):
    device_id: UUID
    success: bool
    message: str
    data: Any = None


def require_device(device_id: UUID):
    config = device_manager.get_device(device_id)
    if config is None:
        raise HTTPException(404, detail={"code": "device_not_found", "message": "Device not found"})
    return config


def capabilities_for(config):
    try:
        return get_driver_capabilities(config["device_driver_name"])
    except ValueError as exc:
        raise HTTPException(409, detail={"code": "invalid_driver", "message": str(exc)}) from exc


def summary(config):
    try:
        capabilities = get_driver_capabilities(config["device_driver_name"])
        error = None
    except ValueError as exc:
        capabilities, error = None, str(exc)
    return DeviceSummary(
        id=config["id"], name=config.get("name"),
        type=config.get("device_type_name"), driver=config.get("device_driver_name"),
        capabilities=capabilities, configuration_error=error,
    )


@router.get("", response_model=DeviceList)
def list_devices():
    # Discovery only: do not start readers or issue hardware requests.
    return DeviceList(items=[summary(config) for config in device_manager.get_devices()])


@router.get("/{device_id}", response_model=DeviceSummary)
def get_device(device_id: UUID):
    return summary(require_device(device_id))


@router.get("/{device_id}/capabilities", response_model=DeviceCapabilities)
def get_capabilities(device_id: UUID):
    return capabilities_for(require_device(device_id))


@router.get("/{device_id}/state", response_model=DeviceStateResponse)
def get_state(device_id: UUID):
    config = require_device(device_id)
    capabilities = capabilities_for(config)
    try:
        state = device_manager.runtime_devices.get_state(config)
        values = {field.key: state.raw_data[field.key]
                  for field in capabilities.state_fields if field.key in state.raw_data}
        if any(field.key == "power" for field in capabilities.state_fields):
            values["power"] = state.power_state
        return DeviceStateResponse(
            device_id=device_id,
            connection=state.state if state.state in ("online", "offline", "error") else "unknown",
            values=values, message=state.message, observed_at=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.exception("Could not read device %s", device_id)
        raise HTTPException(502, detail={"code": "device_read_failed", "message": "Could not read device state"}) from exc


@router.post("/{device_id}/commands", response_model=CommandResponse)
def execute_command(device_id: UUID, request: CommandRequest):
    config = require_device(device_id)
    capabilities = capabilities_for(config)
    try:
        capabilities.validate_command(request.cmd, request.arg)
    except UnsupportedCommandError as exc:
        raise HTTPException(422, detail={"code": "unsupported_command", "message": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(422, detail={"code": "invalid_argument", "message": str(exc)}) from exc
    try:
        result = device_manager.runtime_devices.execute_command(config, request.cmd, request.arg)
        if not result.success:
            raise HTTPException(502, detail={"code": "command_failed", "message": result.message or "Command failed"})
        return CommandResponse(device_id=device_id, success=True, message=result.message, data=result.data)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Command failed for device %s", device_id)
        raise HTTPException(502, detail={"code": "command_failed", "message": "Device command failed"}) from exc
