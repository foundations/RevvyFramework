from rrrc_control import RevvyControl


class SensorPortHandler:
    def __init__(self, interface: RevvyControl):
        self._interface = interface
        self._types = interface.get_sensor_port_types()
        count = interface.get_sensor_port_amount()
        self._ports = [SensorPortInstance(i, self) for i in range(count)]

    @property
    def available_types(self):
        return self._types

    @property
    def port_count(self):
        return len(self._ports)

    @property
    def interface(self):
        return self._interface

    def port(self, port_idx):
        return self._ports[port_idx]


class SensorPortInstance:
    def __init__(self, port_idx, owner: SensorPortHandler):
        self._port_idx = port_idx
        self._owner = owner
        self._handlers = {
            'NotConfigured': lambda: None,
        }
        self._handler = None
        self._current_port_type = "NotConfigured"

    def configure(self, port_type):
        if self._current_port_type == port_type:
            return self._handler

        if self._handler is not None:
            self._handler.uninitialize()

        self._owner.interface.set_motor_port_type(self._port_idx, self._owner.available_types[port_type])
        self._current_port_type = port_type
        handler = self._handlers[port_type]()
        self._handler = handler
        return handler

    def uninitialize(self):
        self.configure("NotConfigured")

    def handler(self):
        return self._handler

    @property
    def interface(self):
        return self._owner.interface


class BaseSensorPort:
    def __init__(self, handler: SensorPortInstance, port_idx):
        self._handler = handler
        self._interface = handler.interface
        self._port_idx = port_idx
        self._configured = True

    def uninitialize(self):
        self._handler.uninitialize()
        self._configured = False

    def get_position(self):
        return self._interface.get_motor_position(self._port_idx)


class BumperSwitch(BaseSensorPort):
    def is_pressed(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        result = self._interface.get_sensor_port_value(self._port_idx)
        return result[0] == 1


class HcSr04(BaseSensorPort):
    def get_distance(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        result = self._interface.get_sensor_port_value(self._port_idx)
        return int.from_bytes(result, byteorder='little')
