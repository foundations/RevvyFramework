import json
import traceback
from json import JSONDecodeError


motor_types = [
    # left             right
    ["NotConfigured",  "NotConfigured"],
    ["RevvyMotor_CCW", "RevvyMotor"],  # motor
    ["RevvyMotor_CCW", "RevvyMotor"],  # drivetrain
]
motor_sides = ["left", "right"]

sensor_types = ["NotConfigured", "HC_SR04", "BumperSwitch"]


class PortConfig:
    def __init__(self):
        self._ports = {}
        self._port_names = {}

    @property
    def names(self):
        return self._port_names

    def __getitem__(self, item):
        return self._ports.get(item, "NotConfigured")

    def __setitem__(self, item, value):
        self._ports[item] = value


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
                for assignment in script['assignments']:
                    # todo analog channel scripts
                    btn_id = assignment['btnId']

                    if btn_id == -1:
                        # background script
                        script_name = 'script_background_{}'.format(len(config.background_scripts))
                        config.background_scripts.append(script_name)
                    else:
                        script_name = 'script_btn_{}'.format(btn_id)
                        config.controller.buttons[btn_id] = script_name

                    priority = assignment['priority'] if 'priority' in assignment else 0
                    config.scripts[script_name] = {'script': script['pythonCode'], 'priority': priority}

            for partial_config in robot_config:
                if partial_config['title'] == 'Motors':
                    i = 1
                    for motor in partial_config['data']:
                        motor_type = motor_types[motor['type']][motor['direction']]
                        config.motors[i] = motor_type
                        config.motors.names[motor['name']] = i

                        if motor['type'] == 2:  # drivetrain
                            config.drivetrain[motor_sides[motor['side']]].append(i)

                        i += 1
                elif partial_config['title'] == 'Sensors':
                    i = 1
                    for sensor in partial_config['data']:
                        sensor_type = sensor_types[sensor['type']]
                        config.sensors[i] = sensor_type
                        config.sensors.names[sensor['name']] = i

                        i += 1

            return config
        except (JSONDecodeError, KeyError):
            print('Failed to decode received configuration')
            print(traceback.format_exc())
            return None

    def __init__(self):
        self.motors = PortConfig()
        self.drivetrain = {'left': [], 'right': []}
        self.sensors = PortConfig()
        self.controller = RemoteControlConfig()
        self.scripts = {}
        self.background_scripts = []
