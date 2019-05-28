import collections
import hashlib
from json import JSONDecodeError
from revvy.file_storage import StorageInterface, StorageError


def hexdigest2bytes(hexdigest):
    """
    >>> hexdigest2bytes("aabbcc")
    b'\\xaa\\xbb\\xcc'
    >>> hexdigest2bytes("ABCDEF")
    b'\\xab\\xcd\\xef'
    """
    return b"".join([int(hexdigest[i:i + 2], 16).to_bytes(1, byteorder="big") for i in range(0, len(hexdigest), 2)])


def bytes2hexdigest(bytes):
    """
    >>> bytes2hexdigest(b'\\xaa\\xbb\\xcc')
    'aabbcc'
    >>> bytes2hexdigest(b'\\xAB\\xCD\\xEF')
    'abcdef'
    """
    return "".join([hex(byte)[2:] for byte in bytes])


LongMessageStatusInfo = collections.namedtuple('LongMessageStatusInfo', ['status', 'md5', 'length'])


class LongMessageStatus:
    UNUSED = 0
    UPLOAD = 1
    VALIDATION = 2
    READY = 3
    VALIDATION_ERROR = 4


class LongMessageType:
    FIRMWARE_DATA = 1
    FRAMEWORK_DATA = 2
    CONFIGURATION_DATA = 3
    TEST_KIT = 4
    MAX = 5

    PermanentMessages = [FIRMWARE_DATA, FRAMEWORK_DATA, CONFIGURATION_DATA]

    @staticmethod
    def validate(long_message_type):
        if not (0 < long_message_type < LongMessageType.MAX):
            raise LongMessageError("Invalid long message type {}".format(long_message_type))


class MessageType:
    SELECT_LONG_MESSAGE_TYPE = 0
    INIT_TRANSFER = 1
    UPLOAD_MESSAGE = 2
    FINALIZE_MESSAGE = 3


class LongMessageError(Exception):
    def __init__(self, message):
        self.message = message


class LongMessageStorage:
    """Store long messages using the given storage class, with extra validation"""

    def __init__(self, storage: StorageInterface, temp_storage: StorageInterface):
        self._storage = storage
        self._temp_storage = temp_storage

    def _get_storage(self, message_type):
        return self._storage if message_type in LongMessageType.PermanentMessages else self._temp_storage

    def read_status(self, long_message_type):
        """Return status with triplet of (LongMessageStatus, md5-hexdigest, length). Last two fields might be None)."""
        print("LongMessageStorage:read_status")
        LongMessageType.validate(long_message_type)
        try:
            storage = self._get_storage(long_message_type)
            data = storage.read_metadata(long_message_type)
            return LongMessageStatusInfo(LongMessageStatus.READY, data['md5'], data['length'])
        except (StorageError, JSONDecodeError):
            return LongMessageStatusInfo(LongMessageStatus.UNUSED, None, None)

    def set_long_message(self, long_message_type, data, md5):
        print("LongMessageStorage:set_long_message")
        LongMessageType.validate(long_message_type)
        storage = self._get_storage(long_message_type)
        storage.write(long_message_type, data, md5)

    def get_long_message(self, long_message_type):
        print("LongMessageStorage:get_long_message")
        storage = self._get_storage(long_message_type)
        return storage.read(long_message_type)


class LongMessageAggregator:
    """Helper class for building long messages"""

    def __init__(self, md5):
        self.md5 = md5
        self.data = bytearray()
        self.md5calc = hashlib.md5()
        self.md5computed = None

    @property
    def is_empty(self):
        return len(self.data) == 0

    def append_data(self, data):
        self.data += data
        self.md5calc.update(data)

    def finalize(self):
        """Returns true if the uploaded data matches the predefined md5 checksum."""
        self.md5computed = self.md5calc.hexdigest()
        print('Received MD5: {}'.format(self.md5))
        print('Calculated MD5: {}'.format(self.md5computed))
        return self.md5computed == self.md5


class LongMessageHandler:
    """Implements the long message writer/status reader protocol"""

    def __init__(self, long_message_storage):
        self._long_message_storage = long_message_storage
        self._long_message_type = None
        self._status = "READ"
        self._aggregator = None
        self._callback = lambda x, y: None

    def on_message_updated(self, callback):
        self._callback = callback

    def read_status(self):
        print("LongMessageHandler:read_status")
        if self._long_message_type is None:
            return LongMessageStatusInfo(LongMessageStatus.UNUSED, None, None)
        if self._status == "READ":
            return self._long_message_storage.read_status(self._long_message_type)
        if self._status == "INVALID":
            return LongMessageStatusInfo(LongMessageStatus.VALIDATION_ERROR, None, None)
        assert self._status == "WRITE"
        return LongMessageStatusInfo(LongMessageStatus.UPLOAD, self._aggregator.md5, len(self._aggregator.data))

    def select_long_message_type(self, long_message_type):
        print("LongMessageHandler:select_long_message_type")
        LongMessageType.validate(long_message_type)
        self._long_message_type = long_message_type
        self._status = "READ"

    def init_transfer(self, md5):
        print("LongMessageHandler:init_transfer")
        if self._long_message_type is None:
            raise LongMessageError("init-transfer needs to be called after select_long_message_type")
        self._status = "WRITE"
        self._aggregator = LongMessageAggregator(md5)

    def upload_message(self, data):
        print("LongMessageHandler:upload_message")
        if self._status != "WRITE":
            raise LongMessageError("init-transfer needs to be called before upload_message")
        self._aggregator.append_data(data)

    def finalize_message(self):
        print("LongMessageHandler:finalize_message")
        if self._status != "WRITE":
            raise LongMessageError("init-transfer needs to be called before finalize_message")

        if self._aggregator.is_empty:
            self._callback(self._long_message_storage, self._long_message_type)
            self._status = "READ"
        elif self._aggregator.finalize():
            self._long_message_storage.set_long_message(self._long_message_type, self._aggregator.data,
                                                        self._aggregator.md5)
            self._callback(self._long_message_storage, self._long_message_type)
            self._status = "READ"
        else:
            self._status = "INVALID"
