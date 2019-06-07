class Sound:
    def __init__(self, setup, play, sounds=None):
        if sounds is None:
            sounds = {}
        setup()

        self._play = play
        self._sounds = sounds

    def play_tune(self, name):
        self._play(self._sounds[name])
