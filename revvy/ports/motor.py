import math

from revvy.ports.common import PortHandler, PortInstance
from revvy.mcu.rrrc_control import RevvyControl
import struct


class MotorPortHandler(PortHandler):
    def __init__(self, interface: RevvyControl, configs: dict):
        super().__init__(interface, configs, {
            'NotConfigured': lambda port, cfg: None,
            'DcMotor': lambda port, cfg: DcMotorController(port, cfg)
        })

    def _get_port_amount(self):
        return self._interface.get_motor_port_amount()

    def _get_port_types(self):
        return self._interface.get_motor_port_types()

    def _set_port_type(self, port, port_type):
        self._interface.set_motor_port_type(port, port_type)


class BaseMotorController:
    def __init__(self, port: PortInstance):
        self._port = port
        self._interface = port.interface

        self._pos = 0
        self._speed = 0
        self._power = 0
        self._pos_reached = None

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
        if self._pos_reached is None:
            return not (math.fabs(round(self._speed, 2)) == 0 and math.fabs(self._power) < 80)
        else:
            return not (self._pos_reached and math.fabs(round(self._speed, 2)) == 0 and math.fabs(self._power) < 80)


class DcMotorController(BaseMotorController):
    """Generic driver for dc motors"""
    def __init__(self, port: PortInstance, port_config):
        super().__init__(port)

        (posMin, posMax) = port_config['position_limits']
        (posP, posI, posD, speedLowerLimit, speedUpperLimit) = port_config['position_controller']
        (speedP, speedI, speedD, powerLowerLimit, powerUpperLimit) = port_config['speed_controller']

        config = list(struct.pack("<ll", posMin, posMax))
        config += list(struct.pack("<{}".format("f" * 5), posP, posI, posD, speedLowerLimit, speedUpperLimit))
        config += list(struct.pack("<{}".format("f" * 5), speedP, speedI, speedD, powerLowerLimit, powerUpperLimit))
        config += list(struct.pack("<h", port_config['encoder_resolution']))

        print('Sending configuration: {}'.format(config))

        self._interface.set_motor_port_config(self._port.id, config)

    def set_speed(self, speed, power_limit=None):
        print('Motor::set_speed')
        control = list(struct.pack("<f", speed))
        if power_limit is not None:
            control += list(struct.pack("<f", power_limit))

        self._interface.set_motor_port_control_value(self._port.id, [1] + control)

    def set_position(self, position: int, speed_limit=None, power_limit=None, pos_type='absolute'):
        print('Motor::set_position')
        control = list(struct.pack('<l', position))

        if speed_limit is not None and power_limit is not None:
            control += list(struct.pack("<ff", speed_limit, power_limit))
        elif speed_limit is not None:
            control += list(struct.pack("<bf", 1, speed_limit))
        elif power_limit is not None:
            control += list(struct.pack("<bf", 0, power_limit))

        pos_request_types = {'absolute': 2, 'relative': 3}
        self._interface.set_motor_port_control_value(self._port.id, [pos_request_types[pos_type]] + control)

    def set_power(self, power):
        print('Motor::set_power')
        self._interface.set_motor_port_control_value(self._port.id, [0, power])

    def get_status(self):
        data = self._interface.get_motor_position(self._port.id)

        if len(data) == 9:
            (pos, speed, power) = struct.unpack('<lfb', bytearray(data))
            pos_reached = None
        elif len(data) == 10:
            (pos, speed, power, pos_reached) = struct.unpack('<lfbb', bytearray(data))
        else:
            print('Motor {}: Received {} bytes of data instead of 9 or 13'.format(self._port.id, len(data)))
            return

        self._pos = pos
        self._speed = speed
        self._power = power
        self._pos_reached = pos_reached

        return {'position': pos, 'speed': speed, 'power': power}
