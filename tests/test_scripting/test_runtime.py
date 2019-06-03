import time
import unittest
from mock import Mock

from revvy.scripting.robot_interface import RobotInterface
from revvy.scripting.runtime import ScriptManager


def create_robot_mock():
    robot_mock = Mock()
    robot_mock._ring_led = Mock()
    robot_mock._ring_led.count = 6
    robot_mock.resources = []
    robot_mock._motor_ports = []
    robot_mock._sensor_ports = []
    robot_mock._remote_controller = Mock()
    robot_mock._remote_controller.is_button_pressed = Mock(return_value=False)

    return robot_mock


class TestRuntime(unittest.TestCase):
    def test_string_script_can_access_assigned_variables(self):
        robot_mock = create_robot_mock()

        mock = Mock()

        sm = ScriptManager(robot_mock)
        sm.assign('mock', mock)
        sm.assign('test', self)
        sm.assign('RobotInterface', RobotInterface)
        sm.add_script('test', '''
test.assertIsInstance(robot, RobotInterface)
mock()''')

        sm['test'].start()
        time.sleep(0.1)
        sm['test'].cleanup()

        self.assertEqual(1, mock.call_count)

    def test_variables_are_passed_to_callable_script_as_args(self):
        robot_mock = create_robot_mock()

        mock = Mock()

        sm = ScriptManager(robot_mock)
        sm.assign('mock', mock)
        sm.assign('test', self)
        sm.assign('RobotInterface', RobotInterface)

        def _script(args):
            args['test'].assertIsInstance(args['robot'], RobotInterface)
            args['mock']()

        sm.add_script('test', _script)

        sm['test'].start()
        time.sleep(0.1)
        sm['test'].cleanup()

        self.assertEqual(1, mock.call_count)

    def test_string_script_can_access_variables_assigned_after_creation(self):
        robot_mock = create_robot_mock()

        mock = Mock()

        sm = ScriptManager(robot_mock)
        sm.add_script('test', '''
test.assertIsInstance(robot, RobotInterface)
mock()''')
        sm.assign('mock', mock)
        sm.assign('test', self)
        sm.assign('RobotInterface', RobotInterface)

        sm['test'].start()
        time.sleep(0.1)
        sm['test'].cleanup()

        self.assertEqual(1, mock.call_count)

    def test_overwriting_a_script_stops_the_previous_one(self):
        robot_mock = create_robot_mock()

        mock = Mock()
        stopped_mock = Mock()

        sm = ScriptManager(robot_mock)
        sm.add_script('test', '''
while not ctx.stop_requested:
    pass
mock()''')
        sm.assign('mock', mock)

        # first call, make sure the script runs
        sm['test'].on_stopped(stopped_mock)
        sm['test'].start()
        time.sleep(0.1)

        # add second script
        sm.add_script('test', 'mock()')

        # check that the first script ran and was stopped
        self.assertEqual(1, mock.call_count)
        self.assertEqual(1, stopped_mock.call_count)

        # run and check second script
        sm['test'].on_stopped(stopped_mock)
        sm['test'].start()
        time.sleep(0.1)

        # test that stop also stops a script
        sm['test'].stop()

        self.assertEqual(2, mock.call_count)
        self.assertEqual(2, stopped_mock.call_count)

        sm['test'].cleanup()

    def test_resetting_the_manager_stops_running_scripts(self):
        robot_mock = create_robot_mock()

        stopped_mock = Mock()

        sm = ScriptManager(robot_mock)
        sm.add_script('test', '''
while not ctx.stop_requested:
    pass
''')
        sm.add_script('test2', '''
while not ctx.stop_requested:
    pass
''')

        # first call, make sure the script runs
        sm['test'].on_stopped(stopped_mock)
        sm['test2'].on_stopped(stopped_mock)
        sm['test'].start()
        sm['test2'].start()
        time.sleep(0.1)

        sm.reset()

        self.assertEqual(2, stopped_mock.call_count)
