from threading import Lock
import logging
from app.driver.types.nfc_reader import NfcData
from app.core.webhook_dispatcher import enqueue_webhook

logger = logging.getLogger(__name__)

nfc_lock = Lock()
latest_nfc_data = None

def get_latest_nfc_data():
	"""Read the latest card without consuming it."""
	with nfc_lock:
		return latest_nfc_data

def set_latest_nfc_data(data: NfcData):
	global latest_nfc_data
	if not data.uid:
		return
	with nfc_lock:
		latest_nfc_data = data
	enqueue_webhook("WEBHOOK_NFC", data.toUrlQuery())

def pop_latest_nfc_data():
	global latest_nfc_data
	with nfc_lock:
		latest_nfc_data = None

def get_and_pop_latest_nfc_data():
	global latest_nfc_data
	try:
		with nfc_lock:
			# Pop the latest NFC data and return it
			to_return = latest_nfc_data
			latest_nfc_data = None
			return to_return
	except Exception as e:
		logger.exception("Error getting latest NFC data")
		return None
