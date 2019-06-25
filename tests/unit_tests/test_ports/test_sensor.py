import unittest

from mock import Mock

from revvy.ports.common import PortInstance
from revvy.ports.sensor import SensorPortHandler


class TestSensorPortHandler(unittest.TestCase):
    def test_reset_reads_port_amount_and_types(self):
        configs = {"NotConfigured": {}}

        mock_control = Mock()
        mock_control.get_sensor_port_amount = Mock(return_value=4)
        mock_control.get_sensor_port_types = Mock(return_value={"NotConfigured": 0, "BumperSwitch": 1, "HC_SR04": 2})

        ports = SensorPortHandler(mock_control, configs)
        ports.reset()

        self.assertEqual(1, mock_control.get_sensor_port_amount.call_count)
        self.assertEqual(1, mock_control.get_sensor_port_types.call_count)

        self.assertEqual(4, ports.port_count)

    def test_motor_ports_are_indexed_from_one(self):
        configs = {"NotConfigured": {}}

        mock_control = Mock()
        mock_control.get_sensor_port_amount = Mock(return_value=4)
        mock_control.get_sensor_port_types = Mock(return_value={"NotConfigured": 0})

        ports = SensorPortHandler(mock_control, configs)
        ports.reset()

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

        ports = SensorPortHandler(mock_control, configs)
        ports.reset()

        self.assertIs(PortInstance, type(ports[1]))
        self.assertEqual(0, mock_control.set_sensor_port_type.call_count)

        ports[1].configure("NotConfigured")
        self.assertEqual(1, mock_control.set_sensor_port_type.call_count)

        self.assertRaises(KeyError, lambda: ports[1].configure("Test"))
        self.assertEqual(1, mock_control.set_sensor_port_type.call_count)

