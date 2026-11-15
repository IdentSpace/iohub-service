"""Shared device commands. Values are the existing public API strings."""
from enum import Enum


class DeviceCommand(str, Enum):
    SWITCH = "switch"
    OPEN = "open"
    CLOSE = "close"


class CommandArgument(str, Enum):
    ON = "on"
    OFF = "off"
