from threading import Lock


class ResourceHandle:
    def __init__(self, resource, callback=None):
        self._resource = resource
        self._callback = callback if callback is not None else lambda: None
        self._is_interrupted = False

    def release(self):
        self._resource.release(self)

    def interrupt(self):
        self._is_interrupted = True
        self._callback()

    def run(self, callback):
        with self._resource._lock:
            if not self._is_interrupted:
                callback()

    @property
    def is_interrupted(self):
        return self._is_interrupted


class Resource:
    def __init__(self):
        self._lock = Lock()
        self._current_priority = -1
        self._active_handle = None

    def request(self, with_priority=0, on_taken_away=None):
        with self._lock:
            if self._current_priority < with_priority:
                if self._active_handle is not None:
                    self._active_handle.interrupt()
                self._current_priority = with_priority
                self._active_handle = ResourceHandle(self, on_taken_away)
                return self._active_handle
            else:
                return None

    def release(self, resource_handle):
        with self._lock:
            if self._active_handle == resource_handle:
                self._active_handle = None
                self._current_priority = -1
