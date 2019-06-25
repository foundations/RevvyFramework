
from revvy.mcu.rrrc_control import RevvyControl
from revvy.robot.ports.common import PortHandler, PortInstance


def create_sensor_port_handler(interface: RevvyControl, configs: dict):
    port_amount = interface.get_sensor_port_amount()
    port_types = interface.get_sensor_port_types()

    drivers = {
        'NotConfigured': lambda port, cfg: None,
        'BumperSwitch':  lambda port, cfg: BumperSwitch(port),
        'HC_SR04':       lambda port, cfg: HcSr04(port)
    }
    handler = PortHandler(interface, configs, drivers, port_amount, port_types)
    handler._set_port_type = interface.set_sensor_port_type

    return handler


class BaseSensorPort:
    def __init__(self, port: PortInstance):
        self._port = port
        self._interface = port.interface
        self._value = 0

    def read(self):
        raw = self._interface.get_sensor_port_value(self._port.id)
        self._value = self.convert_sensor_value(raw)

        return {'raw': raw, 'converted': self._value}

    @property
    def value(self):
        return self._value

    def convert_sensor_value(self, raw): raise NotImplementedError


class BumperSwitch(BaseSensorPort):
    def convert_sensor_value(self, raw):
        return raw[0] == 1


class HcSr04(BaseSensorPort):
    def convert_sensor_value(self, raw):
        return int.from_bytes(raw, byteorder='little')
