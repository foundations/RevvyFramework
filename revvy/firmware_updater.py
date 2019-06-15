import binascii
import time

from revvy.configuration.version import Version
from revvy.rrrc_control import BootloaderControl, RevvyControl

op_mode_application = 0xAA
op_mode_bootloader = 0xBB


def split(data, chunk_size):
    """
    >>> list(split([1, 2, 3, 4], 2))
    [[1, 2], [3, 4]]
    >>> list(split([1, 2, 3, 4, 5], 2))
    [[1, 2], [3, 4], [5]]
    >>> list(split(b'apple', 2))
    [b'ap', b'pl', b'e']
    """
    return (data[i:i + chunk_size] for i in range(0, len(data), chunk_size))


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

    def ensure_firmware_up_to_date(self, expected_version: Version, fw_loader):
        mode = self._read_operation_mode()

        if mode == op_mode_application:
            # do we need to update?
            fw = Version(self._robot.get_firmware_version())
            need_to_update = fw != expected_version  # allow downgrade as well

            if not need_to_update:
                return

            print("Upgrading firmware: {} -> {}".format(fw, expected_version))

            try:
                print("Rebooting to bootloader")
                self._robot.reboot_bootloader()
            except OSError:
                # TODO make sure this is the right exception
                pass  # ignore, this error is expected because MCU reboots before sending response

            # if we need to update, reboot to bootloader
            mode = self._read_operation_mode()

        if mode == op_mode_bootloader:
            print("Loading binary to memory")
            fw_successfully_loaded = False
            # noinspection PyBroadException
            try:
                data = fw_loader()
                fw_successfully_loaded = True
            except Exception as e:
                print(e)

            if fw_successfully_loaded:
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

            # finalize - or reboot if fw_loader raised an error
            print("Finalizing update")
            # noinspection PyBroadException
            try:
                # todo handle failed update
                self._bootloader.finalize_update()
                # at this point, the bootloader shall start the application
            except Exception as e:
                print(e)
        else:
            raise ValueError('Unexpected operating mode: {}'.format(mode))
