import unittest

from revvy.rrrc_transport import Command, crc7, crc16


class TestCommand(unittest.TestCase):
    def test_first_byte_is_opcode(self):
        ch = Command.start(5)
        self.assertEqual(0, ch.get_bytes()[0])

        ch = Command.get_result(5)
        self.assertEqual(2, ch.get_bytes()[0])

        ch = Command.cancel(5)
        self.assertEqual(3, ch.get_bytes()[0])

    def test_max_payload_length_is_255(self):
        ch = Command.start(5, [0]*25)
        self.assertEqual(6 + 25, len(ch.get_bytes()))
        self.assertEqual(25, ch.get_bytes()[2])

        ch = Command.start(5, [0]*255)
        self.assertEqual(6 + 255, len(ch.get_bytes()))
        self.assertEqual(255, ch.get_bytes()[2])

        self.assertRaises(ValueError, lambda: Command.start(5, [0] * 256))

    def test_empty_payload_header_is_ffff(self):
        ch = Command.start(5)

        self.assertListEqual([0xFF, 0xFF], ch.get_bytes()[3:5])

    def test_header_checksum_is_calculated_using_crc7(self):
        ch = Command.start(5)
        expected_checksum = crc7([Command.OpStart, 5, 0, 0xFF, 0xFF], 0xFF)

        self.assertEqual(expected_checksum, ch.get_bytes()[5])

    def test_header_checksum_includes_payload(self):
        ch = Command.start(5, [1, 2, 3])

        payload_checksum = bytes(crc16([1, 2, 3], 0xFFFF).to_bytes(2, byteorder='little'))

        checksum_if_payload_ffff = crc7([Command.OpStart, 5, 0, 0xFF, 0xFF], 0xFF)
        expected_checksum = crc7([Command.OpStart, 5, 0, *payload_checksum], 0xFF)

        self.assertNotEqual(checksum_if_payload_ffff, ch.get_bytes()[5])
        self.assertNotEqual(expected_checksum, ch.get_bytes()[5])
