from rrrc_transport import RevvyTransport


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


class RevvyControl:
    mcu_address = 0x2D

    command_ping = 0x00
    command_get_hardware_version = 0x01
    command_get_firmware_version = 0x02
    command_get_battery_status = 0x03
    command_set_master_status = 0x04
    command_set_bluetooth_status = 0x05

    command_get_motor_port_amount = 0x10
    command_get_motor_port_types = 0x11
    command_set_motor_port_type = 0x12
    command_set_motor_port_config = 0x13
    command_set_motor_port_control_value = 0x14

    command_get_sensor_port_amount = 0x20
    command_get_sensor_port_types = 0x21
    command_set_sensor_port_type = 0x22
    command_set_sensor_port_config = 0x23
    command_get_sensor_port_value = 0x24

    def __init__(self, transport: RevvyTransport):
        self._transport = transport

    # general commands

    def ping(self):
        self._transport.send_command(self.command_ping)

    def set_master_status(self, status):
        self._transport.send_command(self.command_set_master_status, [status])

    def set_bluetooth_connection_status(self, status):
        self._transport.send_command(self.command_set_bluetooth_status, [status])

    def get_hardware_version(self):
        response = self._transport.send_command(self.command_get_hardware_version)
        return "".join(map(chr, response.payload))

    def get_firmware_version(self):
        response = self._transport.send_command(self.command_get_firmware_version)
        return "".join(map(chr, response.payload))

    def get_battery_status(self):
        response = self._transport.send_command(self.command_get_battery_status)
        return {'chargerStatus': response.payload[0], 'main': response.payload[1], 'motor': response.payload[2]}

    # motor commands

    def get_motor_port_amount(self):
        response = self._transport.send_command(self.command_get_motor_port_amount)
        return response.payload[0]

    def get_motor_port_types(self):
        response = self._transport.send_command(self.command_get_motor_port_types)
        return parse_string_list(response.payload)

    def set_motor_port_type(self, port_idx, type_idx):
        self._transport.send_command(self.command_set_motor_port_type, [port_idx, type_idx])

    def set_motor_port_config(self, port_idx, config):
        self._transport.send_command(self.command_set_motor_port_config, [port_idx] + config)

    def set_motor_port_control_value(self, port_idx, value):
        self._transport.send_command(self.command_set_motor_port_control_value, [port_idx] + value)

    # sensor commands

    def get_sensor_port_amount(self):
        response = self._transport.send_command(self.command_get_sensor_port_amount)
        return response.payload[0]

    def get_sensor_port_types(self):
        response = self._transport.send_command(self.command_get_sensor_port_types)
        return parse_string_list(response.payload)

    def set_sensor_port_type(self, port_idx, type_idx):
        self._transport.send_command(self.command_set_sensor_port_type, [port_idx, type_idx])

    def set_sensor_port_config(self, port_idx, config):
        self._transport.send_command(self.command_set_sensor_port_config, [port_idx] + config)

    def get_sensor_port_value(self, port_idx, parameters=None):
        parameters = parameters if parameters else []
        response = self._transport.send_command(self.command_get_sensor_port_value, [port_idx] + parameters)
        return response.payload

    # ring led commands

