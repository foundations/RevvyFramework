from threading import Lock, Event

from revvy.activation import EdgeTrigger
from revvy.thread_wrapper import ThreadWrapper, ThreadContext


class RemoteController:
    def __init__(self):
        self._button_mutex = Lock()

        self._analogActions = []
        self._analogStates = []
        self._buttonHandlers = []
        self._buttonStates = [False] * 32

        self._controller_detected = lambda: None
        self._controller_disappeared = lambda: None

        for i in range(32):
            self._buttonHandlers.append(EdgeTrigger())

    def is_button_pressed(self, button_idx):
        with self._button_mutex:
            return self._buttonStates[button_idx]

    def analog_value(self, analog_idx):
        try:
            with self._button_mutex:
                return self._analogStates[analog_idx]
        except IndexError:
            return 0

    def reset(self):
        print('RemoteController: reset')
        with self._button_mutex:
            self._analogActions.clear()
            self._analogStates.clear()
            for handler in self._buttonHandlers:
                handler.on_rising_edge(lambda: None)

            self._buttonStates = [False] * 32

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
        self._buttonHandlers[button].on_rising_edge(action)

    def on_analog_values(self, channels, action):
        self._analogActions.append({'channels': channels, 'action': action})


class RemoteControllerScheduler:
    def __init__(self, rc: RemoteController):
        self._controller = rc
        self._data_ready_event = Event()
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

    def handle_controller(self, ctx: ThreadContext):
        print('RemoteControllerScheduler: Waiting for controller')

        self._data_ready_event.clear()

        ctx.on_stopped(self._data_ready_event.set)

        # wait for first message
        first = True
        while self._data_ready_event.wait(None if first else 0.5):
            if ctx.stop_requested:
                break

            if first:
                self._controller_detected_callback()
                first = False

            self._data_ready_event.clear()
            self._controller.tick(self.get_message())

        if not ctx.stop_requested:
            self._controller_lost_callback()

        # reset here, controller was lost or stopped
        self._controller.reset()

    def on_controller_detected(self, callback):
        print('RemoteControllerScheduler: Register controller found handler')
        self._controller_detected_callback = callback

    def on_controller_lost(self, callback):
        print('RemoteControllerScheduler: Register controller lost handler')
        self._controller_lost_callback = callback


class RemoteControllerThread(ThreadWrapper):
    def __init__(self, rcs: RemoteControllerScheduler):
        self._scheduler = rcs

        super().__init__(self._run, "RemoteControllerThread")

    def _run(self, ctx: ThreadContext):
        while not ctx.stop_requested:
            self._scheduler.handle_controller(ctx)
        print('RemoteControllerScheduler: Stopped')
