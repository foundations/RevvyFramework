import argparse

from revvy.hardware_dependent.rrrc_transport_i2c import RevvyTransportI2C
from revvy.mcu.rrrc_control import RevvyControl


def format_error(error):
    error_id = error[0]
    error_data = error[1:]

    if error_id == 0:
        pc = int.from_bytes(error_data[0:4], byteorder='little')
        psr = int.from_bytes(error_data[4:8], byteorder='little')
        lr = int.from_bytes(error_data[8:12], byteorder='little')
        return 'Hard fault ({})\nData:\n\tPC: {}\n\tPSR: {}\n\tLR: {}'.format(error_id, pc, psr, lr)

    elif error_id == 1:
        task = bytes(error_data).decode("utf-8")
        return 'Stack overflow ({})\nTask: {}'.format(error_id, task)

    elif error_id == 2:
        line = int.from_bytes(error_data[0:4], byteorder='little')
        file = bytes(error_data[4:]).decode("utf-8")
        return 'Assertion failure ({})\nFile: {}, Line: {}'.format(error_id, file, line)

    elif error_id == 3:
        return 'Test error ({})\nData: {}'.format(error_id, error_data)

    else:
        return 'Unknown error id ({})\nData: {}'.format(error_id, error_data)


parser = argparse.ArgumentParser()
parser.add_argument('--inject-test-error', help='Record an error', action='store_true')
parser.add_argument('--read-all', help='Read and display stored errors', action='store_true')
parser.add_argument('--clear', help='Clear the error memory', action='store_true')

args = parser.parse_args()

if not (args.read_all or args.clear):
    parser.print_help()
else:
    with RevvyTransportI2C() as transport:
        robot_control = RevvyControl(transport.bind(0x2D))

        if args.inject_test_error:
            print('Recording a test error')
            robot_control.error_memory_test()

        if args.read_all:
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
