from app.driver.shelly import Shelly
from app.driver.types.device import Default
from app.driver.default_data_scanner import DefaultDataScanner
from app.driver.dummy_serial import DummyDataScanner, DummyNfcReader
from app.driver.default_nfc_reader import DefaultNfcReader
from app.driver.as1620 import AS1620
from app.driver.feig_cpr0210 import CPR0210
from app.driver.gis_tshr import GiSTSHR
from app.driver.feig_cpr46 import CPR46
from app.driver.hoptschuler_890 import HoptSchuler890

DRIVERS = {
	"dummy_datascanner": DummyDataScanner,
	"dummy_nfcreader": DummyNfcReader,
	"shelly_http": Shelly,
	"default_datascanner": DefaultDataScanner,
	"default_nfcreader": DefaultNfcReader,
	"hoptschuler_890": HoptSchuler890,
	"feig_cpr0210": CPR0210,
	"feig_cpr46": CPR46,
	"gis_tshr": GiSTSHR,
	"as1620": AS1620,
	"default": Default
}

def driver_factory(driver_type: str, **kwargs):
	if "args" in kwargs:
		args = dict(kwargs["args"])
		args.setdefault("port", args.get("device_host"))
		kwargs["args"] = args
	if driver_type in DRIVERS:
		return DRIVERS[driver_type](**kwargs)
	else:
		return DRIVERS["default"](**kwargs)

# TODO: load into DB and co
def load_drivers():
	pass
