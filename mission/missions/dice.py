# Written by Will Smith.

from mission.framework.task import Task
from mission.framework.combinators import Sequential, Concurrent, MasterConcurrent, Retry, Conditional, While
from mission.framework.movement import Heading, RelativeToInitialHeading, VelocityX, VelocityY, Depth, RelativeToCurrentHeading, RelativeToCurrentDepth
from mission.framework.primitive import Log, NoOp, Zero, Succeed, Fail
from mission.framework.targeting import ForwardTarget, HeadingTarget, CameraTarget, PIDLoop
from mission.framework.timing import Timer, Timeout
from mission.framework.helpers import ConsistencyCheck, call_if_function

import shm

CAM_DIM = (shm.camera.forward_width.get(), shm.camera.forward_height.get())
CAM_CENTER = (shm.camera.forward_width.get()/2, shm.camera.forward_height.get()/2)

shm_vars = [shm.dice0, shm.dice1]

get_normed = lambda num: lambda: (shm_vars[num].center_x.get(), shm_vars[num].center_y.get())
                         #lambda: ((shm_vars[num].center_x.get() - CAM_CENTER[0]) / CAM_DIM[0],
                         #         (shm_vars[num].center_y.get() - CAM_CENTER[1]) / CAM_DIM[1])

#align_buoy = lambda num, db: ForwardTarget(get_normed(num), (0, 0), deadband=(db, db))

class ThetaTarget(CameraTarget):
    def on_first_run(self, *args, **kwargs):
        self.pid_loop_x = PIDLoop(output_function=RelativeToCurrentHeading(), negate=True)
        self.pid_loop_y = PIDLoop(output_function=RelativeToCurrentDepth(), negate=True)
        self.px_default = 10
        self.py_default = 0.8

align_buoy = lambda num, dbh, dbd: ThetaTarget((shm_vars[num].theta.get, lambda: shm_vars[num].depth.get() - shm.kalman.depth.get()), (0, 0))

class BoolSuccess(Task):
    def on_run(self, test):
        self.finish(success=call_if_function(test))

class Consistent(Task):
    def on_first_run(self, test, count, total, invert):
        self.checker = ConsistencyCheck(count, total, default=False)

    def on_run(self, test, count, total, invert):
        test_result = call_if_function(test)
        if self.checker.check(not test_result if invert else test_result):
            self.finish()

# MoveX for minisub w/o a DVL
def fake_move_x(d):
    v = 0.2
    if d < 0:
        d *= -1
        v *= -1
    return Sequential(MasterConcurrent(Timer(d / v), VelocityX(v)), Zero())

RamBuoy = lambda num: Retry(
    lambda: Sequential(
        Log('Ramming buoy {}'.format(num)),
        Log('Aligning...'),
        align_buoy(num=num, dbh=0.01, dbd=0.1),
        Log('Driving forward...'),
        MasterConcurrent(
            Consistent(lambda: shm_vars[num].visible.get, count=5, total=20, invert=True),
            VelocityX(0.2),
            align_buoy(num=num, dbh=0, dbd=0),
        ),
        Conditional(
            # Make sure that we are close enough to the buoy
            BoolSuccess(lambda: shm_vars[num].radius > 100),
            on_success=Sequential(
                Log('Ramming buoy...'),
                # Ram buoy
                fake_move_x(1),
                # Should be rammed
                fake_move_x(-2),
            ),
            on_fail=Fail(
                # We weren't close enough when we lost the buoy - back up and try again
                Sequential(
                    Log('Not close enough to buoy. Backing up...'),
                    Zero(),
                    fake_move_x(-1),
                ),
            )
        )
    ), attempts = 3
)

Full = Sequential(
    RamBuoy(num=0),
    RamBuoy(num=1),
)
