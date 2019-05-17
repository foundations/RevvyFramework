#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI

from utils import *
from rrrc_transport import *


class SuperchargeDemo(RevvyApp):
    def __init__(self, robot: RevvyControl):
        super().__init__(robot)

        self._maxVl = 90
        self._maxVr = 90

        self._drivetrain = None

        self._remote_controller.on_analog_values([0, 1], self._handle_joystick)
        self._remote_controller.on_button_pressed(0, self._toggle_ring_led)

    def init(self):
        self._motor_ports[2].configure('SpeedControlled')
        self._motor_ports[3].configure('SpeedControlled')
        self._motor_ports[5].configure('SpeedControlled')
        self._motor_ports[6].configure('SpeedControlled')

        self._drivetrain = DifferentialDrivetrain()

        self._drivetrain.add_left_motor(self._motor_ports[2])
        self._drivetrain.add_left_motor(self._motor_ports[3])

        self._drivetrain.add_right_motor(self._motor_ports[5])
        self._drivetrain.add_right_motor(self._motor_ports[6])

    def _handle_joystick(self, channels):
        if self._drivetrain:
            (angle, length) = joystick(channels[0], channels[1])
            (sl, sr) = differentialControl(length, angle)

            self._drivetrain.set_speeds(sl * self._maxVl, sr * self._maxVr)

    def _toggle_ring_led(self):
        if self._ring_led:
            if self._ring_led.scenario == RingLed.ColorWheel:
                self._ring_led.set_scenario(RingLed.Off)
            else:
                self._ring_led.set_scenario(RingLed.ColorWheel)


def main():
    with RevvyTransportI2C(RevvyControl.mcu_address) as robot_interface:
        startRevvy(SuperchargeDemo(robot_interface))


if __name__ == "__main__":
    main()
