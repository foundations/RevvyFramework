from revvy.rrrc_control import RevvyControl


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
