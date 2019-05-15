from threading import Thread
import time


class ScriptContext:
    def __init__(self):
        self.exit_requested = False


class ScriptHandle:
    def __init__(self, script, global_variables: dict):
        self._context = ScriptContext()
        self._globals = {
            **global_variables,
            'thread': self._context,
            'time':   time
        }

        self._thread = Thread(target=exec, args=(script, self._globals))
        self._thread.start()

    def stop(self):
        self._context.exit_requested = True
        self._thread.join()


class ScriptRunner:
    def __init__(self):
        self._globals = {}

    def set(self, global_variables: dict):
        self._globals = {**self._globals, **global_variables}

    def run(self, script, global_variables: dict = None):
        if not global_variables:
            global_variables = {}
        return ScriptHandle(script, {**self._globals, **global_variables})
