import unittest
from unittest.mock import Mock

from application.activation import EdgeTrigger


class TestEdgeTrigger(unittest.TestCase):
    def test_missing_callbacks_cause_no_error(self):
        trigger = EdgeTrigger()

        trigger.handle(0)
        trigger.handle(1)
        trigger.handle(2)
        trigger.handle(1)
        trigger.handle(0)

    def test_edge_detection(self):

        rising = Mock()
        falling = Mock()

        trigger = EdgeTrigger()
        trigger.onRisingEdge(rising)
        trigger.onFallingEdge(falling)

        rising.assert_not_called()
        falling.assert_not_called()

        trigger.handle(0)
        trigger.handle(0)
        trigger.handle(0)
        trigger.handle(1)
        trigger.handle(1)
        trigger.handle(1)

        rising.assert_called_once()
        falling.assert_not_called()

        trigger.handle(0)
        trigger.handle(0)
        trigger.handle(0)

        rising.assert_called_once()
        falling.assert_called_once()

    def test_rising_edge_is_triggered_on_increasing_values(self):

        rising = Mock()
        falling = Mock()

        trigger = EdgeTrigger()
        trigger.onRisingEdge(rising)
        trigger.onFallingEdge(falling)

        rising.assert_not_called()

        trigger.handle(1)
        trigger.handle(2)
        trigger.handle(3)

        self.assertEqual(rising.call_count, 3)
        falling.assert_not_called()

        trigger.handle(2)
        trigger.handle(1)
        trigger.handle(0)

        self.assertEqual(rising.call_count, 3)
        self.assertEqual(falling.call_count, 3)
