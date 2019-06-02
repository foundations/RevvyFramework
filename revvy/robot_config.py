import json
import traceback
from json import JSONDecodeError


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
        try:
            json_config = json.loads(config_string)

            robot_config = json_config['robotConfig']
            scripts = json_config['blocklies']

            config = RobotConfig()

            for script in scripts:
                btn_id = script['assignments']['btnId']
                script_name = 'script_btn_{}'.format(btn_id)
                priority = 0 # TODO
                config.controller.buttons[btn_id] = script_name
                config.scripts[script_name] = {'script': script['pythonCode'], 'priority': priority}

            return config
        except (JSONDecodeError, KeyError):
            print('Failed to decode received configuration')
            print(traceback.format_exc())
            return None

    def __init__(self):
        self.motors = MotorConfig()
        self.drivetrain = {'left': [], 'right': []}
        self.sensors = SensorConfig()
        self.controller = RemoteControlConfig()
        self.scripts = {}
