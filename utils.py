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

def emptyCallback():
    pass

class EdgeTrigger:
    def __init__(self):
        self._risingEdge = emptyCallback
        self._fallingEdge = emptyCallback
        self._previous = 0

    def onRisingEdge(self, l):
        self._risingEdge = l

    def onFallingEdge(self, l):
        self._fallingEdge = l

    def handle(self, value):
        if value > self._previous:
            self._risingEdge()
        elif value < self._previous:
            self._fallingEdge()
        self._previous = value

class LevelTrigger:
    def __init__(self):
        self._high = emptyCallback
        self._low = emptyCallback

    def onHigh(self, l):
        self._high = l

    def onLow(self, l):
        self._low = l

    def handle(self, value):
        if value > 0:
            self._high()
        else:
            self._low()

class ToggleButton:
    def __init__(self):
        self._onEnabled = emptyCallback
        self._onDisabled = emptyCallback
        self._edgeDetector = EdgeTrigger()
        self._edgeDetector.onRisingEdge(self.toggle)
        self._isEnabled = False

    def toggle(self):
        self._isEnabled = not self._isEnabled
        if self._isEnabled:
            self._onEnabled()
        else:
            self._onDisabled()

    def onEnabled(self, l):
        self._onEnabled = l

    def onDisabled(self, l):
        self._onDisabled = l

    def handle(self, value):
        self._edgeDetector.handle(value)

class NullHandler:
    def handle(slef, value):
        pass

def buttonValue(buttons, pos):
    if ((buttons & (1 << pos)) != 0):
        return 1
    else:
        return 0

def clip(x, min, max):
    if (x < min): return min
    if (x > max): return max
    return x

def map_values(x, minx, maxx, miny, maxy):
    inFs  = maxx - minx
    outFs = maxy - miny
    return (x - minx) * (outFs / inFs) + miny

def differentialControl(r, angle):
    v = 0.4 * r * math.cos(angle + math.pi/2) / 100
    w = 0.4 * r * math.sin(angle + math.pi/2) / 100

    sr = +(v - w)
    sl = -(v + w)
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

class RevvyApp:

    _myrobot = None
    # index: logical number; value: physical number
    motorPortMap = [-1, 3, 4, 5, 2, 1, 0]

    # index: logical number; value: physical number
    sensorPortMap = [-1, 0, 1, 2, 3]
    
    mutex = Lock()
    event = Event()

    def __init__(self):
        self._buttons      = [ NullHandler() ] * 32
        self._buttonData   = [ False ] * 32
        self._analogInputs = [ NullHandler() ] * 10
        self._analogData   = [ 128 ] * 10
        self._stop = False

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

    def indicatorRed(self):
        if self._myrobot is not None:
            self._myrobot.indicator_set_led(3, 0x10, 0, 0)

    def indicatorGreen(self):
        if self._myrobot is not None:
            self._myrobot.indicator_set_led(3, 0, 0x10, 0)

    def deinitBrain(self):
        print("deInit")
        if self._myrobot is not None:
            self.indicatorRed()

            # robot deInit
            try:
                for i in range(0, 6):
                    status = self._myrobot.motor_set_type(self.motorPortMap[i + 1], self._myrobot.motors["MOTOR_NO_SET"])
                for i in range(0, 4):
                    status = self._myrobot.sensor_set_type(self.sensorPortMap[i + 1], self._myrobot.sensors["NO_SET"])
            except:
                pass

        _myrobot = None

    def setMotorPid(self, motor, pid):
        if pid == None:
            return True
        else:
            (p, i, d, ll, ul) = pid
            pidConfig = bytearray(struct.pack(">" + 5 * "f", p, i, d, ll, ul))
            return self._myrobot.motor_set_config(motor, pidConfig)

    def handleButton(self, data):
        for i in len(self._buttons):
            self._buttons[i].handle(data[i])

    def commandReceived(self, data):
        self.mutex.acquire()
        self.command = data[1:4]
        self.mutex.release()
        self.event.set()

    def handle(self):
        while(self._stop == False):
            try:
                status = False
                retries = 5
                retryNum = 1
                while retryNum <= retries and not status:
                    print("Prepare {}".format(retryNum))
                    status = self.prepare()
                    if status:
                        self.indicatorRed()
                    else:
                        print('Prepare failed')
                    retryNum = retryNum + 1

                status = False
                retryNum = 1
                while retryNum <= retries and not status:
                    print("Init {}".format(retryNum))
                    status = self.init()
                    if not status:
                        print('Init failed')
                    retryNum = retryNum + 1

                if not status:
                    print("Init failed")
                else:
                    print("Init ok")
                    self.indicatorGreen()

                while(self._stop == False):
                    if self.event.wait(0.1):
                        if (self._stop == False):
                            self.event.clear()
                            self.mutex.acquire()
                            analogData = self._analogData
                            buttonData = self._buttonData
                            self.mutex.release()

                            self.handleAnalogValues(analogData)
                            self.handleButton(buttonData)

                    if (self._stop == False):
                        self.run()
            except Exception as e:
                print("Oops! {}".format(e))
            finally:
                self.deinitBrain()

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

    def register(self, revvy):
        for i in range(10):
            revvy.registerAnalogHandler(i, lambda x: self._updateAnalog(i, x))
        for i in range(32):
            revvy.registerButtonHandler(i, lambda x: self._updateButton(i, x))
        revvy.registerKeepAliveHandler(lambda x: self.event.set())

    def init(self):
        pass

    def run(self):
        pass

def startRevvy(app):
    t1 = Thread(target=app.handle, args=())
    t1.start()
    serviceName = "Revvy_%s" % getserial().lstrip('0')
    revvy = RevvyBLE(serviceName)
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
        print ('stopping')
        revvy.stop()

        app._stop = True
        app.event.set()
        t1.join()

    print ('terminated.')
    sys.exit(1)