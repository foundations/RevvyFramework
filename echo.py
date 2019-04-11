#!/usr/bin/python3

import math
import struct
import rrrc_control as rrrc_control
import sys

def main():
    try:
        myrobot = rrrc_control.rrrc_control()
        i = 0
        out = "012345678901234567890123456789012345678901234567890123456789\n012345678901234567890123456789012345678901234567890123456789"
        d = "012345678901234567890123456789012345678901234567890123456789\n012345678901234567890123456789012345678901234567890123456789"
        while KeyboardInterrupt and d == out:
            try:
                d = myrobot.echo(out)
                print(d)
            except KeyboardInterrupt:
                break
            except:
                pass
    except KeyboardInterrupt:
        pass

    print ('terminated.')
    sys.exit(1)

if __name__ == "__main__":
    main()
