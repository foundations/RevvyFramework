from revvy.scripting.robot_interface import RobotInterface
from revvy.thread_wrapper import *
import time


class TimeWrapper:
    def __init__(self, ctx: ThreadContext):
        self._ctx = ctx

    # noinspection PyMethodMayBeStatic
    def time(self):
        return time.time()

    def sleep(self, s):
        self._ctx.sleep(s)


class ScriptHandle:
    def __init__(self, owner, script, name, global_variables: dict):
        self._owner = owner
        self._globals = dict(global_variables)
        self._thread = ThreadWrapper(self._run, 'ScriptThread: {}'.format(name))
        self._thread_ctx = None

        if callable(script):
            self._runnable = script
        else:
            self._runnable = lambda x: exec(script, x)

    @property
    def is_stop_requested(self):
        return self._thread.stopping

    @property
    def is_running(self):
        return self._thread.is_running

    def on_stopped(self, callback):
        self._thread.on_stopped(callback)

    def assign(self, name, value):
        self._globals[name] = value

    def _run(self, ctx):
        try:
            # script control interface
            ctx.terminate = self._terminate
            ctx.terminate_all = self._owner.stop_all_scripts

            self._thread_ctx = ctx
            self._runnable({
                **self._globals,
                'Control': ctx,
                'ctx': ctx,
                'time': TimeWrapper(ctx)
            })
        finally:
            self._thread_ctx = None

    def sleep(self, s):
        if self._thread_ctx is not None:
            self._thread_ctx.sleep(s)

    def start(self):
        self._thread.start()

    def stop(self):
        self._thread.stop()

    def cleanup(self):
        self._thread.exit()

    def _terminate(self):
        self.stop()
        raise InterruptedError


class ScriptManager:
    def __init__(self, robot):
        self._robot = robot
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

    def add_script(self, name, script, priority=0):
        if name in self._scripts:
            self._scripts[name].cleanup()

        print('New script: {}'.format(name))
        script = ScriptHandle(self, script, name, self._globals)
        script.assign('robot', RobotInterface(script, self._robot, priority))
        self._scripts[name] = script

    def __getitem__(self, name):
        return self._scripts[name]

    def stop_all_scripts(self):
        for script in self._scripts:
            self._scripts[script].stop()
