import unittest

from mock import Mock

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
