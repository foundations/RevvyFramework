#!/usr/bin/python3
import array

import pybleno
from functools import reduce
from pybleno import Characteristic


# Device communication related services
class BrainToMobileCharacteristic(pybleno.Characteristic):
    def __init__(self):
        super().__init__({
            'uuid':       'd59bb321-7218-4fb9-abac-2f6814f31a4d'.replace('-', ''),
            'properties': ['read', 'write'],
            'value':      None
        })


class MobileToBrainCharacteristic(pybleno.Characteristic):
    def __init__(self):
        super().__init__({
            'uuid':       'b81239d9-260b-4945-bcfe-8b1ef1fc2879'.replace('-', ''),
            'properties': ['read', 'write'],
            'value':      None
        })


class LongMessageService(pybleno.BlenoPrimaryService):
    def __init__(self):
        pybleno.BlenoPrimaryService.__init__(self, {
            'uuid':            '97148a03-5b9d-11e9-8647-d663bd873d93'.replace("-", ""),
            'characteristics': [
                BrainToMobileCharacteristic(),
                MobileToBrainCharacteristic()
            ]})


class MobileToBrainFunctionCharacteristic(pybleno.Characteristic):
    def __init__(self, uuid, minLength, maxLength, description, callback):
        self._callbackFn = callback
        self._minLength = minLength
        self._maxLength = maxLength
        super().__init__({
            'uuid':        uuid.replace('-', ''),
            'properties':  ['write'],
            'value':       None,
            'descriptors': [
                pybleno.Descriptor({
                    'uuid':  '2901',
                    'value': description
                }),
            ]
        })

    def onWriteRequest(self, data, offset, withoutResponse, callback):
        if offset:
            callback(Characteristic.RESULT_ATTR_NOT_LONG)

        if len(data) < self._minLength or len(data) > self._maxLength:
            callback(pybleno.Characteristic.RESULT_INVALID_ATTRIBUTE_LENGTH)
        elif self._callbackFn(data):
            callback(pybleno.Characteristic.RESULT_SUCCESS)
        else:
            callback(pybleno.Characteristic.RESULT_UNLIKELY_ERROR)


class BrainToMobileFunctionCharacteristic(pybleno.Characteristic):
    def __init__(self, description, uuid):
        self._value = None
        super().__init__({
            'uuid':        uuid.replace('-', ''),
            'properties':  ['read', 'notify'],
            'value':       None,
            'descriptors': [
                pybleno.Descriptor({
                    'uuid':  '2901',
                    'value': description
                }),
            ]
        })

    def onReadRequest(self, offset, callback):
        if offset:
            callback(Characteristic.RESULT_ATTR_NOT_LONG)
        else:
            callback(Characteristic.RESULT_SUCCESS, self._value)

    def onSubscribe(self, maxValueSize, updateValueCallback):
        self._updateValueCallback = updateValueCallback

    def onUnsubscribe(self):
        self._updateValueCallback = None

    def updateValue(self, value):
        self._value = value

        if self._updateValueCallback:
            self._updateValueCallback(self._value)


class LiveMessageService(pybleno.BlenoPrimaryService):
    def __init__(self):
        def emptyFn(x): pass

        self._keepAliveHandler = emptyFn
        self._buttonHandlers = [emptyFn] * 32
        self._analogHandlers = [emptyFn] * 10

        print('Created {} button handlers'.format(len(self._buttonHandlers)))
        print('Created {} analog handlers'.format(len(self._analogHandlers)))

        super().__init__({
            'uuid':            'd2d5558c-5b9d-11e9-8647-d663bd873d93'.replace("-", ""),
            'characteristics': [
                MobileToBrainFunctionCharacteristic('7486bec3-bb6b-4abd-a9ca-20adc281a0a4', 20, 20, 'simpleControl',
                                                    self.simpleControlCallback),
            ]})

    def registerKeepAliveHandler(self, callback):
        self._keepAliveHandler = callback

    def registerAnalogHandler(self, channelId, callback):
        if channelId < len(self._analogHandlers):
            self._analogHandlers[channelId] = callback
        else:
            print('Incorrect analog handler id {}'.format(channelId))

    def registerButtonHandler(self, channelId, callback):
        if channelId < len(self._buttonHandlers):
            self._buttonHandlers[channelId] = callback
        else:
            print('Incorrect button handler id {}'.format(channelId))

    def _fireKeepAliveHandler(self, counter):
        self._keepAliveHandler(counter)

    def _fireButtonHandler(self, idx, state):
        if idx < len(self._buttonHandlers):
            self._buttonHandlers[idx](value=state)

    def _fireAnalogHandler(self, idx, state):
        if idx < len(self._analogHandlers):
            self._analogHandlers[idx](value=state)

    def simpleControlCallback(self, data):
        # print(repr(data))
        counter = data[0]
        analogValues = data[1:11]

        def nthBit(byte, bit):
            return (byte & (1 << bit)) != 0

        def expandByte(byte):
            return [nthBit(byte, x) for x in range(8)]

        buttonValues = reduce(lambda x, y: x + y, map(expandByte, data[11:15]), [])

        for i in range(len(analogValues)):
            self._fireAnalogHandler(i, analogValues[i])

        for i in range(len(buttonValues)):
            self._fireButtonHandler(i, buttonValues[i])

        self._fireKeepAliveHandler(counter)
        return True


# Device Information Service
class ReadOnlyCharacteristic(pybleno.Characteristic):
    def __init__(self, uuid, value):
        super().__init__({
            'uuid':       uuid,
            'properties': ['read'],
            'value':      value
        })


class SerialNumberCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, serial):
        super().__init__('2A25', serial)


class ManufacturerNameCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, name):
        super().__init__('2A29', name)


class ModelNumberCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, modelNo):
        super().__init__('2A24', modelNo)


class HardwareRevisionCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, version):
        super().__init__('2A27', version)


class SoftwareRevisionCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, version):
        super().__init__('2A28', version)


class FirmwareRevisionCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, version):
        super().__init__('2A26', version)


class SystemIdCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, id):
        super().__init__('2A23', id)


class RevvyDeviceInforrmationService(pybleno.BlenoPrimaryService):
    def __init__(self, deviceName):
        super().__init__({
            'uuid':            '180A',
            'characteristics': [
                SerialNumberCharacteristic('12345'),
                ManufacturerNameCharacteristic('RevolutionRobotics'),
                ModelNumberCharacteristic("RevvyAlpha"),
                HardwareRevisionCharacteristic("v1.0.0"),
                SoftwareRevisionCharacteristic("v1.0.0"),
                FirmwareRevisionCharacteristic("v1.0.0"),
                SystemIdCharacteristic(deviceName),
            ]})


# BLE SIG battery service, that is differentiated via Characteristic Presentation Format
class BatteryLevelCharacteristic(pybleno.Characteristic):
    def __init__(self, description, id):
        super().__init__({
            'uuid':        '2A19',
            'properties':  ['read', 'notify'],
            'value':       None,
            'descriptors': [
                pybleno.Descriptor({
                    'uuid':  '2901',
                    'value': description
                }),
                pybleno.Descriptor({
                    'uuid':  '2904',
                    'value': array.array('B', [0x04, 0x01, 0x27, 0xAD, 0x02, 0x00, id])
                    # unsigned 8 bit, pybleno.Descriptor defined by RR
                })
            ]
        })


class BatteryService(pybleno.BlenoPrimaryService):
    def __init__(self, description, id):
        super().__init__({
            'uuid':            '180F',
            'characteristics': [
                BatteryLevelCharacteristic(description, id)
            ]})


# Custom battery service that contains 2 characteristics
class CustomBatteryLevelCharacteristic(pybleno.Characteristic):
    def __init__(self, uuid, description):
        super().__init__({
            'uuid':        uuid.replace('-', ''),
            'properties':  ['read', 'notify'],
            'value':       None,  # needs to be None because characteristic is not constant value
            'descriptors': [
                pybleno.Descriptor({
                    'uuid':  '2901',
                    'value': description
                })
            ]
        })

        self._updateValueCallback = None
        self._value = 99  # initial value only

    def onReadRequest(self, offset, callback):
        if offset:
            callback(Characteristic.RESULT_ATTR_NOT_LONG)
        else:
            callback(Characteristic.RESULT_SUCCESS, self._value)

    def onSubscribe(self, maxValueSize, updateValueCallback):
        self._updateValueCallback = updateValueCallback

    def onUnsubscribe(self):
        self._updateValueCallback = None

    def updateValue(self, value):
        self._value = value

        if self._updateValueCallback:
            self._updateValueCallback(self._value)


class CustomBatteryService(pybleno.BlenoPrimaryService):
    def __init__(self):
        self._mainBattery = CustomBatteryLevelCharacteristic('2A19', 'Main battery percentage')
        self._motorBattery = CustomBatteryLevelCharacteristic('00002a19-0000-1000-8000-00805f9b34fa',
                                                              'Motor battery percentage')

        super().__init__({
            'uuid':            '180F',
            'characteristics': [
                self._mainBattery,
                self._motorBattery
            ]
        })

    def updateMainBatteryValue(self, value):
        self._mainBattery.updateValue(value)

    def updateMotorBatteryValue(self, value):
        self._motorBattery.updateValue(value)


class RevvyBLE:
    def __init__(self, deviceName):
        print('Initializing {}'.format(deviceName))
        self._deviceName = deviceName

        self._deviceInformationService = RevvyDeviceInforrmationService(deviceName)
        self._batteryService = CustomBatteryService()
        self._liveMessageService = LiveMessageService()
        self._longMessageService = LongMessageService()

        self._services = [
            self._liveMessageService,
            self._longMessageService,
            self._deviceInformationService,
            self._batteryService
        ]
        self._advertisedUuids = [
            self._liveMessageService.uuid
        ]

        self._bleno = pybleno.Bleno()
        self._bleno.on('stateChange', self.onStateChange)
        self._bleno.on('advertisingStart', self.onAdvertisingStart)

    def onStateChange(self, state):
        print('on -> stateChange: ' + state);

        if (state == 'poweredOn'):
            self._bleno.startAdvertising(self._deviceName, self._advertisedUuids)
        else:
            self._bleno.stopAdvertising()

    def onAdvertisingStart(self, error):
        print('on -> advertisingStart: ' + ('error ' + str(error) if error else 'success'))

        if not error:
            print('setServices')

            def on_setServiceError(error):
                print('setServices: %s' % ('error ' + str(error) if error else 'success'))

            self._bleno.setServices(self._services, on_setServiceError)

    def registerConnectionChangedHandler(self, callback):
        self._bleno.on('accept', lambda x: callback(True))
        self._bleno.on('disconnected', lambda x: callback(False))

    def start(self):
        self._bleno.start()

    def stop(self):
        self._bleno.stopAdvertising()
        self._bleno.disconnect()

    def updateMainBattery(self, level):
        self._batteryService.updateMainBatteryValue(level)

    def updateMotorBattery(self, level):
        self._batteryService.updateMotorBatteryValue(level)

    def registerButtonHandler(self, channelIdx, callback):
        self._liveMessageService.registerButtonHandler(channelIdx, callback)

    def registerAnalogHandler(self, channelIdx, callback):
        self._liveMessageService.registerAnalogHandler(channelIdx, callback)

    def registerKeepAliveHandler(self, callback):
        self._liveMessageService.registerKeepAliveHandler(callback)
