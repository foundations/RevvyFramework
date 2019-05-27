from threading import Lock

from revvy.functions import retry


def crc16(data, crc=0xFFFF):
    """
    CRC-16-CCITT Algorithm
    """
    crc16_table = [
        0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
        0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
        0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
        0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
        0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
        0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
        0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
        0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
        0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
        0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
        0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
        0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
        0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
        0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
        0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
        0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
        0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
        0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
        0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
        0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
        0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
        0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
        0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
        0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
        0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
        0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
        0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
        0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
        0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
        0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
        0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
        0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0]
    for b in data:
        crc = (crc16_table[(b ^ (crc >> 8)) & 0xFF] ^ (crc << 8)) & 0xFFFF

    return crc & 0xFFFF


def crc7(data, crc=0xFF):
    crc7_table = [
        0x00, 0x09, 0x12, 0x1b, 0x24, 0x2d, 0x36, 0x3f,
        0x48, 0x41, 0x5a, 0x53, 0x6c, 0x65, 0x7e, 0x77,
        0x19, 0x10, 0x0b, 0x02, 0x3d, 0x34, 0x2f, 0x26,
        0x51, 0x58, 0x43, 0x4a, 0x75, 0x7c, 0x67, 0x6e,
        0x32, 0x3b, 0x20, 0x29, 0x16, 0x1f, 0x04, 0x0d,
        0x7a, 0x73, 0x68, 0x61, 0x5e, 0x57, 0x4c, 0x45,
        0x2b, 0x22, 0x39, 0x30, 0x0f, 0x06, 0x1d, 0x14,
        0x63, 0x6a, 0x71, 0x78, 0x47, 0x4e, 0x55, 0x5c,
        0x64, 0x6d, 0x76, 0x7f, 0x40, 0x49, 0x52, 0x5b,
        0x2c, 0x25, 0x3e, 0x37, 0x08, 0x01, 0x1a, 0x13,
        0x7d, 0x74, 0x6f, 0x66, 0x59, 0x50, 0x4b, 0x42,
        0x35, 0x3c, 0x27, 0x2e, 0x11, 0x18, 0x03, 0x0a,
        0x56, 0x5f, 0x44, 0x4d, 0x72, 0x7b, 0x60, 0x69,
        0x1e, 0x17, 0x0c, 0x05, 0x3a, 0x33, 0x28, 0x21,
        0x4f, 0x46, 0x5d, 0x54, 0x6b, 0x62, 0x79, 0x70,
        0x07, 0x0e, 0x15, 0x1c, 0x23, 0x2a, 0x31, 0x38,
        0x41, 0x48, 0x53, 0x5a, 0x65, 0x6c, 0x77, 0x7e,
        0x09, 0x00, 0x1b, 0x12, 0x2d, 0x24, 0x3f, 0x36,
        0x58, 0x51, 0x4a, 0x43, 0x7c, 0x75, 0x6e, 0x67,
        0x10, 0x19, 0x02, 0x0b, 0x34, 0x3d, 0x26, 0x2f,
        0x73, 0x7a, 0x61, 0x68, 0x57, 0x5e, 0x45, 0x4c,
        0x3b, 0x32, 0x29, 0x20, 0x1f, 0x16, 0x0d, 0x04,
        0x6a, 0x63, 0x78, 0x71, 0x4e, 0x47, 0x5c, 0x55,
        0x22, 0x2b, 0x30, 0x39, 0x06, 0x0f, 0x14, 0x1d,
        0x25, 0x2c, 0x37, 0x3e, 0x01, 0x08, 0x13, 0x1a,
        0x6d, 0x64, 0x7f, 0x76, 0x49, 0x40, 0x5b, 0x52,
        0x3c, 0x35, 0x2e, 0x27, 0x18, 0x11, 0x0a, 0x03,
        0x74, 0x7d, 0x66, 0x6f, 0x50, 0x59, 0x42, 0x4b,
        0x17, 0x1e, 0x05, 0x0c, 0x33, 0x3a, 0x21, 0x28,
        0x5f, 0x56, 0x4d, 0x44, 0x7b, 0x72, 0x69, 0x60,
        0x0e, 0x07, 0x1c, 0x15, 0x2a, 0x23, 0x38, 0x31,
        0x46, 0x4f, 0x54, 0x5d, 0x62, 0x6b, 0x70, 0x79]

    for b in data:
        crc = crc7_table[(b ^ (crc << 1) & 0xFF)]
    return crc


class RevvyTransportInterface:
    def read(self, length):
        raise NotImplementedError()

    def write(self, data):
        raise NotImplementedError()

    def write_and_read(self, data, read_length):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()


class CommandHeader:
    OpStart = 0
    OpRestart = 1
    OpGetResult = 2
    OpCancel = 3

    def __init__(self, op, command, payload=None):
        self._op = op
        self._command = command
        self._payload = payload if payload else []

        if len(self._payload) > 255:
            raise ValueError('Payload is too long ({} bytes, 255 allowed)'.format(len(self._payload)))

    def get_bytes(self):
        header = [self._op, self._command, len(self._payload)]
        payload_checksum = crc16(self._payload)
        header += bytes(payload_checksum.to_bytes(2, byteorder='little'))
        header.append(crc7(header, 0xFF))

        return header

    @classmethod
    def start(cls, command, payload=None):
        return cls(cls.OpStart, command, payload)

    @classmethod
    def get_result(cls, command):
        return cls(cls.OpGetResult, command)

    @classmethod
    def cancel(cls, command):
        return cls(cls.OpCancel, command)


class Command:
    def get_bytes(self):
        raise NotImplementedError()


class CommandStart(Command):
    def __init__(self, command, payload=None):
        self._command = command
        self._header = CommandHeader.start(command, payload)
        self._payload = payload if payload else []

    def get_bytes(self):
        return self._header.get_bytes() + self._payload

    @property
    def command(self):
        return self._command


class CommandGetResult(Command):
    def __init__(self, command):
        self._header = CommandHeader.get_result(command)

    def get_bytes(self):
        return self._header.get_bytes()


class CommandCancel(Command):
    def __init__(self, command):
        self._header = CommandHeader.cancel(command)

    def get_bytes(self):
        return self._header.get_bytes()


class ResponseHeader:
    Status_Ok = 0
    Status_Busy = 1
    Status_Pending = 2

    Status_Error_UnknownOperation = 3
    Status_Error_InvalidOperation = 4
    Status_Error_CommandIntegrityError = 5
    Status_Error_PayloadIntegrityError = 6
    Status_Error_PayloadLengthError = 7
    Status_Error_UnknownCommand = 8
    Status_Error_CommandError = 9
    Status_Error_InternalError = 10

    StatusStrings = [
            "Ok",
            "Busy",
            "Pending",
            "Unknown operation",
            "Invalid operation",
            "Command integrity error",
            "Payload integrity error",
            "Payload length error",
            "Unknown command",
            "Command error",
            "Internal error"
        ]

    length = 5

    @staticmethod
    def is_valid_header(data):
        if len(data) >= ResponseHeader.length:
            checksum = crc7(data[0:ResponseHeader.length - 1])
            return checksum == data[4]

        return False

    def __init__(self, data):
        self._status = data[0]
        self._payload_length = data[1]
        self._payload_checksum = int.from_bytes(data[2:4], byteorder='little')
        self._header_checksum = data[4]

    def validate_payload(self, payload):
        return self._payload_checksum == crc16(payload, 0xFFFF)

    def is_same_header(self, header):
        return len(header) >= self.length \
               and self._status == header[0] \
               and self._payload_length == header[1] \
               and self._payload_checksum == int.from_bytes(header[2:4], byteorder='little') \
               and self._header_checksum == header[4]

    @property
    def status(self):
        return self._status

    @property
    def payload_length(self):
        return self._payload_length


class Response:
    def __init__(self, header: ResponseHeader, payload):
        self._header = header
        self._payload = payload

    @property
    def success(self):
        return self._header.status == ResponseHeader.Status_Ok

    @property
    def header(self):
        return self._header

    @property
    def payload(self):
        return self._payload


class RevvyTransport:
    def __init__(self, transport: RevvyTransportInterface):
        self._transport = transport
        self._mutex = Lock()

    def send_command(self, command, payload=None) -> Response:
        with self._mutex:
            # once a command gets through and a valid response is read, this loop will exit
            while True:
                # send command and read back status
                header = self._send_command(CommandStart(command, payload))

                # wait for command execution to finish
                while header.status == ResponseHeader.Status_Pending:
                    header = self._send_command(CommandGetResult(command))

                # check result
                # return a result even in case of an error, except when we know we have to resend
                if header.status != ResponseHeader.Status_Error_CommandIntegrityError:
                    response_payload = self._read_payload(header)
                    response = Response(header, response_payload)
                    return response

    def _read_response_header(self, retries=5):

        def _read_response_header_once():
            header_bytes = self._transport.read(ResponseHeader.length)
            has_valid_response = ResponseHeader.is_valid_header(header_bytes)
            if not has_valid_response:
                return False
            return ResponseHeader(header_bytes)
        
        header = retry(_read_response_header_once, retries)

        if not header:
            raise BrokenPipeError('Read response header: Retry limit reached')
        return header

    def _read_payload(self, header, retries=5):
        if header.payload_length == 0:
            return []

        def _read_payload_once():
            response_bytes = self._transport.read(header.length + header.payload_length)
            if ResponseHeader.is_valid_header(response_bytes):
                if not header.is_same_header(response_bytes):
                    raise ValueError('Read payload: Unexpected header received')

                payload = response_bytes[ResponseHeader.length:]
                has_valid_payload = header.validate_payload(payload)
                if has_valid_payload:
                    return payload

            return False

        payload = retry(_read_payload_once, retries)

        if not payload:
            raise BrokenPipeError('Read payload: Retry limit reached')

        return payload

    def _send_command(self, command: Command):
        """
        Send a command, wait for a proper response and returns with the header
        """
        # TODO: for safety, a timeout should be added later
        self._transport.write(command.get_bytes())
        while True:
            response = self._read_response_header()
            if response.status != ResponseHeader.Status_Busy:
                return response