from revvy.ports.motor import MotorPortInstance
from revvy.ports.sensor import SensorPortInstance


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
        self._motor.set_position(position)


class RingLedWrapper:
    """Wrapper class to expose LED ring to user scripts"""
    def __init__(self, ring_led):
        self._ring_led = ring_led

    def set_scenario(self, scenario):
        return self._ring_led.set_scenario(scenario)


# FIXME: type hints missing because of circular reference that causes ImportError
class RobotInterface:
    """Wrapper class that exposes API to user-written scripts"""
    def __init__(self, robot):
        self._motors = map(lambda port: MotorPortWrapper(port), robot._motor_ports)
        self._sensors = map(lambda port: SensorPortWrapper(port), robot._sensor_ports)
        self._ring_led = RingLedWrapper(robot._ring_led)

    @property
    def motors(self):
        return self._motors

    @property
    def sensors(self):
        return self._sensors

    @property
    def ring_led(self):
        return self._ring_led
