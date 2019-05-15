#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI

from utils import *
from activation import *
from rrrc_transport import *


class SuperchargeDemo(RevvyApp):
    def __init__(self, interface):
        super().__init__(interface)

        self._drivetrain = DifferentialDrivetrain()

        self._maxVl = 90
        self._maxVr = 90

        button_led = ToggleButton()
        button_led.onEnabled(lambda: self.set_ring_led_mode(RingLed.LED_RING_COLOR_WHEEL))
        button_led.onDisabled(lambda: self.set_ring_led_mode(RingLed.LED_RING_OFF))
        self._buttons[0] = button_led

    def init(self):
        status = True

        self._drivetrain.add_left_motor(self._motor_ports.configure(self.motorPortMap[2], 'SpeedControlled'))
        self._drivetrain.add_left_motor(self._motor_ports.configure(self.motorPortMap[3], 'SpeedControlled'))

        self._drivetrain.add_right_motor(self._motor_ports.configure(self.motorPortMap[5], 'SpeedControlled'))
        self._drivetrain.add_right_motor(self._motor_ports.configure(self.motorPortMap[6], 'SpeedControlled'))

        return status

    def handle_analog_values(self, analog_values):
        (angle, length) = joystick(analog_values[0], analog_values[1])
        (sl, sr) = differentialControl(length, angle)

        self._drivetrain.set_speeds(sl * self._maxVl, sr * self._maxVr)


def main():
    with RevvyTransportI2C(RevvyControl.mcu_address) as robot_interface:
        startRevvy(SuperchargeDemo(robot_interface))


if __name__ == "__main__":
    main()
