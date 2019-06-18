import struct
from abc import ABC

from revvy.mcu.rrrc_control import McuCommand


class PingCommand(McuCommand):
    @property
    def command_id(self): return 0x00


class ReadVersionCommand(McuCommand, ABC):
    def parse_response(self, payload):
        return parse_string(payload)


class ReadHardwareVersionCommand(ReadVersionCommand):
    @property
    def command_id(self): return 0x01


class ReadFirmwareVersionCommand(ReadVersionCommand):
    @property
    def command_id(self): return 0x02


class ReadBatteryStatusCommand(McuCommand):
    @property
    def command_id(self): return 0x03

    def parse_response(self, payload):
        assert len(payload) == 3
        return {
            'chargerStatus': int(payload[0]),
            'main': int(payload[1]),
            'motor': int(payload[2])
        }


class SetMasterStatusCommand(McuCommand):
    @property
    def command_id(self): return 0x04

    def __call__(self, status):
        # TODO: make this accept something meaningful
        self.send([status])


class SetBluetoothStatusCommand(McuCommand):
    @property
    def command_id(self): return 0x05

    def __call__(self, status):
        # TODO: make this accept something meaningful
        self.send([status])


class ReadOperationModeCommand(McuCommand):
    @property
    def command_id(self): return 0x06

    def parse_response(self, payload):
        # TODO: make this return something meaningful
        assert len(payload) == 1
        return int(payload[0])


class RebootToBootloaderCommand(McuCommand):
    @property
    def command_id(self): return 0x0B


class ReadPortTypesCommand(McuCommand, ABC):
    def parse_response(self, payload):
        return parse_string_list(payload)


class ReadMotorPortTypesCommand(ReadPortTypesCommand):
    @property
    def command_id(self): return 0x11


class ReadSensorPortTypesCommand(ReadPortTypesCommand):
    @property
    def command_id(self): return 0x21


class ReadRingLedScenarioTypesCommand(McuCommand):
    @property
    def command_id(self): return 0x30

    def parse_response(self, payload):
        return parse_string_list(payload)


class ReadPortAmountCommand(McuCommand, ABC):
    def parse_response(self, payload):
        assert len(payload) == 1
        return int(payload[0])


class ReadMotorPortAmountCommand(ReadPortAmountCommand):
    @property
    def command_id(self): return 0x10


class ReadSensorPortAmountCommand(ReadPortAmountCommand):
    @property
    def command_id(self): return 0x20


class SetPortTypeCommand(McuCommand, ABC):
    def __call__(self, port, port_type_idx):
        self.send([port, port_type_idx])


class SetMotorPortTypeCommand(SetPortTypeCommand):
    @property
    def command_id(self): return 0x12


class SetSensorPortTypeCommand(SetPortTypeCommand):
    @property
    def command_id(self): return 0x22


class SetRingLedScenarioCommand(McuCommand):
    @property
    def command_id(self): return 0x31

    def __call__(self, scenario_idx):
        self.send([scenario_idx])


class GetRingLedAmountCommand(McuCommand):
    @property
    def command_id(self): return 0x32

    def parse_response(self, payload):
        assert len(payload) == 1
        return int(payload[0])


class SendRingLedUserFrameCommand(McuCommand):
    @property
    def command_id(self): return 0x33

    def __call__(self, colors):
        rgb565_values = list(map(rgb_to_rgb565_bytes, colors))
        led_bytes = list(struct.pack("<" + "H" * len(rgb565_values), *rgb565_values))
        self.send(led_bytes)


class SetDifferentialDriveTrainMotorsCommand(McuCommand):
    @property
    def command_id(self): return 0x1A

    def __call__(self, motors):
        self.send([0] + motors)


class RequestDifferentialDriveTrainSpeedCommand(McuCommand):
    @property
    def command_id(self): return 0x1B

    def __call__(self, left, right, pwr_limit=0):
        speed_cmd = list(struct.pack('<bffb', 1, left, right, pwr_limit))
        self.send(speed_cmd)


class RequestDifferentialDriveTrainPositionCommand(McuCommand):
    @property
    def command_id(self): return 0x1B

    def __call__(self, left, right, left_spd_limit=0, right_spd_limit=0, pwr_limit=0):
        pos_cmd = list(struct.pack('<bllffb', 0, left, right, left_spd_limit, right_spd_limit, pwr_limit))
        self.send(pos_cmd)


class SetPortConfigCommand(McuCommand, ABC):
    def __call__(self, port_idx, config):
        self.send([port_idx] + config)


class SetMotorPortConfigCommand(SetPortConfigCommand):
    @property
    def command_id(self): return 0x13


class SetSensorPortConfigCommand(SetPortConfigCommand):
    @property
    def command_id(self): return 0x23


class SetMotorPortControlCommand(McuCommand):
    @property
    def command_id(self): return 0x14

    def __call__(self, port_idx, control):
        self.send([port_idx] + control)


class ReadPortStatusCommand(McuCommand, ABC):
    def __call__(self, port_idx):
        self.send([port_idx])

    def parse_response(self, payload):
        """Return the raw response"""
        return payload


class ReadMotorPortStatusCommand(ReadPortStatusCommand):
    @property
    def command_id(self): return 0x15


class ReadSensorPortStatusCommand(ReadPortStatusCommand):
    @property
    def command_id(self): return 0x24


# Bootloader-specific commands:
class InitializeUpdateCommand(McuCommand):
    @property
    def command_id(self): return 0x08

    def __call__(self, crc, length):
        self.send(list(struct.pack("<LL", crc, length)))


class SendFirmwareCommand(McuCommand):
    @property
    def command_id(self): return 0x09

    def __call__(self, data):
        self.send(data)


class FinalizeUpdateCommand(McuCommand):
    @property
    def command_id(self): return 0x0A


def parse_string(data):
    """
    >>> parse_string(b'foobar')
    'foobar'
    >>> parse_string([ord('f'), ord('o'), ord('o'), ord('b'), ord('a'), ord('r')])
    'foobar'
    """
    return bytes(data).decode("utf-8")


def parse_string_list(data):
    """
    >>> parse_string_list(b'\x01\x06foobar')
    {'foobar': 1}
    """
    val = {}
    idx = 0
    while idx < len(data):
        key = data[idx]
        idx += 1
        sz = data[idx]
        idx += 1
        name = parse_string(data[idx:(idx + sz)])
        idx += sz
        val[name] = key
    return val


def rgb_to_rgb565_bytes(rgb):
    """
    Convert 24bit color to 16bit

    >>> rgb_to_rgb565_bytes(0)
    0
    >>> rgb_to_rgb565_bytes(0x800000)
    32768
    >>> rgb_to_rgb565_bytes(0x080408)
    2081
    >>> rgb_to_rgb565_bytes(0x808080)
    33808
    >>> rgb_to_rgb565_bytes(0xFFFFFF)
    65535
    """
    r = (rgb & 0x00F80000) >> 8
    g = (rgb & 0x0000FC00) >> 5
    b = (rgb & 0x000000F8) >> 3

    return r | g | b
