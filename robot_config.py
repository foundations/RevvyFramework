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
        self.analog_scripts = [
            # for now, analog[0] and analog[1] are hardwired to drivetrain
            {'channels': [0, 1], 'script': 'drivetrain'}
        ]
        self.buttons = [None] * 32


class RobotConfig:
    @staticmethod
    def from_string(config):
        pass

    def __init__(self):
        self.motors = MotorConfig()
        self.drivetrain = {'left': [], 'right': []}
        self.sensors = SensorConfig()
        self.controller = RemoteControlConfig()
        self.scripts = {}
