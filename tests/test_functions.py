import unittest
from unittest.mock import Mock

from revvy.functions import retry


class TestRetry(unittest.TestCase):
    def test_dont_retry_when_successful(self):
        mock = Mock(return_value=True)
        retry(mock, 3)
        self.assertEqual(mock.call_count, 1)

    def test_dont_retry_when_none_is_returned(self):
        mock = Mock(return_value=None)
        retry(mock, 3)
        self.assertEqual(mock.call_count, 1)

    def test_retry_when_exception_is_thrown(self):
        mock = Mock(side_effect=IOError)
        retry(mock, 3)
        self.assertEqual(mock.call_count, 3)

    def test_retry_when_false_is_returned(self):
        mock = Mock(return_value=False)
        retry(mock, 3)
        self.assertEqual(mock.call_count, 3)
