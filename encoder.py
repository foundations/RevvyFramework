#!/usr/bin/python3

import math
import struct
import rrrc_control as rrrc_control
import time
import sys

pid = [1, 0, 0, -10, 10]


def main():
    myrobot = rrrc_control.rrrc_control()
    try:

        for j in range(6):
            myrobot.motor_set_type(j, myrobot.motors["MOTOR_SPEED_CONTROLLED"])
            myrobot.motor_set_state(j, 0)
            (p, i, d, ll, ul) = pid
            pidConfig = bytearray(struct.pack(">" + 5 * "f", p, i, d, ll, ul))
            myrobot.motor_set_config(j, pidConfig)
            myrobot.motor_set_state(j, 10)

        while KeyboardInterrupt:
            poss = [0, 0, 0, 0, 0, 0]
            for i in range(6):
                poss[i] = "{}".format(myrobot.motor_get_position(i))

            print(", ".join(poss))
            time.sleep(1)
    except KeyboardInterrupt:
        for i in range(6):
            myrobot.motor_set_type(i, 0)

    print('terminated.')
    sys.exit(1)


if __name__ == "__main__":
    main()
