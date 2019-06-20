import unittest

from mock import Mock

from revvy.ports.motor import MotorPortHandler


class TestMotorPortHandler(unittest.TestCase):
    def test_reset_reads_port_amount_and_types(self):
        configs = {"NotConfigured": {}}

        mock_control = Mock()
        mock_control.get_motor_port_amount = Mock(return_value=6)
        mock_control.get_motor_port_types = Mock(return_value={"NotConfigured": 0, "DcMotor": 1})

        ports = MotorPortHandler(mock_control, configs)
        ports.reset()

        self.assertEqual(1, mock_control.get_motor_port_amount.call_count)
        self.assertEqual(1, mock_control.get_motor_port_types.call_count)

        self.assertEqual(6, ports.port_count)
