import traceback
import math


def clip(x, min_x, max_x):
    """Constrain a number between two limits

    >>> clip(3, 1, 2)
    2
    >>> clip(0, 1, 2)
    1
    >>> clip(1.5, 1, 2)
    1.5
    """
    if x < min_x:
        return min_x
    if x > max_x:
        return max_x
    return x


def map_values(x, min_x, max_x, min_y, max_y):
    """Scales a number from the input range of [min_x, max_x] to between [min_y, max_y]

    >>> map_values(0.5, 0, 1, 0, 900)
    450.0
    >>> map_values(math.pi/2, 0, math.pi, 0, 180)
    90.0
    >>> map_values(8, 0, 10, 5, 0)
    1.0
    """
    full_scale_in = max_x - min_x
    full_scale_out = max_y - min_y
    return (x - min_x) * (full_scale_out / full_scale_in) + min_y


def getserial():
    """Extract serial from cpuinfo file"""

    cpu_serial = "0000000000000000"
    # noinspection PyBroadException
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    cpu_serial = line.rstrip()[-16:]
                    break
    except Exception:
        cpu_serial = "ERROR000000000"

    return cpu_serial


def retry(fn, retries=5):
    """Retry the given function a number of times, or until it returns True or None"""
    status = False
    retry_num = 0
    while retry_num < retries and not status:
        # noinspection PyBroadException
        try:
            status = fn()
            if status is None:
                status = True
        except Exception:
            print(traceback.format_exc())
            status = False
        retry_num += 1

    return status


def hex2rgb(hex_str):
    """
    >>> hex2rgb("#aabbcc")
    11189196
    """
    stripped_hex = hex_str.lstrip('#')
    rgb = tuple(int(stripped_hex[i:i + 2], 16) for i in range(0, len(stripped_hex), 2))

    return rgb[0] << 16 | rgb[1] << 8 | rgb[2]
