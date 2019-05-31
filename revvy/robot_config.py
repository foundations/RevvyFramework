class MotorConfig:
    def __init__(self):
        self._motors = {}

    def __getitem__(self, item):
        return self._motors.get(item, "NotConfigured")

    def __setitem__(self, item, value):
        self._motors[item] = value


class SensorConfig:
    def __init__(self):
        self._sensors = {}

    def __getitem__(self, item):
        return self._sensors.get(item, "NotConfigured")

    def __setitem__(self, item, value):
        self._sensors[item] = value


class RemoteControlConfig:
    def __init__(self):
        self.analog = []
        self.buttons = [None] * 32


class RobotConfig:
    @staticmethod
    def from_string(config_string):
        config = RobotConfig()

        return config

    def __init__(self):
        self.motors = MotorConfig()
        self.drivetrain = {'left': [], 'right': []}
        self.sensors = SensorConfig()
        self.controller = RemoteControlConfig()
        self.scripts = {}
