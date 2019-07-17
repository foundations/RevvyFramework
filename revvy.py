#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI
import os

from revvy.bluetooth.ble_revvy import Observable, RevvyBLE
from revvy.file_storage import FileStorage, MemoryStorage, StorageElementNotFoundError
from revvy.firmware_updater import McuUpdater
from revvy.functions import getserial
from revvy.hardware_dependent.sound import play_sound, setup_sound
from revvy.bluetooth.longmessage import LongMessageHandler, LongMessageStorage, LongMessageType
from revvy.hardware_dependent.rrrc_transport_i2c import RevvyTransportI2C
from revvy.robot.sound import Sound
from revvy.utils import *
from revvy.mcu.rrrc_transport import *
from revvy.mcu.rrrc_control import *
import sys

from tools.check_manifest import check_manifest


def start_revvy(config: RobotConfig = None):

    directory = os.path.dirname(os.path.realpath(__file__))
    os.chdir(directory)

    # self-test
    if not check_manifest(os.path.join(directory, 'manifest.json')):
        return 2

    # prepare environment
    data_dir = os.path.join(directory, '..', '..', 'data')
    package_data_dir = os.path.join(directory, 'data')

    serial = getserial()

    print('Revvy run from {} ({})'.format(directory, __file__))

    package_storage = FileStorage(package_data_dir)
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
    sound_paths = {key: os.path.join(package_data_dir, 'assets', sound_files[key]) for key in sound_files}
    sound = Sound(setup_sound, play_sound, sound_paths)

    dnp = DeviceNameProvider(device_storage, lambda: 'Revvy_{}'.format(serial.lstrip('0')))
    device_name = Observable(dnp.get_device_name())
    long_message_handler = LongMessageHandler(LongMessageStorage(ble_storage, MemoryStorage()))

    ble = RevvyBLE(device_name, serial, long_message_handler)

    with RevvyTransportI2C() as transport:
        robot_control = RevvyControl(transport.bind(0x2D))
        bootloader_control = BootloaderControl(transport.bind(0x2B))

        updater = McuUpdater(robot_control, bootloader_control)

        try:
            fw_metadata = package_storage.read_metadata('firmware')

            expected_version = Version(fw_metadata['version'])
            updater.ensure_firmware_up_to_date(expected_version, lambda: package_storage.read('firmware'))
        except StorageElementNotFoundError:
            pass

        robot = RobotManager(robot_control, ble, sound, config)

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
                robot._scripts.add_script("test_kit", message_data, 0)
                robot._scripts["test_kit"].on_stopped(lambda: robot.configure(None))
                robot._scripts["test_kit"].start()
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
            sound.play_tune('robot2')
            robot.start()
            print("Press Ctrl-C to exit")
            while not robot.update_requested:
                time.sleep(1)
            # exit due to update request
            ret_val = 3
        except KeyboardInterrupt:
            # manual exit
            ret_val = 0
        except Exception:
            print(traceback.format_exc())
            ret_val = 1
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


motor_test = '''
configs = {
    'cw': 'RevvyMotor',
    'ccw': 'RevvyMotor_CCW'
}
robot.motors[{MOTOR}].configure(configs["{MOTOR_DIR}"])
robot.motors[{MOTOR}].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_DEG, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
time.sleep(1)
robot.motors[{MOTOR}].move(direction=Motor.DIR_CCW, amount=180, unit_amount=Motor.UNIT_DEG, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
time.sleep(1)
robot.motors[{MOTOR}].stop(action=Motor.ACTION_RELEASE)
robot.motors[{MOTOR}].configure("NotConfigured")
'''.replace('{MOTOR}', '1').replace('{MOTOR_DIR}', 'cw')


drivetrain_test = '''
configs = {
    'left': {
        'cw': 'RevvyMotor_CCW',
        'ccw': 'RevvyMotor'
    },
    'right': {
        'cw': 'RevvyMotor',
        'ccw': 'RevvyMotor_CCW'
    }
}
robot.motors[{MOTOR}].configure(configs["{MOTOR_SIDE}"]["{MOTOR_DIR}"])
robot.motors[{MOTOR}].spin(direction=Motor.DIR_CW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
time.sleep(3)
robot.motors[{MOTOR}].stop(action=Motor.ACTION_RELEASE)
time.sleep(0.2)
robot.motors[{MOTOR}].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
time.sleep(3)
robot.motors[{MOTOR}].stop(action=Motor.ACTION_RELEASE)
time.sleep(0.2)
robot.motors[{MOTOR}].configure("NotConfigured")
'''.replace('{MOTOR}', '1').replace('{MOTOR_SIDE}', 'left').replace('{MOTOR_DIR}', 'cw')


button_light_test = '''
robot.sensors[{SENSOR}].configure("BumperSwitch")
test_ok = False
prev_sec = 12
robot.led.set(list(range(1, 13)), "#FF0000")

start = time.time()
while time.time() - start < 12:
    seconds = 12 - int(round(time.time() - start, 0))

    if seconds != prev_sec:
        robot.led.set(list(range(1, seconds+1)), "#FF0000")
        robot.led.set(list(range(seconds+1, 13)), "#000000")
        prev_sec = seconds

    if robot.sensors[{SENSOR}].read() == 1:
        test_ok = True
        break

if test_ok:
    # draw smiley face
    robot.led.set(list(range(1, 13)), "#000000")
    robot.led.set([1, 2, 3, 4, 5, 8, 10], "#00FF00")
    time.sleep(3)

robot.led.set(list(range(1, 13)), "#000000")
robot.sensors[{SENSOR}].configure("NotConfigured")
'''.replace('{SENSOR}', '2')


ultrasound_light_test = '''
robot.sensors[{SENSOR}].configure("HC_SR04")
test_ok = False
prev_sec = 12
robot.led.set(list(range(1, 13)), "#FF0000")
prev_dist = 48

start = time.time()
while time.time() - start < 12:
    seconds = 12 - int(round(time.time() - start, 0))

    dist = robot.sensors[{SENSOR}].read()
    if dist < 48:
        nleds = int(round((48 - dist)/4))
        robot.led.set(list(range(1, nleds+1)), "#0000FF")
        robot.led.set(list(range(nleds+1, 13)), "#000000")
        prev_sec = 12
    elif seconds != prev_sec:
        dist = 48
        robot.led.set(list(range(1, seconds+1)), "#FF0000")
        robot.led.set(list(range(seconds+1, 13)), "#000000")
        prev_sec = seconds
        
robot.sensors[{SENSOR}].configure("NotConfigured")
robot.led.set(list(range(1, 13)), "#000000")
'''.replace('{SENSOR}', '1')


lift_test = '''
configs = {
    'cw': 'RevvyMotor',
    'ccw': 'RevvyMotor_CCW'
}
robot.motors[{MOTOR}].configure(configs["{MOTOR_DIR}"])
robot.motors[{MOTOR}].move(direction=Motor.DIR_CW, amount=130, unit_amount=Motor.UNIT_DEG, limit=20, unit_limit=Motor.UNIT_SPEED_RPM)
time.sleep(3)
robot.motors[{MOTOR}].move(direction=Motor.DIR_CCW, amount=130, unit_amount=Motor.UNIT_DEG, limit=20, unit_limit=Motor.UNIT_SPEED_RPM)
time.sleep(1)
robot.motors[{MOTOR}].stop(action=Motor.ACTION_STOP_AND_HOLD)
robot.motors[{MOTOR}].configure("NotConfigured")
'''.replace('{MOTOR}', '6').replace('{MOTOR_DIR}', 'ccw')


if __name__ == "__main__":
    sys.exit(start_revvy())
