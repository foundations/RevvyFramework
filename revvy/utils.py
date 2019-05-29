#!/usr/bin/python3
from revvy.ble_revvy import RevvyBLE
from revvy.file_storage import StorageInterface, StorageError
from revvy.scripting.runtime import ScriptManager
from revvy.thread_wrapper import *
import time

from revvy.rrrc_transport import *
from revvy.rrrc_control import *
from revvy.ports.motor import *
from revvy.ports.sensor import *
from revvy.fw_version import *
from revvy.activation import EdgeTrigger
from revvy.functions import *


class DifferentialDrivetrain:
    def __init__(self):
        self._left_motors = []
        self._right_motors = []
        self._controller = lambda x, y: (0, 0)

    def set_controller(self, controller):
        self._controller = controller

    def reset(self):
        self._left_motors = []
        self._right_motors = []

    def add_left_motor(self, motor):
        self._left_motors.append(motor)

    def add_right_motor(self, motor):
        self._right_motors.append(motor)

    def update(self, channels):
        x = clip((channels[0] - 127) / 127.0, -1, 1)
        y = clip((channels[1] - 127) / 127.0, -1, 1)

        sl, sr = self._controller(x, y)

        sl = map_values(sl, 0, 1, 0, 900)
        sr = map_values(sr, 0, 1, 0, 900)
        self.set_speeds(sl, sr)

    def set_speeds(self, left, right):
        for motor in self._left_motors:
            motor.set_speed(left)

        for motor in self._right_motors:
            motor.set_speed(right)


def stick_contoller(x, y):
    """Two wheel speeds are controlled independently, just pass through"""
    return x, y


def joystick(x, y):
    """Calculate control vector length and angle based on touch (x, y) coordinates

    >>> joystick(0, 0)
    (0.0, 0.0)
    >>> joystick(0, 1)
    (-1.0, 1.0)
    >>> joystick(0, -1)
    (1.0, -1.0)
    >>> joystick(1, 0)
    (-1.0, -1.0)
    >>> joystick(-1, 0)
    (1.0, 1.0)
    """

    if x == y == 0:
        return 0.0, 0.0

    angle = math.atan2(y, x) - math.pi / 2
    length = math.sqrt(x * x + y * y)

    v = length * math.cos(angle)
    w = length * math.sin(angle)

    sr = round(+(v + w), 3)
    sl = round(-(v - w), 3)
    return sl, sr


class RingLed:
    Off = 0
    UserFrame = 1
    ColorWheel = 2

    def __init__(self, interface: RevvyControl):
        self._interface = interface
        self._ring_led_count = 0
        self._current_scenario = self.Off
        self._user_led_feature_supported = False

    def reset(self):
        try:
            self.set_scenario(RingLed.Off)
            self._ring_led_count = self._interface.ring_led_get_led_amount()
            self._user_led_feature_supported = True
        except UnknownCommandError:
            print('RingLed: user led feature is not supported in current firmware')
            self._user_led_feature_supported = False

    def set_scenario(self, scenario):
        self._current_scenario = scenario
        self._interface.ring_led_set_scenario(scenario)

    @property
    def scenario(self):
        return self._current_scenario

    def upload_user_frame(self, frame):
        """
        :param frame: array of 12 RGB values
        """
        if not self._user_led_feature_supported:
            return

        if len(frame) != self._ring_led_count:
            raise ValueError("Number of colors ({}) does not match LEDs ({})", len(frame), self._ring_led_count)

        self._interface.ring_led_set_user_frame(frame)

    def display_user_frame(self, frame):
        if not self._user_led_feature_supported:
            return

        self.upload_user_frame(frame)
        self.set_scenario(self.UserFrame)


class RemoteController:
    def __init__(self):
        self._data_mutex = Lock()
        self._button_mutex = Lock()

        self._analogActions = []
        self._buttonActions = [lambda: None] * 32
        self._buttonHandlers = [None] * 32
        self._controller_detected = lambda: None
        self._controller_disappeared = lambda: None

        self._message = None
        self._missedKeepAlives = -1

        for i in range(len(self._buttonHandlers)):
            handler = EdgeTrigger()
            handler.onRisingEdge(lambda idx=i: self._button_pressed(idx))
            self._buttonHandlers[i] = handler

    def _button_pressed(self, idx):
        print('Button {} pressed'.format(idx))
        action = self._buttonActions[idx]
        if action:
            action()

    def reset(self):
        print('RemoteController: reset')
        with self._button_mutex:
            self._analogActions = []
            self._buttonActions = [lambda: None] * 32
            self._message = None
            self._missedKeepAlives = -1

    def tick(self):
        # copy data
        with self._data_mutex:
            message = self._message
            self._message = None

        if message is not None:
            if self._missedKeepAlives == -1:
                self._controller_detected()
            self._missedKeepAlives = 0

            # handle analog channels
            for handler in self._analogActions:
                # check if all channels are present in the message
                if all(map(lambda x: x < len(message['analog']), handler['channels'])):
                    values = list(map(lambda x: message['analog'][x], handler['channels']))
                    handler['action'](values)
                else:
                    print('Skip analog handler for channels {}'.format(",".join(map(str, handler['channels']))))

            # handle button presses
            for idx in range(len(self._buttonHandlers)):
                with self._button_mutex:
                    self._buttonHandlers[idx].handle(message['buttons'][idx])
        else:
            if not self._handle_keep_alive_missed():
                self._controller_disappeared()

    def _handle_keep_alive_missed(self):
        if self._missedKeepAlives >= 0:
            self._missedKeepAlives += 1
            print('RemoteController: Missed {}'.format(self._missedKeepAlives))

        if self._missedKeepAlives >= 5:
            self._missedKeepAlives = -1
            return False
        else:
            return True

    def on_controller_detected(self, action):
        self._controller_detected = action

    def on_controller_disappeared(self, action):
        self._controller_disappeared = action

    def on_button_pressed(self, button, action):
        self._buttonActions[button] = action

    def on_analog_values(self, channels, action):
        self._analogActions.append({'channels': channels, 'action': action})

    def update(self, message):
        with self._data_mutex:
            self._message = message

    def start(self):
        print('RemoteController: start')
        self._missedKeepAlives = -1


class RemoteControllerScheduler(ThreadWrapper):
    def __init__(self, rc: RemoteController):
        self._controller = rc
        self._data_ready_event = Event()
        super().__init__(self._schedule_controller, "RemoteControllerThread")

    def data_ready(self):
        self._data_ready_event.set()

    def _schedule_controller(self, ctx: ThreadContext):
        while not ctx.stop_requested:
            self._data_ready_event.wait(0.15)
            self._data_ready_event.clear()
            self._controller.tick()

    def start(self):
        self._data_ready_event.clear()
        self._controller.start()
        super().start()

    def reset(self):
        self.stop()
        self._controller.reset()


class RobotManager:
    StatusStartingUp = 0
    StatusNotConfigured = 1
    StatusConfigured = 2

    status_led_not_configured = 0
    status_led_configured = 1
    status_led_controlled = 2

    def __init__(self, interface: RevvyTransportInterface, revvy: RevvyBLE, default_config=None):
        self._robot = RevvyControl(RevvyTransport(interface))
        self._ble = revvy
        self._is_connected = False
        self._default_configuration = default_config

        self._reader = FunctionSerializer(self._robot.ping)
        self._data_dispatcher = DataDispatcher()

        self._status_update_thread = ThreadWrapper(self._update_thread, "RobotUpdateThread")
        self._background_fn_lock = Lock()
        self._config_lock = Lock()
        self._background_fn = None

        rc = RemoteController()
        rc.on_controller_detected(self._on_controller_detected)
        rc.on_controller_disappeared(self._on_controller_lost)

        self._remote_controller = rc
        self._remote_controller_scheduler = RemoteControllerScheduler(rc)

        self._drivetrain = DifferentialDrivetrain()
        self._ring_led = RingLed(self._robot)
        self._motor_ports = MotorPortHandler(self._robot)
        self._sensor_ports = SensorPortHandler(self._robot)

        revvy.register_remote_controller_handler(self._on_controller_message_received)
        revvy.registerConnectionChangedHandler(self._on_connection_changed)
        # revvy.on_configuration_received(self._process_new_configuration)

        self._scripts = ScriptManager()

        self._status = self.StatusStartingUp

    def _on_controller_message_received(self, message):
        self._remote_controller.update(message)
        self._remote_controller_scheduler.data_ready()

    def start(self):
        if self._status != self.StatusStartingUp:
            return

        print("Waiting for MCU")
        # TODO if we are getting stuck here (> ~3s), firmware is probably not valid
        retry_ping = True
        while retry_ping:
            retry_ping = False
            try:
                self._robot.ping()
            # TODO do NACK responses raise exceptions?
            except (BrokenPipeError, IOError):
                retry_ping = True

        # start reader thread (do it here to prevent unwanted reset)
        self._status_update_thread.start()

        # read versions
        hw = self._robot.get_hardware_version()
        fw = self._robot.get_firmware_version()
        sw = FRAMEWORK_VERSION

        print('Hardware: {}\nFirmware: {}\nFramework: {}'.format(hw, fw, sw))

        self._ble.set_hw_version(hw)
        self._ble.set_fw_version(fw)
        self._ble.set_sw_version(sw)

        # call reset to read port counts, types
        self._ring_led.reset()
        self._sensor_ports.reset()
        self._motor_ports.reset()

        for port in self._motor_ports:
            port.on_config_changed(self._motor_config_changed)

        for port in self._sensor_ports:
            port.on_config_changed(self._sensor_config_changed)

        self._ble.start()

        self.configure(None)

    def _motor_config_changed(self, motor: MotorPortInstance, config_name):
        motor_name = 'motor_{}'.format(motor.id)
        if config_name != 'NotConfigured':
            self._reader.add(motor_name, motor.get_status)
        else:
            self._reader.remove(motor_name)

    def _sensor_config_changed(self, sensor: SensorPortInstance, config_name):
        sensor_name = 'sensor_{}'.format(sensor.id)
        if config_name != 'NotConfigured':
            self._reader.add(sensor_name, lambda s=sensor: s.read())
            self._data_dispatcher.add(sensor_name, lambda value, sid=sensor.id: self._update_sensor(sid, value))
        else:
            self._reader.remove(sensor_name)
            self._data_dispatcher.remove(sensor_name)

    def run_in_background(self, callback):
        with self._background_fn_lock:
            self._background_fn = callback

    def _update_thread(self, ctx: ThreadContext):
        while not ctx.stop_requested:
            data = self._reader.run()
            self._data_dispatcher.dispatch(data)
            time.sleep(0.1)

            with self._background_fn_lock:
                fn = self._background_fn
                self._background_fn = None

            if callable(fn):
                fn()

    def _on_connection_changed(self, is_connected):
        self._is_connected = is_connected
        self._robot.set_bluetooth_connection_status(is_connected)
        if not is_connected:
            self.configure(None)

    def _on_controller_detected(self):
        if self._status == self.StatusConfigured:
            self._robot.set_master_status(self.status_led_controlled)

    def _on_controller_lost(self):
        self.configure(None)

    def _update_sensor(self, sid, value):
        # print('Sensor {}: {}'.format(sid, value['converted']))
        self._ble.update_sensor(sid, value['raw'])

    def configure(self, config):
        self.run_in_background(lambda: self._configure(config))

    def _configure(self, config):
        with self._config_lock:
            if not config:
                config = self._default_configuration

            if config:
                # apply new configuration
                print("Applying new configuration")
                self._ring_led.set_scenario(RingLed.Off)

                self._drivetrain.reset()
                self._drivetrain.set_controller(joystick)
                self._remote_controller_scheduler.reset()

                # set up status reader, data dispatcher
                self._reader.reset()
                self._data_dispatcher.reset()

                # set up motors
                for motor in self._motor_ports:
                    motor.configure(config.motors[motor.id])

                for motor_id in config.drivetrain['left']:
                    print('Drivetrain: Add motor {} to left side'.format(motor_id))
                    self._drivetrain.add_left_motor(self._motor_ports[motor_id])

                for motor_id in config.drivetrain['right']:
                    print('Drivetrain: Add motor {} to right side'.format(motor_id))
                    self._drivetrain.add_right_motor(self._motor_ports[motor_id])

                # set up sensors
                for sensor in self._sensor_ports:
                    sensor.configure(config.sensors[sensor.id])
    
                # set up scripts
                self._scripts.reset()
                self._scripts.assign('robot', self)
                self._scripts.assign('RingLed', RingLed)
                for name in config.scripts.keys():
                    self._scripts[name] = config.scripts[name]['script']

                # set up remote controller
                self._remote_controller.on_analog_values([0, 1], self._drivetrain.update)
                for button in range(len(config.controller.buttons)):
                    script = config.controller.buttons[button]
                    if script:
                        self._remote_controller.on_button_pressed(button, self._scripts[script].start)

                self._remote_controller_scheduler.start()
                self._robot.set_master_status(self.status_led_configured)
                print('Robot configured')
                self._status = self.StatusConfigured
            else:
                print("Deinitialize robot")
                self._ring_led.set_scenario(RingLed.Off)
                self._remote_controller_scheduler.reset()
                self._scripts.reset()
                self._robot.set_master_status(self.status_led_not_configured)
                self._drivetrain.reset()
                self._motor_ports.reset()
                self._sensor_ports.reset()
                self._reader.reset()
                self._remote_controller_scheduler.stop()
                self._status = self.StatusNotConfigured

    def stop(self):
        print("Stopping robot manager")
        self._remote_controller_scheduler.exit()
        self._ble.stop()
        self._scripts.reset()
        self._status_update_thread.exit()


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
                return True
            except KeyError:
                return False

    def run(self):
        data = {}
        with self._fn_lock:
            if len(self._functions) == 0:
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
            del self._handlers[name]

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
