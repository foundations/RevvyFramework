import unittest

from revvy.bluetooth.longmessage import LongMessageStorage, LongMessageHandler, LongMessageProtocol
from revvy.file_storage import MemoryStorage


class TestLongMessageRead(unittest.TestCase):
    def test_reading_unused_message_returns_zero(self):
        persistent = MemoryStorage()
        temp = MemoryStorage()

        storage = LongMessageStorage(persistent, temp)
        handler = LongMessageHandler(storage)
        ble = LongMessageProtocol(handler)

        ble.handle_write(0, [2])  # select long message 2
        result = ble.handle_read()

        # unused long message response is a 0 byte
        self.assertEqual(b'\x00', result)
