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
        
        self._motorFL = None
        self._motorFR = None
        self._motorRL = None
        self._motorRR = None
        
        # 1 gomb, ami labdát adagol pos ctrl motorral
        self._armMotor = self.motorPortMap[4]
        
        # analóg gomb szintén kilövőnek
        self._shooterButton  = self.sensorPortMap[1]
        
        self._currentArmPosition = 0
        self._minArmPosition = 0
        self._maxArmPosition = 200
        
        shooterButtonHandler = EdgeTrigger()
        shooterButtonHandler.onRisingEdge(self.shoot)
        self._buttons[0] = shooterButtonHandler
        
        retractButtonHandler = EdgeTrigger()
        retractButtonHandler.onRisingEdge(self.retract)
        self._buttons[1] = retractButtonHandler
        
        self._analogShooterButtonHandler = EdgeTrigger()
        self._analogShooterButtonHandler.onRisingEdge(self.shootAndRetract)
        
    def init(self):
        status = True

        status = status and self.configureMotor(self._armMotor, "good", "position")
        
        if status == True:
            self.retract()
        
        return status

    def run(self):
        buttonValue = self._myrobot.sensor_get_value(self._shooterButton)
        if (len(buttonValue) > 0):
            self._analogShooterButtonHandler.handle(buttonValue[0])

    def shootAndRetract(self):
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
        
        #self._myrobot.motor_set_state(self._leftDriveMotor,  int(sl * self._maxVl))
        #self._myrobot.motor_set_state(self._rightDriveMotor, int(sr * self._maxVr))
    
app = CatAppPult()
def main():
    startRevvy(CatAppPult())

if __name__ == "__main__":
    main()
