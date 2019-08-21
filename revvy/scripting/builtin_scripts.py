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

    robot.drivetrain.set_speeds(sl, sr)


def drive_joystick(args):
    drive(args, expo_joystick)


def drive_2sticks(args):
    drive(args, stick_controller)
