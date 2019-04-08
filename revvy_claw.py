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
        'ugly': [2, 0.2, 0, -60, 100],
        'good': [2, 0.05, 0, -30, 30],
        'bad':  [2, 0.05, 0, -90, 90]
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

openClawPosition = 150
    
class ClawApp(RevvyApp):
    def __init__(self):
        super().__init__()

        self._motorL = self.motorPortMap[6]
        self._motorR = self.motorPortMap[3]
        
        self._maxVl = motorSpeeds['good']
        self._maxVr = motorSpeeds['good']
        
        # 1 gomb, ami labdát adagol pos ctrl motorral
        self._clawMotor = self.motorPortMap[2]
        self._armMotor = self.motorPortMap[1]
        
        self._armPosition = 0
        
        openButtonHandler = EdgeTrigger()
        openButtonHandler.onRisingEdge(self.openClaw)
        self._buttons[0] = openButtonHandler

        closeButtonHandler = EdgeTrigger()
        closeButtonHandler.onRisingEdge(self.closeClaw)
        self._buttons[1] = closeButtonHandler
        
        openButtonHandler = EdgeTrigger()
        openButtonHandler.onRisingEdge(self.armUp)
        self._buttons[2] = openButtonHandler

        closeButtonHandler = EdgeTrigger()
        closeButtonHandler.onRisingEdge(self.armDown)
        self._buttons[3] = closeButtonHandler

        #openButtonHandler = LevelTrigger()
        #openButtonHandler.onHigh(self.armUp)
        #self._buttons[2] = openButtonHandler
        #
        #closeButtonHandler = LevelTrigger()
        #closeButtonHandler.onHigh(self.armDown)
        #self._buttons[3] = closeButtonHandler
        
    def init(self):
        status = True

        status = status and self.configureMotor(self._clawMotor, "good", "position")
        status = status and self.configureMotor(self._armMotor,  "ugly", "position")
                 
        status = status and self.configureMotor(self._motorL, "good", "speed")
        status = status and self.configureMotor(self._motorR, "good", "speed")
        
        self._myrobot.ring_led_set_scenario(6)
        
        return status
        
    def run(self):
        pass
        
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
        status = status and self._myrobot.motor_set_state(motor, 0)
        if controlTypeMap[controlType] is not None:
            status = status and self.setMotorPid(motor, controlTypeMap[controlType][motorType])
        
        return status
    
    def openClaw(self):
        print("Open")
        self._myrobot.motor_set_state(self._clawMotor, openClawPosition)
    
    def closeClaw(self):
        print("Close")
        self._myrobot.motor_set_state(self._clawMotor, -openClawPosition)
    
    def armUp(self):
        print("Up")
        self._myrobot.motor_set_state(self._armMotor, 700)
    
    def armDown(self):
        print("Down")
        self._myrobot.motor_set_state(self._armMotor, 0)

    def handleSpeedControl(self, vecLen, vecAngle):
        (sl, sr) = differentialControl(vecLen, vecAngle)
        
        self._myrobot.motor_set_state(self._motorL, int(sl * self._maxVl))
        self._myrobot.motor_set_state(self._motorR, int(sr * self._maxVr))

def main():
    startRevvy(ClawApp())

if __name__ == "__main__":
    main()
