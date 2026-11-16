from app.driver.types.commands import DeviceCommand, CommandArgument
from app.driver.types.nfc_reader import NfcReader,NfcData
from app.driver.types.device import DeviceState, UnsupportedCommandError, CommandResult
import serial
import threading
import time

class DefaultNfcReader(NfcReader):
	def __init__(self, port, baudrate=115200, timeout=1):
		self._init_nfc(None)
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

	def listen(self):
		if not self.serial or not self.serial.is_open:
			self.connect()

		while not self._stop_event.is_set():
			try:
				if self.serial.in_waiting > 0:
					try:
						data_bytes = self.serial.readline()
						data = data_bytes.hex()
						if data:
							data2 = DefaultNfcReader.extract_uid(data)
							print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
							print(f"NFC Tag erkannt: {data2}")
							print(f"Rohdaten: {data}") 
							self.publish_nfc(NfcData(uid=data2))

					except Exception as e:
						print(f"Error: {e}")
						continue

			except serial.SerialException as e:
				print(f"SERIAL EXCEPTION: {e}")
				if self.serial:
					self.serial.close()
				self.connect()
				continue
			except Exception as e:
				print("FEHLER LISTEN")
				if self.serial:
					self.serial.close()
				print(e)
				time.sleep(1)
				continue                              

	def listen_in_thread(self):
		self.thread = threading.Thread(target=self.listen)
		self.thread.daemon = True
		self.thread.start()
		return self
	

	def get_state(self):
		return DeviceState(state=DeviceState.ONLINE if self.serial and self.serial.is_open else DeviceState.OFFLINE)
	
	def raw_command(self):
		return super().raw_command()

	def extract_uidN(hex_string):
		try:
			data = bytes.fromhex(hex_string)
			if len(data) < 7:
				print("Datensatz zu kurz fÃ¼r gÃ¼ltiges Event.")
				return None

			offset = 4 if data[0] == 0x01 else 0
			event_code = data[offset]

			if event_code != 0x31:
				print(f"Kein PICC_ACK Event (Code: {hex(event_code)})")
				return None

			tag_info = data[offset + 1]
			taginfo_uid_map = {
				0x40: 4,
				0x44: 7,
				0x48: 4,
				0x68: 7,
				0x6C: 7,
				0x74: 7,
				0x78: 10
			}

			uid_len = taginfo_uid_map.get(tag_info, 0)
			if uid_len == 0:
				print(f"Unbekannter TagInfo-Wert: {hex(tag_info)}")
				return None

			uid_start = offset + 2
			uid_end = uid_start + uid_len
			if len(data) < uid_end:
				print("Datensatz zu kurz fÃ¼r vollstÃ¤ndige UID.")
				return None

			uid_bytes = data[uid_start:uid_end]
			uid_hex = uid_bytes.hex().upper()
			return uid_hex

		except Exception as e:
			print(f"Fehler beim Parsen: {e}")
			return None
	
	def extract_uid(hex_string):
		try:
			data = bytes.fromhex(hex_string)

			# --- HEADER-SYNCHRONISIERUNG ---
			start_index = data.find(b'\x01\x01')
			if start_index == -1:
				print("Kein gÃ¼ltiger Header (0101) gefunden.")
				return ''
			# Daten ab Header
			data = data[start_index:]

			# MindestlÃ¤nge prÃ¼fen
			if len(data) < 7:
				print("Datensatz zu kurz fÃ¼r gÃ¼ltiges Event.")
				return ''

			# Event-Code prÃ¼fen (0x31 = PICC_ACK)
			event_code = data[4]
			if event_code != 0x31:
				print(f"Kein PICC_ACK Event (Code: {hex(event_code)})")
				return ''

			# TagInfo-Byte auslesen
			tag_info = data[5]

			# Bekannte TagInfo-Werte direkt zuordnen
			taginfo_uid_map = {
				0x40: 4,  # Mifare Classic
				0x44: 7,  # Mifare Ultralight
				0x48: 4,  # Mifare DESFire
				0x68: 7,  # NTAG
				0x6C: 7,  # ICODE
				0x74: 7,  # DESFire EV1
				0x78: 10  # ISO14443-4 Extended UID
			}

			uid_len = taginfo_uid_map.get(tag_info, 0)
			if uid_len == 0:
				print(f"Unbekannter TagInfo-Wert: {hex(tag_info)}")
				return ''

			# UID extrahieren
			uid_start = 6
			uid_end = uid_start + uid_len
			if len(data) < uid_end:
				print("Datensatz zu kurz fÃ¼r vollstÃ¤ndige UID.")
				return ''

			uid_bytes = data[uid_start:uid_end]
			uid_hex = uid_bytes.hex().upper()
			return uid_hex

		except Exception as e:
			print(f"Fehler beim Parsen: {e}")
			return ''


	def execute_command(self, cmd: DeviceCommand, arg: CommandArgument | None = None) -> CommandResult:
		raise UnsupportedCommandError(cmd)
