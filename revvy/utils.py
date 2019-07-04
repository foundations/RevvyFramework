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


class RobotStatus:
    StartingUp = 0
    NotConfigured = 1
    Configured = 2
    Stopped = 3


class RemoteControllerStatus:
    NotConnected = 0
    ConnectedNoControl = 1
    Controlled = 2


class RobotStatusIndicator:
    master_led_not_configured = 0
    master_led_configured = 1
    master_led_controlled = 2

    bluetooth_led_not_connected = 0
    bluetooth_led_connected = 1

    def __init__(self, interface: RevvyControl):
        self._interface = interface

        self._robot_status = RobotStatus.StartingUp
        self._controller_status = RemoteControllerStatus.NotConnected

        self._master_led = None
        self._bluetooth_led = None

        self._update_leds()

    def _set_master_led(self, value):
        if value != self._master_led:
            self._master_led = value
            self._interface.set_master_status(self._master_led)

    def _set_bluetooth_led(self, value):
        if value != self._bluetooth_led:
            self._bluetooth_led = value
            self._interface.set_bluetooth_connection_status(self._bluetooth_led == self.bluetooth_led_connected)

    def update(self):
        self._interface.set_master_status(self._master_led)
        self._interface.set_bluetooth_connection_status(self._bluetooth_led == self.bluetooth_led_connected)

    def _update_leds(self):
        if self._robot_status == RobotStatus.Configured:
            if self._controller_status == RemoteControllerStatus.Controlled:
                self._set_master_led(self.master_led_controlled)
            else:
                self._set_master_led(self.master_led_configured)
        else:
            self._set_master_led(self.master_led_not_configured)

        if self._controller_status == RemoteControllerStatus.NotConnected:
            self._set_bluetooth_led(self.bluetooth_led_not_connected)
        else:
            self._set_bluetooth_led(self.bluetooth_led_connected)

    @property
    def robot_status(self):
        return self._robot_status

    @robot_status.setter
    def robot_status(self, value):
        if self._robot_status != RobotStatus.Stopped:
            self._robot_status = value
            self._update_leds()

    @property
    def controller_status(self):
        return self._controller_status

    @controller_status.setter
    def controller_status(self, value):
        self._controller_status = value
        self._update_leds()


class RobotManager:

    # FIXME: revvy intentionally doesn't have a type hint at this moment because it breaks tests right now
    def __init__(self, robot: RevvyControl, revvy, sound, default_config=None):
        print("RobotManager: __init__()")
        self._start_time = time.time()
        self._robot = robot
        self._ble = revvy
        self._is_connected = False
        self._default_configuration = default_config if default_config is not None else RobotConfig()
        self._sound = sound
        self._status = RobotStatusIndicator(robot)

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

        self._resources = {
            'led_ring':   Resource(),
            'drivetrain': Resource(),
            'sound':      Resource()
        }
        self._motor_ports = create_motor_port_handler(self._robot, Motors)
        for port in self._motor_ports:
            port.on_config_changed(self._motor_config_changed)
            self._resources['motor_{}'.format(port.id)] = Resource()

        self._sensor_ports = create_sensor_port_handler(self._robot, Sensors)
        for port in self._sensor_ports:
            port.on_config_changed(self._sensor_config_changed)
            self._resources['sensor_{}'.format(port.id)] = Resource()

        self._drivetrain = DifferentialDrivetrain(self._robot, self._motor_ports.port_count)

        revvy['live_message_service'].register_message_handler(self._remote_controller_scheduler.data_ready)
        revvy.on_connection_changed(self._on_connection_changed)

        self._scripts = ScriptManager(self)
        self._config = self._default_configuration

        self._update_requested = False

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
        if self._status.robot_status == RobotStatus.StartingUp:
            print("Waiting for MCU")
            # TODO if we are getting stuck here (> ~3s), firmware is probably not valid
            self._ping_robot()

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

            self._ble.start()
            self._status.robot_status = RobotStatus.NotConfigured
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
        if not is_connected:
            self._status.controller_status = RemoteControllerStatus.NotConnected
            self.configure(None)
        else:
            self._status.controller_status = RemoteControllerStatus.ConnectedNoControl

    def _on_controller_detected(self):
        print('Controller detected')
        self._status.controller_status = RemoteControllerStatus.Controlled

    def _on_controller_lost(self):
        print('Controller lost')
        if self._status.controller_status == RemoteControllerStatus.Controlled:
            self._status.controller_status = RemoteControllerStatus.ConnectedNoControl
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
        if self._status.robot_status != RobotStatus.Stopped:
            self.run_in_background(lambda: self._configure(config))

    def _configure(self, config):
        with self._config_lock:
            is_configured = True if config else False

            if not config and self._status.robot_status != RobotStatus.Stopped:
                config = self._default_configuration
            self._config = config

            self._scripts.reset()
            self._scripts.assign('Motor', MotorConstants)
            self._scripts.assign('RingLed', RingLed)

            # ping robot, because robot may reset after stopping scripts
            self._ping_robot()

            self._ring_led.set_scenario(RingLed.BreathingGreen)

            # set up status reader, data dispatcher
            self._reader.reset()
            self._data_dispatcher.reset()

            self._reader.add('battery', self._robot.get_battery_status)
            self._data_dispatcher.add('battery', self._update_battery)

            self._drivetrain.reset()
            self._remote_controller_thread.stop()

            self._motor_ports.reset()
            self._sensor_ports.reset()

            self._status.robot_status = RobotStatus.NotConfigured
            self._status.update()

            if config:
                # apply new configuration
                print("Applying new configuration")

                # set up motors
                for motor in self._motor_ports:
                    motor.configure(config.motors[motor.id])

                for motor_id in config.drivetrain['left']:
                    self._drivetrain.add_left_motor(self._motor_ports[motor_id])

                for motor_id in config.drivetrain['right']:
                    self._drivetrain.add_right_motor(self._motor_ports[motor_id])

                self._drivetrain.configure()

                # set up sensors
                for sensor in self._sensor_ports:
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

                print('Robot configured')

                # start background scripts
                for script in config.background_scripts:
                    self._scripts[script].start()

            if is_configured:
                self._status.robot_status = RobotStatus.Configured
            else:
                self._status.robot_status = RobotStatus.NotConfigured

    def stop(self):
        print("Stopping robot manager")
        self._status.robot_status = RobotStatus.Stopped
        self._remote_controller_thread.exit()
        self._ble.stop()
        self._scripts.reset()
        self._status_update_thread.exit()

    def _ping_robot(self):
        retry_ping = True
        while retry_ping:
            retry_ping = False
            try:
                self._robot.ping()
            except (BrokenPipeError, IOError, OSError):
                retry_ping = True


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
