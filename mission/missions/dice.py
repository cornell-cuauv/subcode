# Written by Will Smith.

from mission.framework.task import Task
from mission.framework.combinators import Sequential, Concurrent, MasterConcurrent, Retry, Conditional, While, Either
from mission.framework.movement import Heading, RelativeToInitialHeading, VelocityX, VelocityY, Depth, RelativeToCurrentHeading, RelativeToCurrentDepth
from mission.framework.primitive import Log, NoOp, Zero, Succeed, Fail, FunctionTask
from mission.framework.targeting import ForwardTarget, HeadingTarget, CameraTarget, PIDLoop
from mission.framework.timing import Timer, Timeout, Timed
from mission.framework.helpers import ConsistencyCheck, call_if_function

import shm

CAM_DIM = (shm.camera.forward_width.get(), shm.camera.forward_height.get())
CAM_CENTER = (shm.camera.forward_width.get()/2, shm.camera.forward_height.get()/2)

shm_vars = [shm.dice0, shm.dice1]

# True for HeadingTarget, False for ForwardTarget
HEADING_TARGET = False

# True for simulator, False for on sub
SIMULATOR = True

buoy_pick_checker = ConsistencyCheck(15, 20, default=0)

def __correct_buoy(num):
    if shm_vars[1].visible.get():
        # We assume that we can see both buoys
        coords = [(var.center_x.get(), var.center_y.get()) for var in shm_vars]
        required_diff = 0.04

        axis = not (abs(coords[1][0] - coords[0][0]) > required_diff)
        return num if coords[1][axis] > coords[0][axis] else int(not num)
    else:
        return 0

# TODO the sub can get stuck going back and forth between the two buoys because the nums are not consistent
def update_correct_buoy(num):
    buoy_pick_checker.check(__correct_buoy(num))
    #print(buoy_pick_checker.state)

def pick_correct_buoy(num, ret=True):
    return buoy_pick_checker.state

MAX_DEPTH = 2.4

def align_buoy(num, db, mult=1):
    if HEADING_TARGET:
        return HeadingTarget(point=lambda: (shm_vars[pick_correct_buoy(num)].center_x.get(),
                                            shm_vars[pick_correct_buoy(num)].center_y.get()),
                             target=(0, 0), deadband=(db, db), px=5, py=0.5,
                             depth_bounds=(1, MAX_DEPTH))
    else:
        return ForwardTarget(point=lambda: (shm_vars[pick_correct_buoy(num)].center_x.get(),
                                            shm_vars[pick_correct_buoy(num)].center_y.get()),
                             target=(0, 0.1), deadband=(db, db), px=0.08*mult, py=0.05*mult,
                             depth_bounds=(1, MAX_DEPTH))

class Consistent(Task):
    def on_first_run(self, test, count, total, invert, result):
        # Multiply by 60 to specify values in seconds, not ticks
        self.checker = ConsistencyCheck(count*60, total*60, default=False)

    def on_run(self, test, count, total, invert, result):
        test_result = call_if_function(test)
        if self.checker.check(not test_result if invert else test_result):
            self.finish(success=result)

search_buoy = lambda num: NoOp()

back_up_until_visible = lambda num, speed, timeout: Conditional(
    Sequential(
        Timeout(
            task=Sequential(
                # Get at least a little bit away first
                fake_move_x(-1),
                VelocityX(-speed),
                Consistent(lambda: shm_vars[num].visible.get(),
                           count=1, total=3, result=True, invert=False)
            ),
            time=timeout # don't back up too far
        ),
        VelocityX(0),
    ),
    on_success=Succeed(NoOp()),
    on_fail=Sequential(
        Log('Timed out, searching for buoy again'),
        search_buoy(num),
    )
)

# MoveX for minisub w/o a DVL
def fake_move_x(d):
    v = 0.1
    if d < 0:
        v *= -2
    return Sequential(MasterConcurrent(Timer(d / v), VelocityX(v)), VelocityX(0))

# Depends on camera dimensions (simulator vs Teagle)
MIN_DIST = 0.07 if SIMULATOR else 0.10

BackUp = lambda: Sequential(
    Log('Backing up...'),
    # Should be rammed, back up until we can see both buoys
    # If we see the second buoy then we can see both
    back_up_until_visible(num=1, speed=0.3, timeout=20),
)

RamBuoyAttempt = lambda num: Sequential(
    Log('Ramming buoy {}'.format(num)),
    Conditional(
        Either(
            Consistent(lambda: shm_vars[pick_correct_buoy(num)].visible.get(),
                       count=0.5, total=1.5, invert=True, result=False),
            Sequential(
                MasterConcurrent(
                    Consistent(lambda: shm_vars[pick_correct_buoy(num)].radius_norm.get() < MIN_DIST,
                               count=0.5, total=1.5, invert=True, result=True),
                    Sequential(
                        Zero(),
                        Log('Aligning...'),
                        align_buoy(num=num, db=0.1, mult=5),
                        Log('Driving forward...'),
                        VelocityX(0.1 if SIMULATOR else 0.04),
                        align_buoy(num=num, db=0, mult=3),
                    ),
                ),
                Zero(),
                Log('Aligning one more time...'),
                align_buoy(num=num, db=0.1, mult=3),
            ),
        ),
        on_success=Sequential(
            Zero(),
            Log('Ramming buoy...'),
            # Ram buoy
            fake_move_x(0.8),
        ),
        on_fail=Fail(
            # We weren't close enough when we lost the buoy - back up and try again
            Sequential(
                Zero(),
                Log('Lost sight of buoy, backing up...'),
                back_up_until_visible(0, 0.1, 5), # we only need to see the first buoy
            ),
        ),
    ),
    Zero(),
)

# Perform a task while keeping track of the buoy by updating the consistency checker
TrackBuoy = lambda num, task: MasterConcurrent(
    task,
    FunctionTask(lambda: update_correct_buoy(num)),
    finite=False
)

# Ram either buoy, 0 or 1
RamBuoy = lambda num: Sequential(
    # We track the current buoy while ramming and the next one while backing up
    TrackBuoy(num, Retry(lambda: RamBuoyAttempt(num), attempts = 10)),
    TrackBuoy(num + 1, BackUp()),
)


Full = Sequential(
    Log('Searching for buoys...'),
    search_buoy(1), # if we see the second buoy then we see both
    Succeed(RamBuoy(num=0)),
    Succeed(RamBuoy(num=1)),
)
