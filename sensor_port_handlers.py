from rrrc_control import RevvyControl


class SensorPort:
    def __init__(self, interface: RevvyControl, port_idx):
        self._interface = interface
        self._port_idx = port_idx


class BumperSwitch(SensorPort):
    def __init__(self, interface: RevvyControl, port_idx):
        super().__init__(interface, port_idx)
        self._interface.set_sensor_port_type(port_idx, 1)

    def is_pressed(self):
        result = self._interface.get_sensor_port_value(self._port_idx)
        return result[0] == 1


class HcSr04(SensorPort):
    def __init__(self, interface: RevvyControl, port_idx):
        super().__init__(interface, port_idx)
        self._interface.set_sensor_port_type(port_idx, 2)

    def get_distance(self):
        result = self._interface.get_sensor_port_value(self._port_idx)
        return int.from_bytes(result, byteorder='little')
