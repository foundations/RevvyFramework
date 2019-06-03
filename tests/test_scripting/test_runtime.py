import time
import unittest
from mock import Mock

from revvy.scripting.robot_interface import RobotInterface
from revvy.scripting.runtime import ScriptManager


class TestRuntime(unittest.TestCase):
    def test_string_script_can_access_assigned_variables(self):
        robot_mock = Mock()
        robot_mock.resources = []
        robot_mock._motor_ports = []
        robot_mock._sensor_ports = []
        robot_mock._remote_controller = Mock()
        robot_mock._remote_controller.is_button_pressed = Mock(return_value=False)

        mock = Mock()

        sm = ScriptManager(robot_mock)
        sm.assign('mock', mock)
        sm.assign('test', self)
        sm.assign('RobotInterface', RobotInterface)
        sm.add_script('test', '''
test.assertIsInstance(robot, RobotInterface)
mock()''')

        sm['test'].start()
        time.sleep(0.0000001)
        sm['test'].cleanup()

        self.assertEqual(1, mock.call_count)
