from revvy.functions import clip, map_values
from revvy.scripting.controllers import stick_controller, expo_joystick


def normalize_analog(b):
    """
    >>> normalize_analog(0)
    -1.0
    >>> normalize_analog(255)
    1.0
    >>> normalize_analog(127)
    0.0
    """
    return clip((b - 127) / 127.0, -1.0, 1.0)


def drive(args, controller):
    robot = args['robot']
    channels = args['input']

    x = normalize_analog(channels[0])
    y = normalize_analog(channels[1])

    (sl, sr) = controller(x, y)

    sl = map_values(sl, 0, 1, 0, 900)
    sr = map_values(sr, 0, 1, 0, 900)

    robot.joystick.set_speeds(sl, sr)


def drive_joystick(args):
    drive(args, expo_joystick)


def drive_2sticks(args):
    drive(args, stick_controller)


def imu_test(args):
    """Simple script that points in the 0° yaw angle direction"""
    robot = args['robot']
    time = args['time']
    ctx = args['ctx']

    prev_angle = 1

    robot.led_ring.set(list(range(1, 13)), "000000")
    robot.led_ring.set(1, "00ff00")

    while not ctx.stop_requested:
        angle = (((robot.imu.yaw_angle - 30) % 360) // 30) + 1

        if angle != prev_angle:
            robot.led_ring.set(angle, "00ff00")
            robot.led_ring.set(prev_angle, "000000")

            prev_angle = angle

        time.sleep(0.1)


builtin_scripts = {
    'drive_2sticks': drive_2sticks,
    'drive_joystick': drive_joystick,
    'imu_test': imu_test  # necessary to allow the default configuration remain simple
}
