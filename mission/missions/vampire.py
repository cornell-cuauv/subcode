import shm

from mission.framework.search import SearchFor, SwaySearch, SpiralSearch
from mission.framework.combinators import Sequential, MasterConcurrent, While
from mission.framework.primitive import Zero, Log, AlwaysLog
from mission.framework.targeting import DownwardTarget
from mission.framework.movement import Depth, RelativeToInitialDepth
from mission.framework.position import MoveY
from mission.framework.timing import Timeout
from mission.framework.actuators import FireActuator

from mission.missions.will_common import Consistent
from mission.missions.attilus_garbage import PIDHeading

DEPTH_TEAGLE = 2.3
DEPTH_TRANSDECK = None

DEPTH = DEPTH_TEAGLE

SIZE_THRESH = 9000

CAM_CENTER = shm.recovery_vampire.cam_x.get(), shm.recovery_vampire_.cam_y.get()

def visible_closed():
    return shm.recovery_vampire.visible.closed_get()
def center_closed():
    return shm.recovery_vampire.closed_center_x.get(), shm.recovery_vampire.closed_center_y.get()
def angle_offset_closed():
    return shm.recovery_vampire.closed_angle_offset.get()
def size_closed():
    return shm.recovery_vampire.closed_size.get()


Search = lambda visiblef: Sequential(  # TODO: TIMEOUT?
            Log('Searching'),
            SearchFor(
                SpiralSearch(),
                visiblef,
                consistent_frames=(5, 7)
            ),
            Zero())

close_to = lambda point1, point2, dbx=20, dby=20: abs(point1[0]-point2[0]) < dbx and abs(point1[1]-point2[1]) < dby

Center = lambda centerf, visiblef, db=40, px=0.0008, py=0.0008: Sequential(
            Log('Centering'),
            MasterConcurrent(
                Consistent(lambda: close_to(centerf(), CAM_CENTER, db, db))
                Consistent(visiblef, count=2.5, total=3.0, invert=True, result=False),
                DownwardTarget(point=centerf, target=CAM_CENTER, deadband=(0, 0), px=px, py=py),
                AlwaysLog(lambda: 'center = {}, target = {}'.format(center(), CAM_CENTER))))

Descend = lambda depth=DEPTH, db=0.1, size_thresh=SIZE_THRESH: Sequential(  # TODO: FIND THE ACTUAL DEPTH1!!
            Log('Descent into Madness'),
            MasterConcurrent(  # TODO: TIMEOUT
                Consistent(lambda: abs(shm.kalman.depth.get() - depth) < db or size() > size_thresh, count=2.3, total=3, invert=False, result=True),
                Depth(depth)),  # TODO: BigDepth?
            Zero())

close_to = lambda point1, point2, db=10: abs(point1[0]-point2[0]) < db and abs(point1[1]-point2[1]) < db

Align = lambda centerf, anglef, visiblef, closedb=20, aligndb=3: Sequential(
            Log('Aligning'),
            MasterConcurrent(
                Consistent(lambda: close_to(centerf(), CAM_CENTER) and abs(anglef()) < aligndb, count=2.3, total=3, invert=False, result=True),
                Consistent(visiblef, count=2.5, total=3.0, invert=True, result=False),
                While(lambda: Center(visiblef, centerf), True),
                PIDHeading(anglef)),
            Zero())

Grab = lambda: Sequential(
            MoveY(-0.1),
            Timeout(RelativeToInitialDepth(0.5), 20),
            FireActuator(),  # TODO
            )

DeadReckonLid = lambda: None

GrabVampireOpenCoffin = lambda: \
    Sequential(
        Depth(DEPTH),
        Search(visible_closed),
        Center(center_closed, visible_closed),
        Align(center_closed, angle_offset_closed, visible_closed),
        Grab(),  # ???
        Depth(0),
        # Release???
    )

GrabVampireClosedCoffin = lambda: \
    Sequential(
        Depth(DEPTH),
        Search(visible_open),
        Center(center_open, visible_open),
        Align(center_open, angle_offset_open, visible_open),
        # DeadReckonLid(),
        Depth(DEPTH),
        GrabVampireOpenCoffin()
    )
