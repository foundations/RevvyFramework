from revvy.mcu.rrrc_control import RevvyControl


class PortHandler:
    def __init__(self, interface: RevvyControl, configs: dict, drivers: dict):
        self._interface = interface
        self._types = {"NotConfigured": 0}
        self._ports = []
        self._drivers = drivers
        self._configurations = configs
        self._port_count = 0

    def __getitem__(self, item):
        return self.port(item)

    def __iter__(self):
        return self._ports.__iter__()

    @property
    def available_types(self):
        return self._types

    @property
    def port_count(self):
        return self._port_count

    @property
    def interface(self):
        return self._interface

    def port(self, port_idx):
        return self._ports[port_idx - 1]

    def reset(self):
        for port in self._ports:
            port.uninitialize()
        self._ports.clear()

        self._types = self._get_port_types()
        self._port_count = self._get_port_amount()

    def _get_port_types(self): raise NotImplementedError
    def _get_port_amount(self): raise NotImplementedError
    def _set_port_type(self, port, port_type): raise NotImplementedError

    def configure_port(self, port, config_name):
        config = self._configurations[config_name]
        new_driver_name = config['driver']
        print('PortInstance: Configuring port {} to {} ({})'.format(port.id, config_name, new_driver_name))
        self._set_port_type(port.id, self.available_types[new_driver_name])
        return self._drivers[new_driver_name](port, config['config'])


class PortInstance:
    def __init__(self, port_idx, owner: PortHandler):
        self._port_idx = port_idx
        self._owner = owner
        self._driver = None
        self._config_changed_callback = lambda port, cfg_name: None

    def on_config_changed(self, callback):
        self._config_changed_callback = callback

    def _notify_config_changed(self, config_name):
        self._config_changed_callback(self, config_name)

    def configure(self, config_name):
        self._notify_config_changed("NotConfigured")  # temporarily disable reading port
        self._driver = self._owner.configure_port(self, config_name)
        self._notify_config_changed(config_name)

        return self._driver

    def uninitialize(self):
        self.configure("NotConfigured")

    def handler(self):
        return self._driver

    @property
    def interface(self):
        return self._owner.interface

    @property
    def id(self):
        return self._port_idx

    def __getattr__(self, name):
        return self._driver.__getattribute__(name)
