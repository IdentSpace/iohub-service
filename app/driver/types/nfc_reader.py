from app.driver.types.reader import ReaderBase
from app.driver.types.capabilities import DeviceCapabilities
from abc import ABC, abstractmethod
from datetime import datetime
from urllib.parse import urlencode


class NfcData:
	def __init__(self, uid: str, deviceId: str = None):
		self.uid = uid
		self.deviceId = deviceId
		self.timestamp = datetime.now()

	def toUrlQuery(self) -> str:
		params = {
			"UID": self.uid,
			"device_id": self.deviceId
		}

		params["timestamp"] = self.timestamp.isoformat()

		return "?" + urlencode(params)

class NfcReader(ReaderBase[NfcData]):
    def _init_nfc(self, device_id):
        # Compatibility adapter for existing direct driver users.
        from app.state.nfc import set_latest_nfc_data
        self._init_events(device_id, set_latest_nfc_data)

    def publish_nfc(self, data: NfcData) -> None:
        if not isinstance(data, NfcData):
            raise TypeError("Expected NfcData")
        if not data.uid:
            return
        data.deviceId = self.device_id
        self._emit(data)

    @classmethod
    def get_capabilities(cls) -> DeviceCapabilities:
        return DeviceCapabilities(capabilities=("nfc_reader",))
