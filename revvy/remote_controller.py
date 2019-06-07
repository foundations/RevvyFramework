from threading import Lock, Event

from revvy.activation import EdgeTrigger
from revvy.thread_wrapper import ThreadWrapper, ThreadContext


class RemoteController:
    def __init__(self):
        self._button_mutex = Lock()

        self._analogActions = []
        self._analogStates = []
        self._buttonActions = [lambda: None] * 32
        self._buttonHandlers = [None] * 32

        self._buttonStates = [False] * 32
        self._controller_detected = lambda: None
        self._controller_disappeared = lambda: None

        self._message = None
        self._missedKeepAlives = -1

        for i in range(len(self._buttonHandlers)):
            handler = EdgeTrigger()
            handler.on_rising_edge(lambda idx=i: self._button_pressed(idx))
            self._buttonHandlers[i] = handler

    def is_button_pressed(self, button_idx):
        with self._button_mutex:
            return self._buttonStates[button_idx]

    def analog_value(self, analog_idx):
        with self._button_mutex:
            return self._analogStates[analog_idx]

    def _button_pressed(self, idx):
        print('Button {} pressed'.format(idx))
        action = self._buttonActions[idx]
        if action:
            action()

    def reset(self):
        print('RemoteController: reset')
        with self._button_mutex:
            self._analogActions.clear()
            self._analogStates.clear()
            self._buttonActions = [lambda: None] * 32

            self._buttonStates = [False] * 32
            self._message = None
            self._missedKeepAlives = -1

    def tick(self, message):
        # copy states
        with self._button_mutex:
            self._analogStates = message['analog']
            self._buttonStates = message['buttons']

        # handle analog channels
        for handler in self._analogActions:
            # check if all channels are present in the message
            if all(map(lambda x: x < len(message['analog']), handler['channels'])):
                values = list(map(lambda x: message['analog'][x], handler['channels']))
                handler['action'](values)
            else:
                print('Skip analog handler for channels {}'.format(",".join(map(str, handler['channels']))))

        # handle button presses
        for idx in range(len(self._buttonHandlers)):
            with self._button_mutex:
                self._buttonHandlers[idx].handle(message['buttons'][idx])

    def on_button_pressed(self, button, action):
        self._buttonActions[button] = action

    def on_analog_values(self, channels, action):
        self._analogActions.append({'channels': channels, 'action': action})


class RemoteControllerScheduler(ThreadWrapper):
    def __init__(self, rc: RemoteController):
        self._controller = rc
        self._data_ready_event = Event()
        super().__init__(self._schedule_controller, "RemoteControllerThread")
        self._controller_detected_callback = lambda: None
        self._controller_lost_callback = lambda: None
        self._data_mutex = Lock()
        self._message = None

    def data_ready(self, message):
        with self._data_mutex:
            self._message = message
        self._data_ready_event.set()

    def get_message(self):
        with self._data_mutex:
            return self._message

    def _schedule_controller(self, ctx: ThreadContext):
        while not ctx.stop_requested:
            # wait for first message
            self._data_ready_event.wait()

            if ctx.stop_requested:
                break

            self._controller_detected_callback()

            self._data_ready_event.clear()
            self._controller.tick(self.get_message())

            while self._data_ready_event.wait(0.5):
                if ctx.stop_requested:
                    break

                self._data_ready_event.clear()
                self._controller.tick(self.get_message())

            if ctx.stop_requested:
                break

            self._controller_lost_callback()

    def start(self):
        self._data_ready_event.clear()
        super().start()

    def stop(self):
        super().stop()
        # break out of a wait-for-message
        self._data_ready_event.set()

    def reset(self):
        self.stop()
        if not self._exiting:
            self._controller.reset()

    def on_controller_detected(self, callback):
        self._controller_detected_callback = callback

    def on_controller_lost(self, callback):
        self._controller_lost_callback = callback
