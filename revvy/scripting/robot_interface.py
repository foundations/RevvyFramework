import time
import math

from revvy.ports.motor import MotorPortInstance, MotorPortHandler
from revvy.ports.sensor import SensorPortInstance, SensorPortHandler


class Wrapper:
    def __init__(self, resources: dict, priority=0):
        self._resources = resources
        self._priority = priority

    def try_take(self, resource_name):
        return self._resources[resource_name].try_take(self._priority)


class SensorPortWrapper(Wrapper):
    """Wrapper class to expose sensor ports to user scripts"""
    def __init__(self, sensor: SensorPortInstance, resources: dict, priority=0):
        super().__init__(resources, priority)
        self._sensor = sensor

    def configure(self, config_name):
        self._sensor.configure(config_name)

    def read(self):
        """Return the last converted value"""
        return self._sensor.value


class MotorPortWrapper(Wrapper):
    """Wrapper class to expose motor ports to user scripts"""
    def __init__(self, motor: MotorPortInstance, resources: dict, priority=0):
        super().__init__(resources, priority)
        self._motor = motor

    def configure(self, config_name):
        self._motor.configure(config_name)

    def move_to_position(self, position):
        """Move the motor to the given position - give control back only if we're close"""
        resource = self.try_take('motor_{}')
        try:
            resource.run(lambda: self._motor.set_position(position))
            current_pos = self._motor.position
            close_threshold = math.fabs(position - current_pos) * 0.1
            while not resource.is_interrupted and math.fabs(position - self._motor.position) > close_threshold:
                time.sleep(0.2)
            while not resource.is_interrupted and self._motor.is_moving:
                time.sleep(0.2)
        finally:
            resource.release()


class RingLedWrapper(Wrapper):
    """Wrapper class to expose LED ring to user scripts"""
    def __init__(self, ring_led, resources: dict, priority=0):
        super().__init__(resources, priority)
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


class DriveTrainWrapper(Wrapper):
    def __init__(self, drivetrain, resources: dict, priority=0):
        super().__init__(resources, priority)
        self._drivetrain = drivetrain

    def drive(self, direction, amount, limit=None):
        degrees = amount * 360
        if direction in [Direction.BACKWARD, Direction.RIGHT]:
            degrees *= -1

        if direction in [Direction.FORWARD, Direction.BACKWARD]:
            print('Moving {} degrees'.format(degrees))
            left_degrees = degrees
            right_degrees = degrees
        else:
            print('Turning {} degrees'.format(degrees))
            left_degrees = -degrees
            right_degrees = degrees

        # start moving depending on limits
        resource = self.try_take('drivetrain')
        if resource:
            try:
                if limit is None:
                    resource.run(lambda: self._drivetrain.move(left_degrees, right_degrees))
                elif limit is RPM:
                    resource.run(lambda: self._drivetrain.move(left_degrees, right_degrees, limit.rpm, limit.rpm))
                elif limit is Power:
                    resource.run(lambda: self._drivetrain.move(left_degrees, right_degrees, power_limit=limit.power))

                # wait for movement to finish
                while not resource.is_interrupted and self._drivetrain.is_moving:
                    time.sleep(0.2)
            finally:
                resource.release()


# FIXME: type hints missing because of circular reference that causes ImportError
class RobotInterface:
    """Wrapper class that exposes API to user-written scripts"""
    def __init__(self, robot, priority=0):
        motor_wrappers = list(map(lambda port: MotorPortWrapper(port, robot.resources, priority), robot._motor_ports))
        sensor_wrappers = list(map(lambda port: SensorPortWrapper(port, robot.resources, priority), robot._sensor_ports))
        self._motors = PortCollection(motor_wrappers, MotorPortHandler.motorPortMap)
        self._sensors = PortCollection(sensor_wrappers, SensorPortHandler.sensorPortMap)
        self._ring_led = RingLedWrapper(robot._ring_led, robot.resources, priority)
        self._drivetrain = DriveTrainWrapper(robot._drivetrain, robot.resources, priority)

        # shorthand functions
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

    @property
    def drivetrain(self):
        return self._drivetrain

    # property alias
    led_ring = ring_led
