from app.driver.types.capabilities import DeviceCapabilities, CommandDescriptor, CommandArgumentSchema, ArgumentOption, StateField
from app.driver.types.commands import DeviceCommand, CommandArgument
from app.driver.types.nfc_reader import NfcReader,NfcData
from app.driver.types.device import DeviceBase, DeviceState, UnsupportedCommandError, CommandResult
from app.state.nfc import set_latest_nfc_data
import serial
import threading
import time
import logging

logger = logging.getLogger(__name__)

class HoptSchuler890(DeviceBase, NfcReader):

	cmd_start_polling = bytes([0x01, 0x01, 0x00, 0x01, 0x5D, 0x01, 0x5D])

	def __init__(self, args:dict):
		self.port = args.get("port", None)
		self.baudrate = args.get("baudrate", 115200)
		self.timeout = 0.1
		self.serial = None
		self.thread = None
		self.name = "HoptSchuler890"
		self._stop_event = threading.Event()

	def connect(self):
		while not self._stop_event.is_set():
			try:
				self.serial = serial.Serial(
					port=self.port,
					baudrate=self.baudrate,        # Standard-Baudrate laut Handbuch
					bytesize=serial.EIGHTBITS,
					parity=serial.PARITY_NONE,
					stopbits=serial.STOPBITS_ONE,
					timeout=self.timeout,
					xonxoff=False,          # Kein Software-Flow-Control
					rtscts=False,           # Kein Hardware-Flow-Control (DTR/CTS)
					dsrdtr=False
				)

				logger.info(f"NFC Reader verbunden an {self.port} @ {self.baudrate} Baud")
				self.wakeup_and_arm_reader()
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
						self.serial = serial.Serial(
							port=self.port,
							baudrate=self.baudrate,        # Standard-Baudrate laut Handbuch
							bytesize=serial.EIGHTBITS,
							parity=serial.PARITY_NONE,
							stopbits=serial.STOPBITS_ONE,
							timeout=self.timeout,
							xonxoff=False,          # Kein Software-Flow-Control
							rtscts=False,           # Kein Hardware-Flow-Control (DTR/CTS)
							dsrdtr=False
						)
						self.wakeup_and_arm_reader()
					except serial.SerialException as e:
						logger.error(f"Device {self.name} Error(R1): " + str(e))
						self._stop_event.wait(2)
						continue


				if self.serial.in_waiting > 0:
					time.sleep(0.05) # Kurze Pause, damit das Paket vollstÃ¤ndig ankommen kann
					data_bytes = self.serial.read(self.serial.in_waiting)
				else:
					self._stop_event.wait(0.01)
					continue
				# data_bytes = self.serial.readline()
				# if not data_bytes:
					# continue

				data = self.parse_rfid_response(data_bytes.hex())

				try:
					logger.info(f"Device {self.name} RX: {data_bytes.hex().upper()}  => UUID: {data}")
					if(data != None):
						set_latest_nfc_data(NfcData(uid=data))
				except Exception as e:
					logger.error(f"Device {self.name} Error(R2): " + str(e))
					continue
			except Exception as e:
				logger.error(f"Device {self.name} Error(R3): " + str(e))
				if self.serial:
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
	
	def close(self):
		logger.info(f"Device {self.name}: close serial/thread")
		self._stop_event.set()
		if self.serial and self.serial.is_open:
			self.serial.close()
		if self.thread:
			self.thread.join(timeout=3)
			if self.thread.is_alive():
				raise RuntimeError("Reader thread did not stop")

	def get_state(self):
		return DeviceState(state=DeviceState.ONLINE if self.serial and self.serial.is_open else DeviceState.OFFLINE)
	
	def raw_command(self):
		return super().raw_command()


	def wakeup_and_arm_reader(self):
		"""
		Initialisiert den Reader vollstÃ¤ndig:
		1. GET_INFO (Weckt den Kommunikationsstack)
		2. PCD_TYPEA_INIT (Aktiviert das 13.56 MHz Feld)
		3. SET RUNNING MODE (Startet das automatische Polling)
		"""
		# Die Adresse aus deiner GerÃ¤te-Config (netAdr: 1)
		addr = 0x01
		
		def send_internal_cmd(cmd_byte, data=[]):
			# Frame-Struktur: SOH, ADDR, LEN_MSB, LEN_LSB, CMD, DATA..., BCC
			length = len(data) + 1
			msg = [0x01, addr, (length >> 8) & 0xFF, length & 0xFF, cmd_byte] + data
			
			# BCC berechnen (XOR Ã¼ber alle Bytes im Paket)
			bcc = 0
			for b in msg:
				bcc ^= b
			msg.append(bcc)
			
			self.serial.write(bytes(msg))
			time.sleep(0.15) # Dem Reader Zeit zum Verarbeiten geben
			
			if self.serial.in_waiting > 0:
				return self.serial.read(self.serial.in_waiting)
			return None

		logging.info("Sende Wakeup-Sequenz an Reader...")

		# Schritt 1: GET_INFO (Index 00) - Der "Ping"
		# SOH(01) ADDR(01) LEN(0001) CMD(72) DATA(00) BCC(73)
		res_info = send_internal_cmd(0x72, [0x00])
		if res_info:
			logging.info(f"Reader gefunden: {res_info.hex()}")
		else:
			logging.warning("Keine Antwort auf GET_INFO (Reader evtl. schon wach?)")

		# Schritt 2: PCD_TYPEA_INIT - Antenne einschalten
		# SOH(01) ADDR(01) LEN(0001) CMD(20) BCC(21)
		res_init = send_internal_cmd(0x20)
		logging.info("Antennenfeld aktiviert.")

		# Schritt 3: SET RUNNING MODE (Mode 1 = Polling / Automatik)
		# SOH(01) ADDR(01) LEN(0001) CMD(5D) DATA(01) BCC(5D)
		res_mode = send_internal_cmd(0x5D, [0x01])
		
		if res_mode and res_mode[4] == 0x00: # Status Byte prÃ¼fen
			logging.info("Erfolg: Reader ist jetzt im automatischen Event-Modus.")
		else:
			logging.error("Fehler beim Setzen des Polling-Modus.")

		# Puffer leeren, damit nur noch neue Karten-Events kommen
		self.serial.reset_input_buffer()
	
	def parse_rfid_response(self, data_hex):
		# In Bytes umwandeln falls es ein String ist
		raw = bytes.fromhex(data_hex)
		
		if raw[0] != 0x01:
			logging.error('UngÃ¼ltiger Header')
			return None
		
		length = (raw[2] << 8) + raw[3]
		payload = raw[4:4+length]
		bcc_received = raw[-1]
		
		# BCC Validierung (XOR Ã¼ber alles vor dem BCC)
		bcc_calc = 0
		for b in raw[:-1]:
			bcc_calc ^= b
			
		if bcc_calc != bcc_received:
			logging.error("BCC Fehler (Daten korrupt)")
			return None
		
		
		if payload[0] != 0x31: # Event PICC_ACK
			logging.error("KEIN NFC EVENT")
			return None

		# Wenn du weiÃŸt, dass du 7-Byte Karten nutzt:
		uid_len = 7 
		
		# Alternativ: Dynamisch prÃ¼fen, ob das 7-Byte Flag im tag_info (0x74) steckt
		# Bei 0x74 ist oft Bit 6 oder 4 der Indikator fÃ¼r 7 Bytes
		if (payload[1] & 0x70) == 0x70: 
			uid_len = 7
		else:
			uid_len = 4

		uid = payload[2:2+uid_len]
		return uid.hex().upper()

	def start(self):
		if self.thread and self.thread.is_alive():
			return
		self._stop_event.clear()
		self.listen_in_thread()

	def execute_command(self, cmd: DeviceCommand, arg: CommandArgument | None = None) -> CommandResult:
		raise UnsupportedCommandError(cmd)

	@classmethod
	def get_capabilities(cls) -> DeviceCapabilities:
		return DeviceCapabilities(capabilities=("nfc_reader",))
