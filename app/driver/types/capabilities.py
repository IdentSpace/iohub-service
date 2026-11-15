"""Hardware-independent descriptions used by clients and command validation."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.driver.types.commands import DeviceCommand, CommandArgument


class Descriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ArgumentOption(Descriptor):
    value: CommandArgument
    label: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$",
                       description="Stable translation slug; localized by the client")


class CommandArgumentSchema(Descriptor):
    type: Literal["enum"] = "enum"
    required: bool = True
    options: tuple[ArgumentOption, ...]


class CommandDescriptor(Descriptor):
    cmd: DeviceCommand
    label: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$",
                       description="Stable translation slug; localized by the client")
    argument: CommandArgumentSchema | None = None


class StateField(Descriptor):
    key: str
    label: str = Field(pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$",
                       description="Stable translation slug; localized by the client")
    type: Literal["boolean", "string", "number"]


class DeviceCapabilities(Descriptor):
    capabilities: tuple[str, ...] = ()
    commands: tuple[CommandDescriptor, ...] = ()
    state_fields: tuple[StateField, ...] = ()

    def validate_command(self, cmd: DeviceCommand, arg: CommandArgument | None):
        from app.driver.types.device import UnsupportedCommandError
        command = next((item for item in self.commands if item.cmd == cmd), None)
        if command is None:
            raise UnsupportedCommandError(f"Unsupported command: {cmd.value}")
        if command.argument is None:
            if arg is not None:
                raise ValueError(f"{cmd.value} does not accept an argument")
        elif arg is None:
            if command.argument.required:
                raise ValueError(f"{cmd.value} requires an argument")
        elif arg not in [option.value for option in command.argument.options]:
            raise ValueError(f"Invalid argument for {cmd.value}")
