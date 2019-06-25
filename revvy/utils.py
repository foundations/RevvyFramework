#!/usr/bin/python3
from revvy.file_storage import StorageInterface, StorageError
from revvy.mcu.rrrc_control import RevvyControl
from revvy.robot.drivetrain import DifferentialDrivetrain
from revvy.robot.remote_controller import RemoteController, RemoteControllerScheduler, create_remote_controller_thread
from revvy.robot.led_ring import RingLed
from revvy.robot.ports.common import PortInstance
from revvy.robot.ports.motor import create_motor_port_handler
from revvy.robot.ports.sensor import create_sensor_port_handler
from revvy.robot_config import RobotConfig
from revvy.scripting.resource import Resource
from revvy.scripting.robot_interface import MotorConstants
from revvy.scripting.runtime import ScriptManager
from revvy.thread_wrapper import *

from revvy.mcu.rrrc_transport import *
from revvy.fw_version import *


class Motors:
    types = {
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
        'RevvyMotor_CCW':    {
            'driver': 'DcMotor',
            'config': {
                'speed_controller':    [1 / 25, 0.3, 0, -100, 100],
                'position_controller': [10, 0, 0, -900, 900],
                'position_limits':     [0, 0],
                'encoder_resolution': -1168
            }
        },
        'RevvyMotor_Dexter':    {
            'driver': 'DcMotor',
            'config': {
                'speed_controller':    [1 / 8, 0.3, 0, -100, 100],
                'position_controller': [10, 0, 0, -900, 900],
                'position_limits':     [0, 0],
                'encoder_resolution':  292
            }
        },
        'RevvyMotor_Dexter_CCW':    {
            'driver': 'DcMotor',
            'config': {
                'speed_controller':    [1 / 8, 0.3, 0, -100, 100],
                'position_controller': [10, 0, 0, -900, 900],
                'position_limits':     [0, 0],
                'encoder_resolution': -292
            }
        }
    }


class Sensors:
    types = {
        'NotConfigured': {'driver': 'NotConfigured', 'config': {}},
        'HC_SR04': {'driver': 'HC_SR04', 'config': {}},
        'BumperSwitch': {'driver': 'BumperSwitch', 'config': {}},
    }


class RobotManager:
    StatusStartingUp = 0
    StatusNotConfigured = 1
    StatusConfigured = 2
    StatusStopped = 3

    status_led_not_configured = 0
    status_led_configured = 1
    status_led_controlled = 2

    # FIXME: revvy intentionally doesn't have a type hint at this moment because it breaks tests right now
    def __init__(self, robot: RevvyControl, revvy, sound, default_config=None):
        print("RobotManager: __init__()")
        self._start_time = time.time()
        self._robot = robot
        self._ble = revvy
        self._is_connected = False
        self._default_configuration = default_config if default_config is not None else RobotConfig()
        self._sound = sound

        self._reader = FunctionSerializer(self._robot.ping)
        self._data_dispatcher = DataDispatcher()

        self._status_update_thread = ThreadWrapper(self._update_thread, "RobotUpdateThread")
        self._background_fn_lock = Lock()
        self._config_lock = Lock()
        self._background_fn = None

        rc = RemoteController()
        rcs = RemoteControllerScheduler(rc)
        rcs.on_controller_detected(self._on_controller_detected)
        rcs.on_controller_lost(self._on_controller_lost)

        self._remote_controller = rc
        self._remote_controller_scheduler = rcs
        self._remote_controller_thread = create_remote_controller_thread(rcs)

        self._ring_led = RingLed(self._robot)
        self._motor_ports = create_motor_port_handler(self._robot, Motors.types)
        self._sensor_ports = create_sensor_port_handler(self._robot, Sensors.types)
        self._drivetrain = DifferentialDrivetrain(self._robot, self._motor_ports.port_count)

        revvy['live_message_service'].register_message_handler(self._remote_controller_scheduler.data_ready)
        revvy.on_connection_changed(self._on_connection_changed)

        self._scripts = ScriptManager(self)
        self._resources = {}
        self._config = self._default_configuration

        self._update_requested = False
        self._status = self.StatusStartingUp

    @property
    def start_time(self):
        return self._start_time

    @property
    def resources(self):
        return self._resources

    @property
    def config(self):
        return self._config

    @property
    def sound(self):
        return self._sound

    @property
    def update_requested(self):
        return self._update_requested

    def request_update(self):
        self._update_requested = True

    def start(self):
        print("RobotManager: start()")
        if self._status != self.StatusStartingUp:
            return

        print("Waiting for MCU")
        # TODO if we are getting stuck here (> ~3s), firmware is probably not valid
        retry_ping = True
        while retry_ping:
            retry_ping = False
            try:
                self._robot.ping()
            except (BrokenPipeError, IOError, OSError):
                retry_ping = True

        # read versions
        hw = self._robot.get_hardware_version()
        fw = self._robot.get_firmware_version()
        sw = FRAMEWORK_VERSION

        print('Hardware: {}\nFirmware: {}\nFramework: {}'.format(hw, fw, sw))

        self._ble['device_information_service'].characteristic('hw_version').update(str(hw))
        self._ble['device_information_service'].characteristic('fw_version').update(str(fw))
        self._ble['device_information_service'].characteristic('sw_version').update(sw)

        # start reader thread
        self._status_update_thread.start()
        self._robot.set_bluetooth_connection_status(False)

        self._resources = {
            'led_ring': Resource(),
            'drivetrain': Resource(),
            'sound': Resource()
        }
        for port in self._motor_ports:
            port.on_config_changed(self._motor_config_changed)
            self._resources['motor_{}'.format(port.id)] = Resource()

        for port in self._sensor_ports:
            port.on_config_changed(self._sensor_config_changed)
            self._resources['sensor_{}'.format(port.id)] = Resource()

        self._ble.start()

        self.configure(None)

    def _motor_config_changed(self, motor: PortInstance, config_name):
        motor_name = 'motor_{}'.format(motor.id)
        if config_name != 'NotConfigured':
            self._reader.add(motor_name, motor.get_status)
            self._data_dispatcher.add(motor_name, lambda value, mid=motor.id: self._update_motor(mid, value))
        else:
            self._reader.remove(motor_name)
            self._data_dispatcher.remove(motor_name)

    def _sensor_config_changed(self, sensor: PortInstance, config_name):
        sensor_name = 'sensor_{}'.format(sensor.id)
        if config_name != 'NotConfigured':
            self._reader.add(sensor_name, sensor.read)
            self._data_dispatcher.add(sensor_name, lambda value, sid=sensor.id: self._update_sensor(sid, value))
        else:
            self._reader.remove(sensor_name)
            self._data_dispatcher.remove(sensor_name)

    def run_in_background(self, callback):
        with self._background_fn_lock:
            self._background_fn = callback

    def _update_thread(self, ctx: ThreadContext):
        _next_call = time.time()

        while not ctx.stop_requested:
            data = self._reader.run()
            self._data_dispatcher.dispatch(data)

            with self._background_fn_lock:
                fn = self._background_fn
                self._background_fn = None

            if callable(fn):
                fn()
                _next_call = time.time()
            else:
                _next_call += 0.1
                diff = _next_call - time.time()
                if diff > 0:
                    time.sleep(diff)

    def _on_connection_changed(self, is_connected):
        print('Phone connected' if is_connected else 'Phone disconnected')
        self._is_connected = is_connected
        self._robot.set_bluetooth_connection_status(is_connected)
        if not is_connected:
            self.configure(None)

    def _on_controller_detected(self):
        print('Controller detected')
        if self._status == self.StatusConfigured:
            self._robot.set_master_status(self.status_led_controlled)

    def _on_controller_lost(self):
        print('Controller lost')
        self.configure(None)

    def _update_sensor(self, sid, value):
        self._ble['live_message_service'].update_sensor(sid, value['raw'])

    def _update_motor(self, mid, value):
        self._ble['live_message_service'].update_motor(mid, value['power'], value['speed'], value['position'])

    def _update_battery(self, battery):
        self._ble['battery_service'].characteristic('main_battery').update_value(battery['main'])
        self._ble['battery_service'].characteristic('motor_battery').update_value(battery['motor'])

    def configure(self, config):
        print('RobotManager: configure()')
        if self._status != self.StatusStopped:
            self.run_in_background(lambda: self._configure(config))

    def _configure(self, config):
        with self._config_lock:
            if not config:
                status = self.status_led_not_configured
            else:
                status = self.status_led_configured

            if not config and self._status != self.StatusStopped:
                config = self._default_configuration
            self._config = config

            self._ring_led.set_scenario(RingLed.Off)

            self._scripts.reset()

            # wait for a potential reset
            retry_ping = True
            while retry_ping:
                retry_ping = False
                try:
                    self._robot.ping()
                except (BrokenPipeError, IOError, OSError):
                    retry_ping = True

            self._robot.set_bluetooth_connection_status(self._is_connected)

            # set up status reader, data dispatcher
            self._reader.reset()
            self._data_dispatcher.reset()

            self._reader.add('battery', self._robot.get_battery_status)
            self._data_dispatcher.add('battery', self._update_battery)

            self._drivetrain.reset()
            self._remote_controller_thread.stop()

            if config:
                # apply new configuration
                print("Applying new configuration")

                # set up motors
                for motor in self._motor_ports:
                    motor.configure(config.motors[motor.id])

                for motor_id in config.drivetrain['left']:
                    print('Drivetrain: Add motor {} to left side'.format(motor_id))
                    self._drivetrain.add_left_motor(self._motor_ports[motor_id])

                for motor_id in config.drivetrain['right']:
                    print('Drivetrain: Add motor {} to right side'.format(motor_id))
                    self._drivetrain.add_right_motor(self._motor_ports[motor_id])

                self._drivetrain.configure()

                # set up sensors
                for sensor in self._sensor_ports:
                    sensor.configure(config.sensors[sensor.id])

                # set up scripts
                self._scripts.assign('Motor', MotorConstants)
                self._scripts.assign('RingLed', RingLed)
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

                print('Robot configured')
                self._set_status(self.StatusConfigured)

                # start background scripts
                for script in config.background_scripts:
                    self._scripts[script].start()
            else:
                print("Deinitialize robot")
                self._drivetrain.configure()
                self._motor_ports.reset()
                self._sensor_ports.reset()
                self._remote_controller_thread.stop()
                self._set_status(self.StatusNotConfigured)

            self._robot.set_master_status(status)

    def stop(self):
        print("Stopping robot manager")
        self._status = self.StatusStopped
        self._remote_controller_thread.exit()
        self._ble.stop()
        self._scripts.reset()
        self._status_update_thread.exit()

    def _set_status(self, status):
        if self._status != self.StatusStopped:
            self._status = status


class FunctionSerializer:
    def __init__(self, default_action=lambda: None):
        self._functions = {}
        self._returnValues = {}
        self._fn_lock = Lock()
        self._default_action = default_action

    def reset(self):
        with self._fn_lock:
            self._functions = {}

    def add(self, name, reader):
        print('FunctionSerializer: new function: {}'.format(name))
        with self._fn_lock:
            self._functions[name] = reader
            self._returnValues[name] = None

    def remove(self, name):
        with self._fn_lock:
            try:
                del self._functions[name]
            except KeyError:
                pass

    def run(self):
        data = {}
        with self._fn_lock:
            if not self._functions:
                self._default_action()
            else:
                for name in self._functions:
                    data[name] = self._functions[name]()
        return data


class DataDispatcher:
    def __init__(self):
        self._handlers = {}
        self._lock = Lock()

    def reset(self):
        with self._lock:
            self._handlers = {}

    def add(self, name, handler):
        with self._lock:
            self._handlers[name] = handler

    def remove(self, name):
        with self._lock:
            try:
                del self._handlers[name]
            except KeyError:
                pass

    def dispatch(self, data):
        for key in data:
            with self._lock:
                if key in self._handlers:
                    self._handlers[key](data[key])


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
