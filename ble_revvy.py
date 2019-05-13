#!/usr/bin/python3
import array

from functools import reduce
from pybleno import Bleno, BlenoPrimaryService, Characteristic, Descriptor


# Device communication related services
class BrainToMobileCharacteristic(Characteristic):
    def __init__(self):
        super().__init__({
            'uuid':       'd59bb321-7218-4fb9-abac-2f6814f31a4d',
            'properties': ['read', 'write'],
            'value':      None
        })


class MobileToBrainCharacteristic(Characteristic):
    def __init__(self):
        super().__init__({
            'uuid':       'b81239d9-260b-4945-bcfe-8b1ef1fc2879',
            'properties': ['read', 'write'],
            'value':      None
        })


class LongMessageService(BlenoPrimaryService):
    def __init__(self):
        BlenoPrimaryService.__init__(self, {
            'uuid':            '97148a03-5b9d-11e9-8647-d663bd873d93',
            'characteristics': [
                BrainToMobileCharacteristic(),
                MobileToBrainCharacteristic()
            ]})


class MobileToBrainFunctionCharacteristic(Characteristic):
    def __init__(self, uuid, min_length, max_length, description, callback):
        self._callbackFn = callback
        self._minLength = min_length
        self._maxLength = max_length
        super().__init__({
            'uuid':        uuid,
            'properties':  ['write'],
            'value':       None,
            'descriptors': [
                Descriptor({
                    'uuid':  '2901',
                    'value': description
                }),
            ]
        })

    def onWriteRequest(self, data, offset, without_response, callback):
        if offset:
            callback(Characteristic.RESULT_ATTR_NOT_LONG)

        if len(data) < self._minLength or len(data) > self._maxLength:
            callback(Characteristic.RESULT_INVALID_ATTRIBUTE_LENGTH)
        elif self._callbackFn(data):
            callback(Characteristic.RESULT_SUCCESS)
        else:
            callback(Characteristic.RESULT_UNLIKELY_ERROR)


class BrainToMobileFunctionCharacteristic(Characteristic):
    def __init__(self, description, uuid):
        self._value = None
        self._updateValueCallback = None
        super().__init__({
            'uuid':        uuid,
            'properties':  ['read', 'notify'],
            'value':       None,
            'descriptors': [
                Descriptor({
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

    def onSubscribe(self, max_value_size, update_value_callback):
        self._updateValueCallback = update_value_callback

    def onUnsubscribe(self):
        self._updateValueCallback = None

    def updateValue(self, value):
        self._value = value

        if self._updateValueCallback:
            self._updateValueCallback(self._value)


class LiveMessageService(BlenoPrimaryService):
    def __init__(self):
        def empty_fn(x): pass

        self._keepAliveHandler = empty_fn
        self._buttonHandlers = [empty_fn] * 32
        self._analogHandlers = [empty_fn] * 10

        print('Created {} button handlers'.format(len(self._buttonHandlers)))
        print('Created {} analog handlers'.format(len(self._analogHandlers)))

        super().__init__({
            'uuid':            'd2d5558c-5b9d-11e9-8647-d663bd873d93',
            'characteristics': [
                MobileToBrainFunctionCharacteristic('7486bec3-bb6b-4abd-a9ca-20adc281a0a4', 20, 20, 'simpleControl',
                                                    self.simpleControlCallback),
            ]})

    def registerKeepAliveHandler(self, callback):
        self._keepAliveHandler = callback

    def registerAnalogHandler(self, channel_id, callback):
        if channel_id < len(self._analogHandlers):
            self._analogHandlers[channel_id] = callback
        else:
            print('Incorrect analog handler id {}'.format(channel_id))

    def registerButtonHandler(self, channel_id, callback):
        if channel_id < len(self._buttonHandlers):
            self._buttonHandlers[channel_id] = callback
        else:
            print('Incorrect button handler id {}'.format(channel_id))

    def _fireButtonHandler(self, idx, state):
        if idx < len(self._buttonHandlers):
            self._buttonHandlers[idx](value=state)

    def _fireAnalogHandler(self, idx, state):
        if idx < len(self._analogHandlers):
            self._analogHandlers[idx](value=state)

    def simpleControlCallback(self, data):
        # print(repr(data))
        counter = data[0]
        analog_values = data[1:11]

        button_values = self.extract_button_states(data)

        for i in range(len(analog_values)):
            self._fireAnalogHandler(i, analog_values[i])

        for i in range(len(button_values)):
            self._fireButtonHandler(i, button_values[i])

        self._keepAliveHandler(counter)
        return True

    @staticmethod
    def extract_button_states(data):
        def nth_bit(byte, bit):
            return (byte & (1 << bit)) != 0

        def expand_byte(byte):
            return [nth_bit(byte, x) for x in range(8)]

        return reduce(
            lambda x, y: x + y,
            map(expand_byte, data[11:15]),
            []
        )


# Device Information Service
class ReadOnlyCharacteristic(Characteristic):
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
    def __init__(self, model_no):
        super().__init__('2A24', model_no)


class VersionCharacteristic(Characteristic):
    version_max_length = 20

    def __init__(self, uuid):
        super().__init__({
            'uuid':       uuid,
            'properties': ['read'],
            'value':      None
        })
        self._version = []

    def onReadRequest(self, offset, callback):
        if offset:
            callback(Characteristic.RESULT_ATTR_NOT_LONG)
        else:
            callback(Characteristic.RESULT_SUCCESS, self._version)

    def update(self, version):
        if len(version) > self.version_max_length:
            version = version[:self.version_max_length]
        self._version = version.encode("utf-8")


class HardwareRevisionCharacteristic(VersionCharacteristic):
    def __init__(self):
        super().__init__('2A27')


class FirmwareRevisionCharacteristic(VersionCharacteristic):
    def __init__(self):
        super().__init__('2A26')


class SoftwareRevisionCharacteristic(VersionCharacteristic):
    def __init__(self):
        super().__init__('2A28')


class SystemIdCharacteristic(ReadOnlyCharacteristic):
    def __init__(self, system_id):
        super().__init__('2A23', system_id)


class RevvyDeviceInforrmationService(BlenoPrimaryService):
    def __init__(self, device_name):
        self._hw_version_characteristic = HardwareRevisionCharacteristic()
        self._fw_version_characteristic = FirmwareRevisionCharacteristic()
        self._sw_version_characteristic = SoftwareRevisionCharacteristic()
        super().__init__({
            'uuid':            '180A',
            'characteristics': [
                SerialNumberCharacteristic(b'12345'),
                ManufacturerNameCharacteristic(b'RevolutionRobotics'),
                ModelNumberCharacteristic(b"RevvyAlpha"),
                self._hw_version_characteristic,
                self._fw_version_characteristic,
                self._sw_version_characteristic,
                SystemIdCharacteristic(device_name.encode()),
            ]})

    def update_hw_version(self, version):
        self._hw_version_characteristic.update(version)

    def update_fw_version(self, version):
        self._fw_version_characteristic.update(version)

    def update_sw_version(self, version):
        self._sw_version_characteristic.update(version)


# BLE SIG battery service, that is differentiated via Characteristic Presentation Format
class BatteryLevelCharacteristic(Characteristic):
    def __init__(self, description, char_id):
        super().__init__({
            'uuid':        '2A19',
            'properties':  ['read', 'notify'],
            'value':       None,
            'descriptors': [
                Descriptor({
                    'uuid':  '2901',
                    'value': description
                }),
                Descriptor({
                    'uuid':  '2904',
                    'value': array.array('B', [0x04, 0x01, 0x27, 0xAD, 0x02, 0x00, char_id])
                    # unsigned 8 bit, descriptor defined by RR
                })
            ]
        })


class BatteryService(BlenoPrimaryService):
    def __init__(self, description, char_id):
        super().__init__({
            'uuid':            '180F',
            'characteristics': [
                BatteryLevelCharacteristic(description, char_id)
            ]})


# Custom battery service that contains 2 characteristics
class CustomBatteryLevelCharacteristic(Characteristic):
    def __init__(self, uuid, description):
        super().__init__({
            'uuid':        uuid,
            'properties':  ['read', 'notify'],
            'value':       None,  # needs to be None because characteristic is not constant value
            'descriptors': [
                Descriptor({
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
            callback(Characteristic.RESULT_SUCCESS, [self._value])

    def onSubscribe(self, max_value_size, update_value_callback):
        self._updateValueCallback = update_value_callback

    def onUnsubscribe(self):
        self._updateValueCallback = None

    def updateValue(self, value):
        self._value = value

        if self._updateValueCallback:
            self._updateValueCallback([value])


class CustomBatteryService(BlenoPrimaryService):
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
    def __init__(self, device_name):
        print('Initializing {}'.format(device_name))
        self._deviceName = device_name

        self._deviceInformationService = RevvyDeviceInforrmationService(device_name)
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
            self._liveMessageService['uuid']
        ]

        self._bleno = Bleno()
        self._bleno.on('stateChange', self.onStateChange)
        self._bleno.on('advertisingStart', self.onAdvertisingStart)

    def set_hw_version(self, version):
        self._deviceInformationService.update_hw_version(version)

    def set_fw_version(self, version):
        self._deviceInformationService.update_fw_version(version)

    def set_sw_version(self, version):
        self._deviceInformationService.update_sw_version(version)

    def onStateChange(self, state):
        print('on -> stateChange: ' + state)

        if state == 'poweredOn':
            self._bleno.startAdvertising(self._deviceName, self._advertisedUuids)
        else:
            self._bleno.stopAdvertising()

    def onAdvertisingStart(self, error):
        print('on -> advertisingStart: {0}'.format(('error ' + str(error) if error else 'success')))

        if not error:
            print('setServices')

            # noinspection PyShadowingNames
            def on_set_service_error(error):
                print('setServices: {}'.format('error ' + str(error) if error else 'success'))

            self._bleno.setServices(self._services, on_set_service_error)

    def registerConnectionChangedHandler(self, callback):
        self._bleno.on('accept', lambda x: callback(True))
        self._bleno.on('disconnect', lambda x: callback(False))

    def start(self):
        self._bleno.start()

    def stop(self):
        self._bleno.stopAdvertising()
        self._bleno.disconnect()

    def updateMainBattery(self, level):
        self._batteryService.updateMainBatteryValue(level)

    def updateMotorBattery(self, level):
        self._batteryService.updateMotorBatteryValue(level)

    def registerButtonHandler(self, channel_idx, callback):
        self._liveMessageService.registerButtonHandler(channel_idx, callback)

    def registerAnalogHandler(self, channel_idx, callback):
        self._liveMessageService.registerAnalogHandler(channel_idx, callback)

    def registerKeepAliveHandler(self, callback):
        self._liveMessageService.registerKeepAliveHandler(callback)
