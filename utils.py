#!/usr/bin/python3

import math

from longmessage import LongMessageStorage, LongMessageHandler
from robot_config import RobotConfig
from runtime import ScriptManager
from thread_wrapper import *
import sys
import os
import time

from ble_revvy import *

from rrrc_transport import *
from motor_controllers import *
from sensor_port_handlers import *
from fw_version import *
from activation import EdgeTrigger
from functions import *


def empty_callback():
    pass


class NullHandler:
    def handle(self, value):
        pass


class DifferentialDrivetrain:
    def __init__(self):
        self._left_motors = []
        self._right_motors = []
        self._max_speed = 90

    def reset(self):
        self._left_motors = []
        self._right_motors = []
        self._max_speed = 90

    def add_left_motor(self, motor):
        self._left_motors.append(motor)

    def add_right_motor(self, motor):
        self._right_motors.append(motor)

    def update(self, channels):
        (angle, length) = joystick(channels[0], channels[1])
        (sl, sr) = differentialControl(length, angle)
        self.set_speeds(self._max_speed * sl, self._max_speed * sr)

    def set_speeds(self, left, right):
        for motor in self._left_motors:
            motor.set_speed(left)

        for motor in self._right_motors:
            motor.set_speed(right)


def differentialControl(r, angle):
    """
    Calculates left and right wheel speeds
    :param r: Vector magnitude, between 0 and 1
    :param angle: Vector angle, between -pi/2 and pi/2
    :return: wheel speeds
    """
    v = r * math.cos(angle + math.pi / 2)
    w = r * math.sin(angle + math.pi / 2)

    sr = +(v + w)
    sl = -(v - w)
    return sl, sr


def joystick(a, b):
    x = clip((a - 127) / 127.0, -1, 1)
    y = clip((b - 127) / 127.0, -1, 1)

    angle = math.atan2(y, x)
    length = math.sqrt(x * x + y * y)
    return angle, length


class RingLed:
    Off = 0
    UserFrame = 1
    ColorWheel = 2

    def __init__(self, interface: RevvyControl):
        self._interface = interface
        self._ring_led_count = 0
        self._current_scenario = self.Off

    def reset(self):
        self._ring_led_count = self._interface.ring_led_get_led_amount()
        self.set_scenario(RingLed.Off)

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
        # TODO what to do if called before first reset?
        if len(frame) != self._ring_led_count:
            raise ValueError("Number of colors ({}) does not match LEDs ({})", len(frame), self._ring_led_count)

        self._interface.ring_led_set_user_frame(frame)

    def display_user_frame(self, frame):
        # TODO what to do if called before first reset?
        self.upload_user_frame(frame)
        self.set_scenario(self.UserFrame)


class RemoteController:
    def __init__(self):
        self._data_mutex = Lock()
        self._button_mutex = Lock()
        self._data_ready_event = Event()

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

        self._handler_thread = ThreadWrapper(self._background_thread, "RemoteControllerThread")

    def _button_pressed(self, idx):
        print('Button {} pressed'.format(idx))
        action = self._buttonActions[idx]
        if action:
            action()

    def reset(self):
        self.stop()
        with self._button_mutex:
            self._analogActions = []
            self._buttonActions = [lambda: None] * 32
            self._message = None
            self._missedKeepAlives = -1

    def _background_thread(self, ctx: ThreadContext):
        while not ctx.stop_requested:
            # Wait for data
            if self._data_ready_event.wait(0.1):
                self._data_ready_event.clear()

                if self._missedKeepAlives == -1:
                    self._controller_detected()
                self._missedKeepAlives = 0

                # copy data
                with self._data_mutex:
                    message = self._message

                # handle analog channels
                for handler in self._analogActions:
                    values = list(map(lambda x: message['analog'][x], handler['channels']))
                    handler['action'](values)

                # handle button presses
                for idx in range(len(self._buttonHandlers)):
                    with self._button_mutex:
                        self._buttonHandlers[idx].handle(message['buttons'][idx])
            else:
                # timeout
                if not self._handle_keep_alive_missed():
                    self._controller_disappeared()

    def _handle_keep_alive_missed(self):
        if self._missedKeepAlives > 5:
            self._missedKeepAlives = -1
            return False
        elif self._missedKeepAlives >= 0:
            print('RemoteController: Missed {}'.format(self._missedKeepAlives))
            self._missedKeepAlives += 1
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
        self._data_ready_event.set()

    def start(self):
        print('RemoteController: start')
        self._missedKeepAlives = -1
        self._data_ready_event.clear()
        self._handler_thread.start()

    def stop(self):
        print('RemoteController: stop')
        self._handler_thread.stop()

    def cleanup(self):
        print("RemoteController: exiting")
        self._handler_thread.exit()
        print("RemoteController: exited")


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
        self._remote_controller = RemoteController()
        self._remote_controller.on_controller_detected(self._on_controller_detected)
        self._remote_controller.on_controller_disappeared(self._on_controller_lost)

        self._drivetrain = DifferentialDrivetrain()
        self._ring_led = RingLed(self._robot)
        self._motor_ports = MotorPortHandler(self._robot)
        self._sensor_ports = SensorPortHandler(self._robot)

        revvy.register_remote_controller_handler(self._remote_controller.update)
        revvy.registerConnectionChangedHandler(self._on_connection_changed)
        # revvy.on_configuration_received(self._process_new_configuration)

        self._scripts = ScriptManager()

        self._status = self.StatusStartingUp

    def start(self):
        if self._status != self.StatusStartingUp:
            return

        print("Waiting for MCU")
        # TODO if we are getting stuck here (> ~3s), firmware is probably not valid
        retry = True
        while retry:
            retry = False
            try:
                self._robot.ping()
            # TODO do NACK responses raise exceptions?
            except (BrokenPipeError, IOError):
                retry = True

        # start reader thread (do it here to prevent unwanted reset)
        self._status_update_thread.start()

        # call reset to read port counts, types
        self._ring_led.reset()
        self._sensor_ports.reset()
        self._motor_ports.reset()

        # read versions
        hw = self._robot.get_hardware_version()
        fw = self._robot.get_firmware_version()
        sw = FRAMEWORK_VERSION

        print('Hardware: {}\nFirmware: {}\nFramework: {}'.format(hw, fw, sw))

        self._ble.set_hw_version(hw)
        self._ble.set_fw_version(fw)
        self._ble.set_sw_version(sw)

        self._ble.start()

        self.configure(None)

    def _update_thread(self, ctx: ThreadContext):
        while not ctx.stop_requested:
            data = self._reader.run()
            self._data_dispatcher.dispatch(data)
            time.sleep(0.1)

    def _on_connection_changed(self, is_connected):
        self._robot.set_bluetooth_connection_status(is_connected)
        if not is_connected:
            self.configure(None)

    def _on_controller_detected(self):
        if self._status == self.StatusConfigured:
            self._robot.set_master_status(self.status_led_controlled)

    def _on_controller_lost(self):
        if self._status == self.StatusConfigured:
            self._robot.set_master_status(self.status_led_configured)

    def _update_sensor(self, sid, value):
        print('Sensor {}: {}'.format(sid, value['converted']))
        self._ble.update_sensor(sid, value['raw'])

    def configure(self, config):
        if not config:
            config = self._default_configuration

        if config:
            # apply new configuration
            print("Applying new configuration")
            self._drivetrain.reset()
            self._remote_controller.reset()

            # set up status reader, data dispatcher
            self._reader.reset()
            self._data_dispatcher.reset()

            # set up motors
            for motor in self._motor_ports:
                motor_config = config.motors[motor.id]
                if motor_config == "Drivetrain_Left":
                    motor.configure("SpeedControlled")
                    self._drivetrain.add_left_motor(motor)
                elif motor_config == "Drivetrain_Right":
                    motor.configure("SpeedControlled")
                    self._drivetrain.add_right_motor(motor)
                else:
                    motor.configure(motor_config)

            # set up sensors
            for sensor in self._sensor_ports:
                if sensor.configure(config.sensors[sensor.id]):
                    sensor_name = 'sensor_{}'.format(sensor.id)
                    self._reader.add(sensor_name, lambda s=sensor: s.read())
                    self._data_dispatcher.add(sensor_name, lambda value, sid=sensor.id: self._update_sensor(sid, value))

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

            self._remote_controller.start()
            self._robot.set_master_status(self.status_led_configured)
            self._status = self.StatusConfigured
        else:
            print("Deinitialize robot")
            self._ring_led.set_scenario(RingLed.Off)
            self._remote_controller.reset()
            self._scripts.reset()
            self._robot.set_master_status(self.status_led_not_configured)
            self._drivetrain.reset()
            self._motor_ports.reset()
            self._sensor_ports.reset()
            self._reader.reset()
            self._remote_controller.stop()
            self._status = self.StatusNotConfigured

    def stop(self):
        # todo
        print("Stopping robot manager")
        self._remote_controller.cleanup()
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
        for key in self._handlers:
            with self._lock:
                if key in self._handlers:
                    self._handlers[key](data[key])


class StorageInterface:
    def store(self, data):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError


class FileStorage(StorageInterface):
    def __init__(self, filename):
        self._filename = filename

    def store(self, data):
        with open(self._filename, 'w') as f:
            f.write(data)

    def read(self):
        with open(self._filename, 'r') as f:
            return f.read()


class DeviceNameProvider:
    def __init__(self, storage: StorageInterface):
        self._storage = storage
        try:
            self._name = storage.read()
        except:
            self._name = 'Revvy_{}'.format(getserial().lstrip('0'))

    def get_device_name(self):
        return self._name

    def update_device_name(self, new_device_name):
        if new_device_name != self._name:
            self._name = new_device_name
            self._storage.store(self._name)


def startRevvy(interface: RevvyTransportInterface, config: RobotConfig = None):
    directory = os.path.dirname(__file__)
    print(directory)
    os.chdir(directory)
    dnp = DeviceNameProvider(FileStorage('./data/device_name'))
    device_name = Observable(dnp.get_device_name())

    def on_device_name_changed(new_name):
        print('Device name changed to {}'.format(new_name))
        dnp.update_device_name(new_name)

    device_name.subscribe(on_device_name_changed)
    long_message_handler = LongMessageHandler(LongMessageStorage("./data/"))
    ble = RevvyBLE(device_name, getserial(), long_message_handler)
    robot = RobotManager(interface, ble, config)

    try:
        robot.start()
        print("Press enter to exit")
        input()
    except KeyboardInterrupt:
        pass
    except EOFError:
        # Running as a service will end up here as stdin is empty.
        while True:
            time.sleep(1)
    finally:
        print('stopping')
        robot.stop()

    print('terminated.')
    sys.exit(1)
