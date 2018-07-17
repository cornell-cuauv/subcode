# Written by Will Smith.

from collections import namedtuple
import math
import time
import shm
from mission.framework.task import Task
from mission.framework.combinators import (
    Sequential,
    Concurrent,
    MasterConcurrent,
    Retry,
    Conditional,
    While
)
from mission.framework.helpers import call_if_function
from mission.framework.targeting import DownwardTarget, DownwardAlign
from mission.framework.timing import Timer
from mission.framework.movement import (
    RelativeToInitialDepth,
    RelativeToCurrentDepth,
    VelocityX,
    VelocityY,
    Depth,
)
from mission.framework.primitive import (
    Zero,
    Log,
    Succeed,
    Fail,
    FunctionTask,
    NoOp,
)

from mission.missions.actuate import FireBlue

from conf.vehicle import cameras

# These values are for Teagle
# Perhaps we should instead do this by determining the size in the camera
DEPTH_STANDARD = 0.8
DEPTH_TARGET_ALIGN_BIN = 2.5
DEPTH_TARGET_DROP = 2.6

CAM_CENTER = (cameras['downward']['width']/2, cameras['downward']['height']/2)

def interpolate_list(a, b, steps):
    return [a + (b - a) / steps * i for i in range(steps)]

def tasks_from_params(task, params):
    return [task(param) for param in params]

def tasks_from_param(task, param, length):
    return [task(param) for i in range(length)]

def interleave(a, b):
    # https://stackoverflow.com/a/7946825
    return [val for pair in zip(a, b) for val in pair]

DEPTH_STEPS = interpolate_list(DEPTH_STANDARD, DEPTH_TARGET_ALIGN_BIN, 4)

BIN_CENTER = [shm.bins_vision.center_x, shm.bins_vision.center_y]
#GREEN_CENTER = [shm.bins_green0.centroid_x, shm.bins_green0.centroid_y]
GREEN_CENTER = BIN_CENTER
GREEN_ANGLE = shm.bins_green0.angle

negator = lambda fcn: -fcn()

align_roulette_center = lambda db=20, p=0.0005: DownwardTarget((BIN_CENTER[0].get, BIN_CENTER[1].get), target=CAM_CENTER, px=p, py=p, deadband=(db, db))
align_green_angle = lambda db=10, p=0.8: DownwardAlign(GREEN_ANGLE.get, target=0, deadband=db, p=p)

DropBall = lambda: FireBlue()

Search = lambda: NoOp()

Full = Retry(
    lambda: Sequential(
        Log('Starting'),
        Zero(),
        Depth(DEPTH_STANDARD),
        Log('Searching for roulette...'),
        Search(),
        Zero(),
        Log('Centering on roulette...'),
        align_roulette_center(db=40, p=0.0005),
        Log('Descending on roulette...'),
        MasterConcurrent(
            # Descend slowly, not all at once
            Sequential(*interleave(tasks_from_params(Depth, DEPTH_STEPS), tasks_from_param(Timer, 1, len(DEPTH_STEPS)))),
            align_roulette_center(0.0003),
        ),
        Log('Aligning with table again...'),
        align_roulette_center(db=60, p=0.0001),
        Log('Descending on table...'),
        MasterConcurrent(
            Depth(DEPTH_TARGET_DROP),
            align_roulette_center(db=0.000001, p=0.00008),
        ),
        Log('Aligning heading with green bin...'),
        MasterConcurrent(
            align_green_angle(db=15, p=0.5),
            align_roulette_center(db=0.000001, p=0.00008),
        ),
        Zero(),
        Log('Dropping ball...'),
        DropBall(),
        Log('Returning to normal depth...'),
        Depth(DEPTH_STANDARD),
        Log('Done'),
    )
, attempts=5)
