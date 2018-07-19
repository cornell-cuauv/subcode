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
from mission.framework.search import SpiralSearch, SearchFor

from mission.missions.actuate import FireBlue, FireRed, FireGreen
from mission.missions.will_common import BigDepth

from conf.vehicle import cameras

# These values are for Teagle
# Perhaps we should instead do this by determining the size in the camera
DEPTH_STANDARD = 0.8
DEPTH_TARGET_ALIGN_BIN = 2.2
DEPTH_TARGET_DROP = 2.3

CAM_CENTER = (cameras['downward']['width']/2, cameras['downward']['height']/2)

BIN_CENTER = [shm.bins_vision.center_x, shm.bins_vision.center_y]
#GREEN_CENTER = [shm.bins_green0.centroid_x, shm.bins_green0.centroid_y]
GREEN_CENTER = BIN_CENTER
GREEN_ANGLE = shm.bins_green0.angle

negator = lambda fcn: -fcn()

align_roulette_center = lambda db=20, p=0.0005: DownwardTarget((BIN_CENTER[0].get, BIN_CENTER[1].get), target=CAM_CENTER, px=p, py=p, deadband=(db, db))
align_green_angle = lambda db=10, p=0.8: DownwardAlign(GREEN_ANGLE.get, target=0, deadband=db, p=p)

DropBall = lambda: FireRed()

Search = lambda: SearchFor(
    SpiralSearch(),
    shm.bins_vision.board_visible.get,
    consistent_frames=(7*60, 10*60) # multiply by 60 to specify in seconds
)

Full = Retry(
    lambda: Sequential(
        Log('Starting'),
        Zero(),
        BigDepth(DEPTH_STANDARD),
        Log('Searching for roulette...'),
        Search(),
        Zero(),
        Log('Centering on roulette...'),
        align_roulette_center(db=40, p=0.0005),
        Log('Descending on roulette...'),
        MasterConcurrent(
            BigDepth(DEPTH_TARGET_ALIGN_BIN),
            align_roulette_center(0.0003),
        ),
        Log('Aligning with table again...'),
        align_roulette_center(db=60, p=0.0001),
        Log('Descending on table...'),
        MasterConcurrent(
            BigDepth(DEPTH_TARGET_DROP),
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
        BigDepth(DEPTH_STANDARD),
        Log('Done'),
    )
, attempts=5)
