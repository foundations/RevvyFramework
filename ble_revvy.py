#!/usr/bin/python3
import array

from functools import reduce
from pybleno import Bleno, BlenoPrimaryService, Characteristic, Descriptor


class Observable:
    def __init__(self, value):
        self._value = value
        self._observers = []

    def update(self, value):
        self._value = value
        self._notify_observers(value)

    def get(self):
        return self._value

    def subscribe(self, observer):
        self._observers.append(observer)

    def unsubscribe(self, observer):
        self._observers.remove(observer)

    def _notify_observers(self, new_value):
        for observer in self._observers:
            observer(new_value)


class LongMessageChunk:
    InitMessage = 1
    UploadMessage = 2
    FinalizeMessage = 3

    def __init__(self, chunk):
        self._type = chunk[0]
        self._payload = chunk[1:]
        pass

    @property
    def chunk_type(self):
        return self._type

    @property
    def payload(self):
        return self._payload


class LongMessage:
    def __init__(self, message_id, checksum):
        self._message_id = message_id
        self._checksum = checksum
        self._payload = ""

    def append(self, payload):
        self._payload += payload.decode('utf-8')

    @property
    def message_id(self):
        return self._message_id

    @property
    def is_valid(self):
        return True


class LongMessageParser:
    def __init__(self, handler):
        self._message_received_handler = handler
        self._current_message = None

    def process_chunk(self, chunk: LongMessageChunk):
        if chunk.chunk_type == LongMessageChunk.InitMessage:
            self._current_message = None

        if not self._current_message:
            if chunk.chunk_type == LongMessageChunk.InitMessage:
                self._current_message = LongMessage(chunk.payload[0], chunk.payload[1:])
            else:
                raise ValueError('Expected init message')
        else:
            if chunk.chunk_type == LongMessageChunk.InitMessage:
                raise ValueError('Unreachable code')
            elif chunk.chunk_type == LongMessageChunk.UploadMessage:
                self._current_message.append(chunk.payload)
            elif chunk.chunk_type == LongMessageChunk.FinalizeMessage:
                self._message_received_handler(self._current_message)
                self._current_message = None
            else:
                raise ValueError('Unknown chunk type')

    @property
    def is_processing(self):
        return self._current_message is None


class LongMessageType:
    FirmwareData = 1,
    FrameworkData = 2,
    ConfigurationData = 3,
    TestKit = 4


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
                    'value': description.encode()
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
    def __init__(self, uuid, description):
        self._value = []
        self._updateValueCallback = None
        super().__init__({
            'uuid':        uuid,
            'properties':  ['read', 'notify'],
            'value':       None,
            'descriptors': [
                Descriptor({
                    'uuid':  '2901',
                    'value': description.encode()
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

    def update(self, value):
        self._value = [len(value)] + value

        if self._updateValueCallback:
            self._updateValueCallback(self._value)


class LiveMessageService(BlenoPrimaryService):
    def __init__(self):
        self._message_handler = lambda x: None

        self._sensor_characteristics = [
                BrainToMobileFunctionCharacteristic('135032e6-3e86-404f-b0a9-953fd46dcb17', 'Sensor 1'),
                BrainToMobileFunctionCharacteristic('36e944ef-34fe-4de2-9310-394d482e20e6', 'Sensor 2'),
                BrainToMobileFunctionCharacteristic('b3a71566-9af2-4c9d-bc4a-6f754ab6fcf0', 'Sensor 3'),
                BrainToMobileFunctionCharacteristic('9ace575c-0b70-4ed5-96f1-979a8eadbc6b', 'Sensor 4'),
        ]

        super().__init__({
            'uuid':            'd2d5558c-5b9d-11e9-8647-d663bd873d93',
            'characteristics': [
                MobileToBrainFunctionCharacteristic('7486bec3-bb6b-4abd-a9ca-20adc281a0a4', 20, 20, 'simpleControl',
                                                    self.simple_control_callback),
                self._sensor_characteristics[0],
                self._sensor_characteristics[1],
                self._sensor_characteristics[2],
                self._sensor_characteristics[3],
            ]
        })

    def register_message_handler(self, callback):
        self._message_handler = callback

    def simple_control_callback(self, data):
        # print(repr(data))
        counter = data[0]
        analog_values = data[1:11]
        button_values = self.extract_button_states(data[11:15])

        self._message_handler({'counter': counter, 'analog': analog_values, 'buttons': button_values})
        return True

    def update_sensor(self, sensor, value):
        if 0 < sensor <= len(self._sensor_characteristics):
            self._sensor_characteristics[sensor - 1].update(value)

    @staticmethod
    def extract_button_states(data):
        def nth_bit(byte, bit):
            return (byte & (1 << bit)) != 0

        def expand_byte(byte):
            return [nth_bit(byte, x) for x in range(8)]

        return reduce(
            lambda x, y: x + y,
            map(expand_byte, data),
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
        super().__init__('2A25', serial.encode())


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


class SystemIdCharacteristic(Characteristic):
    def __init__(self, system_id: Observable):
        super().__init__({
            'uuid':       '2A23',
            'properties': ['read', 'write'],
            'value':      None
        })
        self._system_id = system_id

    def onReadRequest(self, offset, callback):
        if offset:
            callback(Characteristic.RESULT_ATTR_NOT_LONG)
        else:
            callback(Characteristic.RESULT_SUCCESS, self._system_id.get().encode('utf-8'))

    def onWriteRequest(self, data, offset, withoutResponse, callback):
        if offset:
            callback(Characteristic.RESULT_ATTR_NOT_LONG)

        try:
            self._system_id.update(data.decode('utf-8'))
            callback(Characteristic.RESULT_SUCCESS)
        except UnicodeDecodeError:
            callback(Characteristic.RESULT_UNLIKELY_ERROR)


class RevvyDeviceInforrmationService(BlenoPrimaryService):
    def __init__(self, device_name: Observable, serial):
        self._hw_version_characteristic = HardwareRevisionCharacteristic()
        self._fw_version_characteristic = FirmwareRevisionCharacteristic()
        self._sw_version_characteristic = SoftwareRevisionCharacteristic()
        super().__init__({
            'uuid':            '180A',
            'characteristics': [
                SerialNumberCharacteristic(serial),
                ManufacturerNameCharacteristic(b'RevolutionRobotics'),
                ModelNumberCharacteristic(b"RevvyAlpha"),
                self._hw_version_characteristic,
                self._fw_version_characteristic,
                self._sw_version_characteristic,
                SystemIdCharacteristic(device_name),
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
                    'value': description.encode()
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
                    'value': description.encode()
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
    def __init__(self, device_name: Observable, serial):
        self._deviceName = device_name.get()
        print('Initializing {}'.format(self._deviceName))

        device_name.subscribe(self._device_name_changed)

        self._deviceInformationService = RevvyDeviceInforrmationService(device_name, serial)
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

    def _device_name_changed(self, name):
        self._deviceName = name
        self._bleno.stopAdvertising(lambda: self._bleno.startAdvertising(self._deviceName, self._advertisedUuids))

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

    def update_sensor(self, sensor, value):
        self._liveMessageService.update_sensor(sensor, value)

    def register_remote_controller_handler(self, callback):
        self._liveMessageService.register_message_handler(callback)
