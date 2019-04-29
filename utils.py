#!/usr/bin/python3

import math
import rrrc_control as rrrc_control
from threading import Lock, Event
from threading import Thread
import sys
import struct
import time
from ble_revvy import *
import functools


def empty_callback():
    pass


class NullHandler:
    def handle(self, value):
        pass


def buttonValue(buttons, pos):
    if (buttons & (1 << pos)) != 0:
        return 1
    else:
        return 0


def clip(x, min_x, max_x):
    if x < min_x:
        return min_x
    if x > max_x:
        return max_x
    return x


def map_values(x, minx, maxx, miny, maxy):
    inFs = maxx - minx
    outFs = maxy - miny
    return (x - minx) * (outFs / inFs) + miny


def differentialControl(r, angle):
    v = 0.4 * r * math.cos(angle + math.pi / 2) / 100
    w = 0.4 * r * math.sin(angle + math.pi / 2) / 100

    sr = +(v + w)
    sl = -(v - w)
    return (sl, sr)


def max(a, b):
    if a > b:
        return a
    else:
        return b


def min(a, b):
    if a < b:
        return a
    else:
        return b


def getserial():
    # Extract serial from cpuinfo file
    cpuserial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                cpuserial = line.rstrip()[-16:]
        f.close()
    except:
        cpuserial = "ERROR000000000"

    return cpuserial


def _retry(fn, retries=5):
    status = False
    retry_num = 1
    while retry_num <= retries and not status:
        status = fn()
        retry_num = retry_num + 1

    return status


class RevvyApp:
    LED_RING_OFF = 0
    LED_RING_COLOR_WHEEL = 6

    _myrobot = None
    # index: logical number; value: physical number
    motorPortMap = [-1, 3, 4, 5, 2, 1, 0]

    # index: logical number; value: physical number
    sensorPortMap = [-1, 0, 1, 2, 3]

    mutex = Lock()
    event = Event()

    def __init__(self):
        self._buttons = [NullHandler()] * 32
        self._buttonData = [False] * 32
        self._analogInputs = [NullHandler()] * 10
        self._analogData = [128] * 10
        self._stop = False
        self._missedKeepAlives = 0
        self._isConnected = False

    def prepare(self):
        print("Prepare")
        try:
            self._myrobot = rrrc_control.rrrc_control()

            print(self._myrobot.sensors)
            print(self._myrobot.motors)
            return True
        except Exception as e:
            print("Prepare error: ", e)
            return False

    def indicateStopped(self):
        if self._myrobot:
            self._myrobot.indicator_set_led(3, 0x10, 0, 0)

    def indicateCommFailure(self):
        if self._myrobot:
            self._myrobot.indicator_set_led(3, 0x10, 0x05, 0)

    def indicateWorking(self):
        if self._myrobot:
            self._myrobot.indicator_set_led(3, 0, 0x10, 0)

    def setLedRingMode(self, mode):
        if self._myrobot:
            self._myrobot.ring_led_set_scenario(mode)

    def deinitBrain(self):
        print("deInit")
        if self._myrobot:
            self.indicateStopped()
            self.setLedRingMode(self.LED_RING_OFF)
            self._myrobot.indicator_set_led(2, 0, 0, 0)

            # robot deInit
            try:
                for i in range(0, 6):
                    status = self._myrobot.motor_set_type(self.motorPortMap[i + 1],
                                                          self._myrobot.motors["MOTOR_NO_SET"])
                for i in range(0, 4):
                    status = self._myrobot.sensor_set_type(self.sensorPortMap[i + 1], self._myrobot.sensors["NO_SET"])
            except:
                pass

        _myrobot = None

    def setMotorPid(self, motor, pid):
        if pid is None:
            return True
        else:
            (p, i, d, ll, ul) = pid
            pid_config = bytearray(struct.pack(">{}".format("f" * 5), p, i, d, ll, ul))
            return self._myrobot.motor_set_config(motor, pid_config)

    def handleButton(self, data):
        for i in range(len(self._buttons)):
            self._buttons[i].handle(data[i])

    def _setupRobot(self):
        status = _retry(self.prepare)
        if status:
            self.indicateStopped()
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
                status = _retry(self._setupRobot)

                if status:
                    print("Init ok")
                    self.indicateCommFailure()
                    self._updateConnectionIndication()
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
                                self.indicateWorking()
                                comm_missing = False
                    else:
                        if not self._checkKeepAlive():
                            if not comm_missing:
                                self.indicateCommFailure()
                                comm_missing = True
                            restart = True

                    if not self._stop:
                        self.run()
            except Exception as e:
                print("Oops! {}".format(e))
            finally:
                self.deinitBrain()

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
        if is_connected != self._isConnected:
            self._isConnected = is_connected
            self._updateConnectionIndication()

    def _updateConnectionIndication(self):
        if self._myrobot:
            if self._isConnected:
                self._myrobot.indicator_set_led(2, 0, 0x10, 0x10)
            else:
                self._myrobot.indicator_set_led(2, 0, 0, 0)

    def register(self, revvy):
        print('Registering callbacks')
        for i in range(10):
            revvy.registerAnalogHandler(i, functools.partial(self._updateAnalog, channel=i))
        for i in range(32):
            revvy.registerButtonHandler(i, functools.partial(self._updateButton, channel=i))
        revvy.registerKeepAliveHandler(self._handleKeepAlive)
        revvy.registerConnectionChangedHandler(self._onConnectionChanged)

    def init(self):
        pass

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
