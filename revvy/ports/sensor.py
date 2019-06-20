from revvy.ports.common import PortHandler, PortInstance
from revvy.mcu.rrrc_control import RevvyControl


class SensorPortHandler(PortHandler):
    def __init__(self, interface: RevvyControl, configs: dict):
        super().__init__(interface, configs, {
            'NotConfigured': lambda port, cfg: None,
            'BumperSwitch': lambda port, cfg: BumperSwitch(port),
            'HC_SR04': lambda port, cfg: HcSr04(port)
        })

    def _get_port_types(self):
        return self._interface.get_sensor_port_types()

    def _get_port_amount(self):
        return self._interface.get_sensor_port_amount()

    def _set_port_type(self, port, port_type):
        self._interface.set_sensor_port_type(port, port_type)


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
