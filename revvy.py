#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI

from utils import *
from activation import *
from rrrc_transport import *
from functions import *


class SuperchargeDemo(RevvyApp):
    def __init__(self, interface):
        super().__init__(interface)

        self._maxVl = 90
        self._maxVr = 90

        self._left_motors = None
        self._right_motors = None

        button_led = ToggleButton()
        button_led.onEnabled(lambda: self.set_ring_led_mode(RingLed.LED_RING_COLOR_WHEEL))
        button_led.onDisabled(lambda: self.set_ring_led_mode(RingLed.LED_RING_OFF))
        self._buttons[0] = button_led

    def init(self):
        status = True

        self._left_motors = [
            self._motor_ports.configure(self.motorPortMap[2], 'SpeedControlled'),
            self._motor_ports.configure(self.motorPortMap[3], 'SpeedControlled')
        ]

        self._right_motors = [
            self._motor_ports.configure(self.motorPortMap[5], 'SpeedControlled'),
            self._motor_ports.configure(self.motorPortMap[6], 'SpeedControlled')
        ]

        return status

    def handle_analog_values(self, analog_values):
        x = clip((analog_values[0] - 128) / 127.0, -1, 1)
        y = clip((analog_values[1] - 128) / 127.0, -1, 1)

        vec_angle = math.atan2(y, x)
        vec_len = math.sqrt(x * x + y * y)
        (sl, sr) = differentialControl(vec_len, vec_angle)

        for motor in self._left_motors:
            motor.set_speed(sl * self._maxVl)

        for motor in self._right_motors:
            motor.set_speed(sr * self._maxVr)


def main():
    with RevvyTransportI2C(RevvyControl.mcu_address) as robot_interface:
        startRevvy(SuperchargeDemo(robot_interface))


if __name__ == "__main__":
    main()
