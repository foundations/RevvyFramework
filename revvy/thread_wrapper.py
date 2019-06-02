import traceback
from threading import Event, Thread


class ThreadWrapper:
    """
    Helper class to enable stopping/restarting threads from the outside
    Threads are not automatically stopped (as it is not possible), but a stop request can be read using the
    context object that is passed to the thread function
    """

    def __init__(self, func, name="WorkerThread"):
        self._exiting = False
        self._name = name
        self._stopping = False
        self._func = func
        self._stopped_callback = lambda: None
        self._stop_requested_callback = lambda: None
        self._control = Event()
        self._thread = Thread(target=self._thread_func, args=())
        self._thread.start()

    # noinspection PyBroadException
    def _thread_func(self):
        ctx = ThreadContext(self)
        while not self._exiting:
            self._control.wait()
            if not self._exiting:
                try:
                    self._func(ctx)
                except Exception:
                    print(traceback.format_exc())

                print('{}: stopped'.format(self._name))
                self._stopped_callback()
            self._control.clear()

    @property
    def stopping(self):
        return self._stopping

    def start(self):
        if self._exiting:
            raise AssertionError("Can't restart thread")
        print("{}: starting".format(self._name))
        self._stopping = False
        self._control.set()

    def stop(self):
        print("{}: stopping".format(self._name))
        self._stopping = True
        self._stop_requested_callback()

    def exit(self):
        self._exiting = True
        self.stop()
        print("{}: exiting".format(self._name))
        self._control.set()
        self._thread.join()
        print("{}: exited".format(self._name))

    def on_stopped(self, callback):
        self._stopped_callback = callback

    def on_stop_requested(self, callback):
        self._stop_requested_callback = callback


class ThreadContext:
    def __init__(self, thread: ThreadWrapper):
        self._thread = thread

    @property
    def stop_requested(self):
        return self._thread.stopping

    def on_stopped(self, callback):
        self._thread.on_stop_requested(callback)
