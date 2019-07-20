import shm

from mission.framework.search import SearchFor, SwaySearch, SpiralSearch
from mission.framework.combinators import Sequential, MasterConcurrent, While
from mission.framework.primitive import Zero, Log, AlwaysLog
from mission.framework.targeting import DownwardTarget
from mission.framework.movement import Depth, RelativeToInitialDepth
from mission.framework.position import MoveY
from mission.framework.timing import Timeout, Timer
from mission.framework.actuators import FireActuator, SetActuators

from mission.missions.will_common import Consistent
from mission.missions.attilus_garbage import PIDHeading

INITIAL_DEPTH_TEAGLE=2
DEPTH_TEAGLE = 2.5
INITIAL_DEPTH_TRANSDECK = None
DEPTH_TRANSDECK = None

INITIAL_DEPTH = INITIAL_DEPTH_TEAGLE
DEPTH = DEPTH_TEAGLE
DESCEND_DEPTH = 0.7

SIZE_THRESH = 9000

# CAM_CENTER = shm.recovery_vampire.cam_x.get(), shm.recovery_vampire.cam_y.get()
CAM_CENTER = shm.recovery_crucifix.cam_x.get(), shm.recovery_crucifix.cam_y.get()

def visible_closed():
    return shm.recovery_vampire.closed_visible.get()
def center_closed():
    print(shm.recovery_vampire.closed_handle_x.get(), shm.recovery_vampire.closed_handle_y.get())
    return (shm.recovery_vampire.closed_handle_x.get(), shm.recovery_vampire.closed_handle_y.get())
def angle_offset_closed():
    return shm.recovery_vampire.closed_angle_offset.get()
def size_closed():
    return shm.recovery_vampire.closed_size.get()

def visible_open():
    return shm.recovery_vampire.open_visible.get()
def center_open():
    print(shm.recovery_vampire.open_handle_x.get(), shm.recovery_vampire.open_handle_y.get())
    return (shm.recovery_vampire.open_handle_x.get(), shm.recovery_vampire.open_handle_y.get())
def angle_offset_open():
    return shm.recovery_vampire.open_angle_offset.get()
def size_open():
    return shm.recovery_vampire.open_size.get()


def visible_crucifix():
    return shm.recovery_crucifix.visible.get()
def center_crucifix():
    return (shm.recovery_crucifix.center_x.get(), shm.recovery_crucifix.center_y.get())
def offset_crucifix():
    return (shm.recovery_crucifix.offset_x.get(), shm.recovery_crucifix.offset_y.get())
def angle_offset_crucifix():
    return shm.recovery_crucifix.angle_offset.get()
def size_crucifix():
    return shm.recovery_crucifix.size.get()


Search = lambda visiblef: Sequential(  # TODO: TIMEOUT?
            Log('Searching'),
            SearchFor(
                SpiralSearch(),
                visiblef,
                consistent_frames=(15, 19)
            ),
            Zero())

close_to = lambda point1, point2, dbx=20, dby=20: abs(point1[0]-point2[0]) < dbx and abs(point1[1]-point2[1]) < dby

Center = lambda centerf, visiblef, db=15, px=0.0008, py=0.00095: Sequential(
            Log('Centering'),
            MasterConcurrent(
                Consistent(lambda: close_to(centerf(), CAM_CENTER,  db), count=2.5, total=3.0, invert=False, result=True),
                Consistent(visiblef, count=2.5, total=3.0, invert=True, result=False),
                While(lambda: DownwardTarget(point=centerf, target=CAM_CENTER, deadband=(0, 0), px=px, py=py), True),
                AlwaysLog(lambda: 'center = {}, target = {}'.format(centerf(), CAM_CENTER))))

Descend = lambda depth=DEPTH, db=0.1, size_thresh=SIZE_THRESH: Sequential(  # TODO: FIND THE ACTUAL DEPTH1!!
            Log('Descent into Madness'),
            MasterConcurrent(  # TODO: TIMEOUT
                Consistent(lambda: abs(shm.kalman.depth.get() - depth) < db or size() > size_thresh, count=2.3, total=3, invert=False, result=True),
                Depth(depth)),  # TODO: BigDepth?
            Zero())

close_to = lambda point1, point2, db=15: abs(point1[0]-point2[0]) < db and abs(point1[1]-point2[1]) < db

Align = lambda centerf, anglef, visiblef, closedb=10, aligndb=7: Sequential(
            Log('Aligning'),
            MasterConcurrent(
                Consistent(lambda: close_to(centerf(), CAM_CENTER) and abs(anglef()) < aligndb, count=2.3, total=3, invert=False, result=True),
                While(lambda: Consistent(visiblef, count=2.5, total=3.0, invert=True, result=False), True),
                While(lambda: Center(centerf, visiblef), True),
                PIDHeading(anglef, p=0.47)),
            Zero())

_Grab = lambda: SetActuators(on_triggers=['manipulator_grab'])
_Release = lambda: Sequential(
                    SetActuators(on_triggers=['manipulator_release'], off_triggers=['manipulator_grab']),
                    Timer(0.3),
                    SetActuators(off_triggers=['manipulator_release']))

Grab = lambda: Sequential(
            MoveY(-0.1),
            Timeout(RelativeToInitialDepth(0.5), 20),
            FireActuator(),  # TODO
            )

DeadReckonLid = lambda: None

GrabVampireOpenCoffin = lambda: \
    Sequential(
        Depth(INITIAL_DEPTH, error=0.2),
        Search(visible_open),
        Center(center_open, visible_closed),
        Align(centerf=center_open, anglef=angle_offset_closed, visiblef=visible_closed),
        # Grab(),  # ???
        Depth(0),
        # Release???
    )

GrabVampireClosedCoffin = lambda: \
    Sequential(
        Depth(INITIAL_DEPTH, error=0.2),
        Search(visible_closed),
        Center(center_closed, visible_closed),
        Align(center_closed, angle_offset_closed, visible_closed),
        Center(center_closed, visible_closed),
        # DeadReckonLid(),
        Depth(INITIAL_DEPTH, error=0.2),
        # GrabVampireOpenCoffin()
    )

GrabCrucifix = lambda: \
    Sequential(
        Depth(INITIAL_DEPTH, error=0.2),
        Search(visible_crucifix),
        Center(center_crucifix, visible_crucifix),
        Align(center_crucifix, angle_offset_crucifix, visible_crucifix),
        Center(offset_crucifix, visible_crucifix),
        MasterConcurrent(
            Sequential(
                Timer(5),
                _Grab())
            RelativeToInitialDepth(DESCEND_DEPTH, error=0.2),
            ),
        Depth(INITIAL_DEPTH, error=0.2),
        Timeout(Consistent(visible_crucifix, count=1.5, total=2.0, invert=True, result=True), 5),
    )



# Move = MoveY(0.1, error=0.05)
