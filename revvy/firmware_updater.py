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
        # TODO: implement timeout in case MCU has no bootloader and firmware
        while True:
            try:
                return self._robot.read_operation_mode()
            except OSError:
                try:
                    return self._bootloader.read_operation_mode()
                except OSError:
                    print("Failed to read operation mode. Retrying")
                    time.sleep(0.5)

    def _finalize_update(self):
        """
        Finalize firmware and reboot to application
        """
        # noinspection PyBroadException
        try:
            self._bootloader.finalize_update()
            # at this point, the bootloader shall start the application
        except OSError:
            print('MCU restarted before finishing communication')
        except Exception:
            traceback.print_exc()

    def _request_bootloader_mode(self):
        try:
            print("Rebooting to bootloader")
            self._robot.reboot_bootloader()
        except OSError:
            print('MCU restarted before finishing communication')

    def _update_firmware(self, data):
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

        self._finalize_update()

        # read operating mode - this should return only when application has started
        assert self._read_operation_mode() == op_mode_application

    def read_hardware_version(self):
        """
        Read the hardware version from the MCU
        """
        mode = self._read_operation_mode()
        if mode == op_mode_application:
            return self._robot.get_hardware_version()
        else:
            return self._bootloader.get_hardware_version()

    def is_update_needed(self, fw_version):
        """
        Compare firmware version to the currently running one
        """
        mode = self._read_operation_mode()
        if mode == op_mode_application:
            fw = self._robot.get_firmware_version()
            return fw != fw_version  # allow downgrade as well
        else:
            # in bootloader mode, probably no firmware, request update
            return True

    def reboot_to_bootloader(self):
        """
        Start the bootloader on the MCU

        This function checks the operating mode. Reboot is only requested when in application mode
        """
        mode = self._read_operation_mode()
        if mode == op_mode_application:
            self._request_bootloader_mode()
            # wait for the reboot to complete
            mode = self._read_operation_mode()
            assert mode == op_mode_bootloader

    def ensure_firmware_up_to_date(self, expected_versions: dict, fw_loader):
        hw_version = self.read_hardware_version()
        if hw_version not in expected_versions:
            print('No firmware for the hardware ({})'.format(hw_version))
            return

        new_fw_version = expected_versions[hw_version]
        if self.is_update_needed(new_fw_version):
            self.reboot_to_bootloader()

            # noinspection PyBroadException
            try:
                print("Loading binary to memory")
                data = fw_loader(hw_version)
            except Exception:
                traceback.format_exc()

                # send finalize to reboot to unmodified application
                self._finalize_update()
                return

            self._update_firmware(data)


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
            traceback.print_exc()
            print("Skipping firmware update")
