import unittest
from uuid import uuid4
from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.v2.devices import router
from app.driver.types.device import CommandResult, DeviceState
from app.driver.driver_factory import DRIVERS


class DevicesV2Tests(unittest.TestCase):
    def setUp(self):
        self.device_id = str(uuid4())
        self.config = dict(id=self.device_id, name='Relay', device_type_name='switch',
                           device_driver_name='shelly_http')
        app = FastAPI()
        app.include_router(router, prefix='/api/v2')
        self.client = TestClient(app)
        self.lookup = patch('app.devices.device_manager.get_device', return_value=self.config)
        self.lookup.start()
        self.addCleanup(self.lookup.stop)
        self.base = '/api/v2/devices/' + self.device_id

    def test_discovery_has_options_without_hardware_access(self):
        with patch('app.devices.device_manager.get_devices', return_value=[self.config]), patch(
                'app.devices.device_manager.runtime_devices.get_driver') as hardware:
            response = self.client.get('/api/v2/devices')
            self.assertEqual(response.status_code, 200)
            item = response.json()['items'][0]
            options = item['capabilities']['commands'][0]['argument']['options']
            self.assertEqual([o['value'] for o in options], ['on', 'off'])
            self.assertEqual([o['label'] for o in options], ['argument.on', 'argument.off'])
            self.assertEqual(item['capabilities']['commands'][0]['label'], 'command.switch')
            self.assertEqual(self.client.get(self.base).status_code, 200)
            self.assertEqual(self.client.get(self.base + '/capabilities').status_code, 200)
            hardware.assert_not_called()

    def test_command_validation_happens_before_dispatch(self):
        with patch('app.devices.device_manager.runtime_devices.execute_command',
                   return_value=CommandResult(True)) as execute:
            for body in ({'cmd': 'missing'}, {'cmd': 'switch'},
                         {'cmd': 'switch', 'arg': 'invalid'}, {'cmd': 'open'},
                         {'cmd': 'switch', 'arg': 'on', 'unexpected': True}):
                self.assertEqual(self.client.post(self.base + '/commands', json=body).status_code, 422)
            execute.assert_not_called()
            self.assertEqual(self.client.post(self.base + '/commands', json={
                'cmd': 'switch', 'arg': 'on'}).status_code, 200)
            execute.assert_called_once()

    def test_barrier_rejects_argument_and_accepts_open(self):
        self.config['device_driver_name'] = 'as1620'
        with patch('app.devices.device_manager.runtime_devices.execute_command',
                   return_value=CommandResult(True)) as execute:
            self.assertEqual(self.client.post(self.base + '/commands', json={
                'cmd': 'open', 'arg': 'on'}).status_code, 422)
            execute.assert_not_called()
            self.assertEqual(self.client.post(self.base + '/commands', json={'cmd': 'open'}).status_code, 200)

    def test_state_normalization(self):
        with patch('app.devices.device_manager.runtime_devices.get_state',
                   return_value=DeviceState('online', power_state=True)):
            state = self.client.get(self.base + '/state').json()
            self.assertEqual(state['connection'], 'online')
            self.assertEqual(state['values'], {'power': True})
            self.assertIn('observed_at', state)

    def test_errors_and_missing_devices(self):
        with patch('app.devices.device_manager.get_device', return_value=None):
            self.assertEqual(self.client.get(self.base).status_code, 404)
        with patch('app.devices.device_manager.runtime_devices.execute_command',
                   return_value=CommandResult(False)):
            self.assertEqual(self.client.post(self.base + '/commands', json={
                'cmd': 'switch', 'arg': 'on'}).status_code, 502)
        self.config['device_driver_name'] = 'unknown'
        self.assertEqual(self.client.get(self.base + '/capabilities').status_code, 409)

    def test_all_registered_drivers_describe_valid_capabilities(self):
        for name, driver in DRIVERS.items():
            with self.subTest(driver=name):
                capabilities = driver.get_capabilities()
                for command in capabilities.commands:
                    if command.argument:
                        for option in command.argument.options:
                            capabilities.validate_command(command.cmd, option.value)
                    else:
                        capabilities.validate_command(command.cmd, None)

    def test_openapi_exposes_enum_and_response_schemas(self):
        schema = self.client.get('/openapi.json').json()
        self.assertIn(self.base.replace(self.device_id, '{device_id}') + '/commands', schema['paths'])
        self.assertEqual(schema['components']['schemas']['DeviceCommand']['enum'], ['switch', 'open', 'close'])


    def test_labels_are_translation_slugs(self):
        from pydantic import ValidationError
        from app.driver.types.capabilities import StateField
        with self.assertRaises(ValidationError):
            StateField(key="moving", label="In Bewegung", type="boolean")
        barrier = DRIVERS['as1620'].get_capabilities()
        self.assertEqual([command.label for command in barrier.commands],
                         ['command.open', 'command.close'])
        for driver in DRIVERS.values():
            capabilities = driver.get_capabilities()
            for field in capabilities.state_fields:
                self.assertEqual(field.label, 'state.' + field.key)
