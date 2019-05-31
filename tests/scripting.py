import unittest

from mock import Mock

from revvy.scripting.resource import Resource


class TestResource(unittest.TestCase):
    def test_empty_resource_can_be_taken(self):
        r = Resource()

        handle = r.try_take()
        self.assertIsNotNone(handle)

    def test_lower_priority_handle_can_be_taken_taken_away(self):
        r = Resource()

        mock = Mock()
        handle = r.try_take(0, mock)
        handle2 = r.try_take(1)
        self.assertIsNotNone(handle)
        self.assertEqual(True, handle.is_interrupted)
        self.assertIsNotNone(handle2)
        self.assertEqual(1, mock.call_count)

    def test_higher_priority_handle_can_not_be_taken_taken_away(self):
        r = Resource()

        mock = Mock()
        handle = r.try_take(1, mock)
        handle2 = r.try_take(0)
        self.assertIsNotNone(handle)
        self.assertEqual(False, handle.is_interrupted)
        self.assertIsNone(handle2)
        self.assertEqual(0, mock.call_count)
