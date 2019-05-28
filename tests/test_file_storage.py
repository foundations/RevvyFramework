import unittest

from revvy.file_storage import MemoryStorage, StorageElementNotFoundError, IntegrityError


class TestMemoryStorage(unittest.TestCase):
    def test_reading_missing_item_raises_error(self):
        storage = MemoryStorage()

        self.assertRaises(StorageElementNotFoundError, lambda: storage.read_metadata('foo'))
        self.assertRaises(StorageElementNotFoundError, lambda: storage.read('foo'))

    def test_md5_is_stored_if_provided(self):
        storage = MemoryStorage()

        storage.write('foo', b'data')
        self.assertNotEqual('', storage.read_metadata('foo')['md5'])
        self.assertNotEqual(None, storage.read_metadata('foo')['md5'])

    def test_md5_is_calculated_if_not_provided(self):
        storage = MemoryStorage()

        storage.write('foo', b'data', 'some_md5')
        self.assertEqual('some_md5', storage.read_metadata('foo')['md5'])

    def test_stored_data_can_be_read(self):
        storage = MemoryStorage()

        storage.write('foo', b'data')
        self.assertEqual(b'data', storage.read('foo'))

    def test_stored_data_integrity_is_checked_on_read(self):
        storage = MemoryStorage()

        storage.write('foo', b'data', 'foobar')
        self.assertRaises(IntegrityError, lambda: storage.read('foo'))
