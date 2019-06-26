import traceback
from threading import Event, Thread


def _call_callbacks(cb_list):
    for cb in list(cb_list):
        keep_callback = cb()
        if not keep_callback:
            cb_list.remove(cb)


class ThreadWrapper:
    """
    Helper class to enable stopping/restarting threads from the outside
    Threads are not automatically stopped (as it is not possible), but a stop request can be read using the
    context object that is passed to the thread function
    """

    def __init__(self, func, name="WorkerThread"):
        print("ThreadWrapper: create {}".format(name))
        self._exiting = False
        self._name = name
        self._func = func
        self._stopped_callbacks = []
        self._stop_requested_callbacks = []
        self._control = Event()
        self._thread_running_event = Event()
        self._ctx = None
        self._thread = Thread(target=self._thread_func, args=())
        self._thread.start()

    def _wait_for_start(self):
        self._control.wait()
        self._control.clear()

        return not self._exiting

    # noinspection PyBroadException
    def _thread_func(self):
        while self._wait_for_start():
            try:
                self._ctx = ThreadContext(self)
                self._thread_running_event.set()
                self._func(self._ctx)
            except InterruptedError:
                print('{}: interrupted'.format(self._name))
            except Exception:
                print(traceback.format_exc())
            finally:
                print('{}: stopped'.format(self._name))
                self._thread_running_event.clear()
                _call_callbacks(self._stopped_callbacks)
                self._ctx = None

    @property
    def stopping(self):
        if self._ctx is None:
            return False
        return self._ctx.stop_requested

    @property
    def is_running(self):
        return self._thread_running_event.is_set()

    def start(self):
        if self._exiting:
            raise AssertionError("Can't restart thread")

        print("{}: starting".format(self._name))
        self._control.set()

        return self._thread_running_event

    def stop(self):
        print("{}: stopping".format(self._name))
        evt = Event()
        if self._thread_running_event.is_set():
            self.on_stopped(evt.set)

            if self._ctx is not None:
                self._ctx.stop()

            _call_callbacks(self._stop_requested_callbacks)
        else:
            evt.set()

        return evt

    def exit(self):
        self._exiting = True
        self.stop()
        print("{}: exiting".format(self._name))
        self._control.set()
        self._thread.join()
        print("{}: exited".format(self._name))

    def on_stopped(self, callback):
        self._stopped_callbacks.append(callback)

    def on_stop_requested(self, callback):
        self._stop_requested_callbacks.append(callback)


class ThreadContext:
    def __init__(self, thread: ThreadWrapper):
        self._thread = thread
        self._stop_event = Event()

    def stop(self):
        self._stop_event.set()

    def sleep(self, s):
        if self._stop_event.wait(s):
            raise InterruptedError

    @property
    def stop_requested(self):
        return self._stop_event.is_set()

    def on_stopped(self, callback):
        self._thread.on_stop_requested(callback)
