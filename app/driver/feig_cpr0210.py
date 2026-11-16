from app.driver.types.commands import DeviceCommand, CommandArgument
from app.driver.types.device import DeviceState, UnsupportedCommandError, CommandResult
from app.driver.types.nfc_reader import NfcReader,NfcData
import serial
import threading
import time

class CPR0210(NfcReader):

	def __init__(self, args:dict):
		self._init_nfc(args.get("id"))
		self.port = args.get("port")
		self.baudrate = args.get("baudrate", 38400) or 38400
		self.timeout = args.get("timeout", 0.3)
		self.serial = None
		self.thread = None
		self._stop_event = threading.Event()

	def connect(self):
		while not self._stop_event.is_set():
			try:
				self.serial = serial.Serial(
					port=self.port,
					baudrate=self.baudrate,
					timeout=self.timeout, parity=serial.PARITY_EVEN,
					bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE
				)
				print(f"NFC Reader verbunden an {self.port} @ {self.baudrate} Baud")
				break
			except serial.SerialException as e:
				print(f"FEHLER VERBINDUNG: {e}")
				self._stop_event.wait(2)
				
	def heartbeat(self):
		pass
				
	def listen(self):
		if not self.serial or not self.serial.is_open:
			self.connect()

		last_check = time.time()
		self.heartbeat()

		while not self._stop_event.is_set():
			try:
				
				if self.serial.in_waiting > 0:
					try:
						data_bytes = self.serial.read_until(b'\r\n')
						data = data_bytes.hex().upper()
						if data:
							print(f"NFC Tag erkannt: {data}")
							# print(f"NFC Tag erkannt: {data_bytes}")


							# data2 = DefaultNfcReader.extract_uid(data)
							# print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
							# print(f"Rohdaten: {data}") 
							# self.publish_nfc(NfcData(uid=data))

					except Exception as e:
						print(f"Error: {e}")
						continue

				# Alle 60 Sekunden Heartbeat senden
				if time.time() - last_check > 120:
					self.heartbeat()
					last_check = time.time()

			except serial.SerialException as e:
				print(f"SERIAL EXCEPTION: {e}")
				self.serial.close()
				self.connect()
				continue
			except Exception as e:
				print("FEHLER LISTEN")
				self.serial.close()
				print(e)
				time.sleep(1)
				continue

	def listen_in_thread(self):
		self.thread = threading.Thread(target=self.listen)
		self.thread.daemon = True
		self.thread.start()
		return self

	def crc16_ccitt(self, data: bytes, poly=0x8408, preset=0xFFFF):
		crc = preset
		for byte in data:
			crc ^= byte
			for _ in range(8):
				if crc & 0x0001:
					crc = (crc >> 1) ^ poly
				else:
					crc >>= 1
		return crc & 0xFFFF
	
	def buzzer_on(self):
		frame = bytearray()
		frame.append(0x06)        # LÃ¤nge (inkl. CRC)
		frame.append(0x00)        # COM-ADR (Bus-Adresse)
		frame.append(0x71)        # Command: Set Output
		frame.append(0x03)        # DATA: Ausgang 1 = ON (Buzzer)
		crc = self.crc16_ccitt(frame)
		frame.append(crc & 0xFF)  # CRC LSB
		frame.append((crc >> 8) & 0xFF)
		self.serial.write(frame)
	
	def get_state(self):
		return DeviceState(state=DeviceState.ONLINE if self.serial and self.serial.is_open else DeviceState.OFFLINE)
	
	def raw_command(self):
		return super().raw_command()
	
	def openLock(self, address, channel):
		cmd = b'\xA1' + address.to_bytes(1, byteorder='big') + channel.to_bytes(1, byteorder='big')
		self.serial.write(cmd)

	def getVersion(self):
		cmd = b'\x01'
		self.serial.write(cmd)
		response = self.serial.read(7)
		return response


	def execute_command(self, cmd: DeviceCommand, arg: CommandArgument | None = None) -> CommandResult:
		raise UnsupportedCommandError(cmd)
