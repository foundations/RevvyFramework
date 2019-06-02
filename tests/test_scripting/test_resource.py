import unittest

from mock import Mock

from revvy.scripting.resource import Resource


class TestResource(unittest.TestCase):
    def test_empty_resource_can_be_taken(self):
        r = Resource()

        handle = r.request()
        self.assertIsNotNone(handle)

    def test_lower_priority_handle_can_be_taken_taken_away(self):
        r = Resource()

        mock = Mock()
        handle = r.request(0, mock)
        handle2 = r.request(1)
        self.assertIsNotNone(handle)
        self.assertEqual(True, handle.is_interrupted)
        self.assertIsNotNone(handle2)
        self.assertEqual(1, mock.call_count)

    def test_higher_priority_handle_can_not_be_taken_taken_away(self):
        r = Resource()

        mock = Mock()
        handle = r.request(1, mock)
        handle2 = r.request(0)
        self.assertIsNotNone(handle)
        self.assertEqual(False, handle.is_interrupted)
        self.assertIsNone(handle2)
        self.assertEqual(0, mock.call_count)

    def test_resource_handle_needed_to_release(self):
        r = Resource()

        handle = r.request(0)
        handle2 = r.request(1)
        r.release(handle)
        handle3 = r.request(0)
        self.assertIsNone(handle3)
        self.assertEqual(False, handle2.is_interrupted)

    def test_lower_priority_can_take_resource_after_higher_priority_releases(self):
        r = Resource()

        handle = r.request(1)
        handle.release()
        handle2 = r.request(0)
        self.assertIsNotNone(handle)
        self.assertEqual(False, handle.is_interrupted)
        self.assertIsNotNone(handle2)

    def test_run_should_only_run_on_active_handle(self):
        r = Resource()

        mock = Mock()

        handle = r.request(0)
        handle2 = r.request(1)

        handle2.run(mock)
        handle.run(lambda: self.fail('This should not run'))
        self.assertEqual(1, mock.call_count)
