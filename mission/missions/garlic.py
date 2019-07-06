import shm

from mission.framework.search import SearchFor, SwaySearch
from mission.framework.combinators import Sequential, MasterConcurrent
from mission.framework.primitive import Zero, Log, AlwaysLog
from mission.framework.targeting import DownwardTarget
from mission.framework.movement import Depth, RelativeToInitialDepth
from mission.framework.position import MoveY
from mission.framework.timing import Timeout
from mission.framework.actuators import FireActuator

from mission.missions.will_common import Consistent
from mission.missios.attilu_garbage import PIDHeading

DEPTH_TEAGLE = 2.3
DEPTH_TRANSDECK = None

DEPTH = DEPTH_TEAGLE

SIZE_THRESH = 9000

CAM_CENTER = shm.recovery_garlic.cam_x.get(), shm.recover_garlic.cam_y.get()

def visible():
    return shm.recovery_garlic.visible.get()
def center():
    return shm.recovery_garlic.center_x.get(), shm.recovery_garlic.center_y.get()
def angle_offset():
    return shm.recovery_garlic.angle_offset.get()
def size():
    return shm.recovery_garlic.size.get()


Search = lambda: Sequential(  # TODO: TIMEOUT?
            Log('Searching'),
            SearchFor(
                SwaySearch(width=2.5, stride=2),
                visible,
                consistent_frames=(5, 7)
            ),
            Zero())

Center = lambda db=20, px=0.003, py=0.003: Sequential(
            Log('Centering'),
            MasterConcurrent(
                DownwardTarget(point=center, target=CAM_CENTER, deadband=(db, db), px=px, py=py),
                AlwaysLog(lambda: 'center = {}'.format(center))))

Descend = lambda depth=DEPTH, db=0.1, size_thresh=SIZE_THRESH: Sequential(  # TODO: FIND THE ACTUAL DEPTH1!!
            Log('Descent into Madness'),
            MasterConcurrent(  # TODO: TIMEOUT
                Consistent(lambda: abs(shm.kalman.depth.get() - depth) < db or size() > size_thresh, count=2.3, total=3, invert=False, result=True),
                Depth(depth)),  # TODO: BigDepth?
            Zero())

close_to = lambda point1, point2, db=10: abs(point1[0]-point2[0]) < db and abs(point1[1]-point2[1]) < db

Align = lambda closedb=20, aligndb=10: Sequential(
            Log('Aligning'),
            MasterConcurrent(
                Consistent(lambda: close_to(center(), CAM_CENTER) and abs(angle_offset) < aligndb, count=2.3, total=3, invert=False, result=True),
                Center(),
                PIDHeading(angle_offset)),
            Zero())

Grab = lambda: Sequential(
            MoveY(-0.1),
            Timeout(RelativeToInitialDepth(0.5), 20),
            FireActuator(),  # TODO
            )
