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
from revvy.longmessage import LongMessageHandler, LongMessageStorage, LongMessageType
from revvy.rrrc_transport_i2c import RevvyTransportI2C
from revvy.scripting.builtin_scripts import drive_2sticks, drive_joystick
from revvy.utils import *
from revvy.rrrc_transport import *
from revvy.robot_config import *
import sys


mcu_features = {
    '0.1-r213': [
        'motor-driver-constrained-control',
        'drivetrain-control',
        'motor-control-in-physical-values'
    ]
}


def toggle_ring_led(args):
    if args['robot']._ring_led:
        if args['robot']._ring_led.scenario == RingLed.ColorWheel:
            args['robot']._ring_led.set_scenario(RingLed.Off)
        else:
            args['robot']._ring_led.set_scenario(RingLed.ColorWheel)


test_drivetrain = """
robot.drive(Direction.FORWARD, 5)
time.sleep(3)
robot.drive(Direction.FORWARD, 5, RPM(450))
time.sleep(3)
robot.drive(Direction.RIGHT, 5)
"""


def test_position_control(args):
    robot = args['robot']
    print('moving to 720')
    robot.motors[1].move_to_position(720)
    time.sleep(1)
    print('moving to 0')
    robot.motors[1].move_to_position(0)
    time.sleep(1)
    print('moving to 720')
    robot.motors[1].move_to_position(720)
    print('moving to 0')
    robot.motors[1].move_to_position(0)


def startRevvy(interface: RevvyTransportInterface, config: RobotConfig = None):
    # prepare environment
    directory = os.path.dirname(os.path.realpath(__file__))
    serial = getserial()

    print('Revvy run from {} ({})'.format(directory, __file__))
    os.chdir(directory)

    dnp = DeviceNameProvider(FileStorage('./data/device'), lambda: 'Revvy_{}'.format(serial.lstrip('0')))
    device_name = Observable(dnp.get_device_name())
    long_message_handler = LongMessageHandler(LongMessageStorage(FileStorage("./data/ble"), MemoryStorage()))

    ble = RevvyBLE(device_name, serial, long_message_handler)

    robot = RobotManager(interface, ble, config, mcu_features)

    def on_device_name_changed(new_name):
        print('Device name changed to {}'.format(new_name))
        dnp.update_device_name(new_name)

    def on_message_updated(storage, message_type):
        print('Received message: {}'.format(message_type))
        message_data = storage.get_long_message(message_type)

        if message_type == LongMessageType.TEST_KIT:
            print('Running test script: {}'.format(message_data))
            robot._scripts.add_script("test_kit", message_data, 0)
            robot._scripts["test_kit"].start()
        elif message_type == LongMessageType.CONFIGURATION_DATA:
            print('New configuration: {}'.format(message_data))
            config = RobotConfig.from_string(message_data)
            # robot.configure(config)

    device_name.subscribe(on_device_name_changed)
    long_message_handler.on_message_updated(on_message_updated)

    try:
        robot.start()
        print("Press enter to exit")
        input()
    except KeyboardInterrupt:
        pass
    except EOFError:
        # Running as a service will end up here as stdin is empty.
        while True:
            time.sleep(1)
    finally:
        print('stopping')
        robot.stop()

    print('terminated.')
    sys.exit(1)


def main():

    default_config = RobotConfig()
    default_config.motors[1] = "RevvyMotor_CCW"
    default_config.motors[2] = "RevvyMotor_CCW"
    default_config.motors[3] = "RevvyMotor_CCW"
    default_config.motors[4] = "RevvyMotor_CCW"
    default_config.motors[5] = "RevvyMotor_CCW"
    default_config.motors[6] = "RevvyMotor_CCW"

    default_config.drivetrain['left'] = [2, 3]
    default_config.drivetrain['right'] = [5, 6]

    default_config.sensors[1] = "HC_SR04"
    default_config.sensors[2] = "BumperSwitch"
    default_config.controller.analog.push({'channels': [0, 1], 'script': 'drivetrain_joystick'})
    default_config.controller.buttons[0] = 'toggle_ring_led'
    default_config.controller.buttons[1] = 'test_position_control'

    default_config.scripts['drivetrain_joystick'] = {'script': drive_joystick, 'priority': 0}
    default_config.scripts['drivetrain_2sticks'] = {'script': drive_2sticks, 'priority': 0}
    default_config.scripts['toggle_ring_led'] = {'script': toggle_ring_led, 'priority': 0}
    default_config.scripts['test_position_control'] = {'script': test_drivetrain, 'priority': 1}

    with RevvyTransportI2C(RevvyControl.mcu_address) as robot_interface:
        startRevvy(robot_interface, default_config)


if __name__ == "__main__":
    main()
