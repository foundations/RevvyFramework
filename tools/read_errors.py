import argparse

from revvy.hardware_dependent.rrrc_transport_i2c import RevvyTransportI2C
from revvy.mcu.rrrc_control import RevvyControl


def format_error(error):
    error_id = error[0]
    hw_version = error[1:5]
    fw_version = error[5:9]
    error_data = error[9:]

    if error_id == 0:
        pc = int.from_bytes(error_data[0:4], byteorder='little')
        psr = int.from_bytes(error_data[4:8], byteorder='little')
        lr = int.from_bytes(error_data[8:12], byteorder='little')
        cfsr = int.from_bytes(error_data[12:16], byteorder='little')
        dfsr = int.from_bytes(error_data[16:20], byteorder='little')
        hfsr = int.from_bytes(error_data[20:24], byteorder='little')

        exception_name = 'Hard fault'
        details_str = '\n\tPC: 0x{0:X}\tPSR: 0x{1:X}\tLR: 0x{2:X}'.format(pc, psr, lr)
        details_str += '\n\tCFSR: 0x{0:X}\tDFSR: 0x{1:X}\tHFSR: 0x{2:X}'.format(cfsr, dfsr, hfsr)

        cfsr_reasons = [
            "The processor has attempted to execute an undefined instruction",
            "The processor attempted a load or store at a location that does not permit the operation",
            None,
            "Unstack for an exception return has caused one or more access violations",
            "Stacking for an exception entry has caused one or more access violations",
            "A MemManage fault occurred during floating-point lazy state preservation",
            None,
            None,
            "Instruction bus error",
            "Data bus error (PC value points to the instruction that caused the fault)",
            "Data bus error (PC value is not directly related to the instruction that caused the error)",
            "Unstack for an exception return has caused one or more BusFaults",
            "Stacking for an exception entry has caused one or more BusFaults",
            "A bus fault occurred during floating-point lazy state preservation",
            None,
            None,
            "The processor has attempted to execute an undefined instruction",
            "The processor has attempted to execute an instruction that makes illegal use of the EPSR",
            "The processor has attempted an illegal load to the PC",
            "The processor has attempted to access a coprocessor",
            None,
            None,
            None,
            None,
            "The processor has made an unaligned memory access",
            "The processor has executed an SDIV or UDIV instruction with a divisor of 0",
        ]

        if cfsr != 0:
            details_str += "\n\tReasons:"
            for bit in range(0, len(cfsr_reasons)):
                if (cfsr & 1 << bit) != 0 and cfsr_reasons[bit] is not None:
                    details_str += "\n\t\t" + cfsr_reasons[bit]

    elif error_id == 1:
        task = bytes(error_data).decode("utf-8")

        exception_name = 'Stack overflow'
        details_str = '\nTask: {}'.format(task)

    elif error_id == 2:
        line = int.from_bytes(error_data[0:4], byteorder='little')
        file = bytes(error_data[4:]).decode("utf-8")

        exception_name = 'Assertion failure'
        details_str = '\nFile: {}, Line: {}'.format(file, line)

    elif error_id == 3:
        exception_name = 'Test error'
        details_str = '\nData: {}'.format(error_data)

    else:
        exception_name = 'Unknown error'
        details_str = '\nData: {}'.format(error_data)

    hw = int.from_bytes(hw_version, byteorder='little')
    fw = int.from_bytes(fw_version, byteorder='little')

    hw_formats = {
        0: '1.0.0',
        1: '1.0.1',
        2: '2.0.0'
    }

    fw_formats = {
        0: '0.1.{}',
        1: '0.1.{}',
        2: '0.2.{}'
    }

    hw_str = hw_formats[hw]
    fw_str = fw_formats[hw].format(fw)

    return '{} ({}, HW: {}, FW: {})\nDetails: {}'.format(exception_name, error_id, hw_str, fw_str, details_str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--inject-test-error', help='Record an error', action='store_true')
    parser.add_argument('--clear', help='Clear the error memory', action='store_true')

    args = parser.parse_args()

    with RevvyTransportI2C() as transport:
        robot_control = RevvyControl(transport.bind(0x2D))

        if args.inject_test_error:
            print('Recording a test error')
            robot_control.error_memory_test()

        # read errors
        error_count = robot_control.error_memory_read_count()
        if error_count == 0:
            print('There are no errors stored')
        elif error_count == 1:
            print('There is one error stored')
        else:
            print('There are {} errors stored'.format(error_count))

        if error_count > 0:
            print('Reading error memory...')
            error_list = []
            while len(error_list) < error_count:
                errors = robot_control.error_memory_read_errors(len(error_list))
                if len(errors) == 0:
                    break

                error_list += errors

            i = 0
            for error in error_list:
                print('----------------------------------------')
                print('Error {}'.format(i))
                print(format_error(error))
                i += 1

        if args.clear:
            print('Clearing error memory...')
            robot_control.error_memory_clear()
            print('Error memory cleared')
