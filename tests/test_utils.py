import unittest
from unittest.mock import Mock

from revvy.file_storage import StorageInterface, StorageElementNotFoundError, IntegrityError
from revvy.utils import FunctionSerializer, DeviceNameProvider, DataDispatcher, RemoteController


class TestFunctionSerializer(unittest.TestCase):
    def test_default_action_is_called_when_empty(self):
        default_mock = Mock()

        ser = FunctionSerializer(default_mock)

        ser.run()
        self.assertEqual(default_mock.call_count, 1)

    def test_remove_ignores_missing_keys(self):
        ser = FunctionSerializer(None)

        ser.remove('foo')

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
        storage.read = Mock(side_effect=StorageElementNotFoundError)
        dnp = DeviceNameProvider(storage, lambda: 'default')
        self.assertEqual(dnp.get_device_name(), 'default')

    def test_default_is_used_if_storage_raises_integrity_error(self):
        storage = StorageInterface()
        storage.read = Mock(side_effect=IntegrityError)
        dnp = DeviceNameProvider(storage, lambda: 'default')
        self.assertEqual(dnp.get_device_name(), 'default')

    def test_setting_device_name_stores(self):
        storage = Mock()
        storage.read = Mock()
        storage.write = Mock()
        dnp = DeviceNameProvider(storage, lambda: 'default')
        dnp.update_device_name('something else')
        self.assertEqual(dnp.get_device_name(), 'something else')
        self.assertEqual('device-name', storage.write.call_args[0][0])
        self.assertEqual(b'something else', storage.write.call_args[0][1])


class TestDataDispatcher(unittest.TestCase):
    def test_only_handlers_with_data_are_called(self):
        dsp = DataDispatcher()

        foo = Mock()
        bar = Mock()

        dsp.add("foo", foo)
        dsp.add("bar", bar)

        dsp.dispatch({'foo': 'data', 'baz': 'anything'})

        self.assertEqual(foo.call_count, 1)
        self.assertEqual(bar.call_count, 0)

    def test_removed_handler_is_not_called(self):
        dsp = DataDispatcher()

        foo = Mock()
        bar = Mock()

        dsp.add('foo', foo)
        dsp.add('bar', bar)

        dsp.remove('foo')

        dsp.dispatch({'foo': 'data', 'bar': 'anything'})

        self.assertEqual(foo.call_count, 0)
        self.assertEqual(bar.call_count, 1)

    def test_remove_ignores_missing_keys(self):
        dsp = DataDispatcher()

        dsp.remove('foo')

    def test_reset_removes_all_handlers(self):
        dsp = DataDispatcher()

        foo = Mock()
        bar = Mock()

        dsp.add('foo', foo)
        dsp.add('bar', bar)

        dsp.reset()

        dsp.dispatch({'foo': 'data', 'bar': 'anything'})

        self.assertEqual(foo.call_count, 0)
        self.assertEqual(bar.call_count, 0)


class TestRemoteController(unittest.TestCase):
    def test_callback_called_after_first_received_message(self):
        found = Mock()

        rc = RemoteController()
        rc.on_controller_detected(found)
        rc.start()

        rc.tick()
        rc.tick()
        self.assertEqual(found.call_count, 0)

        rc.update({'buttons': [False]*32, 'analog': [0]*10})
        rc.tick()

        self.assertEqual(found.call_count, 1)

    def test_callback_called_after_5_missed_messages(self):
        disappeared = Mock()

        rc = RemoteController()
        rc.on_controller_disappeared(disappeared)
        rc.start()

        rc.update({'buttons': [False]*32, 'analog': [0]*10})
        rc.tick()
        rc.tick()
        rc.tick()
        rc.tick()
        rc.tick()
        self.assertEqual(disappeared.call_count, 0)

        rc.tick()

        self.assertEqual(disappeared.call_count, 1)

    def test_message_resets_the_missed_counter(self):
        disappeared = Mock()

        rc = RemoteController()
        rc.on_controller_disappeared(disappeared)
        rc.start()

        rc.update({'buttons': [False]*32, 'analog': [0]*10})
        rc.tick()
        rc.tick()
        rc.tick()
        rc.tick()
        rc.tick()
        self.assertEqual(disappeared.call_count, 0)

        rc.update({'buttons': [False]*32, 'analog': [0]*10})
        rc.tick()
        rc.tick()
        rc.tick()
        rc.tick()
        rc.tick()

        self.assertEqual(disappeared.call_count, 0)

        rc.tick()

        self.assertEqual(disappeared.call_count, 1)

    def test_lost_callback_not_called_before_first_message(self):
        disappeared = Mock()

        rc = RemoteController()
        rc.on_controller_disappeared(disappeared)

        rc.start()

        rc.tick()
        rc.tick()
        rc.tick()
        rc.tick()
        rc.tick()
        rc.tick()

        self.assertEqual(disappeared.call_count, 0)

    def test_buttons_are_edge_triggered(self):
        rc = RemoteController()
        mocks = []
        for i in range(32):
            mock = Mock()
            rc.on_button_pressed(i, mock)
            mocks.append(mock)

        for i in range(32):
            buttons = [False] * 32

            rc.update({'buttons': buttons, 'analog': [0] * 10})
            rc.tick()

            # ith button is pressed
            buttons[i] = True
            rc.update({'buttons': buttons, 'analog': [0] * 10})
            rc.tick()

            # button is kept pressed
            rc.update({'buttons': buttons, 'analog': [0] * 10})
            rc.tick()

            for j in range(32):
                self.assertEqual(mocks[j].call_count, 1 if i == j else 0)
                mocks[j].reset_mock()

    def test_last_button_pressed_state_can_be_read(self):
        rc = RemoteController()

        for i in range(32):
            buttons = [False] * 32
            # ith button is pressed
            buttons[i] = True

            rc.update({'buttons': buttons, 'analog': [0] * 10})
            rc.tick()

            for j in range(32):
                self.assertEqual(buttons[i], rc.is_button_pressed(i))

    def test_last_analog_channel_state_can_be_read(self):
        rc = RemoteController()

        for i in range(10):
            analog = [0] * 10
            # ith button is pressed
            analog[i] = 255

            rc.update({'buttons': [False] * 32, 'analog': analog})
            rc.tick()

            for j in range(10):
                self.assertEqual(analog[i], rc.analog_value(i))

    def test_requested_channels_are_passed_to_analog_handlers(self):
        rc = RemoteController()
        mock24 = Mock()
        mock3 = Mock()
        mock_invalid = Mock()

        rc.on_analog_values([2, 4], mock24)
        rc.on_analog_values([3], mock3)
        rc.on_analog_values([3, 11], mock_invalid)

        rc.update({'buttons': [False] * 32, 'analog': [255, 254, 253, 123, 43, 65, 45, 42]})
        rc.tick()

        self.assertEqual(mock24.call_count, 1)
        self.assertEqual(mock3.call_count, 1)

        # invalid channels are silently ignored
        self.assertEqual(mock_invalid.call_count, 0)

        self.assertEqual(mock24.call_args[0][0], [253, 43])
        self.assertEqual(mock3.call_args[0][0], [123])

    def test_error_raised_for_invalid_button(self):
        rc = RemoteController()
        self.assertRaises(IndexError, lambda: rc.on_button_pressed(32, lambda: None))

    def test_reset_removes_handlers_but_not_state_callbacks(self):
        rc = RemoteController()

        mock = Mock()
        found_mock = Mock()
        lost_mock = Mock()

        rc.on_controller_detected(found_mock)
        rc.on_controller_disappeared(lost_mock)

        rc.on_analog_values([0], mock)
        rc.on_analog_values([1], mock)
        rc.on_button_pressed(0, mock)

        rc.reset()

        rc.update({'buttons': [True] * 32, 'analog': [0] * 10})
        rc.tick()

        rc.tick()
        rc.tick()
        rc.tick()
        rc.tick()
        rc.tick()

        self.assertEqual(mock.call_count, 0)
        self.assertEqual(found_mock.call_count, 1)
        self.assertEqual(lost_mock.call_count, 1)
