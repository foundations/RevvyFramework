import unittest

from revvy.longmessage import LongMessageHandler, LongMessageError, LongMessageType


class TestLongMessageHandler(unittest.TestCase):
    def test_init_is_required_before_write_and_finalize(self):
        handler = LongMessageHandler(None)

        self.assertRaises(LongMessageError, lambda: handler.upload_message([1]))
        self.assertRaises(LongMessageError, handler.finalize_message)

    def test_select_validates_longmessage_type(self):
        handler = LongMessageHandler(None)

        self.assertRaises(LongMessageError, lambda: handler.select_long_message_type(0))
        self.assertRaises(LongMessageError, lambda: handler.select_long_message_type(5))

        handler.select_long_message_type(LongMessageType.FIRMWARE_DATA)
        handler.select_long_message_type(LongMessageType.FRAMEWORK_DATA)
        handler.select_long_message_type(LongMessageType.CONFIGURATION_DATA)
        handler.select_long_message_type(LongMessageType.TEST_KIT)
