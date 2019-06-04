from revvy.functions import clip, map_values
from revvy.scripting.controllers import joystick, stick_contoller


def drive(args, controller):
    robot = args['robot']
    channels = args['input']
    x = clip((channels[0] - 127) / 127.0, -1, 1)
    y = clip((channels[1] - 127) / 127.0, -1, 1)
    (sl, sr) = controller(x, y)

    sl = map_values(sl, 0, 1, 0, 900)
    sr = map_values(sr, 0, 1, 0, 900)

    robot.drivetrain.set_speeds(sl, sr)


def drive_joystick(args):
    drive(args, joystick)


def drive_2sticks(args):
    drive(args, stick_contoller)
