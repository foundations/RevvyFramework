#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI

from utils import *
from activation import *

pids = {
    'pos':   {
        'good': [0.9, 0.02, 0, -75, 75],
        'bad':  [0.9, 0.05, 0, -75, 75]
    },
    'speed': {
        'good': [5, 0.25, 0, -90, 90],
        'bad':  [1, 0.2, 0, -50, 50]
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


class ShooterApp(RevvyApp):
    def __init__(self):
        super().__init__()

        # joystick 2 motort sebesség szabályoz
        self._leftDriveMotor = self.motorPortMap[6]
        self._rightDriveMotor = self.motorPortMap[3]

        self._maxVl = motorSpeeds['good']
        self._maxVr = motorSpeeds['good']

        # 2 motor maxon kilövőnek, gombbal kapcsolva
        self._shooterMotor1 = self.motorPortMap[4]
        self._shooterMotor2 = self.motorPortMap[1]

        # 1 gomb, ami labdát adagol pos ctrl motorral
        self._ballFeederMotor = self.motorPortMap[2]

        # kilövő emelő (pos ctrl)
        self._armRaiseMotor = self.motorPortMap[5]

        # analóg gomb szintén kilövőnek
        self._shooterButton = self.sensorPortMap[1]

        self._currentShooterPosition = 0
        self._shooterIncrement = -motorResolutions['good'] / 4

        self._currentArmPosition = 0
        self._minArmPosition = 0
        self._maxArmPosition = 200

        shooterButtonHandler = EdgeTrigger()
        shooterButtonHandler.onRisingEdge(self.feedBall)
        self._buttons[0] = shooterButtonHandler

        startStopButtonHandler = ToggleButton()
        startStopButtonHandler.onEnabled(self.enableShooter)
        startStopButtonHandler.onDisabled(self.disableShooter)
        self._buttons[1] = startStopButtonHandler

        raiseButtonHandler = LevelTrigger()
        raiseButtonHandler.onHigh(self.raiseArm)
        self._buttons[2] = raiseButtonHandler

        lowerButtonHandler = LevelTrigger()
        lowerButtonHandler.onHigh(self.lowerArm)
        self._buttons[4] = lowerButtonHandler

        self._analogShooterButtonHandler = EdgeTrigger()
        self._analogShooterButtonHandler.onRisingEdge(self.feedBall)

    def init(self):
        status = True

        status = status and self.configureMotor(self._leftDriveMotor, "good", "speed")
        status = status and self.configureMotor(self._rightDriveMotor, "good", "speed")
        status = status and self.configureMotor(self._shooterMotor1, "good", "openLoop")
        status = status and self.configureMotor(self._shooterMotor2, "good", "openLoop")
        status = status and self.configureMotor(self._ballFeederMotor, "good", "position")
        status = status and self.configureMotor(self._armRaiseMotor, "good", "position")

        status = status and self._myrobot.sensor_set_type(self._shooterButton, self._myrobot.sensors["ABUTTON"])

        return status

    def run(self):
        # buttonValue = self._myrobot.sensor_get_value(self._shooterButton)
        # if (len(buttonValue) > 0):
        #    self._analogShooterButtonHandler.handle(buttonValue[0])
        pass

    def disableShooter(self):
        self._myrobot.motor_set_state(self._shooterMotor1, 0)
        self._myrobot.motor_set_state(self._shooterMotor2, 0)

    def enableShooter(self):
        self._myrobot.motor_set_state(self._shooterMotor1, -100)
        self._myrobot.motor_set_state(self._shooterMotor2, 100)

    def raiseArm(self):
        if self._currentArmPosition < self._maxArmPosition:
            self._currentArmPosition = self._currentArmPosition + 5
            self._myrobot.motor_set_state(self._armRaiseMotor, self._currentArmPosition)

    def lowerArm(self):
        if self._currentArmPosition > self._minArmPosition:
            self._currentArmPosition = self._currentArmPosition - 5
            self._myrobot.motor_set_state(self._armRaiseMotor, self._currentArmPosition)

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

    def handleSpeedControl(self, vecLen, vecAngle):
        (sl, sr) = differentialControl(vecLen, vecAngle)

        self._myrobot.motor_set_state(self._leftDriveMotor, int(sl * self._maxVl))
        self._myrobot.motor_set_state(self._rightDriveMotor, int(sr * self._maxVr))

    def feedBall(self):
        newPos = self._currentShooterPosition - self._shooterIncrement
        self._myrobot.motor_set_state(self._ballFeederMotor, int(newPos))
        self._currentShooterPosition = newPos


def main():
    startRevvy(ShooterApp())


if __name__ == "__main__":
    main()
