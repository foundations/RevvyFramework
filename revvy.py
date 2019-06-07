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


def start_revvy(interface: RevvyTransportInterface, config: RobotConfig = None):
    # prepare environment
    directory = os.path.dirname(os.path.realpath(__file__))
    data_dir = os.path.join(directory, '..', '..', 'data')
    serial = getserial()

    print('Revvy run from {} ({})'.format(directory, __file__))

    device_storage = FileStorage(os.path.join(data_dir, 'device'))
    ble_storage = FileStorage(os.path.join(data_dir, 'ble'))

    sound = Sound(setup_sound, play_sound, {
        'startup': os.path.join(data_dir, 'assets', 'startup.mp3'),
        'cheer': os.path.join(data_dir, 'assets', 'startup.mp3'),
    })
    sound.play_tune('startup')

    dnp = DeviceNameProvider(device_storage, lambda: 'Revvy_{}'.format(serial.lstrip('0')))
    device_name = Observable(dnp.get_device_name())
    long_message_handler = LongMessageHandler(LongMessageStorage(ble_storage, MemoryStorage()))

    ble = RevvyBLE(device_name, serial, long_message_handler)

    robot = RobotManager(interface, ble, sound, config, mcu_features)

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
        ret_val = 1
    finally:
        print('stopping')
        robot.stop()

    print('terminated.')
    return ret_val


sound_test = '''
while True:
    robot.play_tune('cheer')
'''


motor_test_spin = '''
robot.motors[1].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[2].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[3].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[4].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[5].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[6].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
'''


motor_test_move_sec = '''
while True:
    robot.motors[1].move(direction=Motor.DIR_CCW, amount=1, unit_amount=Motor.UNIT_SEC, limit=20, unit_limit=Motor.UNIT_SPEED_RPM)
    robot.motors[2].move(direction=Motor.DIR_CCW, amount=1, unit_amount=Motor.UNIT_SEC, limit=20, unit_limit=Motor.UNIT_SPEED_RPM)
    robot.motors[3].move(direction=Motor.DIR_CCW, amount=1, unit_amount=Motor.UNIT_SEC, limit=20, unit_limit=Motor.UNIT_SPEED_RPM)
    robot.motors[4].move(direction=Motor.DIR_CCW, amount=1, unit_amount=Motor.UNIT_SEC, limit=20, unit_limit=Motor.UNIT_SPEED_RPM)
    robot.motors[5].move(direction=Motor.DIR_CCW, amount=1, unit_amount=Motor.UNIT_SEC, limit=20, unit_limit=Motor.UNIT_SPEED_RPM)
    robot.motors[6].move(direction=Motor.DIR_CCW, amount=1, unit_amount=Motor.UNIT_SEC, limit=20, unit_limit=Motor.UNIT_SPEED_RPM)
'''


motor_test_move_deg = '''
while True:
    robot.motors[1].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_DEG, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
    robot.motors[2].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_DEG, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
    robot.motors[3].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_DEG, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
    robot.motors[4].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_DEG, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
    robot.motors[5].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_DEG, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
    robot.motors[6].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_DEG, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
'''


motor_test_move_rot = '''
while True:
    robot.motors[1].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_ROT, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
    robot.motors[2].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_ROT, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
    robot.motors[3].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_ROT, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
    robot.motors[4].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_ROT, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
    robot.motors[5].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_ROT, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
    robot.motors[6].move(direction=Motor.DIR_CW, amount=180, unit_amount=Motor.UNIT_ROT, limit=20, unit_limit=Motor.UNIT_SPEED_PWR)
'''


motor_test_stop = '''
robot.motors[1].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[2].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[3].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[4].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[5].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[6].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
time.sleep(3)

robot.stop_all_motors(Motor.ACTION_RELEASE)
time.sleep(3)

robot.motors[1].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[2].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[3].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[4].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[5].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
robot.motors[6].spin(direction=Motor.DIR_CCW, rotation=20, unit_rotation=Motor.UNIT_SPEED_RPM)
time.sleep(3)

robot.stop_all_motors(Motor.ACTION_STOP_AND_HOLD)
'''


motor_test = '''
while True:
    robot.drive(direction=Motor.DIRECTION_RIGHT, rotation=1, unit_rotation=Motor.UNIT_SEC, speed=20, unit_speed=Motor.UNIT_SPEED_PWR)
    time.sleep(1)
    robot.drive(direction=Motor.DIRECTION_LEFT, rotation=1, unit_rotation=Motor.UNIT_SEC, speed=20, unit_speed=Motor.UNIT_SPEED_PWR)
    time.sleep(1)
'''


button_sound_test = '''
while True:
    if robot.sensors[2].read() == 1:
        robot.play_tune('cheer')
'''


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
    default_config.controller.buttons[1] = 'sound_test'

    default_config.scripts['drivetrain_joystick'] = {'script': drive_joystick, 'priority': 0}
    default_config.scripts['drivetrain_2sticks'] = {'script': drive_2sticks, 'priority': 0}
    default_config.scripts['toggle_ring_led'] = {'script': toggle_ring_led, 'priority': 0}
    default_config.scripts['motor_test'] = {'script': motor_test, 'priority': 0}
    default_config.scripts['sound_test'] = {'script': sound_test, 'priority': 0}
    default_config.scripts['button_sound_test'] = {'script': button_sound_test, 'priority': 0}

    default_config.background_scripts.append('button_sound_test')

    with RevvyTransportI2C(RevvyControl.mcu_address) as robot_interface:
        return start_revvy(robot_interface, default_config)


if __name__ == "__main__":
    current_directory = os.path.dirname(os.path.realpath(__file__))
    os.chdir(current_directory)
    if check_manifest(os.path.join(current_directory, 'manifest.json')):
        sys.exit(main())
    else:
        sys.exit(2)
