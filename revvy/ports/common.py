from revvy.mcu.rrrc_control import RevvyControl


class PortHandler:
    def __init__(self, interface: RevvyControl, configs: dict, robot, port_map: list):
        self._interface = interface
        self._robot = robot
        self._types = {"NotConfigured": 0}
        self._ports = []
        self._configurations = configs
        self._port_idx_map = port_map

    def __getitem__(self, item):
        return self.port(item)

    def __iter__(self):
        return self._ports.__iter__()

    @property
    def configurations(self):
        return self._configurations

    @property
    def available_types(self):
        return self._types

    @property
    def port_count(self):
        return len(self._port_idx_map) - 1

    @property
    def interface(self):
        return self._interface

    def port(self, port_idx):
        return self._ports[self._port_idx_map[port_idx]]

    def reset(self):
        for port in self._ports:
            port.uninitialize()
        self._ports.clear()

        self._types = self._get_port_types()
        count = self._get_port_amount()
        if count != self.port_count:
            raise ValueError('Unexpected sensor port count ({} instead of {})'.format(count, len(self._port_idx_map)))

    def _get_port_types(self): raise NotImplementedError
    def _get_port_amount(self): raise NotImplementedError
    def _set_port_type(self, port, port_type): raise NotImplementedError


class PortInstance:
    def __init__(self, port_idx, owner: PortHandler, robot, drivers):
        self._port_idx = port_idx
        self._robot = robot
        self._owner = owner
        self._handlers = drivers
        self._driver = None
        self._config_changed_callback = lambda motor, cfg_name: None

    def on_config_changed(self, callback):
        self._config_changed_callback = callback

    def _notify_config_changed(self, config_name):
        self._config_changed_callback(self, config_name)

    def configure(self, config_name):
        if self._driver is not None and config_name != 'NotConfigured':
            self._driver.uninitialize()

        config = self._owner.configurations[config_name]

        new_driver_name = config['driver']
        print('PortInstance: Configuring port {} to {} ({})'.format(self._port_idx, config_name, new_driver_name))
        self._owner._set_port_type(self._port_idx, self._owner.available_types[new_driver_name])

        handler = self._handlers[new_driver_name](config['config'])
        self._driver = handler

        self._notify_config_changed(config_name)

        return handler

    def uninitialize(self):
        self.configure("NotConfigured")

    def handler(self):
        return self._driver

    @property
    def interface(self):
        return self._owner.interface

    @property
    def idx(self):
        return self._port_idx

    @property
    def id(self):
        """User-facing motor port number"""
        return self._owner._port_idx_map.index(self._port_idx)

    def __getattr__(self, name):
        return self._driver.__getattribute__(name)
