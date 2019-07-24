import subprocess


def _run_command(commands):
    if type(commands) is str:
        commands = [commands]

    command = '; '.join(commands)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    process.wait()
    return process.returncode


def setup_sound_v1():
    _run_command([
        'gpio -g mode 13 alt0',
        'gpio -g mode 22 out'
    ])


def setup_sound_v2():
    _run_command([
        'gpio -g mode 13 alt0',
        'gpio -g mode 22 out',
        'gpio write 3 1'
    ])


def play_sound_v1(sound):
    print('Playing sound: {}'.format(sound))

    _run_command([
        "gpio write 3 1",
        "mpg123 {}".format(sound),
        "gpio write 3 0"
    ])


def play_sound_v2(sound):
    print('Playing sound: {}'.format(sound))

    _run_command([
        "gpio write 3 0",
        "mpg123 {}".format(sound),
        "gpio write 3 1"
    ])
