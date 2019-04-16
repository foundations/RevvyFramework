#!/usr/bin/python3

import pybleno
import urllib.parse
import json

# constants
HM_10_UART_SERIVCE = '0000FFE0-0000-1000-8000-00805F9B34FB'.replace("-", "")
HM_10_UART_CHARACTERISTIC = '0000FFE1-0000-1000-8000-00805F9B34FB'.replace("-", "")
class UartCharacteristic(pybleno.Characteristic):
    def __init__(self, callback):
        pybleno.Characteristic.__init__(self, {
            'uuid': HM_10_UART_CHARACTERISTIC,
            'properties': ['write', 'write-without-response', 'notify'],
            'value': None,
          })
        self._rawData = bytearray()
        self._blockyList = []
        self._value = bytearray()
        self._updateValueCallback = None
        self._commandReceivedCallback = callback
        
    def onWriteRequest(self, data, offset, withoutResponse, callback):
        #print(repr(data))  # DEBUG
        head = data[0]
        if head == 0xff:
            self._commandReceivedCallback(data)
        elif head == 0xfe:
           self.readSyncedPacket(data[1:])
        else:
            # TODO warning/error
            print("Error: Unknown header")
        callback(pybleno.Characteristic.RESULT_SUCCESS)
      
    def readSyncedPacket(self, data):
        isFinalPacket = bool(data[0])
        self._rawData += data[1:]
        if isFinalPacket:
            decoded = urllib.parse.unquote(self._rawData.decode("utf-8"))  # TODO: Is encoding correct?
            try:
                self._blocklyList = json.loads(decoded)
                self._rawData = bytearray()
                print(repr(self._blocklyList))
            except json.decoder.JSONDecodeError:
                print("Error: Invalid JSON payload")

# Device communication related services
class BrainToMobileCharacteristic(pybleno.Characteristic):
    def __init__(self):
        super.__init__(self, {
            'uuid': 'd59bb321-7218-4fb9-abac-2f6814f31a4d'.replace('-', ''),
            'properties': ['read', 'write'],
            'value': None
        })

class MobileToBrainCharacteristic(pybleno.Characteristic):
    def __init__(self):
        super.__init__(self, {
            'uuid': 'b81239d9-260b-4945-bcfe-8b1ef1fc2879'.replace('-', ''),
            'properties': ['read', 'write'],
            'value': None
        })

class LongMessageService(pybleno.BlenoPrimaryService):
    def __init__(self, callback):
        pybleno.BlenoPrimaryService.__init__(self, {
            'uuid': '97148a03-5b9d-11e9-8647-d663bd873d93'.replace("-", ""),
            'characteristics': [
                BrainToMobileCharacteristic(),
                MobileToBrainCharacteristic()
          ]})

class MobileToBrainFunctionCharacteristic(pybleno.Characteristic):
    def __init__(self, uuid, minLength, maxLength, description, callback):
        self._callbackFn = callback
        self._minLength = minLength
        self._maxLength = maxLength
        super.__init__(self, {
            'uuid': uuid.replace('-', ''),
            'properties': ['write'],
            'value': None,
            'descriptors': [
                  Descriptor({
                    'uuid': '2901',
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
        self._callbackFn = callback
        self._value = None
        super.__init__(self, {
            'uuid': uuid.replace('-', ''),
            'properties': ['read', 'notify'],
            'value': None,
            'descriptors': [
                  Descriptor({
                    'uuid': '2901',
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

    def updateValue(self, value)
        self._value = value

        if self._updateValueCallback:
            self._updateValueCallback(self._value)

class LiveMessageService(pybleno.BlenoPrimaryService):
    def __init__(self):
        self._keepAliveHandler = None
        self._updateDirectionHandler = None
        self._startStoredProgramHandler = None
    
        pybleno.BlenoPrimaryService.__init__(self, {
            'uuid': 'd2d5558c-5b9d-11e9-8647-d663bd873d93'.replace("-", ""),
            'characteristics': [
                MobileToBrainFunctionCharacteristic('7486bec3-bb6b-4abd-a9ca-20adc281a0a4', 2, 2, 'startStoredProgram', self.startStoredProgramCallback),
                MobileToBrainFunctionCharacteristic('1e01230f-f5f3-4a94-aac8-d09cd48f8d79', 2, 2, 'updateDirection', self.updateDirectionCallback),
                MobileToBrainFunctionCharacteristic('9e55ea41-69c3-4729-9f9a-90bc27ab6253', 1, 1, 'keepAlive', self.keepAliveCallback),
          ]})

    def registerKeepAliveHandler(self, callback):
        self._keepAliveHandler = callback

    def registerUpdateDirectionCallback(self, callback):
        self._updateDirectionHandler = callback
          
    def registerStartStoredProgramCallback(self, callback):
        self._startStoredProgramHandler = callback

    def keepAliveCallback(self, data):
        counter = data[0]
        
        if self._keepAliveHandler:
            return self._keepAliveHandler(counter)
        else:
            return True

    def updateDirectionCallback(self, data):
        angle = data[0] * 2
        magnitude = data[1]
        
        if self._updateDirectionHandler:
            return self._updateDirectionHandler(angle, magnitude)
        else:
            return True
        
    def startStoredProgramCallback(self, data):
        buttonId = data[0]
        isPressed = data[1]
        
        if self._startStoredProgramHandler:
            return self._startStoredProgramHandler(buttonId, isPressed)
        else:
            return True

# Device Information Service
class ReadOnlyCharacteristic(pybleno.Characteristic):
    def __init__(self, uuid, value):
        super.__init__(self, {
            'uuid': uuid,
            'properties': ['read'],
            'value': value
        })

class SerialNumberCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, serial):
        super.__init__(self, '2A25', serial)

class ManufacturerNameCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, name):
        super.__init__(self, '2A29', name)

class ModelNumberCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, modelNo):
        super.__init__(self, '2A24', modelNo)

class HardwareRevisionCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, version):
        super.__init__(self, '2A27', version)

class SoftwareRevisionCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, version):
        super.__init__(self, '2A28', version)

class FirmwareRevisionCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, version):
        super.__init__(self, '2A26', version)

class SystemIdCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, id):
        super.__init__(self, '2A23', id)

class RevvyDeviceInforrmationService(plybleno.BlenoPrimaryService):
    def __init__(self, deviceName):
        pybleno.BlenoPrimaryService.__init__(self, {
            'uuid': '180A',
            'characteristics': [
                SerialNumberCharacteristic('12345'),
                ManufacturerNameCharacteristic('RevolutionRobotics')
                ModelNumberCharacteristic("RevvyAlpha"),
                HardwareRevisionCharacteristic("v1.0.0"),
                SoftwareRevisionCharacteristic("v1.0.0"),
                FirmwareRevisionCharacteristic("v1.0.0"),
                SystemIdCharacteristic(deviceName),
            ]})

# BLE SIG battery service, that is differentiated via Characteristic Presentation Format
class BatteryLevelCharacteristic(pybleno.Characteristic):
    def __init__(self, callback, description, id):
        pybleno.Characteristic.__init__(self, {
            'uuid': '2A19',
            'properties': ['read', 'notify'],
            'value': None,
            'descriptors': [
                  Descriptor({
                    'uuid': '2901',
                    'value': description
                  }),
                  Descriptor({
                    'uuid': '2904',
                    'value': array.array('B', [0x04, 0x01, 0x27, 0xAD, 0x02, 0x00, id ]) # unsigned 8 bit, descriptor defined by RR
                  })
                ]
          })

class BatteryService(plybleno.BlenoPrimaryService):
    def __init__(self, description, id):
        pybleno.BlenoPrimaryService.__init__(self, {
            'uuid': '180F',
            'characteristics': [
                BatteryCharacteristic(description, id)
            ]})

# Custom battery service that contains 2 characteristics
class CustomBatteryLevelCharacteristic(pybleno.Characteristic):
    def __init__(self, uuid, description, id):
        pybleno.Characteristic.__init__(self, {
            'uuid': uuid.replace('-', ''),
            'properties': ['read', 'notify'],
            'value': None, # needs to be None because characteristic is not constant value
            'descriptors': [
                  Descriptor({
                    'uuid': '2901',
                    'value': description
                  })
                ]
          })
          
        self._updateValueCallback = None
        self._value = 100 # initial value only
          
    def onReadRequest(self, offset, callback):
        if offset:
            callback(Characteristic.RESULT_ATTR_NOT_LONG)
        else:
            callback(Characteristic.RESULT_SUCCESS, self._value)

    def onSubscribe(self, maxValueSize, updateValueCallback):
        self._updateValueCallback = updateValueCallback

    def onUnsubscribe(self):
        self._updateValueCallback = None
        
    def updateValue(self, value)
        self._value = value
        
        if self._updateValueCallback:
            self._updateValueCallback(self._value)

class CustomBatteryService(plybleno.BlenoPrimaryService):
    def __init__(self):
        self._mainBattery  = CustomBatteryLevelCharacteristic('2A19', 'Main battery percentage', 0)
        self._motorBattery = CustomBatteryLevelCharacteristic('00002a19-0000-1000-8000-00805f9b34fa', 'Motor battery percentage', 1)

        super.__init__(self, {
            'uuid': '180F',
            'characteristics': [
                self._mainBattery,
                self._motorBattery
            ]})

    def updateMainBatteryValue(self, value):
        self._mainBattery.updateValue(value)

    def updateMotorBatteryValue(self, value):
        self._motorBattery.updateValue(value)

class RevvyBLE():
    def __init__(self, deviceName):
        self._bleno = Bleno()
        self._deviceName = deviceName
        
        self._batteryService = CustomBatteryService()
        self._deviceInformationService = RevvyDeviceInforrmationService(deviceName)
        self._liveMessageService = LiveMessageService()
        self._longMessageService = LongMessageService()
        
        self._services = [
            self._liveMessageService,
            self._longMessageService,
            self._deviceInformationService,
            self._batteryService
        ]
        self._advertisedUuids = [
            self._liveMessageService.uuid,
            self._longMessageService.uuid,
            self._deviceInformationService.uuid,
            self._batteryService.uuid
        ]
        
        bleno.on('stateChange', self.onStateChange)
        bleno.on('advertisingStart', self.onAdvertisingStart)

    def onStateChange(state):
        print('on -> stateChange: ' + state);

        if (state == 'poweredOn'):
            bleno.startAdvertising(self._deviceName, self._advertisedUuids)
       else:
            bleno.stopAdvertising()
     
    def onAdvertisingStart(error):
        print('on -> advertisingStart: ' + ('error ' + error if error else 'success'))

        if not error:
            def on_setServiceError(error):
                print('setServices: %s' % ('error ' + error if error else 'success'))

            bleno.setServices(self._services, on_setServiceError)
        
    def start(self):
        self._bleno.start()
        
    def stop(self):
        self._bleno.stopAdvertising()
        self._bleno.disconnect()