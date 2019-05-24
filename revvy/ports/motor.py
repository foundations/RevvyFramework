from revvy.rrrc_control import RevvyControl
import struct
from revvy.functions import clip


class MotorPortHandler:
    # index: logical number; value: physical number
    motorPortMap = [-1, 3, 4, 5, 2, 1, 0]

    def __init__(self, interface: RevvyControl):
        self._interface = interface
        self._types = {"NotConfigured": 0}
        self._ports = []

    def reset(self):
        for port in self._ports:
            port.uninitialize()

        self._types = self._interface.get_motor_port_types()
        count = self._interface.get_motor_port_amount()
        if count != len(self.motorPortMap) - 1:
            raise ValueError('Unexpected motor port count ({} instead of {})'.format(count, len(self.motorPortMap)))
        self._ports = [MotorPortInstance(i, self) for i in range(count)]

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
        return self._ports[self.motorPortMap[port_idx]]


class MotorPorts:
    def __init__(self, handler: MotorPortHandler):
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


class MotorPortInstance:
    def __init__(self, port_idx, owner: MotorPortHandler):
        self._port_idx = port_idx
        self._owner = owner
        self._handlers = {
            'NotConfigured': lambda: None,
            'OpenLoop': lambda: OpenLoopMotorController(self, port_idx),
            'PositionControlled': lambda: PositionControlledMotorController(self, port_idx),
            'SpeedControlled': lambda: SpeedControlledMotorController(self, port_idx)
        }
        self._handler = None
        self._current_port_type = 'NotConfigured'

    def configure(self, port_type):
        if self._handler is not None and port_type != 'NotConfigured':
            self._handler.uninitialize()

        print('MotorPort: Configuring port {} to {}'.format(self._port_idx, port_type))
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

    @property
    def id(self):
        return MotorPortHandler.motorPortMap.index(self._port_idx)

    def __getattr__(self, name):
        return self._handler.__getattribute__(name)


class BaseMotorController:
    def __init__(self, handler: MotorPortInstance, port_idx):
        self._handler = handler
        self._interface = handler.interface
        self._port_idx = port_idx
        self._configured = True

    def uninitialize(self):
        self._handler.uninitialize()
        self._configured = False

    def get_position(self):
        return self._interface.get_motor_position(self._port_idx)


class OpenLoopMotorController(BaseMotorController):
    def set_speed(self, speed):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        speed = clip(speed, -100, 100)
        self._interface.set_motor_port_control_value(self._port_idx, [speed])

    def set_max_speed(self, speed):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        speed = clip(speed, 0, 100)
        self._interface.set_motor_port_config(self._port_idx, [speed, 256 - speed])


class PositionControlledMotorController(BaseMotorController):
    def __init__(self, handler: MotorPortInstance, port_idx):
        super().__init__(handler, port_idx)
        self._config = [1.5, 0.02, 0, -80, 80]
        self._update_config()

    def _update_config(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        (p, i, d, ll, ul) = self._config
        config = list(struct.pack(">{}".format("f" * 5), p, i, d, ll, ul))
        self._interface.set_motor_port_config(self._port_idx, config)

    def set_position(self, pos: int):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        self._interface.set_motor_port_control_value(self._port_idx, list(pos.to_bytes(4, byteorder='big')))


class SpeedControlledMotorController(BaseMotorController):
    def __init__(self, handler: MotorPortInstance, port_idx):
        super().__init__(handler, port_idx)
        self._config = [5, 0.25, 0, -90, 90]
        self._update_config()

    def _update_config(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        (p, i, d, ll, ul) = self._config
        config = list(struct.pack(">{}".format("f" * 5), p, i, d, ll, ul))
        self._interface.set_motor_port_config(self._port_idx, config)

    def set_max_speed(self, speed):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        speed = clip(speed, 0, 100)
        self._config[3] = -speed
        self._config[4] = speed
        self._update_config()

    def set_speed(self, speed):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        self._interface.set_motor_port_control_value(self._port_idx, list(struct.pack(">f", speed)))
