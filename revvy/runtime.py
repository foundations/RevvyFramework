from revvy.thread_wrapper import *
import time


class ScriptHandle:
    def __init__(self, script, name, global_variables: dict):
        self._globals = global_variables

        self._thread = ThreadWrapper(self._run, 'ScriptThread: {}'.format(name))

        if callable(script):
            self._runnable = script
        else:
            self._runnable = lambda x: exec(script, x)

    def on_stopped(self, callback):
        self._thread.on_stopped(callback)

    def assign(self, name, value):
        self._globals[name] = value

    def _run(self, ctx):
        self._runnable({**self._globals, 'ctx': ctx, 'time': time})

    def start(self):
        self._thread.start()

    def stop(self):
        self._thread.stop()

    def cleanup(self):
        self._thread.exit()


class ScriptManager:
    def __init__(self):
        self._globals = {}
        self._scripts = {}

    def reset(self):
        for script in self._scripts:
            self._scripts[script].cleanup()

        self._globals = {}
        self._scripts = {}

    def assign(self, name, value):
        self._globals[name] = value
        for script in self._scripts:
            self._scripts[script].assign(name, value)

    def __setitem__(self, name, script):
        if name in self._scripts:
            self._scripts[name].cleanup()

        print('New script: {}'.format(name))
        self._scripts[name] = ScriptHandle(script, name, self._globals)

    def __getitem__(self, name):
        return self._scripts[name]
