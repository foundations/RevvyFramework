#!/usr/bin/python3
from collections import namedtuple

from revvy.file_storage import StorageInterface, StorageError
from revvy.mcu.rrrc_control import RevvyControl, BatteryStatus
from revvy.robot.drivetrain import DifferentialDrivetrain
from revvy.robot.remote_controller import RemoteController, RemoteControllerScheduler, create_remote_controller_thread
from revvy.robot.led_ring import RingLed
from revvy.robot.ports.common import PortInstance
from revvy.robot.ports.motor import create_motor_port_handler
from revvy.robot.ports.sensor import create_sensor_port_handler
from revvy.robot.status import RobotStatus, RemoteControllerStatus, RobotStatusIndicator
from revvy.robot_config import RobotConfig
from revvy.scripting.resource import Resource
from revvy.scripting.robot_interface import MotorConstants
from revvy.scripting.runtime import ScriptManager
from revvy.thread_wrapper import *

from revvy.mcu.rrrc_transport import *
from revvy.fw_version import *


Motors = {
    'NotConfigured': {'driver': 'NotConfigured', 'config': {}},
    'RevvyMotor':    {
        'driver': 'DcMotor',
        'config': {
            'speed_controller':    [1 / 25, 0.3, 0, -100, 100],
            'position_controller': [10, 0, 0, -900, 900],
            'position_limits':     [0, 0],
            'encoder_resolution':  1168
        }
    },
    'RevvyMotor_CCW': {
        'driver': 'DcMotor',
        'config': {
            'speed_controller':    [1 / 25, 0.3, 0, -100, 100],
            'position_controller': [10, 0, 0, -900, 900],
            'position_limits':     [0, 0],
            'encoder_resolution':  -1168
        }
    },
    'RevvyMotor_Dexter': {
        'driver': 'DcMotor',
        'config': {
            'speed_controller':    [1 / 8, 0.3, 0, -100, 100],
            'position_controller': [10, 0, 0, -900, 900],
            'position_limits':     [0, 0],
            'encoder_resolution':  292
        }
    },
    'RevvyMotor_Dexter_CCW': {
        'driver': 'DcMotor',
        'config': {
            'speed_controller':    [1 / 8, 0.3, 0, -100, 100],
            'position_controller': [10, 0, 0, -900, 900],
            'position_limits':     [0, 0],
            'encoder_resolution':  -292
        }
    }
}


Sensors = {
    'NotConfigured': {'driver': 'NotConfigured', 'config': {}},
    'HC_SR04':       {'driver': 'HC_SR04', 'config': {}},
    'BumperSwitch':  {'driver': 'BumperSwitch', 'config': {}},
}


RobotVersion = namedtuple("RobotVersion", ['hw', 'fw', 'sw'])


class Robot:
    def __init__(self, interface: RevvyControl, sound):
        self._interface = interface

        self._start_time = time.time()

        # read versions
        hw = interface.get_hardware_version()
        fw = interface.get_firmware_version()
        sw = FRAMEWORK_VERSION

        print('Hardware: {}\nFirmware: {}\nFramework: {}'.format(hw, fw, sw))

        self._reader = FunctionSerializer(interface.ping)
        self._version = RobotVersion(hw, fw, sw)

        self._ring_led = RingLed(interface)
        self._sound = sound

        self._status = RobotStatusIndicator(interface)
        self._battery = BatteryStatus(0, 0, 0)

        def _motor_config_changed(motor: PortInstance, config_name):
            port_name = 'motor_{}'.format(motor.id)
            if config_name != 'NotConfigured':
                self._reader.add(port_name, motor.get_status)
            else:
                self._reader.remove(port_name)

        def _sensor_config_changed(sensor: PortInstance, config_name):
            port_name = 'sensor_{}'.format(sensor.id)
            if config_name != 'NotConfigured':
                self._reader.add(port_name, sensor.read)
            else:
                self._reader.remove(port_name)

        self._motor_ports = create_motor_port_handler(interface, Motors)
        for port in self._motor_ports:
            port.on_config_changed(_motor_config_changed)

        self._sensor_ports = create_sensor_port_handler(interface, Sensors)
        for port in self._sensor_ports:
            port.on_config_changed(_sensor_config_changed)

        self._drivetrain = DifferentialDrivetrain(interface, self._motor_ports.port_count)

    @property
    def start_time(self):
        return self._start_time

    @property
    def version(self):
        return self._version

    @property
    def battery(self):
        return self._battery

    @property
    def status(self):
        return self._status

    @property
    def motors(self):
        return self._motor_ports

    @property
    def sensors(self):
        return self._sensor_ports

    @property
    def drivetrain(self):
        return self._drivetrain

    @property
    def led_ring(self):
        return self._ring_led

    @property
    def sound(self):
        return self._sound

    def update_status(self):
        self._reader.run()

    def reset(self):
        self._ring_led.set_scenario(RingLed.BreathingGreen)
        self._reader.reset()

        def _update_battery():
            self._battery = self._interface.get_battery_status()

        self._reader.add('battery', _update_battery)

        self._drivetrain.reset()
        self._motor_ports.reset()
        self._sensor_ports.reset()

        self._status.robot_status = RobotStatus.NotConfigured
        self._status.update()


class RobotManager:

    # FIXME: revvy intentionally doesn't have a type hint at this moment because it breaks tests right now
    def __init__(self, interface: RevvyControl, revvy, sound, default_config=None):
        print("RobotManager: __init__()")
        self._robot = Robot(interface, sound)
        self._interface = interface
        self._ble = revvy
        self._default_configuration = default_config if default_config is not None else RobotConfig()

        self._reader = FunctionSerializer(self._interface.ping)

        self._status_update_thread = periodic(self._update, 0.1, "RobotStatusUpdaterThread")
        self._background_fn_lock = Lock()
        self._background_fns = []

        rc = RemoteController()
        rcs = RemoteControllerScheduler(rc)
        rcs.on_controller_detected(self._on_controller_detected)
        rcs.on_controller_lost(self._on_controller_lost)

        self._remote_controller = rc
        self._remote_controller_scheduler = rcs
        self._remote_controller_thread = create_remote_controller_thread(rcs)

        self._resources = {
            'led_ring':   Resource(),
            'drivetrain': Resource(),
            'sound':      Resource()
        }

        for port in self._robot.motors:
            self._resources['motor_{}'.format(port.id)] = Resource()
            port.on_status_changed(lambda p: self._ble['live_message_service'].update_motor(p.id, p.power, p.speed, p.position))

        for port in self._robot.sensors:
            self._resources['sensor_{}'.format(port.id)] = Resource()
            port.on_value_changed(lambda p: self._ble['live_message_service'].update_sensor(p.id, p.raw_value))

        revvy['live_message_service'].register_message_handler(self._remote_controller_scheduler.data_ready)
        revvy.on_connection_changed(self._on_connection_changed)

        self._scripts = ScriptManager(self)
        self._config = self._default_configuration

        self._update_requested = False

    def _update(self):
        self._robot.update_status()

        self._ble['battery_service'].characteristic('main_battery').update_value(self._robot.battery.main)
        self._ble['battery_service'].characteristic('motor_battery').update_value(self._robot.battery.motor)

        with self._background_fn_lock:
            fns = self._background_fns
            self._background_fns = []

        for fn in fns:
            if callable(fn):
                fn()

    @property
    def resources(self):
        return self._resources

    @property
    def config(self):
        return self._config

    @property
    def sound(self):
        return self._robot.sound

    @property
    def update_requested(self):
        return self._update_requested

    @property
    def robot(self):
        return self._robot

    @property
    def remote_controller(self):
        return self._remote_controller

    def request_update(self):
        self._update_requested = True

    def start(self):
        print("RobotManager: start()")
        if self._robot.status.robot_status == RobotStatus.StartingUp:
            print("Waiting for MCU")
            # TODO if we are getting stuck here (> ~3s), firmware is probably not valid
            self._ping_robot()

            self._ble['device_information_service'].characteristic('hw_version').update(str(self._robot.version.hw))
            self._ble['device_information_service'].characteristic('fw_version').update(str(self._robot.version.fw))
            self._ble['device_information_service'].characteristic('sw_version').update(self._robot.version.sw)

            # start reader thread
            self._status_update_thread.start()

            self._ble.start()
            self._robot.status.robot_status = RobotStatus.NotConfigured
            self.configure(None)

    def run_in_background(self, callback):
        with self._background_fn_lock:
            self._background_fns.append(callback)

    def _on_connection_changed(self, is_connected):
        print('Phone connected' if is_connected else 'Phone disconnected')
        if not is_connected:
            self._robot.status.controller_status = RemoteControllerStatus.NotConnected
            self.configure(None)
        else:
            self._robot.status.controller_status = RemoteControllerStatus.ConnectedNoControl

    def _on_controller_detected(self):
        self._robot.status.controller_status = RemoteControllerStatus.Controlled

    def _on_controller_lost(self):
        if self._robot.status.controller_status == RemoteControllerStatus.Controlled:
            self._robot.status.controller_status = RemoteControllerStatus.ConnectedNoControl
            self.configure(None)

    def configure(self, config):
        print('RobotManager: configure()')
        if self._robot.status.robot_status != RobotStatus.Stopped:
            self.run_in_background(lambda: self._configure(config))

    def _reset_configuration(self):
        self._scripts.reset()
        self._scripts.assign('Motor', MotorConstants)
        self._scripts.assign('RingLed', RingLed)

        for res in self._resources:
            self._resources[res].reset()

        # ping robot, because robot may reset after stopping scripts
        self._ping_robot()

        self._robot.reset()

    def _apply_new_configuration(self, config):
        # apply new configuration
        print("Applying new configuration")

        # set up motors
        for motor in self._robot.motors:
            motor.configure(config.motors[motor.id])

        for motor_id in config.drivetrain['left']:
            self._robot.drivetrain.add_left_motor(self._robot.motors[motor_id])

        for motor_id in config.drivetrain['right']:
            self._robot.drivetrain.add_right_motor(self._robot.motors[motor_id])

        self._robot.drivetrain.configure()

        # set up sensors
        for sensor in self._robot.sensors:
            sensor.configure(config.sensors[sensor.id])

        # set up scripts
        for name in config.scripts:
            self._scripts.add_script(name, config.scripts[name]['script'], config.scripts[name]['priority'])

        # set up remote controller
        for analog in config.controller.analog:
            self._remote_controller.on_analog_values(
                analog['channels'],
                lambda in_data, scr=analog['script']: self._scripts[scr].start({'input': in_data})
            )

        for button in range(len(config.controller.buttons)):
            script = config.controller.buttons[button]
            if script:
                self._remote_controller.on_button_pressed(button, self._scripts[script].start)

        self._remote_controller_thread.start()

        # start background scripts
        for script in config.background_scripts:
            self._scripts[script].start()

    def _configure(self, config):
        is_default_config = config is None

        if not config and self._robot.status.robot_status != RobotStatus.Stopped:
            config = self._default_configuration
        self._config = config

        self._scripts.stop_all_scripts()
        self._reset_configuration()

        if config:
            self._apply_new_configuration(config)
            if is_default_config:
                self._robot.status.robot_status = RobotStatus.NotConfigured
            else:
                self._robot.status.robot_status = RobotStatus.Configured
        else:
            self._robot.status.robot_status = RobotStatus.NotConfigured

    def stop(self):
        self._robot.status.robot_status = RobotStatus.Stopped
        self._remote_controller_thread.exit()
        self._ble.stop()
        self._scripts.reset()
        self._status_update_thread.exit()

    def _ping_robot(self):
        retry_ping = True
        while retry_ping:
            retry_ping = False
            try:
                self._interface.ping()
            except (BrokenPipeError, IOError, OSError):
                retry_ping = True


class FunctionSerializer:
    def __init__(self, default_action=lambda: None):
        self._functions = {}
        self._fn_lock = Lock()
        self._default_action = default_action

    def reset(self):
        with self._fn_lock:
            self._functions = {}

    def add(self, name, reader):
        print('FunctionSerializer: new function: {}'.format(name))
        with self._fn_lock:
            self._functions[name] = reader

    def remove(self, name):
        with self._fn_lock:
            try:
                del self._functions[name]
            except KeyError:
                pass

    def run(self):
        with self._fn_lock:
            if not self._functions:
                self._default_action()
                return {}
            else:
                return {key: self._functions[key]() for key in self._functions}


class DeviceNameProvider:
    def __init__(self, storage: StorageInterface, default):
        self._filename = 'device-name'
        self._storage = storage
        try:
            self._name = storage.read(self._filename).decode("utf-8")
        except StorageError:
            self._name = default()

    def get_device_name(self):
        return self._name

    def update_device_name(self, new_device_name):
        if new_device_name != self._name:
            self._name = new_device_name
            self._storage.write(self._filename, self._name.encode("utf-8"))
