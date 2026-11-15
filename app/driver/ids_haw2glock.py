from app.driver.types.commands import DeviceCommand, CommandArgument
from app.driver.types.device import DeviceBase, DeviceState, UnsupportedCommandError, CommandResult
import serial
import threading
import time

class HAW2GLOCK(DeviceBase):

	def __init__(self, port, baudrate=115200, timeout=0.3):
		self.port = port
		self.baudrate = baudrate
		self.timeout = timeout
		self.serial = None
		self.thread = None
		self._stop_event = threading.Event()

	def connect(self):
		while not self._stop_event.is_set():
			try:
				self.serial = serial.Serial(
					port=self.port,
					baudrate=self.baudrate,
					timeout=self.timeout
				)
				print(f"NFC Reader verbunden an {self.port} @ {self.baudrate} Baud")
				break
			except serial.SerialException as e:
				print(f"FEHLER VERBINDUNG: {e}")
				self._stop_event.wait(2)
	
	def get_state(self):
		return DeviceState(state=DeviceState.ONLINE if self.serial and self.serial.is_open else DeviceState.OFFLINE)
	
	def raw_command(self):
		return super().raw_command()
	
	def openLock(self, channel, address):
		cmd = b'\xA1' + channel.to_bytes(1, byteorder='big') + address.to_bytes(1, byteorder='big')
		self.serial.write(cmd)

	def getVersion(self):
		cmd = b'\x01'
		self.serial.write(cmd)
		response = self.serial.read(7)
		return response
	def start(self):
		pass

	def close(self):
		self._stop_event.set()
		if self.serial and self.serial.is_open:
			self.serial.close()
		if self.thread:
			self.thread.join(timeout=3)
			if self.thread.is_alive():
				raise RuntimeError("Reader thread did not stop")

	def execute_command(self, cmd: DeviceCommand, arg: CommandArgument | None = None) -> CommandResult:
		raise UnsupportedCommandError(cmd)
