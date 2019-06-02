import json
import traceback
from json import JSONDecodeError


motor_types = [
    ["NotConfigured", "NotConfigured"],
    ["RevvyMotor", "RevvyMotor_CCW"],  # motor
    ["RevvyMotor", "RevvyMotor_CCW"],  # drivetrain
]
motor_sides = ["left", "right"]

sensor_types = ["NotConfigured", "HC_SR04", "BumperSwitch"]


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
                # todo background scripts, analog channel scripts
                btn_id = script['assignments']['btnId']
                script_name = 'script_btn_{}'.format(btn_id)
                priority = 0  # TODO
                config.controller.buttons[btn_id] = script_name
                config.scripts[script_name] = {'script': script['pythonCode'], 'priority': priority}

            for partial_config in robot_config:
                if partial_config['title'] == 'Motors':
                    i = 1
                    for motor in partial_config['data']:
                        motor_type = motor_types[motor['type']][motor['direction']]
                        config.motors[i] = motor_type

                        if motor['type'] == 2:  # drivetrain
                            config.drivetrain[motor_sides[motor['side']]].append(i)

                        i += 1
                elif partial_config['title'] == 'Sensors':
                    i = 1
                    for sensor in partial_config['data']:
                        sensor_type = sensor_types[sensor['type']]
                        config.sensors[i] = sensor_type

                        i += 1

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
