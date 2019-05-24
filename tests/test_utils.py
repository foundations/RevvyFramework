import unittest
from unittest.mock import Mock

from revvy.file_storage import StorageInterface
from revvy.utils import FunctionSerializer, DeviceNameProvider


class TestFunctionSerializer(unittest.TestCase):
    def test_default_action_is_called_when_empty(self):
        default_mock = Mock()

        ser = FunctionSerializer(default_mock)

        ser.run()
        self.assertEqual(default_mock.call_count, 1)

    def test_default_action_is_not_called_when_not_empty(self):
        default_mock = Mock()
        reader_mock = Mock()

        ser = FunctionSerializer(default_mock)
        ser.add("foo", reader_mock)

        ser.run()
        self.assertEqual(default_mock.call_count, 0)
        self.assertEqual(reader_mock.call_count, 1)

    def test_returned_data_can_be_read_using_reader_name(self):
        default_mock = Mock()
        foo_reader_mock = Mock(return_value='foobar')
        bar_reader_mock = Mock(return_value='barbaz')

        ser = FunctionSerializer(default_mock)
        ser.add("foo", foo_reader_mock)
        ser.add("bar", bar_reader_mock)

        data = ser.run()

        self.assertEqual(data['foo'], 'foobar')
        self.assertEqual(data['bar'], 'barbaz')

    def test_removed_reader_is_not_called(self):
        default_mock = Mock()
        foo_reader_mock = Mock(return_value='foobar')
        bar_reader_mock = Mock(return_value='barbaz')

        ser = FunctionSerializer(default_mock)
        ser.add("foo", foo_reader_mock)
        ser.add("bar", bar_reader_mock)

        ser.remove('foo')

        data = ser.run()

        self.assertEqual(default_mock.call_count, 0)
        self.assertEqual(foo_reader_mock.call_count, 0)
        self.assertEqual(data['bar'], 'barbaz')

    def test_reset_deletes_all_registered_readers(self):
        default_mock = Mock()
        foo_reader_mock = Mock()
        bar_reader_mock = Mock()

        ser = FunctionSerializer(default_mock)
        ser.add("foo", foo_reader_mock)
        ser.add("bar", bar_reader_mock)

        ser.reset()
        data = ser.run()

        self.assertEqual(data, {})
        self.assertEqual(default_mock.call_count, 1)
        self.assertEqual(foo_reader_mock.call_count, 0)
        self.assertEqual(bar_reader_mock.call_count, 0)


class TestDeviceNameProvider(unittest.TestCase):
    def test_device_name_is_read_from_storage(self):
        storage = StorageInterface()
        storage.read = lambda x: b'storage'
        dnp = DeviceNameProvider(storage, lambda: 'default')
        self.assertEqual(dnp.get_device_name(), 'storage')

    def test_default_is_used_if_storage_raises_error(self):
        storage = StorageInterface()
        storage.read = Mock(side_effect=IOError)
        dnp = DeviceNameProvider(storage, lambda: 'default')
        self.assertEqual(dnp.get_device_name(), 'default')
