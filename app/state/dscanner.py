from threading import Lock
from app.driver.types.data_scanner import DataScannerData
from app.core.webhook_dispatcher import enqueue_webhook
import logging

logger = logging.getLogger(__name__)


dscanner_lock = Lock()
# TODO: Refactor to array
latest_dscanner_data = None

def get_latest_dscanner_data():
	"""Read the last scan without consuming it."""
	with dscanner_lock:
		return latest_dscanner_data

def set_latest_dscanner_data(data: DataScannerData):
	global latest_dscanner_data
	with dscanner_lock:
		latest_dscanner_data = data
	enqueue_webhook("WEBHOOK_DATASCANNER", data.toUrlQuery())



def pop_latest_dscanner_data():
	global latest_dscanner_data
	with dscanner_lock:
		latest_dscanner_data = None

def get_and_pop_latest_dscanner_data():
	global latest_dscanner_data
	try:
		with dscanner_lock:
			# Pop the latest dscanner data and return it
			to_return = latest_dscanner_data
			latest_dscanner_data = None
			return to_return
	except Exception as e:
		logger.exception("Error getting latest data scanner data")
		return None
