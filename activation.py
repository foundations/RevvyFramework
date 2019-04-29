def empty_callback():
    pass


class EdgeTrigger:
    def __init__(self):
        self._risingEdge = empty_callback
        self._fallingEdge = empty_callback
        self._previous = 0

    def onRisingEdge(self, l):
        self._risingEdge = l

    def onFallingEdge(self, l):
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

    def onHigh(self, l):
        self._high = l

    def onLow(self, l):
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
        self._edgeDetector.onRisingEdge(self._toggle)
        self._isEnabled = False

    def _toggle(self):
        self._isEnabled = not self._isEnabled
        if self._isEnabled:
            self._onEnabled()
        else:
            self._onDisabled()

    def onEnabled(self, l):
        self._onEnabled = l

    def onDisabled(self, l):
        self._onDisabled = l

    def handle(self, value):
        self._edgeDetector.handle(value)
