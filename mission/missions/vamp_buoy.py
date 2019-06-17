from mission.framework.primitive import (
        Zero,
        Log,
        Succeed,
        Fail,
        FunctionTask,
        NoOp
)
from mission.framework.combinators import (
        Sequential,
        Concurrent,
        MasterConcurrent,
        Retry,
        Conditional,
        While
)
from mission.framework.targeting import ForwardTarget, PIDLoop, HeadingTarget
from mission.framework.task import Task
from mission.framework.movement import VelocityY, VelocityX
from mission.framework.position import MoveX

from mission.missions.will_common import Consistent
from mission.missions.poly import polygon
from mission.framework.search import SearchFor, SwaySearch, VelocitySwaySearch, MoveXRough

import shm

CAM_CENTER = (shm.vamp_buoy_results.camera_x.get, shm.vamp_buoy_results.camera_y.get)

TRIANGLE = ("vetalas", "draugr", "aswang")

single = "jiangshi"

CALL = "draugr"

SIZE_THRESH = 8000

def call_buoy_center():
    return (getattr(shm.vamp_buoy_results, "%s_center_x"%CALL).get, getattr(shm.vamp_buoy_results, "%s_center_y"%CALL).get)

def any_buoy_center():
    for b in TRIANGLE:
        if getattr(shm.vamp_buoy_results, "%s_visible"%CALL).get:
            return (getattr(shm.vamp_buoy_results, "%s_center_x"%CALL).get, getattr(shm.vamp_buoy_results, "%s_center_x"%CALL).get)

def which_buoy_visible():
    for b in TRIANGLE:
        if getattr(shm.vamp_buoy_results, "%s_visible"%CALL).get:
            return b

def call_buoy_size():
    return getattr(shm.vamp_buoy_results, "%s_size"%CALL).get()

def any_buoy_size():
    return getattr(shm.vamp_buoy_results, "%s_size"%CALL).get()

def align_h():
    return getattr(shm.vamp_buoy_results, "%s_align_h"%CALL).get()    

def triangle_visible():
    for t in TRIANGLE:
        if getattr(shm.vamp_buoy_results, "%s_visible"%t).get():
            return True
    return False
    



SearchTriangle = lambda: Sequential(
        Log('Searching for triangular buoy'),
        SearchFor(
            SwaySearch(2.0, 4.0),
            triangle_visible,
            consistent_frames=(1.5*60, 2.0*60) #TODO: Check consistent frames
            ),
        Zero()
)

SearchSpecific = lambda: Sequential(
        Log('Searching for triangular buoy'),
        SearchFor(
            polygon,
            triangle_visible,
            consistent_frames=(1.5*60, 2.0*60) #TODO: Check consistent frames
            ),
        Zero()
)

class PIDVelocity(Task):
    def on_first_run(self, *args, **kwargs):
        self.pid_loop = PIDLoop(output_function=VelocityY())

    def on_run(self, error, p=0.0005,  i=0, d=0.0, db=0.01875, negate=False, *args, **kwargs):
        self.pid_loop(input_value=error, p=p, i=i, d=d, target=0, modulo_error=False, deadband = db, negate=negate)

    def stop(self):
        RelativeToCurrentVelocityY(0)()
    

Point = lambda px=0.1, py=0.003, p=0.01, d=0.0005, db=0: Concurrent(
            HeadingTarget(any_buoy_center(), target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            While(lambda: Log("center: %d, %d, target: %d, %d"%(CAM_CENTER[0](), CAM_CENTER[1](), any_buoy_center()[0](), any_buoy_center()[1]())), True))

AlignAnyNormal = lambda px=0.1, py=0.003, p=0.03, d=0.0005, db=0: Concurrent(
            HeadingTarget(any_buoy_center(), target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            PIDVelocity(align_h, p=p, d=d, db=db),
            While(lambda: Log("align_h: %d"%align_h()), True)) #TODO: Make VelY help with centering buoy

CenterAnyBuoy= lambda px=0.004, py=0.003, d=0.005, db=0: Concurrent(
        ForwardTarget(any_buoy_center(), target=CAM_CENTER, px=px, py=py, dx=d, dy=d, deadband=(db,db)), #TODO: CHECK P VALUES
        While(lambda: Log("center: %d, %d, target: %d, %d"%(CAM_CENTER[0](), CAM_CENTER[1](), any_buoy_center()[0](), any_buoy_center()[1]())), True)
)

CenterCalledBuoy= lambda px=0.004, py=0.003, d=0.005, db=0: Concurrent(
        ForwardTarget(call_buoy_center(), target=CAM_CENTER, px=px, py=py, dx=d, dy=d, deadband=(db,db)), #TODO: CHECK P VALUES
        While(lambda: Log("center: %d, %d, target: %d, %d"%(CAM_CENTER[0](), CAM_CENTER[1](), any_buoy_center()[0](), any_buoy_center()[1]())), True)
)

AlignCalledNormal = lambda px=0.1, py=0.003, p=0.03, d=0.0005, db=0: Concurrent(
            HeadingTarget(call_buoy_center(), target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            PIDVelocity(align_h, p=p, d=d, db=db),
            While(lambda: Log("align_h: %d"%align_h()), True)) #TODO: Make VelY help with centering buoy

ApproachCalled = Sequential(
            VelocityX(.2),
            MasterConcurrent(Retry(lambda: Consistent(lambda: call_buoy_size() > SIZE_THRESH, 0.05, 0.1, False, True), attempts=20), #ADD EITHER LOSE SIGHT OF BUOY
                CenterCalledBuoy(),
                While(lambda: Log("size: %d"%any_buoy_size()),True)),
            Zero())

Ram = Sequential(Concurrent(AlignCalledNormal(), MoveX(1)), Zero())

ApproachAny = Sequential(
            VelocityX(.2),
            MasterConcurrent(Retry(lambda: Consistent(lambda: any_buoy_size() > SIZE_THRESH, 0.05, 0.1, False, True), attempts=20), #ADD EITHER LOSE SIGHT OF BUOY
                CenterAnyBuoy(),
                While(lambda: Log("size: %d"%any_buoy_size()),True)),
            Zero())

SearchAndApproach = Sequential(SearchSpecific, ApproachCalled)


 
Full = Sequential(
        Log('Searching for buoy'),
        SearchTriangle(),
        Log('Found buoy, aligning'),
        AlignAnyNormal(),
        Log('Approaching buoy'),
        ApproachAny(),
        Log('Searching for face'),
        Conditional(FunctionTask(lambda: which_buoy_visible == b), on_fail=SearchAndApproach),
        Log('Face found, ramming'),
        Ram,
        Log('Vamp_Buoy Complete')
     )

SearchSingle = lambda: Sequential(
        Log('Searching for triangular buoy'),
        SearchFor(
            VelocitySwaySearch(0.2, 1),
            shm.vamp_buoy_results.jiangshi_visible,
            consistent_frames=(1.5*60, 2.0*60) #TODO: Check consistent frames
            ),
        Zero()
)

SingleOnly = Sequential(
                SearchSingle,
                AlignCalledNormal,
                ApproachCalled,
                Ram
            )

Move = MoveX(3)
