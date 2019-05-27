from revvy.rrrc_control import RevvyControl
import struct


class Motors:
    types = {
        'NotConfigured': {'driver': 'NotConfigured', 'config': {}},
        'RevvyMotor':    {
            'driver': 'DcMotor',
            'config': {
                # todo controllers need to be tuned
                'speed_controller':    [1 / 25, 0.3, 0, -100, 100],
                'position_controller': [0, 0, 0, -5000, 5000],
                'position_limits':     [0, 0]
            }
        },
        'RevvyMotor_Dexter':    {
            'driver': 'DcMotor',
            'config': {
                # todo controllers need to be tuned
                'speed_controller':    [1 / 8, 0.3, 0, -100, 100],
                'position_controller': [0, 0, 0, -1250, 1250],
                'position_limits':     [0, 0]
            }
        }
    }


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
            'NotConfigured': lambda cfg: None,
            'DcMotor': lambda cfg: DcMotorController(self, port_idx, cfg)
        }
        self._handler = None
        self._current_port_type = 'NotConfigured'

    def configure(self, port_type):
        if self._handler is not None and port_type != 'NotConfigured':
            self._handler.uninitialize()

        config = Motors.types[port_type]

        print('MotorPort: Configuring port {} to {} ({})'.format(self._port_idx, port_type, config['driver']))
        self._owner.interface.set_motor_port_type(self._port_idx, self._owner.available_types[config['driver']])
        self._current_port_type = port_type
        handler = self._handlers[config['driver']](config['config'])
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


class DcMotorController(BaseMotorController):
    """Generic driver for dc motors"""
    def __init__(self, handler: MotorPortInstance, port_idx, config):
        super().__init__(handler, port_idx)
        self._config = config
        self._config_changed = True
        self.apply_configuration()

    def set_speed_limit(self, lower, upper):
        self._config['position_controller'][3] = lower
        self._config['position_controller'][4] = upper
        self._config_changed = True

    def set_position_limit(self, lower, upper):
        self._config['position_limits'] = [lower, upper]
        self._config_changed = True

    def set_power_limit(self, lower, upper):
        self._config['speed_controller'][3] = lower
        self._config['speed_controller'][4] = upper
        self._config_changed = True

    def apply_configuration(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        if not self._config_changed:
            return

        self._config_changed = False

        (posMin, posMax) = self._config['position_limits']
        (posP, posI, posD, speedLowerLimit, speedUpperLimit) = self._config['position_controller']
        (speedP, speedI, speedD, powerLowerLimit, powerUpperLimit) = self._config['speed_controller']

        config = list(posMin.to_bytes(4, byteorder='little')) + list(posMax.to_bytes(4, byteorder='little'))
        config += list(struct.pack("<{}".format("f" * 5), posP, posI, posD, speedLowerLimit, speedUpperLimit))
        config += list(struct.pack("<{}".format("f" * 5), speedP, speedI, speedD, powerLowerLimit, powerUpperLimit))

        print('Sending configuration: {}'.format(config))

        self._interface.set_motor_port_config(self._port_idx, config)

    def set_speed(self, speed):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        if speed > 0:
            speed *= self._config['position_controller'][4]
        elif speed < 0:
            speed *= -self._config['position_controller'][3]

        self._interface.set_motor_port_control_value(self._port_idx, [1] + list(struct.pack("<f", speed)))

    def set_position(self, position: int):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        self._interface.set_motor_port_control_value(self._port_idx, [2] + list(position.to_bytes(4, byteorder='little')))

    def set_power(self, power):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        self._interface.set_motor_port_control_value(self._port_idx, [0, power])

    def get_status(self):
        data = self._interface.get_motor_position(self._port_idx)
        (pos, speed, power) = struct.unpack('<lfb', bytearray(data))
        return {'position': pos, 'speed': speed, 'power': power}
