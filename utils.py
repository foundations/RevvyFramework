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


def empty_callback():
    pass


class NullHandler:
    def handle(self, value):
        pass


def differentialControl(r, angle):
    v = 0.4 * r * math.cos(angle + math.pi / 2) / 100
    w = 0.4 * r * math.sin(angle + math.pi / 2) / 100

    sr = +(v + w)
    sl = -(v - w)
    return sl, sr


def getserial():
    # Extract serial from cpuinfo file
    cpu_serial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                cpu_serial = line.rstrip()[-16:]
        f.close()
    except:
        cpu_serial = "ERROR000000000"

    return cpu_serial


def _retry(fn, retries=5):
    status = False
    retry_num = 1
    while retry_num <= retries and not status:
        status = fn()
        retry_num = retry_num + 1

    return status


class RingLed:
    LED_RING_OFF = 0
    LED_RING_COLOR_WHEEL = 2

    def __init__(self, interface: RevvyControl):
        self._interface = interface

    def set_scenario(self, scenario):
        self._interface.ring_led_set_scenario(scenario)


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

    def prepare(self):
        print("Prepare")
        try:
            self.set_master_status(self.master_status_stopped)
            hw = self._interface.get_hardware_version()
            fw = self._interface.get_firmware_version()
            motor_port_amount = self._interface.get_motor_port_amount()
            motor_port_types = self._interface.get_motor_port_types()
            sensor_port_amount = self._interface.get_sensor_port_amount()
            sensor_port_types = self._interface.get_sensor_port_types()
            print("Hardware Version: {}\nFirmware Version: {}".format(hw, fw))
            print("Motor ports: {}\nSensor ports: {}".format(motor_port_amount, sensor_port_amount))
            print("Motor port types:\n{}".format(motor_port_types))
            print("Sensor port types:\n{}".format(sensor_port_types))

            self._ring_led = RingLed(self._interface)
            self._ring_led.set_scenario(RingLed.LED_RING_COLOR_WHEEL)

            handler = MotorPortHandler(self._interface)
            spcm = handler.configure(4, 'SpeedControlled')
            spcm.set_speed(20)

            print("Init done")
            return True
        except Exception as e:
            print("Prepare error: ", e)
            raise e
            return False

    def set_master_status(self, status):
        if self._interface:
            self._interface.set_master_status(status)

    def setLedRingMode(self, mode):
        if self._ring_led:
            self._ring_led.set_scenario(mode)

    def handleButton(self, data):
        for i in range(len(self._buttons)):
            self._buttons[i].handle(data[i])

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

                while not self._stop and not restart:
                    if self.event.wait(0.1):
                        # print('Packet received')
                        if not self._stop:
                            self.event.clear()
                            self.mutex.acquire()
                            analog_data = self._analogData
                            button_data = self._buttonData
                            self.mutex.release()

                            self.handleAnalogValues(analog_data)
                            self.handleButton(button_data)
                            if comm_missing:
                                self.set_master_status(self.master_status_operational_controlled)
                                comm_missing = False
                    else:
                        if not self._checkKeepAlive():
                            if not comm_missing:
                                self.set_master_status(self.master_status_operational)
                                comm_missing = True
                            restart = True

                    if not self._stop:
                        self.run()
                        self._interface.ping()
            except Exception as e:
                print("Oops! {}".format(e))
                raise e

    def handleAnalogValues(self, analog_values):
        pass

    def _handleKeepAlive(self, x):
        self._missedKeepAlives = 0
        self.event.set()

    def _checkKeepAlive(self):
        if self._missedKeepAlives > 3:
            return False
        elif self._missedKeepAlives >= 0:
            self._missedKeepAlives = self._missedKeepAlives + 1
        return True

    def _updateAnalog(self, channel, value):
        self.mutex.acquire()
        if channel < len(self._analogData):
            self._analogData[channel] = value
        self.mutex.release()

    def _updateButton(self, channel, value):
        self.mutex.acquire()
        if channel < len(self._analogData):
            self._buttonData[channel] = value
        self.mutex.release()

    def _onConnectionChanged(self, is_connected):
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
            revvy.registerAnalogHandler(i, functools.partial(self._updateAnalog, channel=i))
        for i in range(32):
            revvy.registerButtonHandler(i, functools.partial(self._updateButton, channel=i))
        revvy.registerKeepAliveHandler(self._handleKeepAlive)
        revvy.registerConnectionChangedHandler(self._onConnectionChanged)

    def init(self):
        return True

    def run(self):
        pass


def startRevvy(app):
    t1 = Thread(target=app.handle, args=())
    t1.start()
    service_name = 'Revvy_{}'.format(getserial().lstrip('0'))
    revvy = RevvyBLE(service_name)
    app.register(revvy)

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
