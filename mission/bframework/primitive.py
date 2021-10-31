import shm
from mission.bframework.task import Task

class NoOp(Task):
    def run(self):
        pass

# Not so sure I understand the spec for this one
class FunctionTask(Task):
    def run(self, func, finite=True):
        if finite:
            ret = func()
            return ret is None or ret
        while True:
            ret = func()
            success = ret is None or ret
            if success:
                return True

class ZeroWithoutHeading(Task):
    def run(self, pitch=True, roll=True):
        Depth(shm.kalman.depth.get())()
        PositionN(shm.kalman.north.get(), positional_controls=None)()
        PositionE(shm.kalman.east.get(), positional_controls=None)()
        Pitch(0)() if pitch else Pitch(shm.kalman.pitch.get())()
        Roll(0)() if roll else Roll(shm.kalman.roll.get())()
        VelocityX(0, positional_controls=None)()
        VelocityY(0, positional_controls=None)()
        return True

class Zero(Task):
    def run(self, pitch=True, roll=True):
        Heading(shm.kalman.heading.get())()
        ZeroWithoutHeading(pitch=pitch, roll=roll)()
        return True

class EnableController(Task):
    def run(self):
        shm.settings_control.enabled.set(1)
        shm.settings_control.heading_active.set(1)
        shm.settings_control.pitch_active.set(1)
        shm.settings_control.roll_active.set(1)
        shm.settings_control.velx_active.set(1)
        shm.settings_control.vely_active.set(1)
        shm.settings_control.depth_active.set(1)
        return True

class HardkillGuarded(Task):
    def run(self, task):
        if shm.switches.hard_kill.get():
            return True
        task()
        return True

class Log(Task):
    def run(self, message, level="info"):
        pass #TODO: Implement

class AlwaysLog(Task):
    def run(self, message, level="info"):
        pass #TODO: Implement

class Succeed(Task):
    def run(self, task=None, override=True):
        if task is not None:
            task()
        return True

class Fail(Task):
    def run(self, task=None):
        if task is not None:
            task()
        return False

class InvertSuccess(Task):
    def run(self, task):
        return not task()
