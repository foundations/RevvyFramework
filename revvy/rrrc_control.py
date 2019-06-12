import struct
from revvy.rrrc_transport import RevvyTransport, Response, ResponseHeader


def parse_string_list(data):
    val = {}
    idx = 0
    while idx < len(data):
        key = data[idx]
        idx += 1
        sz = data[idx]
        idx += 1
        name = "".join(map(chr, data[idx:(idx + sz)]))
        idx += sz
        val[name] = key
    return val


class UnknownCommandError(Exception):
    pass


class Command:
    def get_payload_bytes(self, payload):
        return payload

    def on_success(self, payload):
        return payload

    def process(self, response: Response):
        if response.header.status == ResponseHeader.Status_Ok:
            return self.on_success(response.payload)
        elif response.header.status == ResponseHeader.Status_Error_UnknownCommand:
            raise UnknownCommandError
        else:
            raise ValueError('Command status: {} payload: {}'.format(response.header.status, repr(response.payload)))


class PingCommand(Command):
    pass


class RebootBootloaderCommand(Command):
    pass


class ReadStringCommand(Command):
    def on_success(self, payload):
        return "".join(map(chr, payload))


class ReadStringListCommand(Command):
    def on_success(self, payload):
        return parse_string_list(payload)


class ReadUint8Command(Command):
    def on_success(self, payload):
        return payload[0]


class SendByteCommand(Command):
    def get_payload_bytes(self, payload):
        if len(payload) != 1:
            raise ValueError('Command expect a single argument')
        return payload


class SendByteListCommand(Command):
    def get_payload_bytes(self, payload):
        if len(payload) != 1:
            raise ValueError("Command requires a data array")

        return payload[0]


class GetHardwareVersionCommand(ReadStringCommand):
    pass


class GetFirmwareVersionCommand(ReadStringCommand):
    pass


class ReadBatteryStatusCommand(Command):
    def on_success(self, payload):
        return {'chargerStatus': payload[0], 'main': payload[1], 'motor': payload[2]}


class SetMasterStatusCommand(SendByteCommand):
    pass


class SetBluetoothStatusCommand(SendByteCommand):
    pass


class MotorPort_GetPortAmountCommand(ReadUint8Command):
    pass


class MotorPort_GetPortTypesCommand(ReadStringListCommand):
    pass


class PortReadCommand(Command):
    def get_payload_bytes(self, payload):
        if len(payload) != 1:
            raise ValueError("Command requires a port number")

        return [payload[0]]


class PortSendByteCommand(Command):
    def get_payload_bytes(self, payload):
        if len(payload) != 2:
            raise ValueError("Command requires a port number and a data array")

        return payload


class PortSendByteListCommand(Command):
    def get_payload_bytes(self, payload):
        if len(payload) != 2:
            raise ValueError("Command requires a port number and a data array")

        return [payload[0]] + payload[1]


class PortSendListCommand(Command):
    def __init__(self, length):
        self._length = length

    def get_payload_bytes(self, payload):
        if len(payload) != 2:
            raise ValueError("Command requires a port number and a data array")

        if len(payload[1]) != self._length:
            raise ValueError('Data array must be {} bytes long'.format(self._length))

        return [payload[0]] + payload[1]


class MotorPort_SetPortTypeCommand(PortSendByteCommand):
    pass


class MotorPort_SetPortConfigCommand(PortSendByteListCommand):
    pass


class MotorPort_SetPortControlValueCommand(PortSendByteListCommand):
    pass


class MotorPort_GetMotorPositionCommand(PortReadCommand):
    pass


class MotorPort_GetMotorStatusCommand(Command):
    pass


class SensorPort_GetPortAmountCommand(ReadUint8Command):
    pass


class SensorPort_GetPortTypesCommand(ReadStringListCommand):
    pass


class SensorPort_SetPortTypeCommand(PortSendByteCommand):
    pass


class SensorPort_SetPortConfigCommand(PortSendByteListCommand):
    pass


class SensorPort_GetValueCommand(Command):
    def get_payload_bytes(self, payload):
        if len(payload) == 1:
            return payload
        elif len(payload) == 2:
            return [payload[0]] + payload[1]
        else:
            raise ValueError("SensorPort_GetValueCommand requires a port number and an optional parameter list")


class RingLed_GetScenarioTypesCommand(ReadStringListCommand):
    pass


class RingLed_GetLedAmountCommand(ReadUint8Command):
    pass


class RingLed_SetRingScenarioCommand(Command):
    pass


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


class RingLed_SetUserFrameCommand(Command):
    def get_payload_bytes(self, payload):
        rgb565_values = list(map(rgb_to_rgb565_bytes, payload[0]))
        led_bytes = list(struct.pack("<"+"H"*len(rgb565_values), *rgb565_values))
        print("Sending user LED bytes: {}".format(repr(led_bytes)))
        return led_bytes


class DriveTrain_SetMotorsCommand(Command):
    def get_payload_bytes(self, payload):
        if len(payload) != 2:
            raise ValueError("Command requires a drive train type and a data array")

        return [payload[0]] + payload[1]


class DriveTrain_ControlCommand(SendByteListCommand):
    pass


class RevvyControl:
    mcu_address = 0x2D

    command_ping = 0x00
    command_get_hardware_version = 0x01
    command_get_firmware_version = 0x02
    command_get_battery_status = 0x03
    command_set_master_status = 0x04
    command_set_bluetooth_status = 0x05
    command_get_operation_mode = 0x06
    command_reboot_bootloader = 0x0B

    command_get_motor_port_amount = 0x10
    command_get_motor_port_types = 0x11
    command_set_motor_port_type = 0x12
    command_set_motor_port_config = 0x13
    command_set_motor_port_control_value = 0x14
    command_get_motor_position = 0x15

    command_set_drivatrain_motors = 0x1A
    command_set_drivetrain_control = 0x1B

    command_get_sensor_port_amount = 0x20
    command_get_sensor_port_types = 0x21
    command_set_sensor_port_type = 0x22
    command_set_sensor_port_config = 0x23
    command_get_sensor_port_value = 0x24

    command_get_ring_led_scenario_types = 0x30
    command_set_ring_led_scenario = 0x31
    command_ring_led_get_led_amount = 0x32
    command_set_ring_led_user_frame = 0x33

    def __init__(self, transport: RevvyTransport):
        self._transport = transport
        self._commands = {
            0x00: PingCommand(),
            0x01: GetHardwareVersionCommand(),
            0x02: GetFirmwareVersionCommand(),
            0x03: ReadBatteryStatusCommand(),
            0x04: SetMasterStatusCommand(),
            0x05: SetBluetoothStatusCommand(),

            0x06: ReadUint8Command(),
            0x0B: RebootBootloaderCommand(),

            0x10: MotorPort_GetPortAmountCommand(),
            0x11: MotorPort_GetPortTypesCommand(),
            0x12: MotorPort_SetPortTypeCommand(),
            0x13: MotorPort_SetPortConfigCommand(),
            0x14: MotorPort_SetPortControlValueCommand(),
            0x15: MotorPort_GetMotorPositionCommand(),

            0x1A: DriveTrain_SetMotorsCommand(),
            0x1B: DriveTrain_ControlCommand(),

            0x20: SensorPort_GetPortAmountCommand(),
            0x21: SensorPort_GetPortTypesCommand(),
            0x22: SensorPort_SetPortTypeCommand(),
            0x23: SensorPort_SetPortConfigCommand(),
            0x24: SensorPort_GetValueCommand(),

            0x30: RingLed_GetScenarioTypesCommand(),
            0x31: RingLed_SetRingScenarioCommand(),
            0x32: RingLed_GetLedAmountCommand(),
            0x33: RingLed_SetUserFrameCommand(),
        }

    def send(self, command, *args):
        command_handler = self._commands[command]
        response = self._transport.send_command(command, command_handler.get_payload_bytes(list(args)))
        return command_handler.process(response)

    # general commands

    def ping(self):
        return self.send(self.command_ping)

    def set_master_status(self, status):
        return self.send(self.command_set_master_status, status)

    def set_bluetooth_connection_status(self, status):
        self.send(self.command_set_bluetooth_status, status)

    def get_hardware_version(self):
        return self.send(self.command_get_hardware_version)

    def get_firmware_version(self):
        return self.send(self.command_get_firmware_version)

    def get_battery_status(self):
        return self.send(self.command_get_battery_status)

    def reboot_bootloader(self):
        return self.send(self.command_reboot_bootloader)

    # motor commands

    def get_motor_port_amount(self):
        return self.send(self.command_get_motor_port_amount)

    def get_motor_port_types(self):
        return self.send(self.command_get_motor_port_types)

    def set_motor_port_type(self, port_idx, type_idx):
        return self.send(self.command_set_motor_port_type, port_idx, type_idx)

    def set_motor_port_config(self, port_idx, config):
        return self.send(self.command_set_motor_port_config, port_idx, config)

    def set_motor_port_control_value(self, port_idx, value):
        return self.send(self.command_set_motor_port_control_value, port_idx, value)

    def get_motor_position(self, port_idx):
        return self.send(self.command_get_motor_position, port_idx)

    def set_drivetrain_motors(self, drivetrain_type, motors):
        return self.send(self.command_set_drivatrain_motors, drivetrain_type, motors)

    def set_drivetrain_control(self, control):
        return self.send(self.command_set_drivetrain_control, control)

    # sensor commands

    def get_sensor_port_amount(self):
        return self.send(self.command_get_sensor_port_amount)

    def get_sensor_port_types(self):
        return self.send(self.command_get_sensor_port_types)

    def set_sensor_port_type(self, port_idx, type_idx):
        return self.send(self.command_set_sensor_port_type, port_idx, type_idx)

    def set_sensor_port_config(self, port_idx, config):
        return self.send(self.command_set_sensor_port_config, port_idx, config)

    def get_sensor_port_value(self, port_idx, parameters=None):
        parameters = parameters if parameters else []
        return self.send(self.command_get_sensor_port_value, port_idx, parameters)

    # ring led commands

    def ring_led_get_scenario_types(self):
        return self.send(self.command_get_ring_led_scenario_types)

    def ring_led_set_scenario(self, scenario):
        return self.send(self.command_set_ring_led_scenario, scenario)

    def ring_led_set_user_frame(self, frame):
        return self.send(self.command_set_ring_led_user_frame, frame)

    def ring_led_get_led_amount(self):
        return self.send(self.command_ring_led_get_led_amount)
