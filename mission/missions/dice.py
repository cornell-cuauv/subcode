# Written by Will Smith.

from mission.framework.task import Task
from mission.framework.combinators import Sequential, Concurrent, MasterConcurrent, Retry, Conditional, While
from mission.framework.movement import Heading, RelativeToInitialHeading, VelocityX, VelocityY, Depth
from mission.framework.primitive import Log, NoOp, Zero, Succeed, Fail
from mission.framework.targeting import ForwardTarget
from mission.framework.timing import Timer, Timeout
from mission.framework.helpers import ConsistencyCheck, call_if_function

import shm

CAM_CENTER = (shm.cameras.forward.width/2, shm.cameras.forward.height/2)

shm_vars = [shm.dice0, shm.dice1, shm.dice2, shm.dice3]

align_buoy = lambda num, db: ForwardTarget((shm_vars[num].center_x.get, shm_vars[num].center_y.get), CAM_CENTER, deadband)

class BoolSuccess(Task):
    def on_run(self, test):
        self.finish(success=call_if_function(test))

class Consistent(Task):
    def on_first_run(self, test, count, total, invert):
        self.checker = ConsistencyCheck(count, total, default=False)

    def on_run(self, test, count, total, invert):
        test_result = call_if_function(not test if invert else test))
        if self.checker.check(test_result):
            self.finish()

# MoveX for minisub w/o a DVL
def fake_move_x(d):
    v = 0.2
    if d < 0:
        d *= -1
        v *= -1
    return Sequential(MasterConcurrent(Timer(d / v), VelocityX(v)), Zero())

RamBuoy = lambda num: Retry(
    Sequential(
        align_buoy(num=num, db=80),
        MasterConcurrent(
            Consistent(lambda: shm_vars[num].visible.get, count=5, total=20, invert=True),
            VelocityX(0.2),
            align_buoy(num=num, db=0),
        ),
        Conditional(
            # Make sure that we are close enough to the buoy
            BoolSuccess(lambda: shm_vars[num].radius > 100),
            on_success=Sequential(
                # Ram buoy
                fake_move_x(1),
                # Should be rammed
                fake_move_x(-2),
            ),
            on_fail=Fail(
                # We weren't close enough when we lost the buoy - back up and try again
                Sequential(
                    Zero(),
                    fake_move_x(-1),
                ),
            )
        )
    ), attempts = 3
)

# Hey... this isn't going to work
# Because we sort dice based on number of sides
# Once we get close enough to not see the second one, the num will switch
# How to reconcile this? Need to actually keep track of which dice is which
# SLAM?

Full = Sequential(
    # TODO figure out which buoy is which consistently
    RamBuoy(num=0),
    RamBuoy(num=1),
)
