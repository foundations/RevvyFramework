#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI
from revvy.ble_revvy import Observable, RevvyBLE
from revvy.file_storage import FileStorage
from revvy.longmessage import LongMessageHandler, LongMessageStorage
from revvy.rrrc_transport_i2c import RevvyTransportI2C
from revvy.utils import *
from revvy.rrrc_transport import *
from revvy.robot_config import *
import sys


def toggle_ring_led(args):
    if args['robot']._ring_led:
        if args['robot']._ring_led.scenario == RingLed.ColorWheel:
            args['robot']._ring_led.set_scenario(RingLed.Off)
        else:
            args['robot']._ring_led.set_scenario(RingLed.ColorWheel)


toggle_ring_led_str = """
if robot._ring_led:
    if robot._ring_led.scenario == RingLed.ColorWheel:
        robot._ring_led.set_scenario(RingLed.Off)
    else:
        robot._ring_led.set_scenario(RingLed.ColorWheel)
"""


def startRevvy(interface: RevvyTransportInterface, config: RobotConfig = None):
    # prepare environment
    directory = os.path.dirname(os.path.realpath(__file__))
    print('Revvy run from {} ({})'.format(directory, __file__))
    os.chdir(directory)

    dnp = DeviceNameProvider(FileStorage('./data/device'), lambda: 'Revvy_{}'.format(getserial().lstrip('0')))
    device_name = Observable(dnp.get_device_name())
    long_message_handler = LongMessageHandler(LongMessageStorage(FileStorage("./data/ble")))

    ble = RevvyBLE(device_name, getserial(), long_message_handler)

    robot = RobotManager(interface, ble, config)

    def on_device_name_changed(new_name):
        print('Device name changed to {}'.format(new_name))
        dnp.update_device_name(new_name)

    def on_message_updated(storage, message_type):
        print('Message type activated: {}'.format(message_type))

        message_data = storage.get_long_message(message_type)
        print('Received message: {}'.format(message_data))
        #robot.configure(RobotConfig.from_string(message_data))

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
    default_config.motors[2] = "RevvyMotor"
    default_config.motors[3] = "RevvyMotor"
    default_config.motors[5] = "RevvyMotor"
    default_config.motors[6] = "RevvyMotor"

    default_config.drivetrain['left'] = [2, 3]
    default_config.drivetrain['right'] = [5, 6]

    default_config.sensors[1] = "HC_SR04"
    # default_config.analog_handlers.push({'channels': [0, 1], )
    default_config.controller.buttons[0] = 'toggle_ring_led'
    # default_config.controller.buttons[1] = 'toggle_ring_led_str'

    default_config.scripts['toggle_ring_led'] = {'script': toggle_ring_led, 'priority': 0}
    # default_config.scripts['toggle_ring_led_str'] = {'script': toggle_ring_led_str, 'priority': 0}

    with RevvyTransportI2C(RevvyControl.mcu_address) as robot_interface:
        startRevvy(robot_interface, default_config)


if __name__ == "__main__":
    main()
