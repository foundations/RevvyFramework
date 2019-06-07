import subprocess
import gpiozero


amp_en = gpiozero.LED(22)


def setup_sound():
    subprocess.Popen("gpio -g mode 13 alt0", stdout=subprocess.PIPE, shell=True).wait()


def play_sound(sound):
    print('Playing sound: {}'.format(sound))

    amp_en.on()
    subprocess.Popen("mpg123 {}".format(sound), stdout=subprocess.PIPE, shell=True).wait()
    amp_en.off()
