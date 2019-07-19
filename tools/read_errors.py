import argparse

from revvy.hardware_dependent.rrrc_transport_i2c import RevvyTransportI2C
from revvy.mcu.rrrc_control import RevvyControl

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
                    print('Error {}'.format(i))
                    print(repr(error))
                    print('----------------------------------------')
                    i += 1

        if args.clear:
            print('Clearing error memory...')
            robot_control.error_memory_clear()
            print('Error memory cleared')
