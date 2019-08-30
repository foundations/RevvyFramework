import binascii
import json
import os
import time
import traceback
from json import JSONDecodeError

from revvy.file_storage import IntegrityError
from revvy.version import Version
from revvy.functions import split
from revvy.mcu.rrrc_control import BootloaderControl, RevvyControl
from tools.common import file_hash

op_mode_application = 0xAA
op_mode_bootloader = 0xBB


class McuUpdater:
    def __init__(self, robot_control: RevvyControl, bootloader_control: BootloaderControl):
        self._robot = robot_control
        self._bootloader = bootloader_control

    def _read_operation_mode(self):
        # TODO: timeout?
        retry = True
        mode = 0
        while retry:
            retry = False
            try:
                mode = self._robot.read_operation_mode()
            except OSError:
                try:
                    mode = self._bootloader.read_operation_mode()
                except OSError:
                    print("Failed to read operation mode. Retrying")
                    retry = True
                    time.sleep(0.5)
        return mode

    def request_bootloader_mode(self):
        try:
            print("Rebooting to bootloader")
            self._robot.reboot_bootloader()
        except OSError:
            # TODO make sure this is the right exception
            pass  # ignore, this error is expected because MCU reboots before sending response

    def update_firmware(self, data):
        # noinspection PyUnboundLocalVariable
        checksum = binascii.crc32(data)
        length = len(data)
        print("Image info: size: {} checksum: {}".format(length, checksum))

        # init update
        print("Initializing update")
        self._bootloader.send_init_update(length, checksum)

        # split data into chunks
        chunks = split(data, chunk_size=255)

        # send data
        print('Sending data')
        start = time.time()
        for chunk in chunks:
            self._bootloader.send_firmware(chunk)
        print('Data transfer took {} seconds'.format(round(time.time() - start, 1)))

        # noinspection PyBroadException
        try:
            # todo handle failed update
            self._bootloader.finalize_update()
            # at this point, the bootloader shall start the application
        except Exception as e:
            print(e)

        # read operating mode - this should return only when application has started
        assert self._read_operation_mode() == op_mode_application
        # todo handle failed update

    def ensure_firmware_up_to_date(self, expected_versions: dict, fw_loader):
        mode = self._read_operation_mode()

        if mode == op_mode_application:
            # do we need to update?
            hw_version = self._robot.get_hardware_version()

            if hw_version not in expected_versions:
                print('No firmware for the hardware ({})'.format(hw_version))
                return

            fw = self._robot.get_firmware_version()
            need_to_update = fw != expected_versions[hw_version]  # allow downgrade as well

            if not need_to_update:
                return

            print("Upgrading firmware: {} -> {}".format(fw, expected_versions[hw_version]))
            self.request_bootloader_mode()

            # if we need to update, reboot to bootloader
            mode = self._read_operation_mode()

        if mode == op_mode_bootloader:
            # we can get here without the above check if there is no application installed yet, so read version
            hw_version = self._bootloader.get_hardware_version()

            if hw_version not in expected_versions:
                print('No firmware for the hardware ({})'.format(hw_version))
                return

            print("Loading binary to memory")

            # noinspection PyBroadException
            try:
                data = fw_loader(hw_version)
            except Exception as e:
                print(e)

                # send finalize to reboot to unmodified application
                # noinspection PyBroadException
                try:
                    self._bootloader.finalize_update()
                    # at this point, the bootloader shall start the application
                except Exception as e:
                    print(e)
                return

            self.update_firmware(data)
        else:
            raise ValueError('Unexpected operating mode: {}'.format(mode))


class McuUpdateManager:
    def __init__(self, fw_dir, updater):
        self._fw_dir = fw_dir
        self._updater = updater

    def update_if_necessary(self):
        try:
            with open(os.path.join(self._fw_dir, 'catalog.json'), 'r') as cf:
                fw_metadata = json.load(cf)

            # hw version -> fw version mapping
            expected_versions = {Version(version): Version(fw_metadata[version]['version']) for version in fw_metadata}

        except (IOError, JSONDecodeError, KeyError):
            print('Invalid firmware catalog')
            return

        # noinspection PyBroadException
        try:
            def fw_loader(hw_version):
                hw_version = str(hw_version)
                print('Loading firmware for HW: {}'.format(hw_version))
                filename = fw_metadata[hw_version]['filename']
                path = os.path.join(self._fw_dir, filename)

                checksum = file_hash(path)
                if checksum != fw_metadata[hw_version]['md5']:
                    raise IntegrityError

                with open(path, "rb") as f:
                    return f.read()

            self._updater.ensure_firmware_up_to_date(expected_versions, fw_loader)
        except Exception:
            print("Skipping firmware update")
            traceback.print_exc()
