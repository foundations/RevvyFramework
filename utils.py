#!/usr/bin/python3

import math
from threading import Lock, Event
from threading import Thread
import sys
import time
import traceback
from typing import Any

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

    def add_left_motor(self, motor):
        self._left_motors.append(motor)

    def add_right_motor(self, motor):
        self._right_motors.append(motor)

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
        self._ring_led_count = self._interface.ring_led_get_led_amount()
        self._current_scenario = self.Off

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
        if len(frame) != self._ring_led_count:
            raise ValueError("Number of colors ({}) does not match LEDs ({})", len(frame), self._ring_led_count)

        self._interface.ring_led_set_user_frame(frame)

    def display_user_frame(self, frame):
        self.upload_user_frame(frame)
        self.set_scenario(self.UserFrame)


class RemoteController:
    def __init__(self):
        self._mutex = Lock()
        self._enabled_event = Event()
        self._data_ready_event = Event()

        self._analogActions = []
        self._buttonActions = [lambda: None] * 32
        self._buttonHandlers = [None] * 32
        self._controller_detected = lambda: None
        self._controller_disappeared = lambda: None
        self._stop = False

        self._message = None
        self._missedKeepAlives = -1

        for i in range(len(self._buttonHandlers)):
            self._buttonHandlers[i] = EdgeTrigger()
            self._buttonHandlers[i].onRisingEdge(lambda idx=i: self._buttonActions[idx]())

        self._handler_thread = Thread(target=self._background_thread, args=())
        self._handler_thread.start()

    def _background_thread(self):
        while not self._stop:
            # Only run if we're enabled
            self._enabled_event.wait()

            # Wait for data
            if self._data_ready_event.wait(0.1):
                self._data_ready_event.clear()

                if self._missedKeepAlives == -1:
                    self._controller_detected()
                self._missedKeepAlives = 0

                # copy data
                with self._mutex:
                    message = self._message

                # handle analog channels
                for handler in self._analogActions:
                    values = list(map(lambda x: message['analog'][x], handler['channels']))
                    handler['action'](values)

                # handle button presses
                for idx in range(len(self._buttonHandlers)):
                    with self._mutex:
                        self._buttonHandlers[idx].handle(message['buttons'][idx])
            else:
                # timeout
                if not self._handle_keep_alive_missed():
                    self._controller_disappeared()

    def _handle_keep_alive_missed(self):
        if self._missedKeepAlives > 3:
            self._missedKeepAlives = -1
            return False
        elif self._missedKeepAlives >= 0:
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
        with self._mutex:
            self._message = message
        self._data_ready_event.set()

    def start(self):
        self._missedKeepAlives = -1
        self._enabled_event.set()

    def stop(self):
        self._enabled_event.clear()

    def cleanup(self):
        self._stop = True
        self._enabled_event.set()
        self._handler_thread.join()


class RevvyApp:
    StatusStopped = 0
    StatusOperational = 1
    StatusOperationalControlled = 2

    def __init__(self, interface):
        self._robot = RevvyControl(RevvyTransport(interface))
        self._remote_controller = RemoteController()
        self._stop = False
        self._is_connected = False
        self._ring_led = None
        self._motor_ports = MotorPorts(MotorPortHandler(self._robot))
        self._sensor_ports = SensorPorts(SensorPortHandler(self._robot))
        self._ble_interface = None
        self._read_thread_enabled = Event()

        # register default status update steps
        self._reader = RobotStateReader(self._robot.ping)
        self._reader.add('battery', self._robot.get_battery_status)

        self._remote_controller.on_controller_detected(
            lambda: self._robot.set_master_status(self.StatusOperationalControlled))
        self._remote_controller.on_controller_disappeared(lambda: self._robot.set_master_status(self.StatusOperational))

        self._data_dispatcher = DataDispatcher()
        self._data_dispatcher.add('battery', self._update_battery)

        self._reader_thread = Thread(target=self.read_status_thread, args=())
        self._reader_thread.start()

    def _update_battery(self, battery):
        self._ble_interface.updateMainBattery(battery['main'])
        self._ble_interface.updateMotorBattery(battery['motor'])

    def prepare(self):
        print("Prepare")
        # force reset
        self._read_thread_enabled.clear()
        self._robot.ping()
        time.sleep(1)
        self._read_thread_enabled.set()

        # signal status
        self._robot.set_master_status(self.StatusStopped)

        # read versions
        hw = self._robot.get_hardware_version()
        fw = self._robot.get_firmware_version()
        sw = FRAMEWORK_VERSION

        print('Hardware: {}\nFirmware: {}\nFramework: {}'.format(hw, fw, sw))

        self._ble_interface.set_hw_version(hw)
        self._ble_interface.set_fw_version(fw)
        self._ble_interface.set_sw_version(sw)

        self._ring_led = RingLed(self._robot)

        self._motor_ports.reset()
        self._sensor_ports.reset()
        return True

    def _setup_robot(self):
        self.prepare()
        self._robot.set_master_status(self.StatusStopped)
        self.init()

    def read_status_thread(self):
        while not self._stop:
            self._read_thread_enabled.wait()
            try:
                self._reader.read()
                self._data_dispatcher.dispatch(self._reader)
                time.sleep(0.1)
            except:
                print(traceback.format_exc())

    def _on_connection_changed(self, is_connected):
        if is_connected != self._is_connected:
            print('Connected' if is_connected else 'Disconnected')
            self._is_connected = is_connected
        self._robot.set_bluetooth_connection_status(self._is_connected)

    def _handle_controller_message(self, message):
        self._remote_controller.update(message)

    def register(self, revvy: RevvyBLE):
        revvy.register_remote_controller_handler(self._handle_controller_message)
        revvy.registerConnectionChangedHandler(self._on_connection_changed)
        self._ble_interface = revvy

    def init(self):
        pass

    def start(self):
        status = _retry(self._setup_robot)

        if status:
            print("Init ok")
            self._robot.set_master_status(self.StatusOperational)
            self._robot.set_bluetooth_connection_status(self._is_connected)
        else:
            print("Init failed")

        self._remote_controller.start()
        self._ble_interface.start()

    def stop(self):
        self._stop = True
        self._remote_controller.cleanup()
        self._read_thread_enabled.set()
        self._reader_thread.join()
        self._ble_interface.stop()


class RobotStateReader:
    def __init__(self, default_action=lambda: None):
        self._readers = {}
        self._data = {}
        self._reader_lock = Lock()
        self._data_lock = Lock()
        self._default_action = default_action

    def __getitem__(self, name: str) -> Any:
        with self._data_lock:
            return self._data[name]

    def __iter__(self):
        return self._data.__iter__

    def add(self, name, reader):
        with self._reader_lock:
            self._readers[name] = reader
            self._data[name] = None

    def remove(self, name):
        with self._reader_lock, self._data_lock:
            try:
                del self._readers[name]
                del self._data[name]
                return True
            except KeyError:
                return False

    def read(self):
        with self._reader_lock:
            if len(self._readers) == 0:
                self._default_action()
            else:
                for name in self._readers:
                    value = self._readers[name]()
                    with self._data_lock:
                        self._data[name] = value


class DataDispatcher:
    def __init__(self):
        self._handlers = {}
        self._lock = Lock()

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


def startRevvy(app: RevvyApp):
    dnp = DeviceNameProvider(FileStorage('device_name.txt'))
    device_name = Observable(dnp.get_device_name())

    def on_device_name_changed(new_name):
        print('Device name changed to {}'.format(new_name))
        dnp.update_device_name(new_name)

    device_name.subscribe(on_device_name_changed)

    revvy = RevvyBLE(device_name, getserial())
    app.register(revvy)

    try:
        app.start()
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
        app.stop()

    print('terminated.')
    sys.exit(1)
