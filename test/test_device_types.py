import threading
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from app.driver.driver_factory import DRIVERS
from app.driver.dummy_serial import DummyNfcReader, DummyDataScanner
from app.driver.types.nfc_reader import NfcReader, NfcData
from app.driver.types.data_scanner import DataScanner, DataScannerData
from app.driver.types.switch import Switch
from app.driver.types.parking_barrier import ParkingBarrier


class DeviceTypeTests(unittest.TestCase):
    def test_declared_types_match_inheritance(self):
        for name, driver in DRIVERS.items():
            for capability, interface in [('nfc_reader', NfcReader), ('data_scanner', DataScanner),
                                          ('switch', Switch), ('parking_barrier', ParkingBarrier)]:
                with self.subTest(driver=name, capability=capability):
                    self.assertEqual(capability in driver.get_capabilities().capabilities,
                                     issubclass(driver, interface))

    def test_nfc_subscription_pipeline_and_device_id(self):
        received = threading.Event()
        events = []
        with patch('app.state.nfc.set_latest_nfc_data') as legacy:
            driver = DummyNfcReader({'id': str(uuid4()), 'port': 'dummy://nfcreader/types?interval=0.01'})
            def callback(data):
                events.append(data)
                received.set()
            driver.subscribe(callback)
            driver.subscribe(callback)
            try:
                driver.start()
                original = driver.thread
                driver.start()
                self.assertIs(original, driver.thread)
                self.assertTrue(received.wait(2))
            finally:
                driver.close()
            self.assertFalse(driver.thread.is_alive())
            self.assertTrue(all(isinstance(data, NfcData) and data.deviceId == driver.device_id for data in events))
            self.assertEqual(legacy.call_count, len(events))
            driver.unsubscribe(callback)
            count = len(events)
            driver.publish_nfc(NfcData('TEST'))
            self.assertEqual(len(events), count)
            with self.assertRaises(TypeError):
                driver.publish_nfc('not an event')

    def test_subscriber_failure_does_not_drop_other_deliveries(self):
        with patch('app.state.dscanner.set_latest_dscanner_data') as legacy:
            scanner = DummyDataScanner({'id': str(uuid4()), 'port': 'dummy://datascanner/types'})
            broken = Mock(side_effect=RuntimeError('subscriber failed'))
            good = Mock()
            scanner.subscribe(broken)
            scanner.subscribe(good)
            event = DataScannerData(type='raw', data='example')
            with self.assertLogs('app.driver.types.reader', level='ERROR'):
                scanner.publish_scan(event)
            legacy.assert_called_once_with(event)
            good.assert_called_once_with(event)
            self.assertEqual(event.id, scanner.device_id)
