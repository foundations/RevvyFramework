from revvy.ports.common import PortHandler, PortInstance
from revvy.rrrc_control import RevvyControl


class SensorPortHandler(PortHandler):
    # index: logical number; value: physical number
    sensorPortMap = [-1, 0, 1, 2, 3]

    def __init__(self, interface: RevvyControl, configs: dict, robot):
        super().__init__(interface, configs, robot, self.sensorPortMap)

    def _get_port_types(self):
        return self._interface.get_sensor_port_types()

    def _get_port_amount(self):
        return self._interface.get_sensor_port_amount()

    def reset(self):
        super().reset()
        self._ports = [SensorPortInstance(i, self, self._robot) for i in range(self.port_count)]


class SensorPortInstance(PortInstance):
    def __init__(self, port_idx, owner: SensorPortHandler, robot):
        super().__init__(port_idx, owner, robot, {
            'NotConfigured': lambda cfg: None,
            'BumperSwitch': lambda cfg: BumperSwitch(self, port_idx),
            'HC_SR04': lambda cfg: HcSr04(self, port_idx)
        })


class BaseSensorPort:
    def __init__(self, handler: SensorPortInstance, port_idx):
        self._handler = handler
        self._interface = handler.interface
        self._port_idx = port_idx
        self._configured = True
        self._value = 0

    def uninitialize(self):
        self._handler.uninitialize()
        self._configured = False

    def read(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        raw = self._interface.get_sensor_port_value(self._port_idx)
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
