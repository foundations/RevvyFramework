from rrrc_control import RevvyControl


class SensorPortHandler:
    def __init__(self, interface: RevvyControl):
        self._interface = interface
        count = interface.get_sensor_port_amount()
        self._ports = [None] * count
        self._types = interface.get_sensor_port_types()
        self._handlers = {
            'DummySensor': None,
            'BumperSwitch': lambda port: BumperSwitch(self, port),
            'HC_SR04': lambda port: HcSr04(self, port)
        }

    def configure(self, port_idx, port_type):
        if port_idx >= len(self._ports):
            raise ValueError('Trying to configure port #{} but there are only {} ports', port_idx, len(self._ports))

        if self._ports[port_idx]:
            self._ports[port_idx].uninitialize()

        self._interface.set_motor_port_type(port_idx, self._types[port_type])
        handler = self._handlers[port_type](port_idx)
        self._ports[port_idx] = handler
        return handler

    def handler(self, port_idx):
        return self._ports[port_idx]

    def uninitialize(self, port_idx):
        self._interface.set_motor_port_type(port_idx, 0)

    @property
    def interface(self):
        return self._interface


class BaseSensorPort:
    def __init__(self, handler: SensorPortHandler, port_idx):
        self._handler = handler
        self._interface = handler.interface
        self._port_idx = port_idx
        self._configured = True

    def uninitialize(self):
        self._handler.uninitialize(self._port_idx)
        self._configured = False


class BumperSwitch(BaseSensorPort):
    def __init__(self, handler: SensorPortHandler, port_idx):
        super().__init__(handler, port_idx)

    def is_pressed(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        result = self._interface.get_sensor_port_value(self._port_idx)
        return result[0] == 1


class HcSr04(BaseSensorPort):
    def __init__(self, handler: SensorPortHandler, port_idx):
        super().__init__(handler, port_idx)

    def get_distance(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        result = self._interface.get_sensor_port_value(self._port_idx)
        return int.from_bytes(result, byteorder='little')
