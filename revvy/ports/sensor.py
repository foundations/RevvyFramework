from revvy.rrrc_control import RevvyControl


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
        self._ports.clear()

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


class SensorPortInstance:
    def __init__(self, port_idx, owner: SensorPortHandler):
        self._port_idx = port_idx
        self._owner = owner
        self._handlers = {
            'NotConfigured': lambda: None,
            'AnalogButton': lambda: BumperSwitch(self, port_idx),
            'HC_SR04': lambda: HcSr04(self, port_idx)
        }
        self._driver = None
        self._config_changed_callback = lambda sensor, cfg_name: None

    def on_config_changed(self, callback):
        self._config_changed_callback = callback

    def _notify_config_changed(self, config_name):
        self._config_changed_callback(self, config_name)

    def configure(self, config_name):
        if self._driver is not None and config_name != 'NotConfigured':
            self._driver.uninitialize()

        print('SensorPort: Configuring port {} to {}'.format(self._port_idx, config_name))
        self._owner.interface.set_sensor_port_type(self._port_idx, self._owner.available_types[config_name])

        handler = self._handlers[config_name]()
        self._driver = handler

        self._notify_config_changed(config_name)

        return handler

    def uninitialize(self):
        self.configure("NotConfigured")

    def handler(self):
        return self._driver

    @property
    def id(self):
        return SensorPortHandler.sensorPortMap.index(self._port_idx)

    @property
    def interface(self):
        return self._owner.interface

    def __getattr__(self, name):
        return self._driver.__getattribute__(name)


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
        result = self.read_sensor()
        self._value = result['converted']
        return result

    @property
    def value(self):
        return self._value

    def read_sensor(self): raise NotImplementedError


class BumperSwitch(BaseSensorPort):
    def read_sensor(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        result = self._interface.get_sensor_port_value(self._port_idx)
        return {'raw': result, 'converted': result[0] == 1}


class HcSr04(BaseSensorPort):
    def read_sensor(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        result = self._interface.get_sensor_port_value(self._port_idx)
        return {'raw': result, 'converted':  int.from_bytes(result, byteorder='little')}
