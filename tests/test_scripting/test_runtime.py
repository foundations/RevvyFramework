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

    def test_script_can_stop_itself(self):
        robot_mock = create_robot_mock()

        mock = Mock()

        sm = ScriptManager(robot_mock)
        sm.add_script('test', '''
while not ctx.stop_requested:
    mock()
    Control.terminate()
    mock()
''')
        sm.assign('mock', mock)

        # first call, make sure the script runs
        sm['test'].start()
        time.sleep(0.1)

        self.assertEqual(1, mock.call_count)
        sm.reset()

    def test_script_can_stop_other_scripts(self):
        robot_mock = create_robot_mock()

        mock1 = Mock()
        mock2 = Mock()

        sm = ScriptManager(robot_mock)
        sm.add_script('test1', '''
mock()
time.sleep(0.1)
while not ctx.stop_requested:
    Control.terminate_all()
''')
        sm.add_script('test2', '''
mock()
while not ctx.stop_requested:
    time.sleep(0.1)
''')
        sm['test1'].assign('mock', mock1)
        sm['test2'].assign('mock', mock2)

        # first call, make sure the script runs
        sm['test1'].start()
        sm['test2'].start()
        time.sleep(0.2)

        # scripts started?
        self.assertEqual(1, mock1.call_count)
        self.assertEqual(1, mock2.call_count)
        self.assertFalse(sm['test1'].is_running)
        self.assertFalse(sm['test2'].is_running)

        sm.reset()
