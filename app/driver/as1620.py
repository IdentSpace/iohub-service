from app.driver.types.capabilities import DeviceCapabilities, CommandDescriptor, CommandArgumentSchema, ArgumentOption, StateField
from app.driver.types.commands import DeviceCommand, CommandArgument
from app.driver.types.parking_barrier import ParkingBarrier
from app.driver.types.device import DeviceBase, DeviceState, UnsupportedCommandError, CommandResult
from abc import ABC
import xmlrpc.client
import time

class AS1620(DeviceBase, ParkingBarrier):

	def __init__(self, args:dict):
		self.URI = "http://{0}:{1}".format(args["device_host"], 8081)
		self.proxy = xmlrpc.client.ServerProxy(self.URI)

	def open_tree(self):
		print("Parking Barrier open")

		try:
			result = self.proxy.SetOpen()
			isMoving = True
			status = None

			while isMoving:
				time.sleep(0.5)
				status = self.get_status()
				isMoving = status["moving"]
				print("Barrier moving...", isMoving)

			status = self.get_status()
			return status["open"]
		except Exception as e:
			print("FEHLER")
			return None

	def close_tree(self):
		print("Parking Barrier Close")
		try:
			result = self.proxy.SetClose()
			isMoving = True
			status = None

			while isMoving:
				time.sleep(0.5)
				status = self.get_status()
				isMoving = status["moving"]

			status = self.get_status()
			return status["closed"]
		except Exception as e:
			return None

	def get_status(self):
		try:
			result = self.proxy.GetStatus()
			return {
				"maintenance": bool(result[0]),
				"open": bool(result[1]),
				"closed": bool(result[2]),
				"moving": bool(result[3]),
			}
		except Exception as e:
			return None

	def get_state(self):
		status = self.get_status()
		if(status is None):
			return DeviceState(state=DeviceState.ERROR, message="ERROR COMMUNICATING", raw_data={})

		return DeviceState(state=DeviceState.ONLINE, message="", raw_data=status)

	def execute_command(self, cmd: DeviceCommand, arg: CommandArgument | None = None):
		if cmd == DeviceCommand.OPEN:
			return CommandResult(success=self.open_tree() is True)
		elif cmd == DeviceCommand.CLOSE:
			return CommandResult(success=self.close_tree() is True)
		else:
			raise UnsupportedCommandError(cmd)

	def raw_command(self):
		return []

	def start(self):
		pass

	def close(self):
		pass

	@classmethod
	def get_capabilities(cls) -> DeviceCapabilities:
		return DeviceCapabilities(
			capabilities=("parking_barrier",),
			commands=(
				CommandDescriptor(cmd=DeviceCommand.OPEN, label="command.open"),
				CommandDescriptor(cmd=DeviceCommand.CLOSE, label="command.close"),
			),
			state_fields=tuple(StateField(key=key, label=label, type="boolean") for key, label in (
				("open", "state.open"), ("closed", "state.closed"),
				("moving", "state.moving"), ("maintenance", "state.maintenance"),
			)),
		)
