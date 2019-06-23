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

from mission.framework.timing import Timer, Timed, Timeout

import shm

CAM_CENTER = (shm.vamp_buoy_results.camera_x.get(), shm.vamp_buoy_results.camera_y.get())

TRIANGLE = ("vetalas", "draugr", "aswang")

single = "jiangshi"

CALL = "draugr"

SIZE_THRESH = 8000

last_visible = None

def call_buoy_center():
    return (getattr(shm.vamp_buoy_results, "%s_center_x"%CALL).get(), getattr(shm.vamp_buoy_results, "%s_center_y"%CALL).get())

def any_buoy_center():
    b = which_buoy_visible()
    return (getattr(shm.vamp_buoy_results, "%s_center_x"%b).get(), getattr(shm.vamp_buoy_results, "%s_center_y"%b).get())

def single_buoy_center():
    return (getattr(shm.vamp_buoy_results, "%s_center_x"%single).get(), getattr(shm.vamp_buoy_results, "%s_center_y"%single).get())

def which_buoy_visible():
    global last_visible
    for b in TRIANGLE:
        if getattr(shm.vamp_buoy_results, "%s_visible"%b).get():
            last_visible = b
            return b
    return last_visible

def call_buoy_visible():
    return which_buoy_visible() == CALL

def single_buoy_visible():
    return getattr(shm.vamp_buoy_results, "%s_visible"%single).get() 

def call_buoy_size():
    return getattr(shm.vamp_buoy_results, "%s_size"%CALL).get()

def single_buoy_size():
    return getattr(shm.vamp_buoy_results, "%s_size"%single).get()

def any_buoy_size():
    b = which_buoy_visible()
    return getattr(shm.vamp_buoy_results, "%s_size"%b).get()

def align_call_h():
    return getattr(shm.vamp_buoy_results, "%s_align_h"%CALL).get()    

def align_single_h():
    return getattr(shm.vamp_buoy_results, "%s_align_h"%single).get()    

def align_any_h():
    b = which_buoy_visible()
            Timed(VelocityY(-speed), width/(2*speed)),
            Zero())

TinySearch = lambda backspeed=0.3, backtime=3: Sequential(
        Zero(),
        Log('Failed, backing up'),
        Timed(VelocityX(-backspeed), backtime), 
        Zero(),
        Log('Doing TinySearch to see if we can find called'),
        Timeout(SearchFor(
            SwayOnlySearch(),
            call_buoy_visible,
            consistent_frames=(0.5*60, 1.0*60)
            ), 20),
        Zero(),
)

ReSearch = lambda: Sequential(
        AlignAnyNormal(),
        SearchCalled())

withReSearchCalledOnFail = lambda task: lambda: Retry(lambda: \
        Conditional(main_task=task(), on_fail= \
            Fail(Conditional(main_task=TinySearch(), on_fail=ReSearch()))), attempts=3)


SearchTriangle = lambda: Sequential(
        Log('Searching for triangular buoy'),
        SearchFor(
            #SwaySearch(2.0, 0.7),
            VelocitySwaySearch(stride=0.7, width=2.0),
            triangle_visible,
            consistent_frames=(0.5*60, 1.0*60) #TODO: Check consistent frames
            ),
        Log('Finish Search'),
        Zero()
)


@withRamAnythingOnFail
def SearchCalled():
    return Sequential(
        Log('Searching for called buoy'),
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


# Point = lambda px=0.3, py=0.0003, d=0.0005, db=0: Concurrent(
#             HeadingTarget(point=any_buoy_center, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
#             AlwaysLog(lambda: "center: {}, target: {}".format(CAM_CENTER, any_buoy_center())))


close_to = lambda point1, point2, db=10: abs(point1[0]-point2[0]) < db and abs(point1[1]-point2[1]) < db
aligned = lambda align, db=2: abs(align) < db

def Align(centerf, alignf, visiblef, px=0.15, py=0.0003, p=0.02, d=0.0005, db=0): 
    return MasterConcurrent(
            Consistent(lambda: close_to(centerf(), CAM_CENTER) and aligned(align_any_h()), count=0.3, total=0.5, invert=False, result=True),
            Consistent(visiblef, count=0.2, total=0.3, invert=True, result=False),
            HeadingTarget(point=centerf, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            PIDSway(alignf, p=p, d=d, db=db),
            AlwaysLog(lambda: "align_h: %d"%(alignf(),))) 

@withSearchTriangleOnFail
def AlignAnyNormal(): 
    return Align(centerf=any_buoy_center, alignf=align_any_h, visiblef=triangle_visible)


def AlignCalledNormal():
    return Align(centerf=call_buoy_center, alignf=align_call_h, visiblef=call_buoy_visible)


AlignSingleNormal = lambda: Align(centerf=single_buoy_center, alignf=align_single_h, visiblef=single_buoy_visible)

# AlignAnyNormal = lambda px=0.15, py=0.0003, p=0.02, d=0.0005, db=0: MasterConcurrent(
#             Consistent(lambda: close_to(any_buoy_center(), CAM_CENTER) and aligned(align_any_h()), count=0.3, total=0.5, invert=False, result=True),
#             HeadingTarget(point=any_buoy_center, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
#             PIDSway(align_any_h, p=p, d=d, db=db),
#             AlwaysLog(lambda: "align_h: %d"%(align_any_h(),))) #TODO: Make VelY help with centering buoy


# AlignCalledNormal = lambda px=0.15, py=0.0303, p=0.02, d=0.0005, db=0: MasterConcurrent(
#             Consistent(lambda: close_to(call_buoy_center(), CAM_CENTER) and aligned(align_any_h()), count=0.3, total=0.5, invert=False, result=True),
#             HeadingTarget(point=call_buoy_center, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
#             PIDSway(align_call_h, p=p, d=d, db=db),
#             AlwaysLog(lambda: "align_h: {}".format(align_call_h()))) #TODO: Make VelY help with centering buoy


# AlignSingleNormal = lambda px=0.15, py=0.0303, p=0.02, d=0.0005, db=0: MasterConcurrent(
#             Consistent(lambda: close_to(single_buoy_center(), CAM_CENTER) and aligned(align_any_h()), count=0.3, total=0.5, invert=False, result=True),
#             HeadingTarget(point=single_buoy_center, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
#             PIDSway(align_single_h, p=p, d=d, db=db),
#             AlwaysLog(lambda: "align_h: {}".format(align_single_h()))) #TODO: Make VelY help with centering buoy

CenterBuoy = lambda centerf, visiblef, px=0.004, py=0.0003, d=0.005, db=0: MasterConcurrent(
            Consistent(lambda: close_to(centerf(), CAM_CENTER), count=0.3, total=0.5, invert=False, result=True),
            Consistent(visiblef, count=0.2, total=0.3, invert=True, result=False),
            ForwardTarget(point=centerf, target=CAM_CENTER, px=px, py=py, dx=d, dy=d, deadband=(db,db)), 
            AlwaysLog(lambda: "center: {}, target: {}".format(CAM_CENTER, centerf())))

CenterAnyBuoy = lambda: CenterBuoy(centerf=any_buoy_center, visiblef=any_buoy_visible)
CenterCalledBuoy = lambda: CenterBuoy(centerf=call_buoy_center, visiblef=call_buoy_visible)
CenterSingleBuoy = lambda: CenterBuoy(centerf=single_buoy_center, visiblef=single_buoy_visible)

# CenterAnyBuoy = lambda px=0.004, py=0.0003, d=0.005, db=0: MasterConcurrent(
#             Consistent(lambda: close_to(any_buoy_center(), CAM_CENTER), count=0.3, total=0.5, invert=False, result=True),
#             ForwardTarget(point=any_buoy_center, target=CAM_CENTER, px=px, py=py, dx=d, dy=d, deadband=(db,db)), 
#             AlwaysLog(lambda: "center: {}, target: {}".format(CAM_CENTER, any_buoy_center())))

# CenterCalledBuoy = lambda px=0.004, py=0.0003, d=0.005, db=0: MasterConcurrent(
#             Consistent(lambda: close_to(call_buoy_center(), CAM_CENTER), count=0.3, total=0.5, invert=False, result=True),
#             ForwardTarget(point=call_buoy_center, target=CAM_CENTER, px=px, py=py, dx=d, dy=d, deadband=(db,db)),
#             AlwaysLog(lambda: "center: {}, target: {}".format(CAM_CENTER, call_buoy_center())))

# CenterSingleBuoy = lambda px=0.004, py=0.0003, d=0.005, db=0: MasterConcurrent(
#             Consistent(lambda: close_to(single_buoy_center(), CAM_CENTER), count=0.3, total=0.5, invert=False, result=True),
#             ForwardTarget(point=single_buoy_center, target=CAM_CENTER, px=px, py=py, dx=d, dy=d, deadband=(db,db)),
#             AlwaysLog(lambda: "center: {}, target: {}".format(CAM_CENTER, single_buoy_center())))

Approach = lambda sizef, centerf, visiblef: Sequential(
            MasterConcurrent(Consistent(lambda: sizef() > SIZE_THRESH, 0.05, 0.1, False, True), #ADD EITHER LOSE SIGHT OF BUOY
                Consistent(visiblef, count=0.2, total=0.3, invert=True, result=False),
                VelocityX(.2, db=10),
                While(lambda: CenterBuoy(centerf=centerf, visiblef=visiblef), True),
                AlwaysLog(lambda: "size: {}, visible: {}".format(sizef(), visiblef()))),
            Zero())

@withReSearchCalledOnFail
def ApproachCalled(): 
    return Approach(sizef=call_buoy_size, centerf=call_buoy_center, visiblef=call_buoy_visible)

@withAlignAnyOnFail
def ApproachAny():
    return Approach(sizef=any_buoy_size, centerf=any_buoy_center, visiblef=triangle_visible)

ApproachSingle = lambda: Approach(sizef=single_buoy_size, centerf=single_buoy_center, visiblef=single_buoy_visible)

# ApproachCalled = lambda: Sequential(
#             MasterConcurrent(Consistent(lambda: call_buoy_size() > SIZE_THRESH, 0.05, 0.1, False, True), #ADD EITHER LOSE SIGHT OF BUOY
#                 VelocityX(.2, db=10),
#                 CenterCalledBuoy(),
#                 AlwaysLog(lambda: "size: {}".format(any_buoy_size()))),
#             Zero())

# ApproachAny = lambda: Sequential(
#             MasterConcurrent(Consistent(lambda: any_buoy_size() > SIZE_THRESH, 0.05, 0.1, False, True), #ADD EITHER LOSE SIGHT OF BUOY
#                 VelocityX(.2, db=10),
#                 CenterAnyBuoy(),
#                 AlwaysLog(lambda: "size: {}".format(any_buoy_size()))),
#             Zero())

# ApproachSingle = lambda: Sequential(
#             MasterConcurrent(Consistent(lambda: single_buoy_size() > SIZE_THRESH, 0.05, 0.1, False, True), #ADD EITHER LOSE SIGHT OF BUOY
#                 VelocityX(.2, db=10),
#                 CenterSingleBuoy(),
#                 AlwaysLog(lambda: "size: {}".format(single_buoy_size()))),
#             Zero())


Ram = lambda: Sequential(Concurrent(AlignAnyNormal(), MoveX(1)), Zero())


RamV = lambda: Sequential(MasterConcurrent(Timer(4), AlignAnyNormal(), VelocityX(.3)), Zero())


SearchAndApproach = lambda: Sequential(SearchCalled(), ApproachCalled())


Full = lambda: Sequential(
        Log('Searching for buoy'),
        Timeout(SearchTriangle(), 120),
        Log('Found buoy, aligning'),
        AlignAnyNormal(),
        Log('Approaching buoy'),
        ApproachAny(),
        Log('Searching for face'),
        Conditional(FunctionTask(lambda: which_buoy_visible() == CALL), on_fail=SearchAndApproach()),
        Log('Face found, ramming'),
        RamV(),
        Log('Vamp_Buoy Complete')
     )

SearchSingle = lambda: Sequential(
        Log('Searching for singular buoy'),
        SearchFor(
            VelocitySwaySearch(width=1, stride=0.2),
            shm.vamp_buoy_results.jiangshi_visible.get,
            consistent_frames=(1.5*60, 2.0*60) #TODO: Check consistent frames
            ),
        Zero()
)

SingleOnly = Sequential(
                SearchSingle(),
                AlignSingleNormal(),
                ApproachSingle(),
                Ram()
            )
