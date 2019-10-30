# SPDX-License-Identifier: GPL-3.0-only

import unittest
from unittest.mock import Mock

from revvy.file_storage import StorageInterface, StorageElementNotFoundError, IntegrityError
from revvy.utils import DeviceNameProvider


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
