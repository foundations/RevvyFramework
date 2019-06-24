import unittest
from mock import Mock

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
        self.assertEqual((0, 0), mock.call_args[0])

    def test_vertical_position_is_drive(self):
        mock = Mock()

        robot = Mock()
        robot.drivetrain = Mock()
        robot.drivetrain.set_speeds = mock

        args = {'robot': robot, 'input': [127, 255]}
        drive_joystick(args)
        self.assertEqual((900, 900), mock.call_args[0])

        args = {'robot': robot, 'input': [127, 0]}
        drive_joystick(args)
        self.assertEqual((-900, -900), mock.call_args[0])


class TestStickDriveScripts(unittest.TestCase):
    def test_middle_position_is_idle(self):
        mock = Mock()

        robot = Mock()
        robot.drivetrain = Mock()
        robot.drivetrain.set_speeds = mock

        args = {'robot': robot, 'input': [127, 127]}
        drive_2sticks(args)
        self.assertEqual(1, mock.call_count)
        self.assertEqual((0, 0), mock.call_args[0])

    def test_right_stick_is_drive(self):
        mock = Mock()

        robot = Mock()
        robot.drivetrain = Mock()
        robot.drivetrain.set_speeds = mock

        args = {'robot': robot, 'input': [127, 255]}
        drive_joystick(args)
        self.assertEqual((900, 900), mock.call_args[0])

        args = {'robot': robot, 'input': [127, 0]}
        drive_joystick(args)
        self.assertEqual((-900, -900), mock.call_args[0])
