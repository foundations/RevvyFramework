#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI

from utils import *
from rrrc_transport import *
from robot_config import *


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


def main():

    default_config = RobotConfig()
    default_config.motors[2] = "Drivetrain_Left"
    default_config.motors[3] = "Drivetrain_Left"
    default_config.motors[5] = "Drivetrain_Right"
    default_config.motors[6] = "Drivetrain_Right"

    default_config.sensors[1] = "HC_SR04"
    # default_config.analog_handlers.push({'channels': [0, 1], )
    default_config.controller.buttons[0] = 'toggle_ring_led'
    default_config.controller.buttons[1] = 'toggle_ring_led_str'

    default_config.scripts['toggle_ring_led'] = {'script': toggle_ring_led, 'priority': 0}
    default_config.scripts['toggle_ring_led_str'] = {'script': toggle_ring_led_str, 'priority': 0}

    with RevvyTransportI2C(RevvyControl.mcu_address) as robot_interface:
        startRevvy(robot_interface, default_config)


if __name__ == "__main__":
    main()
