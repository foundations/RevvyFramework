import subprocess


def _run_command(commands):
    if type(commands) is str:
        commands = [commands]

    command = '; '.join(commands)
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    process.wait()
    return process.returncode


def setup_sound():
    _run_command([
        'gpio -g mode 13 alt0',
        'gpio -g mode 22 out'
    ])


def play_sound(sound):
    print('Playing sound: {}'.format(sound))

    _run_command([
        "gpio write 3 1",
        "mpg123 {}".format(sound),
        "gpio write 3 0"
    ])
