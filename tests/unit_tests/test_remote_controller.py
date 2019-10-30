# SPDX-License-Identifier: GPL-3.0-only

import unittest
from unittest.mock import Mock

from revvy.robot.remote_controller import RemoteController, RemoteControllerCommand


class TestRemoteController(unittest.TestCase):
    def test_buttons_are_edge_triggered(self):
        rc = RemoteController()
        mocks = []
        for i in range(32):
            mock = Mock()
            rc.on_button_pressed(i, mock)
            mocks.append(mock)

        for i in range(32):
            buttons = [False] * 32

            rc.tick(RemoteControllerCommand(buttons=buttons, analog=[0] * 10))

            # ith button is pressed
            buttons[i] = True
            rc.tick(RemoteControllerCommand(buttons=buttons, analog=[0] * 10))

            # button is kept pressed
            rc.tick(RemoteControllerCommand(buttons=buttons, analog=[0] * 10))

            for j in range(32):
                self.assertEqual(mocks[j].call_count, 1 if i == j else 0)
                mocks[j].reset_mock()

    def test_last_button_pressed_state_can_be_read(self):
        rc = RemoteController()
        rc.tick(RemoteControllerCommand(buttons=[False] * 32, analog=[0] * 10))

        for i in range(32):
            buttons = [False] * 32
            # ith button is pressed
            buttons[i] = True

            rc.tick(RemoteControllerCommand(buttons=buttons, analog=[0] * 10))

            for j in range(32):
                self.assertEqual(buttons[i], rc.is_button_pressed(i))

    def test_last_analog_channel_state_can_be_read(self):
        rc = RemoteController()

        for i in range(10):
            analog = [0] * 10
            # ith button is pressed
            analog[i] = 255

            rc.tick(RemoteControllerCommand(buttons=[False]*32, analog=analog))

            for j in range(10):
                self.assertEqual(analog[i], rc.analog_value(i))

    def test_requested_channels_are_passed_to_analog_handlers(self):
        rc = RemoteController()
        mock24 = Mock()
        mock3 = Mock()
        mock_invalid = Mock()

        rc.on_analog_values([2, 4], mock24)
        rc.on_analog_values([3], mock3)
        rc.on_analog_values([3, 11], mock_invalid)

        rc.tick(RemoteControllerCommand(buttons=[False] * 32, analog=[255, 254, 253, 123, 43, 65, 45, 42]))

        self.assertEqual(mock24.call_count, 1)
        self.assertEqual(mock3.call_count, 1)

        # invalid channels are silently ignored
        self.assertEqual(mock_invalid.call_count, 0)

        self.assertEqual(mock24.call_args[0][0], [253, 43])
        self.assertEqual(mock3.call_args[0][0], [123])

    def test_error_raised_for_invalid_button(self):
        rc = RemoteController()
        self.assertRaises(IndexError, lambda: rc.on_button_pressed(32, lambda: None))

    def test_reset_removed_button_and_analog_handlers_and_clears_stored_data(self):
        mock = Mock()
        rc = RemoteController()
        rc.tick(RemoteControllerCommand(buttons=[False] * 32, analog=[]))

        rc.on_analog_values([2, 4], mock)
        rc.on_analog_values([3], mock)

        rc.on_button_pressed(5, mock)

        rc.tick(RemoteControllerCommand(buttons=[True] * 32, analog=[255, 254, 253, 123, 43, 65, 45, 42]))

        self.assertEqual(3, mock.call_count)
        self.assertEqual(254, rc.analog_value(1))
        self.assertTrue(rc.is_button_pressed(1))

        mock.reset_mock()

        rc.reset()

        self.assertEqual(0, rc.analog_value(1))
        self.assertFalse(rc.is_button_pressed(1))

        rc.tick(RemoteControllerCommand(buttons=[True] * 32, analog=[255, 254, 253, 123, 43, 65, 45, 42]))

        self.assertEqual(0, mock.call_count)

    def test_remote_controller_buttons_need_initial_zero_state(self):
        mock = Mock()
        rc = RemoteController()

        rc.on_button_pressed(5, mock)

        rc.tick(RemoteControllerCommand(buttons=[True] * 32, analog=[]))

        self.assertEqual(0, mock.call_count)
        self.assertFalse(rc.is_button_pressed(1))

        rc.tick(RemoteControllerCommand(buttons=[False] * 32, analog=[]))
        rc.tick(RemoteControllerCommand(buttons=[True] * 32, analog=[]))

        self.assertEqual(1, mock.call_count)
        self.assertTrue(rc.is_button_pressed(1))

        rc.tick(RemoteControllerCommand(buttons=[False] * 32, analog=[]))
        mock.reset_mock()
        rc.reset()

        rc.tick(RemoteControllerCommand(buttons=[True] * 32, analog=[]))
        rc.tick(RemoteControllerCommand(buttons=[True] * 32, analog=[]))

        self.assertEqual(0, mock.call_count)
        self.assertFalse(rc.is_button_pressed(1))
