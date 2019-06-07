def empty_callback():
    pass


class EdgeTrigger:
    def __init__(self):
        self._risingEdge = empty_callback
        self._fallingEdge = empty_callback
        self._previous = 0

    def on_rising_edge(self, l):
        self._risingEdge = l

    def on_falling_edge(self, l):
        self._fallingEdge = l

    def handle(self, value):
        if value > self._previous:
            self._risingEdge()
        elif value < self._previous:
            self._fallingEdge()
        self._previous = value


class LevelTrigger:
    def __init__(self):
        self._high = empty_callback
        self._low = empty_callback

    def on_high(self, l):
        self._high = l

    def on_low(self, l):
        self._low = l

    def handle(self, value):
        if value > 0:
            self._high()
        else:
            self._low()


class ToggleButton:
    def __init__(self):
        self._onEnabled = empty_callback
        self._onDisabled = empty_callback
        self._edgeDetector = EdgeTrigger()
        self._edgeDetector.on_rising_edge(self._toggle)
        self._isEnabled = False

    def _toggle(self):
        self._isEnabled = not self._isEnabled
        if self._isEnabled:
            self._onEnabled()
        else:
            self._onDisabled()

    def on_enabled(self, l):
        self._onEnabled = l

    def on_disabled(self, l):
        self._onDisabled = l

    def handle(self, value):
        self._edgeDetector.handle(0 if value <= 0 else 1)
