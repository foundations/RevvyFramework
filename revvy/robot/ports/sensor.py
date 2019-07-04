import struct
from collections import namedtuple

from revvy.mcu.rrrc_control import RevvyControl
from revvy.robot.ports.common import PortHandler, PortInstance


SensorValue = namedtuple('SensorValue', ['raw', 'converted'])


def create_sensor_port_handler(interface: RevvyControl, configs: dict):
    port_amount = interface.get_sensor_port_amount()
    port_types = interface.get_sensor_port_types()

    drivers = {
        'NotConfigured': lambda port, cfg: None,
        'BumperSwitch':  bumper_switch,
        'HC_SR04':       hcsr04
    }
    handler = PortHandler(interface, configs, drivers, port_amount, port_types)
    handler._set_port_type = interface.set_sensor_port_type

    return handler


class BaseSensorPortDriver:
    def __init__(self, port: PortInstance):
        self._port = port
        self._interface = port.interface
        self._value = None

    @property
    def has_data(self):
        return self._value is not None

    def read(self):
        raw = self._interface.get_sensor_port_value(self._port.id)
        converted = self.convert_sensor_value(raw)
        if converted is not None:
            self._value = converted

        return SensorValue(raw=raw, converted=self._value)

    @property
    def value(self):
        return self._value

    def convert_sensor_value(self, raw): raise NotImplementedError


# noinspection PyUnusedLocal
def bumper_switch(port: PortInstance, cfg):
    sensor = BaseSensorPortDriver(port)

    def process_bumper(raw):
        assert len(raw) == 2
        return raw[1] == 1

    sensor.convert_sensor_value = process_bumper
    return sensor


# noinspection PyUnusedLocal
def hcsr04(port: PortInstance, cfg):
    sensor = BaseSensorPortDriver(port)

    def process_ultrasonic(raw):
        assert len(raw) == 4
        dst = int.from_bytes(raw, byteorder='little')
        if dst == 0:
            return None
        return dst

    sensor.convert_sensor_value = process_ultrasonic
    return sensor
