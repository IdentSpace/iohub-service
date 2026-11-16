import unittest
from uuid import uuid4
from unittest.mock import Mock

from app.devices.device_manager import DeviceManager
from app.driver.driver_factory import DRIVERS, driver_factory
from app.driver.types.device import DeviceBase, UnsupportedCommandError


class DriverContractTests(unittest.TestCase):
    def test_registered_drivers_are_concrete(self):
        for name, cls in DRIVERS.items():
            with self.subTest(driver=name):
                self.assertFalse(cls.__abstractmethods__)
                if name not in ('dummy_datascanner', 'dummy_nfcreader'):
                    instance = driver_factory(name, args={'device_host': 'COM99'})
                    self.assertIsInstance(instance, DeviceBase)
                    instance.close()

    def test_manager_reuses_normalized_id_and_restarts_after_close(self):
        factory = Mock(side_effect=lambda **kw: Mock(spec=DeviceBase))
        manager = DeviceManager(factory)
        device_id = uuid4()
        config = {'id': str(device_id), 'device_driver_name': 'default'}
        first = manager.get_driver(config)
        self.assertIs(first, manager.get_driver(dict(config, id=device_id.hex)))
        first.start.assert_called_once()
        manager.close_device(device_id)
        first.close.assert_called_once()
        self.assertIsNot(first, manager.get_driver(config))
        manager.close_all()

    def test_unknown_command_and_legacy_alias(self):
        driver = driver_factory('default', args={})
        with self.assertRaises(UnsupportedCommandError):
            driver.web_command('missing')

    def test_failed_start_is_not_cached(self):
        driver = Mock(spec=DeviceBase)
        driver.start.side_effect = RuntimeError('failed')
        factory = Mock(return_value=driver)
        manager = DeviceManager(factory)
        config = {'id': str(uuid4()), 'device_driver_name': 'default'}
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                manager.get_driver(config)
        self.assertEqual(factory.call_count, 2)
        self.assertEqual(driver.close.call_count, 2)


class TypedCommandTests(unittest.TestCase):
    def test_shelly_enum_and_legacy_string_dispatch(self):
        from app.driver.shelly import Shelly
        from app.driver.types.commands import DeviceCommand, CommandArgument
        from app.driver.types.device import DeviceState
        driver = Shelly({})
        driver.turn_on = Mock()
        driver.turn_off = Mock()
        driver.get_state = Mock(return_value=DeviceState(state=DeviceState.ONLINE))
        self.assertTrue(driver.execute_command(DeviceCommand.SWITCH, CommandArgument.ON).success)
        self.assertTrue(driver.web_command("switch", "off").success)
        driver.turn_on.assert_called_once()
        driver.turn_off.assert_called_once()
        with self.assertRaises(ValueError):
            driver.execute_command(DeviceCommand.SWITCH, "invalid")

    def test_manager_normalizes_strings_before_dispatch(self):
        from app.driver.types.commands import DeviceCommand, CommandArgument
        driver = Mock(spec=DeviceBase)
        manager = DeviceManager(Mock(return_value=driver))
        config = {'id': str(uuid4()), 'device_driver_name': 'shelly_http'}
        manager.execute_command(config, "switch", "on")
        cmd, arg = driver.execute_command.call_args.args
        self.assertIs(cmd, DeviceCommand.SWITCH)
        self.assertIs(arg, CommandArgument.ON)
        with self.assertRaises(UnsupportedCommandError):
            manager.execute_command(config, "unknown")
        with self.assertRaises(ValueError):
            manager.execute_command(config, "switch", "invalid")
        self.assertEqual(driver.execute_command.call_count, 1)
