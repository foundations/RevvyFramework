#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI
import os

from revvy.ble_revvy import Observable, RevvyBLE
from revvy.file_storage import FileStorage, MemoryStorage
from revvy.functions import getserial
from revvy.hardware_dependent.sound import play_sound, setup_sound
from revvy.longmessage import LongMessageHandler, LongMessageStorage, LongMessageType
from revvy.hardware_dependent.rrrc_transport_i2c import RevvyTransportI2C
from revvy.scripting.builtin_scripts import drive_2sticks, drive_joystick
from revvy.sound import Sound
from revvy.utils import *
from revvy.rrrc_transport import *
from revvy.robot_config import *
import sys

from tools.check_manifest import check_manifest

mcu_features = {
}


def toggle_ring_led(args):
    if args['robot']._ring_led:
        if args['robot']._ring_led.scenario == RingLed.Off:
            args['robot']._ring_led.set_scenario(RingLed.ColorWheel)
        elif args['robot']._ring_led.scenario == RingLed.ColorWheel:
            args['robot']._ring_led.set_scenario(RingLed.ColorFade)
        else:
            args['robot']._ring_led.set_scenario(RingLed.Off)


def start_revvy(config: RobotConfig = None):
    # prepare environment
    directory = os.path.dirname(os.path.realpath(__file__))
    data_dir = os.path.join(directory, '..', '..', 'data')
    serial = getserial()

    print('Revvy run from {} ({})'.format(directory, __file__))

    device_storage = FileStorage(os.path.join(data_dir, 'device'))
    ble_storage = FileStorage(os.path.join(data_dir, 'ble'))

    sound = Sound(setup_sound, play_sound, {
        'startup': os.path.join(data_dir, 'assets', 'startup.mp3'),
        'cheer':   os.path.join(data_dir, 'assets', 'startup.mp3'),
    })
    sound.play_tune('startup')

    dnp = DeviceNameProvider(device_storage, lambda: 'Revvy_{}'.format(serial.lstrip('0')))
    device_name = Observable(dnp.get_device_name())
    long_message_handler = LongMessageHandler(LongMessageStorage(ble_storage, MemoryStorage()))

    ble = RevvyBLE(device_name, serial, long_message_handler)

    with RevvyTransportI2C(RevvyControl.mcu_address) as transport:
        robot_control = RevvyControl(transport.bind(RevvyControl.mcu_address))

        robot = RobotManager(robot_control, ble, sound, config, mcu_features)

        def on_device_name_changed(new_name):
            print('Device name changed to {}'.format(new_name))
            dnp.update_device_name(new_name)

        def on_message_updated(storage, message_type):
            print('Received message: {}'.format(message_type))
            message_data = storage.get_long_message(message_type).decode()

            if message_type == LongMessageType.TEST_KIT:
                print('Running test script: {}'.format(message_data))
                robot._scripts.add_script("test_kit", message_data, 0)
                robot._scripts["test_kit"].start()
            elif message_type == LongMessageType.CONFIGURATION_DATA:
                print('New configuration: {}'.format(message_data))
                parsed_config = RobotConfig.from_string(message_data)
                if parsed_config is not None:
                    # robot.configure(parsed_config)
                    pass
            elif message_type == LongMessageType.FRAMEWORK_DATA:
                robot.request_update()

        device_name.subscribe(on_device_name_changed)
        long_message_handler.on_message_updated(on_message_updated)

        # noinspection PyBroadException
        try:
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


motor_test = '''
robot.motors[{MOTOR}].move(direction=Motor.DIRECTION_CW, rotation=180, unit_rotation=Motor.UNIT_DEG, speed=20, unit_speed=Motor.UNIT_SPEED_PWR)
time.sleep(1)
robot.motors[{MOTOR}].move(direction=Motor.DIRECTION_CCW, rotation=180, unit_rotation=Motor.UNIT_DEG, speed=20, unit_speed=Motor.UNIT_SPEED_PWR)
time.sleep(0.2)
robot.motors[{MOTOR}].stop(action=Motor.ACTION_RELEASE)
'''.replace('{MOTOR}', '1')


drivetrain_test = '''
robot.motors[{MOTOR}].spin(direction=Motor.DIR_CW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
time.sleep(3)
robot.motors[{MOTOR}].stop(action=Motor.ACTION_RELEASE)
time.sleep(0.2)
robot.motors[{MOTOR}].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
time.sleep(3)
robot.motors[{MOTOR}].stop(action=Motor.ACTION_RELEASE)
time.sleep(0.2)
'''.replace('{MOTOR}', '1')


button_light_test = '''
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
'''.replace('{SENSOR}', '2')


ultrasound_light_test = '''
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
'''.replace('{SENSOR}', '1')


def main():
    default_config = RobotConfig()
    default_config.motors[1] = "RevvyMotor"
    default_config.motors[2] = "RevvyMotor"
    default_config.motors[3] = "RevvyMotor"
    default_config.motors[4] = "RevvyMotor"
    default_config.motors[5] = "RevvyMotor"
    default_config.motors[6] = "RevvyMotor"

    default_config.drivetrain['left'] = [2, 3]
    default_config.drivetrain['right'] = [5, 6]

    default_config.sensors[1] = "HC_SR04"
    default_config.sensors[2] = "BumperSwitch"
    default_config.controller.analog.append({'channels': [0, 1], 'script': 'drivetrain_joystick'})
    default_config.controller.buttons[0] = 'toggle_ring_led'
    default_config.controller.buttons[1] = 'button_light_test'

    default_config.scripts['drivetrain_joystick'] = {'script': drive_joystick, 'priority': 0}
    default_config.scripts['drivetrain_2sticks'] = {'script': drive_2sticks, 'priority': 0}
    default_config.scripts['toggle_ring_led'] = {'script': toggle_ring_led, 'priority': 0}
    default_config.scripts['motor_test'] = {'script': motor_test, 'priority': 0}
    default_config.scripts['drivetrain_test'] = {'script': drivetrain_test, 'priority': 0}
    default_config.scripts['button_light_test'] = {'script': button_light_test, 'priority': 0}
    default_config.scripts['ultrasound_light_test'] = {'script': ultrasound_light_test, 'priority': 0}

    return start_revvy(default_config)


if __name__ == "__main__":
    current_directory = os.path.dirname(os.path.realpath(__file__))
    os.chdir(current_directory)
    if check_manifest(os.path.join(current_directory, 'manifest.json')):
        sys.exit(main())
    else:
        sys.exit(2)
