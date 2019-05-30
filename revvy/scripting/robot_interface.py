import time

import math

from revvy.ports.motor import MotorPortInstance, MotorPortHandler
from revvy.ports.sensor import SensorPortInstance, SensorPortHandler


class SensorPortWrapper:
    """Wrapper class to expose sensor ports to user scripts"""
    def __init__(self, sensor: SensorPortInstance):
        self._sensor = sensor

    def configure(self, config_name):
        self._sensor.configure(config_name)

    def read(self):
        """Return the last converted value"""
        return self._sensor.value


class MotorPortWrapper:
    """Wrapper class to expose motor ports to user scripts"""
    def __init__(self, motor: MotorPortInstance):
        self._motor = motor

    def configure(self, config_name):
        self._motor.configure(config_name)

    def move_to_position(self, position):
        """Move the motor to the given position - give control back only if we're close"""
        current_pos = self._motor.position
        close_threshold = math.fabs(position - current_pos) * 0.1
        self._motor.set_position(position)
        while math.fabs(position - self._motor.position) > close_threshold:
            print(self._motor.position)
            time.sleep(0.2)
        while math.fabs(self._motor.speed) > self._motor.get_speed_limit() / 10:
            time.sleep(0.2)


class RingLedWrapper:
    """Wrapper class to expose LED ring to user scripts"""
    def __init__(self, ring_led):
        self._ring_led = ring_led

    @property
    def scenario(self):
        return self._ring_led.scenario

    def set_scenario(self, scenario):
        return self._ring_led.set_scenario(scenario)


class PortCollection:
    def __init__(self, ports: list, port_map: list):
        self._ports = ports
        self._portMap = port_map

    def __getitem__(self, item):
        return self._ports[self._portMap[item]]


class Direction:
    FORWARD = 0
    BACKWARD = 1
    LEFT = 2
    RIGHT = 3


class RPM:
    def __init__(self, rpm):
        self._rpm = rpm

    @property
    def rpm(self):
        return self._rpm


class Power:
    def __init__(self, power):
        self._power = power

    @property
    def power(self):
        return self._power


class DriveTrainWrapper:
    def __init__(self, drivetrain):
        self._drivetrain = drivetrain

    def drive(self, direction, amount, limit=None):
        if direction in [Direction.FORWARD, Direction.BACKWARD]:
            degrees = amount * 360
            if direction == Direction.BACKWARD:
                degrees *= -1
            print('Moving {} degrees'.format(degrees))
            if limit is None:
                self._drivetrain.move(degrees, degrees)
            elif limit is RPM:
                self._drivetrain.move(degrees, degrees, limit.rpm, limit.rpm)
            elif limit is Power:
                self._drivetrain.move(degrees, degrees, power_limit=limit.power)
        else:
            degrees = amount * 360
            if direction == Direction.RIGHT:
                degrees *= -1
            print('Turning {} degrees'.format(degrees))
            if limit is None:
                self._drivetrain.move(-degrees, degrees)
            elif limit is RPM:
                self._drivetrain.move(-degrees, degrees, limit.rpm, limit.rpm)
            elif limit is Power:
                self._drivetrain.move(-degrees, degrees, power_limit=limit.power)


# FIXME: type hints missing because of circular reference that causes ImportError
class RobotInterface:
    """Wrapper class that exposes API to user-written scripts"""
    def __init__(self, robot):
        motor_wrappers = list(map(lambda port: MotorPortWrapper(port), robot._motor_ports))
        sensor_wrappers = list(map(lambda port: SensorPortWrapper(port), robot._sensor_ports))
        self._motors = PortCollection(motor_wrappers, MotorPortHandler.motorPortMap)
        self._sensors = PortCollection(sensor_wrappers, SensorPortHandler.sensorPortMap)
        self._ring_led = RingLedWrapper(robot._ring_led)
        self._drivetrain = DriveTrainWrapper(robot._drivetrain)
        self.drive = self._drivetrain.drive

    @property
    def motors(self):
        return self._motors

    @property
    def sensors(self):
        return self._sensors

    @property
    def ring_led(self):
        return self._ring_led

