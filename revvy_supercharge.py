#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI

from utils import *
import time

pids = {
    'pos': {
        'good': [1.5, 0.02, 0, -80, 20],
        'bad':  [0.9, 0.05, 0, -80, 20]
    },
    'speed': {
        'good': [5, 0.25, 0, -90, 90],
        'bad':  [1, 0.2,  0, -90, 90]
    }
}

motorSpeeds = {
    'good': 90,
    'bad':  22
}

ticks = {
    'good': 12 * 2,
    'bad':   3 * 2
}

motorResolutions = {
    'good': 1168,
    'bad': 292
}

class SuperchargeDemo(RevvyApp):
    def __init__(self):
        super().__init__()
        
        self._motorFL = self.motorPortMap[3]
        self._motorFR = self.motorPortMap[6]
        
        self._maxVl = motorSpeeds['good']
        self._maxVr = motorSpeeds['good']

        self._ledMode = 0
        
        ledButton = ToggleButton()
        ledButton.onEnabled(self.switchToColorWheel)
        ledButton.onDisabled(self.ledRingOff)
        self._buttons[0] = ledButton

    def switchToColorWheel(self):
        self._myrobot.ring_led_set_scenario(6)
        
    def ledRingOff(self):
        self._myrobot.ring_led_set_scenario(0)
        
    def init(self):
        status = True

        status = status and self.configureMotor(self._motorFL, "good", "speed")
        status = status and self.configureMotor(self._motorFR, "good", "speed")

        return status
        
    def configureMotor(self, motor, motorType, controlType):
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
        
        status = self._myrobot.motor_set_type(motor, self._myrobot.motors[motorTypeMap[controlType]])
        status = status and self._myrobot.motor_set_state(motor, 0)
        if controlTypeMap[controlType] is not None:
            status = status and self.setMotorPid(motor, controlTypeMap[controlType][motorType])
        
        return status

    def handleAnalogValues(self, analogValues):
        analogA = analogValues[0] # 0...255
        analogB = analogValues[1] # 0...255
        
        x = clip((analogA - 128) / 127.0, -1, 1)
        y = clip((analogB - 128) / 127.0, -1, 1)
        
        vecAngle = math.atan2(y, x)
        vecLen   = math.sqrt(x*x + y*y) * 100
        (sl, sr) = differentialControl(vecLen, vecAngle)
        
        self._myrobot.motor_set_state(self._motorFL, int(sl * self._maxVl))
        self._myrobot.motor_set_state(self._motorFR, int(sr * self._maxVr))

def main():
    startRevvy(SuperchargeDemo())

if __name__ == "__main__":
    main()
