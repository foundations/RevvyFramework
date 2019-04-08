#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI

import math
import struct

from utils import *

pids = {
    'pos': {
        'good': [1.5, 0.02, 0, -10, 100],
        'bad':  [0.9, 0.05, 0, -100, 100]
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
    
class CatAppPult(RevvyApp):
    def __init__(self):
        super().__init__()
        
        self._motorFL = self.motorPortMap[1]
        self._motorFR = self.motorPortMap[6]
        self._motorRL = self.motorPortMap[2]
        self._motorRR = self.motorPortMap[5]
        
        # 1 gomb, ami labdát adagol pos ctrl motorral
        self._armMotor = self.motorPortMap[4]
        
        # analóg gomb szintén kilövőnek
        self._shooterButton  = self.sensorPortMap[1]
        
        self._currentArmPosition = 0
        self._minArmPosition = 0
        self._maxArmPosition = 200
        
        shooterButtonHandler = EdgeTrigger()
        shooterButtonHandler.onRisingEdge(self.shootAndRetract)
        self._buttons[0] = shooterButtonHandler
        
        self._analogShooterButtonHandler = EdgeTrigger()
        self._analogShooterButtonHandler.onRisingEdge(self.shootAndRetract)
        
    def init(self):
        status = True

        status = status and self.configureMotor(self._armMotor, "good", "position")
        status = status and self.configureMotor(self._motorFL, "good", "speed")
        status = status and self.configureMotor(self._motorFR, "good", "speed")
        status = status and self.configureMotor(self._motorRL, "good", "speed")
        status = status and self.configureMotor(self._motorRR, "good", "speed")
        
        if status == True:
            self.retract()
        
        return status

    def run(self):
        buttonValue = self._myrobot.sensor_get_value(self._shooterButton)
        if (len(buttonValue) > 0):
            self._analogShooterButtonHandler.handle(buttonValue[0])

    def shootAndRetract(self):
        print("FIRE!!")
        self.shoot()
        time.sleep(2)
        self.retract()
        
    def shoot(self):
        newPos = self._maxArmPosition
        self._myrobot.motor_set_state(self._armMotor, newPos)
        self._currentArmPosition = newPos

    def retract(self):
        newPos = 0
        self._myrobot.motor_set_state(self._armMotor, newPos)
        self._currentArmPosition = newPos

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
        
        status = self._myrobot.motor_set_type(motor, self._motor_types[motorTypeMap[controlType]])
        
        if controlTypeMap[controlType] != None:
            (p, i, d, ll, ul) = controlTypeMap[controlType][motorType]
            pidConfig = bytearray(struct.pack(">" + 5 * "f", p, i, d, ll, ul))
            status = status and self._myrobot.motor_set_config(motor, pidConfig)
            
        status = status and self._myrobot.motor_set_state(motor, 0)
        
        return status

    def handleSpeedControl(self, vecLen, vecAngle):
        (sl, sr) = differentialControl(vecLen, vecAngle)
        
        self._myrobot.motor_set_state(self._motorFL, int(sl * self._maxVl))
        self._myrobot.motor_set_state(self._motorRL, int(sl * self._maxVl))
        self._myrobot.motor_set_state(self._motorFR, int(sr * self._maxVr))
        self._myrobot.motor_set_state(self._motorRR, int(sr * self._maxVr))
    
app = CatAppPult()
def main():
    startRevvy(CatAppPult())

if __name__ == "__main__":
    main()
