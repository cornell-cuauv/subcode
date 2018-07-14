# Written by Will Smith.

from mission.framework.task import Task
from mission.framework.combinators import Sequential, Concurrent, MasterConcurrent, Retry, Conditional, While
from mission.framework.movement import Heading, RelativeToInitialHeading, VelocityX, VelocityY, Depth, RelativeToCurrentHeading, RelativeToCurrentDepth
from mission.framework.primitive import Log, NoOp, Zero, Succeed, Fail, FunctionTask
from mission.framework.targeting import ForwardTarget, HeadingTarget, CameraTarget, PIDLoop
from mission.framework.timing import Timer, Timeout, Timed
from mission.framework.helpers import ConsistencyCheck, call_if_function

import shm

CAM_DIM = (shm.camera.forward_width.get(), shm.camera.forward_height.get())
CAM_CENTER = (shm.camera.forward_width.get()/2, shm.camera.forward_height.get()/2)

shm_vars = [shm.dice0, shm.dice1]

align_buoy = lambda num, db: ForwardTarget((shm_vars[num].center_x.get, shm_vars[num].center_y.get), target=(0, 0), deadband=(db, db), px=0.8, py=0.8)

class BoolSuccess(Task):
    def on_run(self, test):
        result = call_if_function(test)
        print('result', result)
        self.finish(success=result)

class Consistent(Task):
    def on_first_run(self, test, count, total, invert, result):
        self.checker = ConsistencyCheck(count, total, default=False)

    def on_run(self, test, count, total, invert, result):
        test_result = call_if_function(test)
                
        if self.checker.check(not test_result if invert else test_resultz):
            self.finish(success=result)

# MoveX for minisub w/o a DVL
def fake_move_x(d):
    v = 0.4
    if d < 0:
        v *= -1
    return Sequential(MasterConcurrent(Timer(d / v), VelocityX(v)), VelocityX(0))

MIN_DIST = 50

RamBuoy = lambda num: Retry(
    lambda: Sequential(
        Log('Ramming buoy {}'.format(num)),
        MasterConcurrent(
            Consistent(lambda: shm_vars[num].visible.get() and shm_vars[num].radius.get() < MIN_DIST, count=1*60, total=3*60, invert=True, result=True),
            Sequential(
                Log('Aligning...'),
                align_buoy(num=num, db=0.01),
                Log('Driving forward...'),
                VelocityX(0.2),
                align_buoy(num=num, db=0),
            ),
        ),
        VelocityY(0),
        Conditional(
            # Make sure that we are close enough to the buoy
            BoolSuccess(lambda: shm_vars[num].radius.get() >= MIN_DIST),
            on_success=Sequential(
                Log('Ramming buoy...'),
                # Ram buoy
                fake_move_x(1),
                Log('Backing up...'),
                # Should be rammed
                fake_move_x(-2),
            ),
            on_fail=Fail(
                # We weren't close enough when we lost the buoy - back up and try again
                Sequential(
                    Log('Not close enough to buoy ({}). Backing up...'.format(shm_vars[num].radius.get())),
                    Zero(),
                    fake_move_x(-3),
                ),
            )
        )
    ), attempts = 3
)

def pick_correct_buoy(num):
    # We assume that we can see both buoys
    coords = [(var.center_x.get(), var.center_y.get()) for var in shm_vars]
    required_diff = 0.1

    axis = not (abs(coords[1][0] - coords[0][0]) > required_diff)
    return num if coords[1][axis] > coords[0][axis] else int(not num)

Full = Sequential(
    RamBuoy(num=pick_correct_buoy(0)),
    RamBuoy(num=pick_correct_buoy(1)),
)
