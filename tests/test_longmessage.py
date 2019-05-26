import unittest

from revvy.longmessage import LongMessageHandler, LongMessageError


class TestLongMessageHandler(unittest.TestCase):
    def test_init_is_required_before_write_and_finalize(self):
        handler = LongMessageHandler(None)

        self.assertRaises(LongMessageError, lambda: handler.upload_message([1]))
        self.assertRaises(LongMessageError, handler.finalize_message)
