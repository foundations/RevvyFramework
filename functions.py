def clip(x, min_x, max_x):
    if x < min_x:
        return min_x
    if x > max_x:
        return max_x
    return x


def map_values(x, min_x, max_x, min_y, max_y):
    full_scale_in = max_x - min_x
    full_scale_out = max_y - min_y
    return (x - min_x) * (full_scale_out / full_scale_in) + min_y


def getserial():
    # Extract serial from cpuinfo file
    cpu_serial = "0000000000000000"
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line[0:6] == 'Serial':
                    cpu_serial = line.rstrip()[-16:]
                    break
    except:
        cpu_serial = "ERROR000000000"

    return cpu_serial
