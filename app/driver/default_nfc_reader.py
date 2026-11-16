from app.driver.types.commands import DeviceCommand, CommandArgument
from app.driver.types.nfc_reader import NfcReader,NfcData
from app.driver.types.device import DeviceState, UnsupportedCommandError, CommandResult
import serial
import threading
import time
import logging

logger = logging.getLogger(__name__)

class DefaultNfcReader(NfcReader):
	def __init__(self, args:dict):
		self._init_nfc(args.get("id"))
		self.port = args.get("port", None)
		self.id = args.get("id", None)
		self.baudrate = args.get("baudrate", 115200)
		self.timeout = args.get("timeout", 1)
		self.serial = None
		self.thread = None
		self.name = "DafaultNFCReader"
		self._stop_event = threading.Event()

	def open_serial(self):
		return serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)

	def connect(self):
		while not self._stop_event.is_set():
			try:
				self.serial = serial.Serial(
					port=self.port,
					baudrate=self.baudrate,
					timeout=self.timeout
				)
				logger.info(f"NFC Reader verbunden an {self.port} @ {self.baudrate} Baud")
				break
			except serial.SerialException as e:
				logger.error(f"FEHLER VERBINDUNG: {e}")
				self._stop_event.wait(2)

	# TODO: implement 
	def heartbeat(self):
		pass
		
	def listen(self):
		while not self._stop_event.is_set():
			try:
				if not self.serial or not self.serial.is_open:
					if self.serial:
						self.serial.close()
						self.serial = None
					try:
						self.serial = self.open_serial()
					except serial.SerialException as e:
						logger.error(f"Device {self.name} Error(R1): " + str(e))
						self._stop_event.wait(2)
						continue

				data_bytes = self.serial.readline()
				if not data_bytes:
					continue

				data = data_bytes.decode("utf-8", errors="replace").strip()
				if not data:
					continue

				try:
					logger.debug("Device %s received NFC event", self.name)
					self.publish_nfc(NfcData(uid=data, deviceId=str(self.id) if self.id is not None else None))
				except Exception:
					logger.exception("Device %s Error(R2)", self.name)
					continue
			except Exception:
				logger.exception("Device %s Error(R3)", self.name)
				if self.serial and self.serial.is_open:
					self.serial.close()
				self._stop_event.wait(2)
				continue

	def listen_in_thread(self):
		try:
			logger.info(f"Device {self.name}: listen in thread")
			self.thread = threading.Thread(target=self.listen, daemon=True)
			self.thread.start()
			return self
		except Exception as e:
			logger.error(f"Device {self.name} Error(R4): " + str(e))
			return self
	

	def get_state(self):
		return DeviceState(state=DeviceState.ONLINE if self.serial and self.serial.is_open else DeviceState.OFFLINE)
	
	def raw_command(self):
		return super().raw_command()


	def execute_command(self, cmd: DeviceCommand, arg: CommandArgument | None = None) -> CommandResult:
		raise UnsupportedCommandError(cmd)
