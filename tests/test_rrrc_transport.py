import unittest

from revvy.rrrc_transport import Command, crc7, crc16, RevvyTransport, RevvyTransportInterface, ResponseHeader


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


class MockInterface(RevvyTransportInterface):

    def __init__(self, read_responses):
        self._responses = read_responses
        self._writes = []
        self._reads = []
        self._counter = 0

    def read(self, length):
        idx = len(self._reads)
        self._reads.append((self._counter, length))
        self._counter += 1
        return self._responses[idx][0:length]

    def write(self, data):
        self._writes.append((self._counter, data))
        self._counter += 1


class TestRevvyTransport(unittest.TestCase):
    def test_only_one_write_if_immediate_successful_response(self):
        mock_interface = MockInterface([
            [ResponseHeader.Status_Ok, 0, 0xFF, 0xFF, 117]  # immediately respond with success
        ])
        rt = RevvyTransport(mock_interface)
        response = rt.send_command(10, [8, 9])  # some ping-type command
        self.assertEqual(2, mock_interface._counter)  # write, read header, no data
        self.assertEqual(1, len(mock_interface._writes))
        self.assertEqual(1, len(mock_interface._reads))
        self.assertEqual(0, mock_interface._writes[0][0])  # write happened first
        self.assertEqual(1, mock_interface._reads[0][0])  # read happened second
        self.assertListEqual(Command.start(10, [8, 9]).get_bytes(), mock_interface._writes[0][1])
        self.assertEqual(True, response.success)
        self.assertEqual(0, len(response.payload))

    def test_retry_reading_after_busy_response(self):
        mock_interface = MockInterface([
            [ResponseHeader.Status_Busy, 0, 0xFF, 0xFF, 118],
            [ResponseHeader.Status_Busy, 0, 0xFF, 0xFF, 118],
            [ResponseHeader.Status_Busy, 0, 0xFF, 0xFF, 118],
            [ResponseHeader.Status_Busy, 0, 0xFF, 0xFF, 118],
            [ResponseHeader.Status_Busy, 0, 0xFF, 0xFF, 118],
            [ResponseHeader.Status_Ok, 0, 0xFF, 0xFF, 117]  # finally respond with success
        ])
        rt = RevvyTransport(mock_interface)
        response = rt.send_command(10)  # some ping-type command
        self.assertEqual(1, len(mock_interface._writes))
        self.assertEqual(6, len(mock_interface._reads))
        self.assertEqual(0, mock_interface._writes[0][0])  # write happened first
        self.assertEqual(True, response.success)
        self.assertEqual(0, len(response.payload))

    def test_data_header_is_read_before_full_response(self):
        mock_interface = MockInterface([
            [ResponseHeader.Status_Ok, 2, 0xaf, 0x43, 121],  # respond with header first
            [ResponseHeader.Status_Ok, 2, 0xaf, 0x43, 121, 0x0a, 0x0b]  # respond with success
        ])
        rt = RevvyTransport(mock_interface)
        response = rt.send_command(10)  # some ping-type command
        self.assertEqual(True, response.success)
        self.assertEqual(2, len(mock_interface._reads))
        self.assertEqual(5, mock_interface._reads[0][1])
        self.assertEqual(7, mock_interface._reads[1][1])
        self.assertListEqual([0x0a, 0x0b], response.payload)

    def test_pending_is_retried_with_get_result(self):
        mock_interface = MockInterface([
            [ResponseHeader.Status_Pending, 0, 0xff, 0xff, 115],
            [ResponseHeader.Status_Pending, 0, 0xff, 0xff, 115],
            [ResponseHeader.Status_Pending, 0, 0xff, 0xff, 115],
            [ResponseHeader.Status_Ok, 2, 0xaf, 0x43, 121],             # respond with header first
            [ResponseHeader.Status_Ok, 2, 0xaf, 0x43, 121, 0x0a, 0x0b]  # respond with success
        ])
        rt = RevvyTransport(mock_interface)
        response = rt.send_command(10)  # some ping-type command
        self.assertEqual(True, response.success)
        self.assertEqual(4, len(mock_interface._writes))

        self.assertEqual(0, mock_interface._writes[0][0])
        self.assertEqual(Command.OpStart, mock_interface._writes[0][1][0])

        self.assertEqual(2, mock_interface._writes[1][0])
        self.assertEqual(Command.OpGetResult, mock_interface._writes[1][1][0])

        self.assertEqual(4, mock_interface._writes[2][0])
        self.assertEqual(Command.OpGetResult, mock_interface._writes[2][1][0])

        self.assertEqual(6, mock_interface._writes[3][0])
        self.assertEqual(Command.OpGetResult, mock_interface._writes[3][1][0])

        self.assertEqual(5, len(mock_interface._reads))
        self.assertListEqual([0x0a, 0x0b], response.payload)
