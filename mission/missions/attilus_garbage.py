from mission.framework.task import Task
from mission.framework.helpers import ConsistencyCheck, call_if_function
from mission.framework.targeting import PIDLoop
from mission.framework.movement import VelocityX, VelocityY, RelativeToCurrentHeading, RelativeToInitialHeading, PositionN, PositionE
from mission.framework.position import MoveX, WithPositionalControl
from mission.framework.combinators import While, Sequential, MasterConcurrent, Concurrent
from mission.framework.primitive import FunctionTask, Succeed, Zero, Log, Fail
from mission.framework.timing import Timed

import shm
"""
A bunch of garbage that I (Attilus) want to use across different missions.
"""

# A task that runs a PID loop for VelocityY
class PIDSway(Task):
    def on_first_run(self, *args, **kwargs):
        self.pid_loop = PIDLoop(output_function=VelocityY())

    def on_run(self, error, p=0.0005,  i=0, d=0.0, db=0.01875, max_out=0.5, negate=False, *args, **kwargs):
        self.pid_loop(input_value=error, p=p, i=i, d=d, target=0, modulo_error=False, deadband=db, negate=negate, max_out=max_out)

    def stop(self):
        VelocityY(0)()

# A task that runs a PID loop for VelocityX
class PIDStride(Task):
    def on_first_run(self, *args, **kwargs):
        self.pid_loop = PIDLoop(output_function=VelocityX())

    def on_run(self, error, p=0.00003,  i=0, d=0.0, db=0.01875, negate=False, max_out=0.5, *args, **kwargs):
        self.pid_loop(input_value=error, p=p, i=i, d=d, target=0, modulo_error=False, deadband=db, negate=negate, max_out=max_out)

    def stop(self):
        VelocityY(0)()

# A task that runs a PID loop for Heading
class PIDHeading(Task):
    def on_first_run(self, *args, **kwargs):
        self.pid_loop = PIDLoop(output_function=RelativeToCurrentHeading())

    def on_run(self, error, p=0.35,  i=0, d=0.0, db=0.01875, negate=False, max_out=20, *args, **kwargs):  # TODO: max_out
        self.pid_loop(input_value=error, p=p, i=i, d=d, target=0, modulo_error=360, deadband=db, negate=negate, max_out=max_out)

    def stop(self):
        RelativeToCurrentHeading(0)()

class StillHeadingSearch(Task):
    """
    Search for an object visible from the current location that is in front of
    the sub with highest probability. Edited from ozer_common
    """

    def on_first_run(self, speed=40, db=10, *args, **kwargs):
        init_heading = None

        def set_init_heading():
            nonlocal init_heading
            init_heading = shm.kalman.heading.get()
            return True

        set_init_heading()

        self.use_task(
            While(lambda: Sequential(
                RelativeToInitialHeading(speed),
                MasterConcurrent(
                    FunctionTask(lambda: abs(shm.desires.heading.get() - init_heading) < db, finite=False),
                    RelativeToCurrentHeading(speed)),
                # Move back a bit, we might be too close
                MoveX(-1),
                Succeed(FunctionTask(set_init_heading))
            ), True),
        )


# Sway search but without moving forward
def SwayOnlySearch(speed=0.3, width=2.5, right_first=True):
    direction = 1 if right_first else -1
    return Sequential(
            Log('what'),
            Timed(VelocityY(direction*speed), width/(2*speed)),
            Timed(VelocityY(-direction*speed), width/(speed)),
            Timed(VelocityY(direction*speed), width/(2*speed)),
            Zero())


def MoveNE(vector, deadband=0.1):
    return WithPositionalControl(
            Concurrent(PositionN(target=vector[0], error=deadband),
                       PositionE(target=vector[1], error=deadband),
                       finite=False))


class PositionMarkers:
    def __init__(self):
        self._markers = {}

    def _set(self, marker):
        value = (shm.kalman.north.get(), shm.kalman.east.get())
        self._markers[marker] = value
        return value

    def set(self, marker):
        return Log('Setting marker {} as {}'.format(marker, self._set(marker)))

    def _unset(self, marker):
        try:
            del self._markers[marker]
            return True
        except KeyError:
            return False

    def unset(self, marker):
        if self._unset(marker):
            return Log('Marker {} successfully unset'.format(marker))
        return Sequential(Log('Attempting to unset nonexistent marker {}'.format(marker)), Fail())

    def get(self, marker):
        try:
            return self._markers[marker]
        except KeyError:
            return None

    def go_to(self, marker, deadband=0.1):
        target = self.get(marker)
        if target is not None:
            return Sequential(Log('Moving to marker {} at {}'.format(marker, target)), MoveNE(target, deadband))
        return Sequential(Log('Going to nonexistent marker {}'.format(marker)), Fail())
