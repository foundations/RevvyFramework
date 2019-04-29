#!/usr/bin/python3

# Demo of revvy BLE peripheral using python port of bleno, pybleno
#
# Setup:
# sudo setcap 'cap_net_raw,cap_net_admin+eip' $(readlink -f $(which python3))
# # Enables python3 to open raw sockets. Required by bleno to talk to BT via HCI

from utils import *
import time
from activation import *

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


class CatAppPult(RevvyApp):
    def __init__(self):
        super().__init__()

        self._motorFL = self.motorPortMap[5]
        self._motorFR = self.motorPortMap[3]
        self._motorRL = self.motorPortMap[6]
        self._motorRR = self.motorPortMap[2]

        self._maxVl = motorSpeeds['good']
        self._maxVr = motorSpeeds['good']

        # 1 gomb, ami labdát adagol pos ctrl motorral
        self._armMotor = self.motorPortMap[1]

        # analóg gomb szintén kilövőnek
        self._shooterButton = self.sensorPortMap[1]
        self._ultrasoundSensor = self.sensorPortMap[2]

        self._ledMode = 0

        shooterButtonHandler = EdgeTrigger()
        shooterButtonHandler.onRisingEdge(self.shootAndRetract)
        self._buttons[0] = shooterButtonHandler

        self._analogShooterButtonHandler = EdgeTrigger()
        self._analogShooterButtonHandler.onRisingEdge(self.shootAndRetract)

        self._indicationButtonHandler = EdgeTrigger()
        self._indicationButtonHandler.onRisingEdge(self.switchToColorWheel)
        self._indicationButtonHandler.onFallingEdge(self.ledRingOff)

    def switchToColorWheel(self):
        self._robot_control.ring_led_set_scenario(6)

    def ledRingOff(self):
        self._robot_control.ring_led_set_scenario(0)

    def showDistanceOnLeds(self, distance):
        frame = []
        distance = clip(distance - 3, 0, 33) / 3
        for i in range(12):
            if i >= distance:
                frame += [0x10, 0, 0]
            else:
                frame += [0, 0, 0]

        self._robot_control.ring_led_show_user_frame(frame)

    def init(self):
        status = True

        status = status and self.configureMotor(self._armMotor, "good", "openLoop")
        status = status and self.configureMotor(self._motorFL, "good", "speed")
        status = status and self.configureMotor(self._motorFR, "good", "speed")
        status = status and self.configureMotor(self._motorRL, "good", "speed")
        status = status and self.configureMotor(self._motorRR, "good", "speed")

        status = status and self._robot_control.sensor_set_type(self._shooterButton, self._robot_control.sensors["ABUTTON"])
        status = status and self._robot_control.sensor_set_type(self._ultrasoundSensor, self._robot_control.sensors["HC_SR05"])

        return status

    def run(self):
        buttonValue = self._robot_control.sensor_get_value(self._shooterButton)
        if (len(buttonValue) > 0):
            print("ab: {}".format(buttonValue[0]))
            self._analogShooterButtonHandler.handle(buttonValue[0])

        usValue = self._robot_control.sensor_get_value(self._ultrasoundSensor)
        if (len(usValue) > 0):
            distance = usValue[0]
            print("dis: {}".format(distance))
            if (distance <= 36):
                self._ledMode = 0
                self.showDistanceOnLeds(distance)
            elif self._ledMode == 0:
                self._ledMode = 1
                self.switchToColorWheel()
            else:
                pass

    def shootAndRetract(self):
        print("FIRE!!")
        self.shoot()

    def shoot(self):
        self._robot_control.motor_set_state(self._armMotor, -60)
        time.sleep(0.05)
        self._robot_control.motor_set_state(self._armMotor, 0)

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

        status = self._robot_control.motor_set_type(motor, self._robot_control.motors[motorTypeMap[controlType]])
        status = status and self._robot_control.motor_set_state(motor, 0)
        if controlTypeMap[controlType] is not None:
            status = status and self.setMotorPid(motor, controlTypeMap[controlType][motorType])

        return status

    def handleSpeedControl(self, vecLen, vecAngle):
        (sl, sr) = differentialControl(vecLen, vecAngle)

        self._robot_control.motor_set_state(self._motorFL, int(sl * self._maxVl))
        self._robot_control.motor_set_state(self._motorRL, int(sl * self._maxVl))
        self._robot_control.motor_set_state(self._motorFR, int(sr * self._maxVr))
        self._robot_control.motor_set_state(self._motorRR, int(sr * self._maxVr))


app = CatAppPult()


def main():
    startRevvy(CatAppPult())


if __name__ == "__main__":
    main()
