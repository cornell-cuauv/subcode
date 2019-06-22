from mission.framework.primitive import (
        Zero,
        Log,
        AlwaysLog,
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
from mission.framework.search import SearchFor, SwaySearch, VelocitySwaySearch, MoveX

from mission.framework.timing import Timer

import shm

CAM_CENTER = (shm.vamp_buoy_results.camera_x.get(), shm.vamp_buoy_results.camera_y.get())

TRIANGLE = ("vetalas", "draugr", "aswang")

single = "jiangshi"

CALL = "draugr"

SIZE_THRESH = 8000

def call_buoy_center():
    return (getattr(shm.vamp_buoy_results, "%s_center_x"%CALL).get(), getattr(shm.vamp_buoy_results, "%s_center_y"%CALL).get())

def any_buoy_center():
    b = which_buoy_visible()
    return (getattr(shm.vamp_buoy_results, "%s_center_x"%b).get(), getattr(shm.vamp_buoy_results, "%s_center_y"%b).get())

def which_buoy_visible():
    for b in TRIANGLE:
        if getattr(shm.vamp_buoy_results, "%s_visible"%b).get():
            return b

def call_buoy_visible():
    return which_buoy_visible() == CALL

def call_buoy_size():
    return getattr(shm.vamp_buoy_results, "%s_size"%CALL).get()

def any_buoy_size():
    b = which_buoy_visible()
    return getattr(shm.vamp_buoy_results, "%s_size"%b).get()

def align_call_h():
    return getattr(shm.vamp_buoy_results, "%s_align_h"%CALL).get()    

def align_any_h():
    b = which_buoy_visible()
    return getattr(shm.vamp_buoy_results, "%s_align_h"%b).get()    



def triangle_visible():
    for t in TRIANGLE:
        if getattr(shm.vamp_buoy_results, "%s_visible"%t).get():
            return True
    return False
    



SearchTriangle = lambda: Sequential(
        Log('Searching for triangular buoy'),
        SearchFor(
            #SwaySearch(2.0, 0.7),
            VelocitySwaySearch(forward=0.7, stride=2.0),
            triangle_visible,
            consistent_frames=(1.5*60, 2.0*60) #TODO: Check consistent frames
            ),
        Zero()
)

SearchCalled= lambda: Sequential(
        Log('Searching for triangular buoy'),
        SearchFor(
            polygon,
            call_buoy_visible,
            consistent_frames=(1.5*60, 2.0*60) #TODO: Check consistent frames
            ),
        Zero()
)

class PIDSway(Task):
    def on_first_run(self, *args, **kwargs):
        self.pid_loop = PIDLoop(output_function=VelocityY())

    def on_run(self, error, p=0.0005,  i=0, d=0.0, db=0.01875, negate=False, *args, **kwargs):
        self.pid_loop(input_value=error, p=p, i=i, d=d, target=0, modulo_error=False, deadband = db, negate=negate)

    def stop(self):
        VelocityY(0)()

Point = lambda px=0.3, py=0.0003, d=0.0005, db=0: Concurrent(
            HeadingTarget(point=any_buoy_center, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            AlwaysLog(lambda: "center: %d, %d, target: %d, %d"%(CAM_CENTER[0], CAM_CENTER[1], any_buoy_center()[0], any_buoy_center()[1])))

close_to = lambda point1, point2, db=10: abs(point1[0]-point2[0]) < db and abs(point1[1]-point2[1]) < db
aligned = lambda align, db=2: abs(align) < db

AlignAnyNormal = lambda px=0.15, py=0.0003, p=0.02, d=0.0005, db=0: MasterConcurrent(
            Consistent(lambda: close_to(any_buoy_center(), CAM_CENTER) and aligned(align_any_h()), count=0.3, total=0.5, invert=False, result=True),
            HeadingTarget(point=any_buoy_center, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            PIDSway(align_any_h, p=p, d=d, db=db),
            AlwaysLog(lambda: "align_h: %d"%(align_any_h(),))) #TODO: Make VelY help with centering buoy

CenterAnyBuoy = lambda px=0.004, py=0.0003, d=0.005, db=0: MasterConcurrent(
            Consistent(lambda: close_to(any_buoy_center(), CAM_CENTER), 0.05, 0.1, False, True),
            ForwardTarget(point=any_buoy_center, target=CAM_CENTER, px=px, py=py, dx=d, dy=d, deadband=(db,db)), 
            AlwaysLog(lambda: "center: %d, %d, target: %d, %d"%(CAM_CENTER[0], CAM_CENTER[1], any_buoy_center()[0], any_buoy_center()[1])))


CenterCalledBuoy = lambda px=0.004, py=0.0003, d=0.005, db=0: MasterConcurrent(
            Consistent(lambda: close_to(call_buoy_center(), CAM_CENTER), 0.05, 0.1, False, True),
            ForwardTarget(point=call_buoy_center, target=CAM_CENTER, px=px, py=py, dx=d, dy=d, deadband=(db,db)),
            AlwaysLog(lambda: "center: %d, %d, target: %d, %d"%(CAM_CENTER[0], CAM_CENTER[1], any_buoy_center()[0], any_buoy_center()[1])))



AlignCalledNormal = lambda px=0.15, py=0.0303, p=0.02, d=0.0005, db=0: MasterConcurrent(
            Consistent(lambda: close_to(call_buoy_center(), CAM_CENTER) and aligned(align_call_h()), 0.05, 0.1, False, True),
            HeadingTarget(point=call_buoy_center, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            PIDSway(align_call_h, p=p, d=d, db=db),
            AlwaysLog(lambda: "align_h: %d"%align_call_h())) #TODO: Make VelY help with centering buoy

ApproachCalled = lambda: Sequential(
            VelocityX(.2, db=10),
            MasterConcurrent(Consistent(lambda: call_buoy_size() > SIZE_THRESH, 0.05, 0.1, False, True), #ADD EITHER LOSE SIGHT OF BUOY
                CenterCalledBuoy(),
                AlwaysLog(lambda: "size: %d"%any_buoy_size())),
            Zero())

Ram = lambda: Sequential(Concurrent(AlignCalledNormal(), MoveX(1)), Zero())

RamV = lambda: Sequential(MasterConcurrent(Timer(3), AlignCalledNormal(), VelocityX(.3)), Zero())


ApproachAny = lambda: Sequential(
            VelocityX(.2, db=10),
            MasterConcurrent(Consistent(lambda: any_buoy_size() > SIZE_THRESH, 0.05, 0.1, False, True), #ADD EITHER LOSE SIGHT OF BUOY
                CenterAnyBuoy(),
                AlwaysLog(lambda: "size: %d"%any_buoy_size())),
            Zero())

SearchAndApproach = lambda: Sequential(SearchCalled, ApproachCalled)


 
Full = lambda: Sequential(
        Log('Searching for buoy'),
        SearchTriangle(),
        Log('Found buoy, aligning'),
        AlignAnyNormal(),
        Log('Approaching buoy'),
        ApproachAny(),
        Log('Searching for face'),
        Conditional(FunctionTask(lambda: which_buoy_visible == b), on_fail=SearchAndApproach),
        Log('Face found, ramming'),
        RamV(),
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
