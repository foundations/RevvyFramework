from rrrc_control import RevvyControl


class SensorPortHandler:
    # index: logical number; value: physical number
    sensorPortMap = [-1, 0, 1, 2, 3]

    def __init__(self, interface: RevvyControl):
        self._interface = interface
        self._types = {"NotConfigured": 0}
        self._ports = []

    def reset(self):
        for port in self._ports:
            port.uninitialize()

        self._types = self._interface.get_sensor_port_types()
        count = self._interface.get_sensor_port_amount()
        if count != len(self.sensorPortMap) - 1:
            raise ValueError('Unexpected sensor port count ({} instead of {})'.format(count, len(self.sensorPortMap)))
        self._ports = [SensorPortInstance(i, self) for i in range(count)]

    def __getitem__(self, item):
        return self.port(item)

    def __iter__(self):
        return self._ports.__iter__()

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
        return self._ports[self.sensorPortMap[port_idx]]


class SensorPorts:
    def __init__(self, handler: SensorPortHandler):
        self._handler = handler
        self._names = {}

    def add_alias(self, name, port):
        self._names[name] = port

    def reset(self):
        self._names = {}
        self._handler.reset()

    def __getitem__(self, item):
        if item is str:
            item = self._names[item]

        return self._handler[item]


class SensorPortInstance:
    def __init__(self, port_idx, owner: SensorPortHandler):
        self._port_idx = port_idx
        self._owner = owner
        self._handlers = {
            'NotConfigured': lambda: None,
            'AnalogButton': lambda: BumperSwitch(self, port_idx),
            'HC_SR04': lambda: HcSr04(self, port_idx)
        }
        self._handler = None
        self._current_port_type = "NotConfigured"

    def configure(self, port_type):
        if self._handler is not None and port_type != 'NotConfigured':
            self._handler.uninitialize()

        print('SensorPort: Configuring port {} to {}'.format(self._port_idx, port_type))
        self._owner.interface.set_sensor_port_type(self._port_idx, self._owner.available_types[port_type])
        self._current_port_type = port_type
        handler = self._handlers[port_type]()
        self._handler = handler
        return handler

    def uninitialize(self):
        self.configure("NotConfigured")

    def handler(self):
        return self._handler

    @property
    def id(self):
        return SensorPortHandler.sensorPortMap.index(self._port_idx)

    @property
    def interface(self):
        return self._owner.interface

    def __getattr__(self, name):
        return self._handler.__getattribute__(name)


class BaseSensorPort:
    def __init__(self, handler: SensorPortInstance, port_idx):
        self._handler = handler
        self._interface = handler.interface
        self._port_idx = port_idx
        self._configured = True

    def uninitialize(self):
        self._handler.uninitialize()
        self._configured = False

    def read(self):
        pass


class BumperSwitch(BaseSensorPort):
    def read(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        result = self._interface.get_sensor_port_value(self._port_idx)
        return {'raw': result, 'converted': result[0] == 1}


class HcSr04(BaseSensorPort):
    def read(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        result = self._interface.get_sensor_port_value(self._port_idx)
        return {'raw': result, 'converted':  int.from_bytes(result, byteorder='little')}
