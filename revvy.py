#!/usr/bin/python3

import json
import enum

from revvy.bluetooth.ble_revvy import Observable, RevvyBLE
from revvy.file_storage import FileStorage, MemoryStorage, IntegrityError
from revvy.firmware_updater import McuUpdater
from revvy.functions import getserial
from revvy.bluetooth.longmessage import LongMessageHandler, LongMessageStorage, LongMessageType
from revvy.hardware_dependent.rrrc_transport_i2c import RevvyTransportI2C
from revvy.utils import *
from revvy.mcu.rrrc_transport import *
from revvy.mcu.rrrc_control import *
import sys

from tools.check_manifest import check_manifest
from tools.common import file_hash


class RevvyStatusCode(enum.IntEnum):
    OK = 0
    ERROR = 1
    INTEGRITY_ERROR = 2
    UPDATE_REQUEST = 3


def start_revvy(config: RobotConfig = None):

    directory = os.path.dirname(os.path.realpath(__file__))
    os.chdir(directory)

    # self-test
    if not check_manifest(os.path.join(directory, 'manifest.json')):
        return RevvyStatusCode.INTEGRITY_ERROR

    # prepare environment
    data_dir = os.path.join(directory, '..', '..', 'data')
    package_data_dir = os.path.join(directory, 'data')
    fw_dir = os.path.join(directory, 'data', 'firmware')

    serial = getserial()

    print('Revvy run from {} ({})'.format(directory, __file__))

    # package_storage = FileStorage(package_data_dir)
    device_storage = FileStorage(os.path.join(data_dir, 'device'))
    ble_storage = FileStorage(os.path.join(data_dir, 'ble'))

    sound_files = {
        'alarm_clock':    'alarm_clock.mp3',
        'bell':           'bell.mp3',
        'buzzer':         'buzzer.mp3',
        'car_horn':       'car-horn.mp3',
        'cat':            'cat.mp3',
        'dog':            'dog.mp3',
        'duck':           'duck.mp3',
        'engine_revving': 'engine-revving.mp3',
        'lion':           'lion.mp3',
        'oh_no':          'oh-no.mp3',
        'robot':          'robot.mp3',
        'robot2':         'robot2.mp3',
        'siren':          'siren.mp3',
        'ta_da':          'tada.mp3',
        'uh_oh':          'uh-oh.mp3',
        'yee_haw':        'yee-haw.mp3',
    }

    def sound_path(file):
        return os.path.join(package_data_dir, 'assets', file)

    sound_paths = {key: sound_path(sound_files[key]) for key in sound_files}

    dnp = DeviceNameProvider(device_storage, lambda: 'Revvy_{}'.format(serial.lstrip('0')))
    device_name = Observable(dnp.get_device_name())
    long_message_handler = LongMessageHandler(LongMessageStorage(ble_storage, MemoryStorage()))

    ble = RevvyBLE(device_name, serial, long_message_handler)

    with RevvyTransportI2C() as transport:
        robot_control = RevvyControl(transport.bind(0x2D))
        bootloader_control = BootloaderControl(transport.bind(0x2B))

        updater = McuUpdater(robot_control, bootloader_control)

        # noinspection PyBroadException
        try:
            with open(os.path.join(fw_dir, 'catalog.json'), 'r') as cf:
                fw_metadata = json.load(cf)

            # hw version -> fw version mapping
            expected_versions = {Version(version): Version(fw_metadata[version]['version']) for version in fw_metadata}

            def fw_loader(hw_version):
                hw_version = str(hw_version)
                print('Loading firmware for HW: {}'.format(hw_version))
                filename = fw_metadata[hw_version]['filename']
                path = os.path.join(fw_dir, filename)

                checksum = file_hash(path)
                if checksum != fw_metadata[hw_version]['md5']:
                    raise IntegrityError

                with open(path, "rb") as f:
                    return f.read()

            updater.ensure_firmware_up_to_date(expected_versions, fw_loader)
        except Exception:
            print("Skipping firmware update")
            traceback.print_exc()

        robot = RobotManager(robot_control, ble, sound_paths, config)

        def on_device_name_changed(new_name):
            print('Device name changed to {}'.format(new_name))
            dnp.update_device_name(new_name)

        def on_upload_started():
            robot.run_in_background(lambda: robot.robot.led_ring.set_scenario(RingLed.ColorWheel))

        def on_transmission_finished():
            robot.run_in_background(lambda: robot.robot.led_ring.set_scenario(RingLed.BreathingGreen))

        def on_message_updated(storage, message_type):
            print('Received message: {}'.format(message_type))

            if message_type == LongMessageType.TEST_KIT:
                message_data = storage.get_long_message(message_type).decode()
                print('Running test script: {}'.format(message_data))

                def start_script():
                    print("Starting new test script")
                    robot._scripts.add_script("test_kit", message_data, 0)
                    robot._scripts["test_kit"].on_stopped(lambda: robot.configure(None))

                    # start can't run in on_stopped handler because overwriting script causes deadlock
                    robot.run_in_background(lambda: robot._scripts["test_kit"].start())

                try:
                    script = robot._scripts["test_kit"]
                    script.on_stopped(lambda: robot.run_in_background(start_script))
                    print("Stop running test script")
                    script.stop()
                except KeyError:
                    start_script()

            elif message_type == LongMessageType.CONFIGURATION_DATA:
                message_data = storage.get_long_message(message_type).decode()
                print('New configuration: {}'.format(message_data))
                if config is not None:
                    print('New configuration ignored')
                else:
                    parsed_config = RobotConfig.from_string(message_data)
                    if parsed_config is not None:
                        robot.configure(parsed_config)

            elif message_type == LongMessageType.FRAMEWORK_DATA:
                robot.request_update()

        device_name.subscribe(on_device_name_changed)
        long_message_handler.on_upload_started(on_upload_started)
        long_message_handler.on_upload_finished(on_transmission_finished)
        long_message_handler.on_message_updated(on_message_updated)

        # noinspection PyBroadException
        try:
            robot.start()
            robot.sound.play_tune('robot2')

            print("Press Enter to exit")
            input()
            # manual exit
            ret_val = RevvyStatusCode.OK
        except EOFError:
            robot.needs_interrupting = False
            while not robot.update_requested:
                time.sleep(1)
            ret_val = RevvyStatusCode.UPDATE_REQUEST if robot.update_requested else RevvyStatusCode.OK
        except KeyboardInterrupt:
            # manual exit or update request
            ret_val = RevvyStatusCode.UPDATE_REQUEST if robot.update_requested else RevvyStatusCode.OK
        except Exception:
            print(traceback.format_exc())
            ret_val = RevvyStatusCode.ERROR
        finally:
            print('stopping')
            robot.stop()

        print('terminated.')
        return ret_val


# test scripts


def toggle_ring_led(args):
    if args['robot']._ring_led:
        if args['robot']._ring_led.scenario == RingLed.Off:
            args['robot']._ring_led.set_scenario(RingLed.ColorWheel)
        elif args['robot']._ring_led.scenario == RingLed.ColorWheel:
            args['robot']._ring_led.set_scenario(RingLed.ColorFade)
        else:
            args['robot']._ring_led.set_scenario(RingLed.Off)


if __name__ == "__main__":
    sys.exit(start_revvy())
