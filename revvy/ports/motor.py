import math

from revvy.ports.common import PortHandler, PortInstance
from revvy.mcu.rrrc_control import RevvyControl
import struct


class MotorPortHandler(PortHandler):
    def __init__(self, interface: RevvyControl, configs: dict):
        super().__init__(interface, configs, {
            'NotConfigured': lambda port, cfg: None,
            'DcMotor': lambda port, cfg: DcMotorController(port)
        })

    def _get_port_amount(self):
        return self._interface.get_motor_port_amount()

    def _get_port_types(self):
        return self._interface.get_motor_port_types()

    def _set_port_type(self, port, port_type):
        self.interface.set_motor_port_type(port, port_type)

    def reset(self):
        super().reset()
        self._ports = [PortInstance(i + 1, self) for i in range(self.port_count)]


class BaseMotorController:
    def __init__(self, port: PortInstance):
        self._port = port
        self._interface = port.interface
        self._configured = True

        self._pos = 0
        self._speed = 0
        self._power = 0

    @property
    def speed(self):
        return self._speed

    @property
    def position(self):
        return self._pos

    @property
    def power(self):
        return self._power

    @property
    def is_moving(self):
        # FIXME probably not really reliable
        return not (math.fabs(round(self._speed, 2)) == 0 and math.fabs(self._power) < 80)

    def uninitialize(self):
        self._port.uninitialize()
        self._configured = False

    def get_position(self):
        return self._interface.get_motor_position(self._port.id)


class DcMotorController(BaseMotorController):
    """Generic driver for dc motors"""
    def __init__(self, port: PortInstance, config):
        super().__init__(port)
        self._config = config
        self._original_config = dict(config)
        self._config_changed = True
        self.apply_configuration()

    def set_speed_limit(self, limit):
        prev_limit = self._config['position_controller'][4]
        if limit != prev_limit:
            self._config['position_controller'][3] = -limit
            self._config['position_controller'][4] = limit
            self._config_changed = True

    def get_speed_limit(self):
        return self._config['position_controller'][4]

    def set_position_limit(self, lower, upper):
        self._config['position_limits'] = [lower, upper]
        self._config_changed = True

    def set_power_limit(self, limit):
        if limit is None:
            limit = self._original_config['speed_controller'][4]

        prev_limit = self._config['speed_controller'][4]
        if limit != prev_limit:
            self._config['speed_controller'][3] = -limit
            self._config['speed_controller'][4] = limit
            self._config_changed = True

    def get_power_limit(self):
        return self._config['speed_controller'][4]

    def apply_configuration(self):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        if not self._config_changed:
            return

        self._config_changed = False

        (posMin, posMax) = self._config['position_limits']
        (posP, posI, posD, speedLowerLimit, speedUpperLimit) = self._config['position_controller']
        (speedP, speedI, speedD, powerLowerLimit, powerUpperLimit) = self._config['speed_controller']

        config = list(struct.pack("<ll", posMin, posMax))
        config += list(struct.pack("<{}".format("f" * 5), posP, posI, posD, speedLowerLimit, speedUpperLimit))
        config += list(struct.pack("<{}".format("f" * 5), speedP, speedI, speedD, powerLowerLimit, powerUpperLimit))
        config += list(struct.pack("<h", self._config['encoder_resolution']))

        print('Sending configuration: {}'.format(config))

        self._interface.set_motor_port_config(self._port.id, config)

    def set_speed(self, speed, power_limit=None):
        print('Motor::set_speed')
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        control = list(struct.pack("<f", speed))
        if power_limit is not None:
            control += list(struct.pack("<f", power_limit))

        self._interface.set_motor_port_control_value(self._port.id, [1] + control)

    def set_position(self, position: int, speed_limit=None, power_limit=None, pos_type='absolute'):
        print('Motor::set_position')
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        control = list(struct.pack('<l', position))

        if speed_limit is not None and power_limit is not None:
            control += list(struct.pack("<ff", speed_limit, power_limit))
        elif speed_limit is not None:
            control += list(struct.pack("<bf", 1, speed_limit))
        elif power_limit is not None:
            control += list(struct.pack("<bf", 0, power_limit))

        if pos_type == 'absolute':
            self._interface.set_motor_port_control_value(self._port.id, [2] + control)
        elif pos_type == 'relative':
            self._interface.set_motor_port_control_value(self._port.id, [3] + control)
        else:
            raise ValueError('Unknown position type {}'.format(pos_type))

    def set_power(self, power):
        print('Motor::set_power')
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        self._interface.set_motor_port_control_value(self._port.id, [0, power])

    def get_status(self):
        data = self._interface.get_motor_position(self._port.id)
        if len(data) != 9:
            print('Motor {}: Received {} bytes of data instead of 9'.format(self._port.id, len(data)))

        (pos, speed, power) = struct.unpack('<lfb', bytearray(data))

        self._pos = pos
        self._speed = speed
        self._power = power

        return {'position': pos, 'speed': speed, 'power': power}
