import unittest

from revvy.mcu.commands import *
from revvy.mcu.rrrc_control import RevvyControl, BootloaderControl


class TestParseStringList(unittest.TestCase):
    def test_empty_string_gives_empty_dict(self):
        data = parse_string_list(b"")
        self.assertEqual(data, {})

    def test_string_is_returned_as_dict_key(self):
        data = parse_string_list([0, 3, ord('f'), ord('o'), ord('o')])
        self.assertEqual(data, {'foo': 0})

    def test_multiple_strings_result_in_multiple_pairs_of_data(self):
        data = parse_string_list([0, 3, ord('f'), ord('o'), ord('o'), 1, 3, ord('b'), ord('a'), ord('r')])
        self.assertEqual(data, {'foo': 0, 'bar': 1})


class TestControlCommands(unittest.TestCase):
    def test_revvy_command_instances(self):

        # noinspection PyTypeChecker
        control = RevvyControl(None)

        self.assertIs(PingCommand, type(control.ping))

        self.assertIs(SetMasterStatusCommand, type(control.set_master_status))
        self.assertIs(ReadOperationModeCommand, type(control.read_operation_mode))
        self.assertIs(SetBluetoothStatusCommand, type(control.set_bluetooth_connection_status))
        self.assertIs(ReadHardwareVersionCommand, type(control.get_hardware_version))
        self.assertIs(ReadFirmwareVersionCommand, type(control.get_firmware_version))
        self.assertIs(ReadBatteryStatusCommand, type(control.get_battery_status))
        self.assertIs(RebootToBootloaderCommand, type(control.reboot_bootloader))

        self.assertIs(ReadMotorPortAmountCommand, type(control.get_motor_port_amount))
        self.assertIs(ReadMotorPortTypesCommand, type(control.get_motor_port_types))
        self.assertIs(SetMotorPortTypeCommand, type(control.set_motor_port_type))
        self.assertIs(SetMotorPortConfigCommand, type(control.set_motor_port_config))
        self.assertIs(SetMotorPortControlCommand, type(control.set_motor_port_control_value))
        self.assertIs(ReadMotorPortStatusCommand, type(control.get_motor_position))

        self.assertIs(SetDifferentialDriveTrainMotorsCommand, type(control.set_drivetrain_motors))
        self.assertIs(RequestDifferentialDriveTrainPositionCommand, type(control.set_drivetrain_position))
        self.assertIs(RequestDifferentialDriveTrainSpeedCommand, type(control.set_drivetrain_speed))

        self.assertIs(ReadSensorPortAmountCommand, type(control.get_sensor_port_amount))
        self.assertIs(ReadSensorPortTypesCommand, type(control.get_sensor_port_types))
        self.assertIs(SetSensorPortTypeCommand, type(control.set_sensor_port_type))
        self.assertIs(SetSensorPortConfigCommand, type(control.set_sensor_port_config))
        self.assertIs(ReadSensorPortStatusCommand, type(control.get_sensor_port_value))

        self.assertIs(ReadRingLedScenarioTypesCommand, type(control.ring_led_get_scenario_types))
        self.assertIs(GetRingLedAmountCommand, type(control.ring_led_get_led_amount))
        self.assertIs(SetRingLedScenarioCommand, type(control.ring_led_set_scenario))
        self.assertIs(SendRingLedUserFrameCommand, type(control.ring_led_set_user_frame))

    def test_bootloader_command_instances(self):

        # noinspection PyTypeChecker
        control = BootloaderControl(None)

        self.assertIs(ReadOperationModeCommand, type(control.read_operation_mode))
        self.assertIs(InitializeUpdateCommand, type(control.send_init_update))
        self.assertIs(SendFirmwareCommand, type(control.send_firmware))
        self.assertIs(FinalizeUpdateCommand, type(control.finalize_update))
