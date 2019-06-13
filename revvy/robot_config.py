import json
import traceback
from json import JSONDecodeError

from revvy.scripting.builtin_scripts import drive_joystick, drive_2sticks

motor_types = [
    # left             right
    ["NotConfigured",  "NotConfigured"],
    ["RevvyMotor_CCW", "RevvyMotor"],  # motor
    ["RevvyMotor_CCW", "RevvyMotor"],  # drivetrain
]
motor_sides = ["left", "right"]

sensor_types = ["NotConfigured", "HC_SR04", "BumperSwitch"]

builtin_scripts = {
    'drive_2sticks': drive_2sticks,
    'drive_joystick': drive_joystick
}


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

            config = RobotConfig()

            i = 0
            for script in json_config['blocklyList']:
                if 'builtinScriptName' in script:
                    runnable = builtin_scripts[script['builtinScriptName']]
                else:
                    runnable = script['pythonCode']

                if 'analog' in script['assignments']:
                    for analog_assignment in script['assignments']['analog']:
                        script_name = 'user_script_{}'.format(i)
                        priority = analog_assignment['priority']
                        config.scripts[script_name] = {'script':   runnable,
                                                       'priority': priority}
                        config.controller.analog.append({
                            'channels': analog_assignment['channels'],
                            'script': script_name})
                        i += 1

                if 'buttons' in script['assignments']:
                    for button_assignment in script['assignments']['buttons']:
                        script_name = 'user_script_{}'.format(i)
                        priority = button_assignment['priority']
                        config.scripts[script_name] = {'script': runnable, 'priority': priority}
                        config.controller.buttons[button_assignment['id']] = script_name
                        i += 1

                if 'background' in script['assignments']:
                    script_name = 'user_script_{}'.format(i)
                    priority = script['assignments']['background']
                    config.scripts[script_name] = {'script': runnable, 'priority': priority}
                    config.background_scripts.append(script_name)
                    i += 1

            if 'motors' in robot_config:
                i = 1
                for motor in robot_config['motors']:
                    motor_type = motor_types[motor['type']][motor['direction']]
                    config.motors[i] = motor_type
                    config.motors.names[motor['name']] = i

                    if motor['type'] == 2:  # drivetrain
                        config.drivetrain[motor_sides[motor['side']]].append(i)

                    i += 1

            if 'sensors' in robot_config:
                i = 1
                for sensor in robot_config['sensors']:
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
