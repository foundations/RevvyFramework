import unittest
from mock import Mock, call

from revvy.scripting.builtin_scripts import drive_joystick, drive_2sticks


class TestJoystickScripts(unittest.TestCase):
    def test_middle_position_is_idle(self):
        mock = Mock()

        robot = Mock()
        robot.drivetrain = Mock()
        robot.drivetrain.set_speeds = mock

        args = {'robot': robot, 'input': [127, 127]}
        drive_joystick(args)
        self.assertEqual(1, mock.call_count)
        self.assertEqual(call(0, 0), mock.call_args)


class TestStickDriveScripts(unittest.TestCase):
    def test_middle_position_is_idle(self):
        mock = Mock()

        robot = Mock()
        robot.drivetrain = Mock()
        robot.drivetrain.set_speeds = mock

        args = {'robot': robot, 'input': [127, 127]}
        drive_2sticks(args)
        self.assertEqual(1, mock.call_count)
        self.assertEqual(call(0, 0), mock.call_args)
