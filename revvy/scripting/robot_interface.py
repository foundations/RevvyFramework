import time

from revvy.functions import hex2rgb
from revvy.ports.common import PortInstance


class Wrapper:
    def __init__(self, robot, resources: dict, priority=0):
        self._resources = resources
        self._priority = priority
        self._robot = robot

    @property
    def is_stop_requested(self):
        return self._robot.is_stop_requested

    def try_take(self, resource_name):
        return self._resources[resource_name].request(self._priority)

    def sleep(self, s):
        self._robot._script.sleep(s)

    def check_terminated(self):
        if self._robot.is_stop_requested:
            raise InterruptedError

    def using_resource(self, resource_name, callback):
        resource = self.try_take(resource_name)
        if resource:
            try:
                resource.run(callback)
            finally:
                resource.release()

    def if_resource_available(self, resource_name, callback):
        resource = self.try_take(resource_name)
        if resource:
            try:
                callback()
            finally:
                resource.release()


class SensorPortWrapper(Wrapper):
    """Wrapper class to expose sensor ports to user scripts"""
    def __init__(self, robot, sensor: PortInstance, resources: dict, priority=0):
        super().__init__(robot, resources, priority)
        self._sensor = sensor

    def configure(self, config_name):
        self._sensor.configure(config_name)

    def read(self):
        self.check_terminated()
        """Return the last converted value"""
        return self._sensor.value


def rpm2dps(rpm):
    """
    >>> rpm2dps(1)
    6
    >>> rpm2dps(60)
    360
    """
    return rpm * 6


class MotorPortWrapper(Wrapper):
    """Wrapper class to expose motor ports to user scripts"""
    def __init__(self, robot, motor: PortInstance, resources: dict, priority=0):
        super().__init__(robot, resources, priority)
        self._motor = motor

    def configure(self, config_name):
        self._motor.configure(config_name)

    def move(self, direction, amount, unit_amount, limit, unit_limit):
        self.check_terminated()
        resource = self.try_take('motor_{}'.format(self._motor.id))
        if resource:
            try:
                if unit_amount in [MotorConstants.UNIT_ROT, MotorConstants.UNIT_DEG]:
                    if unit_amount == MotorConstants.UNIT_ROT:
                        amount = amount * 360

                    if direction == MotorConstants.DIR_CCW:
                        amount *= -1

                    # start moving depending on limits
                    print("Rotating {} degrees".format(amount))
                    set_pos_fns = {
                        MotorConstants.UNIT_SPEED_RPM:
                            lambda: self._motor.set_position(amount, speed_limit=rpm2dps(limit), pos_type='relative'),
                        MotorConstants.UNIT_SPEED_PWR:
                            lambda: self._motor.set_position(amount, power_limit=limit, pos_type='relative')
                    }
                    resource.run(set_pos_fns[unit_limit])

                    # wait for movement to finish
                    self.sleep(0.2)
                    while not resource.is_interrupted and self._motor.is_moving:
                        self.sleep(0.2)

                elif unit_amount == MotorConstants.UNIT_SEC:
                    # start moving depending on limits
                    set_speed_fns = {
                        MotorConstants.UNIT_SPEED_RPM: {
                            MotorConstants.DIR_CW: lambda: self._motor.set_speed(rpm2dps(limit)),
                            MotorConstants.DIR_CCW: lambda: self._motor.set_speed(rpm2dps(-limit)),
                        },
                        MotorConstants.UNIT_SPEED_PWR: {
                            MotorConstants.DIR_CW: lambda: self._motor.set_speed(900, power_limit=limit),
                            MotorConstants.DIR_CCW: lambda: self._motor.set_speed(-900, power_limit=limit),
                        }
                    }

                    resource.run(set_speed_fns[unit_limit][direction])
                    self.sleep(amount)
                    resource.run(lambda: self._motor.set_speed(0))
                else:
                    raise ValueError
            finally:
                resource.release()

    def spin(self, direction, rotation, unit_rotation):
        # start moving depending on limits
        set_speed_fns = {
            MotorConstants.UNIT_SPEED_RPM: {
                MotorConstants.DIR_CW: lambda: self._motor.set_speed(rpm2dps(rotation)),
                MotorConstants.DIR_CCW: lambda: self._motor.set_speed(rpm2dps(-rotation))
            },
            MotorConstants.UNIT_SPEED_PWR: {
                MotorConstants.DIR_CW: lambda: self._motor.set_speed(900, power_limit=rotation),
                MotorConstants.DIR_CCW: lambda: self._motor.set_speed(-900, power_limit=rotation)
            }
        }

        self.using_resource('motor_{}'.format(self._motor.id), set_speed_fns[unit_rotation][direction])

    def stop(self, action):
        stop_fn = {
            MotorConstants.ACTION_STOP_AND_HOLD: lambda: self._motor.set_speed(0),
            MotorConstants.ACTION_RELEASE: lambda: self._motor.set_power(0),
        }
        self.using_resource('motor_{}'.format(self._motor.id), stop_fn[action])


class RingLedWrapper(Wrapper):
    """Wrapper class to expose LED ring to user scripts"""
    def __init__(self, robot, ring_led, resources: dict, priority=0):
        super().__init__(robot, resources, priority)
        self._ring_led = ring_led
        self._user_leds = [0] * ring_led.count

    @property
    def scenario(self):
        return self._ring_led.scenario

    def set_scenario(self, scenario):
        self.using_resource('led_ring', lambda: self._ring_led.set_scenario(scenario))

    def set(self, led_index, color):
        self.check_terminated()
        if type(led_index) is not list:
            led_index = [led_index]

        rgb = hex2rgb(color)

        for idx in led_index:
            if not (1 <= idx <= self._ring_led.count):
                raise IndexError('Led index invalid: {}'.format(idx))
            self._user_leds[idx - 1] = rgb

        self.using_resource('led_ring', lambda: self._ring_led.display_user_frame(self._user_leds))


class PortCollection:
    def __init__(self, ports: list, names: dict):
        self._ports = ports
        self._portNameMap = names

    def __getitem__(self, item):
        if type(item) is str:
            item = self._portNameMap[item]
        else:
            item -= 1
        return self._ports[item]

    def __iter__(self):
        return self._ports.__iter__()


class MotorConstants:
    DIR_CW = 0
    DIR_CCW = 1

    DIRECTION_FWD = 0
    DIRECTION_BACK = 1
    DIRECTION_LEFT = 2
    DIRECTION_RIGHT = 3

    UNIT_ROT = 0
    UNIT_SEC = 1
    UNIT_DEG = 2

    UNIT_SPEED_RPM = 0
    UNIT_SPEED_PWR = 1

    ACTION_STOP_AND_HOLD = 0
    ACTION_RELEASE = 1


class DriveTrainWrapper(Wrapper):
    def __init__(self, robot, drivetrain, resources: dict, priority=0):
        super().__init__(robot, resources, priority)
        self._drivetrain = drivetrain

    def drive(self, direction, rotation, unit_rotation, speed, unit_speed):
        left_multipliers = {
            MotorConstants.DIRECTION_FWD: 1,
            MotorConstants.DIRECTION_BACK: -1,
            MotorConstants.DIRECTION_LEFT: -1,
            MotorConstants.DIRECTION_RIGHT: 1,
        }
        right_multipliers = {
            MotorConstants.DIRECTION_FWD: 1,
            MotorConstants.DIRECTION_BACK: -1,
            MotorConstants.DIRECTION_LEFT: 1,
            MotorConstants.DIRECTION_RIGHT: -1,
        }

        self.check_terminated()
        resource = self.try_take('drivetrain')
        if resource:
            try:
                if unit_rotation == MotorConstants.UNIT_ROT:
                    degrees = rotation * 360
                    left_degrees = degrees * left_multipliers[direction]
                    right_degrees = degrees * right_multipliers[direction]
                    move_fns = {
                        MotorConstants.UNIT_SPEED_RPM:
                            lambda: self._drivetrain.move(left_degrees, right_degrees, rpm2dps(speed), rpm2dps(speed)),
                        MotorConstants.UNIT_SPEED_PWR:
                            lambda: self._drivetrain.move(left_degrees, right_degrees, power_limit=speed),
                    }
                    resource.run(move_fns[unit_speed])

                    # wait for movement to finish
                    self.sleep(0.2)
                    while not resource.is_interrupted and self._drivetrain.is_moving:
                        self.sleep(0.2)

                elif unit_rotation == MotorConstants.UNIT_SEC:
                    if unit_speed == MotorConstants.UNIT_SPEED_RPM:
                        left = rpm2dps(speed) * left_multipliers[direction]
                        right = rpm2dps(speed) * right_multipliers[direction]

                        resource.run(lambda: self._drivetrain.set_speeds(left, right))

                    elif unit_speed == MotorConstants.UNIT_SPEED_PWR:
                        left = 900 * left_multipliers[direction]
                        right = 900 * right_multipliers[direction]

                        resource.run(lambda: self._drivetrain.set_speeds(left, right, power_limit=speed))
                    else:
                        raise ValueError

                    self.sleep(rotation)

                    resource.run(lambda: self._drivetrain.set_speeds(0, 0))
                else:
                    raise ValueError
            finally:
                resource.release()

    def set_speeds(self, sl, sr):
        self.using_resource('drivetrain', lambda: self._drivetrain.set_speeds(sl, sr))


class RemoteControllerWrapper:
    def __init__(self, remote_controller):
        self._remote_controller = remote_controller

        self.is_button_pressed = remote_controller.is_button_pressed
        self.analog_value = remote_controller.analog_value


class SoundWrapper(Wrapper):
    def __init__(self, robot, sound, resources: dict, priority=0):
        super().__init__(robot, resources, priority)
        self._sound = sound

    def play_tune(self, name):
        self.check_terminated()
        self.if_resource_available('sound', lambda: self._sound.play_tune(name))


# FIXME: type hints missing because of circular reference that causes ImportError
class RobotInterface:
    """Wrapper class that exposes API to user-written scripts"""
    def __init__(self, script, robot, priority=0):
        self._start_time = robot.start_time
        motor_wrappers = list(MotorPortWrapper(self, port, robot.resources, priority) for port in robot._motor_ports)
        sensor_wrappers = list(SensorPortWrapper(self, port, robot.resources, priority) for port in robot._sensor_ports)
        self._motors = PortCollection(motor_wrappers, robot.config.motors.names)
        self._sensors = PortCollection(sensor_wrappers, robot.config.sensors.names)
        self._sound = SoundWrapper(self, robot.sound, robot.resources, priority)
        self._ring_led = RingLedWrapper(self, robot._ring_led, robot.resources, priority)
        self._drivetrain = DriveTrainWrapper(self, robot._drivetrain, robot.resources, priority)
        self._remote_controller = RemoteControllerWrapper(robot._remote_controller)

        self._script = script

        # shorthand functions
        self.drive = self._drivetrain.drive

    def stop_all_motors(self, action):
        for motor in self._motors:
            motor.stop(action)

    @property
    def is_stop_requested(self):
        return self._script.is_stop_requested

    @property
    def motors(self):
        return self._motors

    @property
    def sensors(self):
        return self._sensors

    @property
    def led(self):
        return self._ring_led

    @property
    def drivetrain(self):
        return self._drivetrain

    @property
    def controller(self):
        return self._remote_controller

    def play_tune(self, name):
        self._sound.play_tune(name)

    def play_note(self): pass  # TODO

    def time(self):
        return time.time() - self._start_time

    # property alias
    led_ring = led
