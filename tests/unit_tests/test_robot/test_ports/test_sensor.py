import unittest

from mock import Mock

from revvy.robot.ports.common import PortInstance
from revvy.robot.ports.sensor import create_sensor_port_handler, BaseSensorPortDriver, bumper_switch, hcsr04


class TestSensorPortHandler(unittest.TestCase):
    def test_constructor_reads_port_amount_and_types(self):
        configs = {"NotConfigured": {}}

        mock_control = Mock()
        mock_control.get_sensor_port_amount = Mock(return_value=4)
        mock_control.get_sensor_port_types = Mock(return_value={"NotConfigured": 0, "BumperSwitch": 1, "HC_SR04": 2})

        ports = create_sensor_port_handler(mock_control, configs)

        self.assertEqual(1, mock_control.get_sensor_port_amount.call_count)
        self.assertEqual(1, mock_control.get_sensor_port_types.call_count)

        self.assertEqual(4, ports.port_count)

    def test_motor_ports_are_indexed_from_one(self):
        configs = {"NotConfigured": {}}

        mock_control = Mock()
        mock_control.get_sensor_port_amount = Mock(return_value=4)
        mock_control.get_sensor_port_types = Mock(return_value={"NotConfigured": 0})

        ports = create_sensor_port_handler(mock_control, configs)

        self.assertRaises(KeyError, lambda: ports[0])
        self.assertIs(PortInstance, type(ports[1]))
        self.assertIs(PortInstance, type(ports[2]))
        self.assertIs(PortInstance, type(ports[3]))
        self.assertIs(PortInstance, type(ports[4]))
        self.assertRaises(KeyError, lambda: ports[5])

    def test_configure_raises_error_if_driver_is_not_supported_in_mcu(self):
        configs = {
            "NotConfigured": {'driver': 'NotConfigured', 'config': {}},
            "Test": {'driver': "NonExistentDriver"}
        }

        mock_control = Mock()
        mock_control.get_sensor_port_amount = Mock(return_value=4)
        mock_control.get_sensor_port_types = Mock(return_value={"NotConfigured": 0})
        mock_control.set_sensor_port_type = Mock()

        ports = create_sensor_port_handler(mock_control, configs)

        self.assertIs(PortInstance, type(ports[1]))
        self.assertEqual(0, mock_control.set_sensor_port_type.call_count)

        self.assertRaises(KeyError, lambda: ports[1].configure("Test"))
        self.assertEqual(0, mock_control.set_sensor_port_type.call_count)

    def test_unconfiguring_not_configured_port_does_nothing(self):
        configs = {
            "NotConfigured": {'driver': 'NotConfigured', 'config': {}},
            "Test": {'driver': "NonExistentDriver"}
        }

        mock_control = Mock()
        mock_control.get_sensor_port_amount = Mock(return_value=6)
        mock_control.get_sensor_port_types = Mock(return_value={"NotConfigured": 0})
        mock_control.set_sensor_port_type = Mock()

        ports = create_sensor_port_handler(mock_control, configs)

        self.assertIs(PortInstance, type(ports[1]))
        self.assertEqual(0, mock_control.set_motor_port_type.call_count)

        ports[1].configure("NotConfigured")
        self.assertEqual(0, mock_control.set_motor_port_type.call_count)


def create_port():

    port = Mock()
    port.id = 3
    port.interface = Mock()
    port.interface.get_sensor_port_value = Mock()

    return port


class TestBaseSensorPortDriver(unittest.TestCase):

    def test_port_has_no_data_before_first_read(self):
        port = create_port()

        sensor = BaseSensorPortDriver(port)
        sensor.convert_sensor_value = Mock(return_value=5)

        self.assertFalse(sensor.has_data)
        sensor.read()
        self.assertEqual(1, port.interface.get_sensor_port_value.call_count)
        self.assertEqual(3, port.interface.get_sensor_port_value.call_args[0][0])

        self.assertEqual(1, sensor.convert_sensor_value.call_count)
        self.assertTrue(sensor.has_data)


class TestBumperSwitch(unittest.TestCase):

    def test_bumper_returns_boolean(self):
        port = create_port()

        port.interface.get_sensor_port_value.side_effect = [[1, 1], [0, 0], [0, 1]]

        sensor = bumper_switch(port, None)

        sensor.read()
        self.assertTrue(sensor.value)

        sensor.read()
        self.assertFalse(sensor.value)

        sensor.read()
        self.assertFalse(sensor.value)


class TestHcSr04(unittest.TestCase):

    def test_sensor_has_no_value_before_first_nonzero_read(self):
        port = create_port()

        port.interface.get_sensor_port_value.side_effect = [
            bytes([0, 0, 0, 0]),
            bytes([0, 0, 0, 0]),
            bytes([5, 0, 0, 0]),  # little endian
            bytes([0, 0, 0, 0])]

        sensor = hcsr04(port, None)

        sensor.read()
        self.assertFalse(sensor.has_data)

        sensor.read()
        self.assertFalse(sensor.has_data)

        sensor.read()
        self.assertTrue(sensor.has_data)
        self.assertEqual(5, sensor.value)

        # if no valid data is read, substitute with last valid
        sensor.read()
        self.assertTrue(sensor.has_data)
        self.assertEqual(5, sensor.value)
