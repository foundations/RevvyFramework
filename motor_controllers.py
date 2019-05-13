from rrrc_control import RevvyControl
import struct
from functions import clip


class MotorPortHandler:
    def __init__(self, interface: RevvyControl):
        self._interface = interface
        count = interface.get_motor_port_amount()
        self._ports = [None] * count
        self._types = interface.get_motor_port_types()
        self._handlers = {
            'NotConfigured': None,
            'OpenLoop': lambda port: OpenLoopMotorController(self, port),
            'PositionControlled': lambda port: PositionControlledMotorController(self, port),
            'SpeedControlled': lambda port: SpeedControlledMotorController(self, port)
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


class BaseMotorController:
    def __init__(self, handler: MotorPortHandler, port_idx):
        self._handler = handler
        self._interface = handler.interface
        self._port_idx = port_idx
        self._configured = True

    def uninitialize(self):
        self._handler.uninitialize(self._port_idx)
        self._configured = False

    def get_position(self):
        return self._interface.get_motor_position(self._port_idx)


class OpenLoopMotorController(BaseMotorController):
    def __init__(self, handler: MotorPortHandler, port_idx):
        super().__init__(handler, port_idx)

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
    def __init__(self, handler: MotorPortHandler, port_idx):
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
    def __init__(self, handler: MotorPortHandler, port_idx):
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
