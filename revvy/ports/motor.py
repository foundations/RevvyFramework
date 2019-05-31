import math

from revvy.functions import map_values
from revvy.rrrc_control import RevvyControl
import struct


class MotorPortHandler:
    # index: logical number; value: physical number
    motorPortMap = [-1, 3, 4, 5, 2, 1, 0]

    def __init__(self, interface: RevvyControl, configs: dict, robot):
        self._interface = interface
        self._robot = robot
        self._types = {"NotConfigured": 0}
        self._ports = []
        self._configurations = configs

    def reset(self):
        for port in self._ports:
            port.uninitialize()
        self._ports.clear()

        self._types = self._interface.get_motor_port_types()
        count = self._interface.get_motor_port_amount()
        if count != len(self.motorPortMap) - 1:
            raise ValueError('Unexpected motor port count ({} instead of {})'.format(count, len(self.motorPortMap)))
        self._ports = [MotorPortInstance(i, self, self._robot) for i in range(count)]

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
        return len(self._ports)

    @property
    def interface(self):
        return self._interface

    def port(self, port_idx):
        return self._ports[self.motorPortMap[port_idx]]


class MotorPortInstance:
    def __init__(self, port_idx, owner: MotorPortHandler, robot):
        self._port_idx = port_idx
        self._robot = robot
        self._owner = owner
        self._handlers = {
            'NotConfigured': lambda cfg: None,
            'DcMotor': lambda cfg: DcMotorController(self, port_idx, cfg)
        }
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
        print('MotorPort: Configuring port {} to {} ({})'.format(self._port_idx, config_name, new_driver_name))
        self._owner.interface.set_motor_port_type(self._port_idx, self._owner.available_types[new_driver_name])

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
        return MotorPortHandler.motorPortMap.index(self._port_idx)

    def __getattr__(self, name):
        return self._driver.__getattribute__(name)


class BaseMotorController:
    def __init__(self, handler: MotorPortInstance, port_idx):
        self._handler = handler
        self._interface = handler.interface
        self._port_idx = port_idx
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
        return math.fabs(round(self._speed, 2)) == 0 and math.fabs(self._power) < 50

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
        self._original_config = dict(config)
        self._config_changed = True
        self.apply_configuration()

    def set_speed_limit(self, limit):
        if 'motor-control-in-physical-values' not in self._handler._robot.features:
            # convert from degrees per sec to ticks per sec
            limit = math.fabs(map_values(limit, 0, 360, 0, self._config['encoder_resolution']))

        prev_limit = self._config['position_controller'][4]
        if limit != prev_limit:
            self._config['position_controller'][3] = -limit
            self._config['position_controller'][4] = limit
            self._config_changed = True

    def get_speed_limit(self):
        return self._config['position_controller'][4]

    def set_position_limit(self, lower, upper):
        # convert from degrees to ticks
        if 'motor-control-in-physical-values' not in self._handler._robot.features:
            lower_sign = -1 if lower < 0 else 1
            upper_sign = -1 if upper < 0 else 1
            lower = lower_sign * math.fabs(map_values(lower, 0, 360, 0, self._config['encoder_resolution']))
            upper = upper_sign * math.fabs(map_values(upper, 0, 360, 0, self._config['encoder_resolution']))

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

        if 'motor-control-in-physical-values' not in self._handler._robot.features:
            speedLowerLimit = -math.fabs(map_values(speedLowerLimit, 0, 360, 0, self._config['encoder_resolution']))
            speedUpperLimit = math.fabs(map_values(speedUpperLimit, 0, 360, 0, self._config['encoder_resolution']))
            powerLowerLimit = -math.fabs(map_values(powerLowerLimit, 0, 360, 0, self._config['encoder_resolution']))
            powerUpperLimit = math.fabs(map_values(powerUpperLimit, 0, 360, 0, self._config['encoder_resolution']))

        config = list(struct.pack("<ll", posMin, posMax))
        config += list(struct.pack("<{}".format("f" * 5), posP, posI, posD, speedLowerLimit, speedUpperLimit))
        config += list(struct.pack("<{}".format("f" * 5), speedP, speedI, speedD, powerLowerLimit, powerUpperLimit))

        if 'motor-control-in-physical-values' in self._handler._robot.features:
            config += list(struct.pack("<h", self._config['encoder_resolution']))

        print('Sending configuration: {}'.format(config))

        self._interface.set_motor_port_config(self._port_idx, config)

    def set_speed(self, speed, power_limit=None):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        if 'motor-control-in-physical-values' not in self._handler._robot.features:
            speed = map_values(speed, 0, 360, 0, self._config['encoder_resolution'])

        control = list(struct.pack("<f", speed))
        if power_limit is not None:
            control += list(struct.pack("<f", power_limit))

        self._interface.set_motor_port_control_value(self._port_idx, [1] + control)

    def set_position(self, position: int, speed_limit=None, power_limit=None):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        if 'motor-control-in-physical-values' not in self._handler._robot.features:
            # calculate encoder ticks from degrees
            position = int(map_values(position, 0, 360, 0, self._config['encoder_resolution']))
            if speed_limit is not None:
                speed_limit = int(map_values(speed_limit, 0, 360, 0, self._config['encoder_resolution']))

        control = list(struct.pack('<l', position))

        if speed_limit is not None and power_limit is not None:
            control += list(struct.pack("<ff", speed_limit, power_limit))
        elif speed_limit is not None:
            control += list(struct.pack("<bf", 1, speed_limit))
        elif power_limit is not None:
            control += list(struct.pack("<bf", 0, power_limit))

        self._interface.set_motor_port_control_value(self._port_idx, [2] + control)

    def set_power(self, power):
        if not self._configured:
            raise EnvironmentError("Port is not configured")

        self._interface.set_motor_port_control_value(self._port_idx, [0, power])

    def get_status(self):
        data = self._interface.get_motor_position(self._port_idx)
        if len(data) != 9:
            print('Received {} bytes of data instead of 9'.format(len(data)))

        (pos, speed, power) = struct.unpack('<lfb', bytearray(data))

        if 'motor-control-in-physical-values' not in self._handler._robot.features:
            speed = map_values(speed, 0, self._config['encoder_resolution'], 0, 360)
            pos = map_values(pos, 0, self._config['encoder_resolution'], 0, 360)

        self._pos = pos
        self._speed = speed
        self._power = power

        return {'position': pos, 'speed': speed, 'power': power}
