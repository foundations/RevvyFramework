import hashlib
import unittest

from revvy.bluetooth.longmessage import LongMessageStorage, LongMessageHandler, LongMessageProtocol, bytes2hexdigest
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

    def test_read_returns_hash(self):
        persistent = MemoryStorage()
        persistent.write(2, b'abcd')

        md5_hash = hashlib.md5(b'abcd').hexdigest()

        temp = MemoryStorage()

        storage = LongMessageStorage(persistent, temp)
        handler = LongMessageHandler(storage)
        ble = LongMessageProtocol(handler)

        ble.handle_write(0, [2])  # select long message 2 (persistent)
        result = ble.handle_read()

        # reading a valid message returns its status, md5 hash and length
        self.assertEqual("03" + md5_hash + "00000004", bytes2hexdigest(result))
