#!/usr/bin/python3

import math
from threading import Lock, Event
from threading import Thread
import sys
import time
from ble_revvy import *
import functools

from rrrc_transport import *
from motor_controllers import *
from sensor_port_handlers import *
from fw_version import *


def empty_callback():
    pass


class NullHandler:
    def handle(self, value):
        pass


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


def _retry(fn, retries=5):
    status = False
    retry_num = 0
    while retry_num < retries and not status:
        status = fn()
        retry_num += 1

    return status


class RingLed:
    LED_RING_OFF = 0
    LED_RING_USER_FRAME = 1
    LED_RING_COLOR_WHEEL = 2

    def __init__(self, interface: RevvyControl):
        self._interface = interface
        self._ring_led_count = self._interface.ring_led_get_led_amount()

    def set_scenario(self, scenario):
        self._interface.ring_led_set_scenario(scenario)

    def upload_user_frame(self, frame):
        """
        :param frame: array of 12 RGB values
        """
        if len(frame) != self._ring_led_count:
            raise ValueError("Number of colors ({}) does not match LEDs ({})", len(frame), self._ring_led_count)

        self._interface.ring_led_set_user_frame(frame)

    def display_user_frame(self, frame):
        self.upload_user_frame(frame)
        self.set_scenario(self.LED_RING_USER_FRAME)


class RevvyApp:
    master_status_stopped = 0
    master_status_operational = 1
    master_status_operational_controlled = 2

    # index: logical number; value: physical number
    motorPortMap = [-1, 3, 4, 5, 2, 1, 0]

    # index: logical number; value: physical number
    sensorPortMap = [-1, 0, 1, 2, 3]

    mutex = Lock()
    event = Event()

    def __init__(self, interface):
        self._interface = RevvyControl(RevvyTransport(interface))
        self._buttons = [NullHandler()] * 32
        self._buttonData = [False] * 32
        self._analogInputs = [NullHandler()] * 10
        self._analogData = [128] * 10
        self._stop = False
        self._missedKeepAlives = 0
        self._is_connected = False
        self._ring_led = None
        self._motor_ports = None
        self._sensor_ports = None
        self._ble_interface = None
        self._status_update_step = 0

    def prepare(self):
        print("Prepare")
        try:
            self.set_master_status(self.master_status_stopped)
            hw = self._interface.get_hardware_version()
            fw = self._interface.get_firmware_version()
            sw = str(FRAMEWORK_VERSION)

            print('Hardware: {}\nFirmware: {}\nFramework: {}'.format(hw, fw, sw))

            self._ble_interface.set_hw_version(hw)
            self._ble_interface.set_fw_version(fw)
            self._ble_interface.set_sw_version(sw)

            self._ring_led = RingLed(self._interface)

            self._motor_ports = MotorPortHandler(self._interface)
            self._sensor_ports = SensorPortHandler(self._interface)

            print("Init done")
            return True
        except Exception as e:
            print("Prepare error: ", e)
            return False

    def set_master_status(self, status):
        if self._interface:
            self._interface.set_master_status(status)

    def set_ring_led_mode(self, mode):
        if self._ring_led:
            self._ring_led.set_scenario(mode)

    def _setup_robot(self):
        status = _retry(self.prepare)
        if status:
            self.set_master_status(self.master_status_stopped)
            status = _retry(self.init)
            if not status:
                print('Init failed')
        else:
            print('Prepare failed')

        return status

    def handle(self):
        comm_missing = True
        while not self._stop:
            try:
                restart = False
                status = _retry(self._setup_robot)

                if status:
                    print("Init ok")
                    self.set_master_status(self.master_status_operational)
                    self._update_ble_connection_indication()
                    self._missedKeepAlives = -1
                else:
                    print("Init failed")
                    restart = True

                self._status_update_step = 0

                while not self._stop and not restart:
                    if self.event.wait(0.1):
                        # print('Packet received')
                        if not self._stop:
                            self.event.clear()
                            self.mutex.acquire()
                            analog_data = self._analogData
                            button_data = self._buttonData
                            self.mutex.release()

                            self.handle_analog_values(analog_data)
                            self.handle_button(button_data)
                            if comm_missing:
                                self.set_master_status(self.master_status_operational_controlled)
                                comm_missing = False
                    else:
                        if not self._check_keep_alive():
                            if not comm_missing:
                                self.set_master_status(self.master_status_operational)
                                comm_missing = True
                            restart = True
                            time.sleep(1)

                    if not self._stop:
                        self.run()
                        self.update_status()
            except Exception as e:
                print("Oops! {}".format(e))

    def handle_button(self, data):
        for i in range(len(self._buttons)):
            self._buttons[i].handle(data[i])

    def handle_analog_values(self, analog_values):
        pass

    def _handle_keepalive(self, x):
        self._missedKeepAlives = 0
        self.event.set()

    def _check_keep_alive(self):
        if self._missedKeepAlives > 3:
            return False
        elif self._missedKeepAlives >= 0:
            self._missedKeepAlives += 1
        return True

    def _update_analog(self, channel, value):
        self.mutex.acquire()
        if channel < len(self._analogData):
            self._analogData[channel] = value
        self.mutex.release()

    def _update_button(self, channel, value):
        self.mutex.acquire()
        if channel < len(self._analogData):
            self._buttonData[channel] = value
        self.mutex.release()

    def _on_connection_changed(self, is_connected):
        if is_connected != self._is_connected:
            print('Connected' if is_connected else 'Disconnected')
            self._is_connected = is_connected
            self._update_ble_connection_indication()

    def _update_ble_connection_indication(self):
        if self._interface:
            if self._is_connected:
                self._interface.set_bluetooth_connection_status(1)
            else:
                self._interface.set_bluetooth_connection_status(0)

    def register(self, revvy):
        print('Registering callbacks')
        for i in range(10):
            revvy.registerAnalogHandler(i, functools.partial(self._update_analog, channel=i))
        for i in range(32):
            revvy.registerButtonHandler(i, functools.partial(self._update_button, channel=i))
        revvy.registerKeepAliveHandler(self._handle_keepalive)
        revvy.registerConnectionChangedHandler(self._on_connection_changed)
        self._ble_interface = revvy

    def init(self):
        return True

    def run(self):
        pass

    def update_status(self):
        """
        Periodically read device status, small pieces of data at a time
        """
        if self._status_update_step == 0:
            battery = self._interface.get_battery_status()
            self._ble_interface.updateMainBattery(battery['main'])
            self._ble_interface.updateMotorBattery(battery['motor'])
        else:
            self._interface.ping()

        if self._status_update_step == 1:
            self._status_update_step = 0
        else:
            self._status_update_step += 1


class RobotStateReader:
    def __init__(self):
        self._readers = {}
        self._data = {}
        pass

    def add(self, name, reader):
        self._readers[name] = reader
        self._data[name] = None

    def remove(self, name):
        try:
            del self._readers[name]
            del self._data[name]
            return True
        except KeyError:
            return False

    def read(self):
        for name in self._readers:
            self._data[name] = self._readers[name]()


def getserial():
    # Extract serial from cpuinfo file
    cpu_serial = "0000000000000000"
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line[0:6] == 'Serial':
                    cpu_serial = line.rstrip()[-16:]
                    break
    except:
        cpu_serial = "ERROR000000000"

    return cpu_serial


class DeviceNameProvider:
    def __init__(self, filename):
        self._filename = filename
        try:
            with open(filename, 'r') as f:
                self._name = f.readline()
        except FileNotFoundError:
            self._name = 'Revvy_{}'.format(getserial().lstrip('0'))

    def get_device_name(self):
        return self._name

    def update_device_name(self, new_device_name):
        if new_device_name != self._name:
            self._name = new_device_name
            self._store()

    def _store(self):
        with open(self._filename, 'w') as f:
            f.write(self._name)


def startRevvy(app):
    dnp = DeviceNameProvider('device_name.txt')
    device_name = Observable(dnp.get_device_name())

    def on_device_name_changed(new_name):
        print('Device name changed to {}'.format(new_name))
        dnp.update_device_name(new_name)

    device_name.subscribe(on_device_name_changed)

    revvy = RevvyBLE(device_name, getserial())
    app.register(revvy)

    t1 = Thread(target=app.handle, args=())
    t1.start()

    try:
        revvy.start()
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
        revvy.stop()

        app._stop = True
        app.event.set()
        t1.join()

    print('terminated.')
    sys.exit(1)
