#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI

from utils import *
from activation import *
from rrrc_transport import *

pids = {
    'pos':   {
        'good': [1.5, 0.02, 0, -80, 20],
        'bad':  [0.9, 0.05, 0, -80, 20]
    },
    'speed': {
        'good': [5, 0.25, 0, -90, 90],
        'bad':  [1, 0.2, 0, -90, 90]
    }
}

motorSpeeds = {
    'good': 90,
    'bad':  22
}

ticks = {
    'good': 12 * 2,
    'bad':  3 * 2
}

motorResolutions = {
    'good': 1168,
    'bad':  292
}

motorTypeMap = {
    'speed':    "MOTOR_SPEED_CONTROLLED",
    'position': "MOTOR_POSITION_CONTROLLED",
    'openLoop': "MOTOR_OPEN_LOOP"
}

controlTypeMap = {
    'speed':    pids['speed'],
    'position': pids['pos'],
    'openLoop': None
}


class SuperchargeDemo(RevvyApp):
    def __init__(self, interface):
        super().__init__(interface)

        self._motorFL = self.motorPortMap[3]
        self._motorFR = self.motorPortMap[6]

        self._maxVl = motorSpeeds['good']
        self._maxVr = motorSpeeds['good']

        self._ledMode = 0

        button_led = ToggleButton()
        button_led.onEnabled(lambda: self.setLedRingMode(RevvyApp.LED_RING_COLOR_WHEEL))
        button_led.onDisabled(lambda: self.setLedRingMode(RevvyApp.LED_RING_OFF))
        self._buttons[0] = button_led

    def init(self):
        status = True

        #status = status and self.configureMotor(self._motorFL, "good", "speed")
        #status = status and self.configureMotor(self._motorFR, "good", "speed")

        return status

    def configureMotor(self, motor, motor_type, control_type):
        status = self._robot_control.motor_set_type(motor, self._robot_control.motors[motorTypeMap[control_type]])
        status = status and self._robot_control.motor_set_state(motor, 0)
        if controlTypeMap[control_type]:
            status = status and self.setMotorPid(motor, controlTypeMap[control_type][motor_type])

        return status

    def handleAnalogValues(self, analog_values):
        analog_a = analog_values[0]  # 0...255
        analog_b = analog_values[1]  # 0...255

        x = clip((analog_a - 128) / 127.0, -1, 1)
        y = clip((analog_b - 128) / 127.0, -1, 1)

        vec_angle = math.atan2(y, x)
        vec_len = math.sqrt(x * x + y * y) * 100
        (sl, sr) = differentialControl(vec_len, vec_angle)

        #self._robot_control.motor_set_state(self._motorFL, int(sl * self._maxVl))
        #self._robot_control.motor_set_state(self._motorFR, int(sr * self._maxVr))


def main():
    with RevvyTransportI2C(RevvyControl.mcu_address) as robot_interface:
        startRevvy(SuperchargeDemo(robot_interface))


if __name__ == "__main__":
    main()
