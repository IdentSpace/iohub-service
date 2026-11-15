from app.driver.types.capabilities import DeviceCapabilities
from app.driver.types.commands import DeviceCommand, CommandArgument
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

class DeviceState:
	ONLINE = "online"
	OFFLINE = "offline"
	ERROR = "error"
	NONE = "none"

	def __init__(self, state: str = NONE, message: str = "", raw_data: dict = None, power_state: bool = None):
		self.state = state
		self.message = message
		self.raw_data = raw_data if raw_data is not None else {}
		self.power_state = power_state

@dataclass
class CommandResult:
	success: bool
	data: Any = None
	message: str = ""


class UnsupportedCommandError(ValueError):
	pass


class DeviceBase(ABC):

	# @abstractmethod
	# def has_web(self)->DeviceState:
		# pass

	@abstractmethod
	def get_state(self)->DeviceState:
		pass

	@abstractmethod
	def raw_command(self):
		pass

	@abstractmethod
	def start(self) -> None:
		pass

	@abstractmethod
	def close(self) -> None:
		pass

	@abstractmethod
	def execute_command(self, cmd: DeviceCommand, arg: CommandArgument | None = None) -> CommandResult:
		pass

	@classmethod
	@abstractmethod
	def get_capabilities(cls) -> DeviceCapabilities:
		"""Describe supported operations without connecting to hardware."""
		pass

	def web_command(self, cmd: str, arg=None):
		"""Compatibility alias for existing integrations."""
		return self.execute_command(cmd, arg)

	def list_bases(self):
		return[
            base.__name__
            for base in type(self).__mro__
            if issubclass(base,ABC) 
            and base is not ABC
			and base is not DeviceBase
            and base is not type(self)
        ]

class Default(DeviceBase):
	def __init__(self, ip: str = "", relay: int = 0, name: str = "DefaultDevice", args=None):
		self.state = None

	def turn_on(self):
		return self.state
	
	def turn_off(self):
		return self.state

	def get_state(self) -> DeviceState:
		return DeviceState(state=DeviceState.NONE, message="NOT IMPLEMENTED", raw_data={})
	
	def raw_command(self):
		pass

	def start(self):
		pass

	def close(self):
		pass

	def execute_command(self, cmd: DeviceCommand, arg: CommandArgument | None = None) -> CommandResult:
		raise UnsupportedCommandError(cmd)

	@classmethod
	def get_capabilities(cls) -> DeviceCapabilities:
		return DeviceCapabilities()
