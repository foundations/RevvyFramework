import struct
from abc import ABC

from revvy.configuration.version import Version
from revvy.mcu.rrrc_transport import RevvyTransport, Response, ResponseHeader


class UnknownCommandError(Exception):
    pass


class Command:
    """A generic command towards the MCU"""
    def __init__(self, transport: RevvyTransport):
        self._transport = transport
        self._command_byte = self.command_id

    @property
    def command_id(self): raise NotImplementedError

    def _process(self, response: Response):
        if response.status == ResponseHeader.Status_Ok:
            return self.parse_response(response.payload)
        elif response.status == ResponseHeader.Status_Error_UnknownCommand:
            raise UnknownCommandError
        else:
            raise ValueError(
                'Command status: {} payload: {}'.format(response.status, repr(response.payload)))

    def _send(self, payload=None):
        """Send the command with the given payload and process the response"""
        if payload is None:
            payload = []
        response = self._transport.send_command(self._command_byte, payload)
        return self._process(response)

    def __call__(self, *args):
        if args:
            raise NotImplementedError

        return self._send()

    def parse_response(self, payload):
        if payload:
            raise NotImplementedError

        return None


class PingCommand(Command):
    @property
    def command_id(self): return 0x00


class ReadVersionCommand(Command, ABC):
    def parse_response(self, payload):
        return Version(parse_string(payload))


class ReadHardwareVersionCommand(ReadVersionCommand):
    @property
    def command_id(self): return 0x01


class ReadFirmwareVersionCommand(ReadVersionCommand):
    @property
    def command_id(self): return 0x02


class ReadBatteryStatusCommand(Command):
    @property
    def command_id(self): return 0x03

    def parse_response(self, payload):
        assert len(payload) == 3
        return {
            'chargerStatus': int(payload[0]),
            'main': int(payload[1]),
            'motor': int(payload[2])
        }


class SetMasterStatusCommand(Command):
    @property
    def command_id(self): return 0x04

    def __call__(self, status):
        # TODO: make this accept something meaningful
        return self._send([status])


class SetBluetoothStatusCommand(Command):
    @property
    def command_id(self): return 0x05

    def __call__(self, status):
        # TODO: make this accept something meaningful
        return self._send([status])


class ReadOperationModeCommand(Command):
    @property
    def command_id(self): return 0x06

    def parse_response(self, payload):
        # TODO: make this return something meaningful
        assert len(payload) == 1
        return int(payload[0])


class RebootToBootloaderCommand(Command):
    @property
    def command_id(self): return 0x0B


class ReadPortTypesCommand(Command, ABC):
    def parse_response(self, payload):
        return parse_string_list(payload)


class ReadMotorPortTypesCommand(ReadPortTypesCommand):
    @property
    def command_id(self): return 0x11


class ReadSensorPortTypesCommand(ReadPortTypesCommand):
    @property
    def command_id(self): return 0x21


class ReadRingLedScenarioTypesCommand(Command):
    @property
    def command_id(self): return 0x30

    def parse_response(self, payload):
        return parse_string_list(payload)


class ReadPortAmountCommand(Command, ABC):
    def parse_response(self, payload):
        assert len(payload) == 1
        return int(payload[0])


class ReadMotorPortAmountCommand(ReadPortAmountCommand):
    @property
    def command_id(self): return 0x10


class ReadSensorPortAmountCommand(ReadPortAmountCommand):
    @property
    def command_id(self): return 0x20


class SetPortTypeCommand(Command, ABC):
    def __call__(self, port, port_type_idx):
        return self._send([port, port_type_idx])


class SetMotorPortTypeCommand(SetPortTypeCommand):
    @property
    def command_id(self): return 0x12


class SetSensorPortTypeCommand(SetPortTypeCommand):
    @property
    def command_id(self): return 0x22


class SetRingLedScenarioCommand(Command):
    @property
    def command_id(self): return 0x31

    def __call__(self, scenario_idx):
        return self._send([scenario_idx])


class GetRingLedAmountCommand(Command):
    @property
    def command_id(self): return 0x32

    def parse_response(self, payload):
        assert len(payload) == 1
        return int(payload[0])


class SendRingLedUserFrameCommand(Command):
    @property
    def command_id(self): return 0x33

    def __call__(self, colors):
        rgb565_values = list(map(rgb_to_rgb565_bytes, colors))
        led_bytes = list(struct.pack("<" + "H" * len(rgb565_values), *rgb565_values))
        return self._send(led_bytes)


class SetDifferentialDriveTrainMotorsCommand(Command):
    @property
    def command_id(self): return 0x1A

    def __call__(self, motors):
        return self._send([0] + motors)


class RequestDifferentialDriveTrainSpeedCommand(Command):
    @property
    def command_id(self): return 0x1B

    def __call__(self, left, right, pwr_limit=0):
        speed_cmd = list(struct.pack('<bffb', 1, left, right, pwr_limit))
        return self._send(speed_cmd)


class RequestDifferentialDriveTrainPositionCommand(Command):
    @property
    def command_id(self): return 0x1B

    def __call__(self, left, right, left_spd_limit=0, right_spd_limit=0, pwr_limit=0):
        pos_cmd = list(struct.pack('<bllffb', 0, left, right, left_spd_limit, right_spd_limit, pwr_limit))
        return self._send(pos_cmd)


class SetPortConfigCommand(Command, ABC):
    def __call__(self, port_idx, config):
        return self._send([port_idx] + config)


class SetMotorPortConfigCommand(SetPortConfigCommand):
    @property
    def command_id(self): return 0x13


class SetSensorPortConfigCommand(SetPortConfigCommand):
    @property
    def command_id(self): return 0x23


class SetMotorPortControlCommand(Command):
    @property
    def command_id(self): return 0x14

    def __call__(self, port_idx, control):
        return self._send([port_idx] + control)


class ReadPortStatusCommand(Command, ABC):
    def __call__(self, port_idx):
        return self._send([port_idx])

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
class InitializeUpdateCommand(Command):
    @property
    def command_id(self): return 0x08

    def __call__(self, crc, length):
        return self._send(list(struct.pack("<LL", crc, length)))


class SendFirmwareCommand(Command):
    @property
    def command_id(self): return 0x09

    def __call__(self, data):
        return self._send(data)


class FinalizeUpdateCommand(Command):
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
