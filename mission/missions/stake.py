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
from mission.framework.search import SearchFor
from mission.framework.movement import RelativeToCurrentDepth, VelocityY, Depth, VelocityX
from mission.framework.timing import Timeout
# from mission.missions.ozer_common import StillHeadingSearch
from mission.missions.will_common import Consistent
from mission.missions.attilus_garbage import PIDStride, PIDSway, StillHeadingSearch

import shm

CAM_CENTER = (shm.torpedoes_stake.camera_x.get(), shm.torpedoes_stake.camera_y.get())

#At the moment, 90% of the mission is fudged and untested. Proceed with caution.

TARGETS = {"upper":"lower", "lower":"upper"}
current_target = ""

def heart():
    return (shm.torpedoes_stake.heart_x.get(), shm.torpedoes_stake.heart_y.get())
def heart_visible():
    return shm.torpedoes_stake.heart_visible.get()

def left_hole():
    return (shm.torpedoes_stake.left_hole_x.get(), shm.torpedoes_stake.left_hole_y.get())
#TODO: we have a bunch of estimating stuff -- incorporate?
def left_hole_visible():
    return shm.torpedoes_stake.left_hole_visible.get()

def lever():
    return (shm.torpedoes_stake.lever_origin_x.get(), shm.torpedoes_stake.lever_origin_y.get())

# def align_h():
#     return shm.torpedoes_stake.align_h.get()

# def align_v():
#     return shm.torpedoes_stake.align_v.get()

def align_any_h():
    pass

def upper_visible(): 
    return shm.torpedoes_stake.upper_visible.get()
def upper_size():
    return shm.torpedoes_stake.upper_size.get()
def upper_center():
    return (shm.torpedoes_stake.upper_center_x.get(), shm.torpedoes_stake.upper_center_y.get())
def upper_align_h():
    return shm.torpedoes_stake.upper_align_h.get()

def lower_visible():
    return shm.torpedoes_stake.lower_visible.get()
def lower_size():
    return shm.torpedoes_stake.lower_size.get()
def lower_center():
    return (shm.torpedoes_stake.lower_center_x.get(), shm.torpedoes_stake.lower_center_y.get())
def lower_align_h():
    return shm.torpedoes_stake.lower_align_h.get()

def any_visible():
    return lower_visible() or upper_visible()

def which_visible(invert=False):
    for k,v in TARGETS.items():
        if getattr(shm.torpedoes_stake, "%s_visible"%k).get():
            return v if invert else k

SearchBoard = lambda: Sequential(
        Log('Searching for torpedo board'),
        SearchFor(
            StillHeadingSearch(),
            any_visible,
            consistent_frames=(1.7*60, 2.0*60) #TODO: Check consistent frames
            ),
        Zero()
)

# IMPORTANT: MAKE SURE U CHANGE THIS FOR TEAGLE/TRANSDECK/WHATEVER so the sub doesn't hit the bottom of the pool
MAX_DEPTH = 3.4
def DepthSearch(min_depth=0.2, max_depth=3.4, speed=0.05):
    return Sequential(
            MasterConcurrent(
                FunctionTask(lambda: shm.desires.depth.get() >= max_depth, finite=False),
                RelativeToCurrentDepth(offset=speed, min_target=min_depth, max_target=max_depth)), 
            Zero(),
            Fail()
    )


#TODO: Edge case: if fails, do a depth heading search
def SearchHalf(target, speed=0.15):
    target = target or which_visible(invert=True)
    direction = -speed if target=="upper" else speed
    return Sequential(
            SearchFor(
                search_task=DepthSearch(speed=direction),
                visible=getattr(shm.torpedoes_stake, "%s_visible"%target).get,
                consistent_frames=(2.7*60, 3*60)
                ),
            Zero()
        )

def SearchUpper():
    return SearchHalf('upper')
def SearchLower():
    return SearchHalf('lower')


close_to = lambda point1, point2, db=10: abs(point1[0]-point2[0]) < db and abs(point1[1]-point2[1]) < db
aligned = lambda align, db=4: abs(align) < db

def Align(centerf, alignf, visiblef, px=0.11, py=0.004, p=0.007, d=0.0005, db=0): 
    return MasterConcurrent(
            Consistent(lambda: close_to(centerf(), CAM_CENTER) and aligned(alignf()), count=1.5, total=2, invert=False, result=True),
            Consistent(visiblef, count=1.5, total=2.0, invert=True, result=False),
            HeadingTarget(point=centerf, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            PIDSway(alignf, p=p, d=d, db=db),
            AlwaysLog(lambda: "align_h: %d"%(alignf(),))) 

def AlignUpper():
    return Align(upper_center, upper_align_h, upper_visible)
def AlignLower():
    return Align(lower_center, lower_align_h, lower_visible)
def AlignAny():
    return AlignUpper() if upper_visible() else AlignLower()
def AlignHeart():
    return Align(heart, lower_align_h, lower_visible)

LEVER_LOCATION = (0, -20)

Center = lambda centerf,  visiblef, targetf=CAM_CENTER, px=0.0018, py=0.004, d=0.005, db=0, closedb=5: MasterConcurrent(
            Consistent(lambda: close_to(centerf(), targetf, db=closedb), count=1.5, total=2.0, invert=False, result=True),
            Consistent(visiblef, count=1.5, total=2.0, invert=True, result=False),
            ForwardTarget(point=centerf, target=targetf, px=px, py=py, dx=d, dy=d, deadband=(db,db)), 
            AlwaysLog(lambda: "center: {}, target: {}".format(targetf, centerf())))

def CenterHeart():
    return Center(centerf=heart, visiblef=heart_visible)
def CeneterLeftHole():
    return Center(centerf=left_hole, visiblef=left_hole_visible)
def CenterLever():
    return Center(centerf=lever, visiblef=any_visible, targetf=[CAM_CENTER[i] + LEVER_LOCATION[i] for i in range(0,2)])

#TODO: tune everything
#TODO: Also max velocity for pid stride?
SIZE_THRESH = 20000
def ApproachSize(sizef, centerf, alignf, visiblef, size_thresh, db=300):
    return MasterConcurrent(
            Consistent(lambda: abs(sizef()-size_thresh) < db and close_to(centerf(), CAM_CENTER) and aligned(alignf(), db=7), count=2.7, total=3.0, invert=False, result=True),
            Consistent(visiblef, count=1.5, total=2.0, invert=True, result=False),
            While(lambda: Align(centerf, alignf, visiblef), True),
            PIDStride(lambda: sizef()-size_thresh),
            AlwaysLog(lambda: "center: {}, target: {}, align: {}, size{}".format(CAM_CENTER, centerf(), alignf(), sizef())))

def ApproachLower():
    return ApproachSize(lower_size, lower_center, lower_align_h, lower_visible, SIZE_THRESH)
def ApproachUpper():
    return ApproachSize(upper_size, upper_center, upper_align_h, upper_visible, SIZE_THRESH)

def Backup(speed=0.2):
    return Sequential(
            Timeout(SearchFor(
                search_task=While(lambda: VelocityX(-speed), True),
                visible=any_visible,
                consistent_frames=(1.7*60, 2.0*60),
                ), 15),
            Zero()
            )


TargetTorpedos = lambda: Sequential(
        Log('Aligning shot'),
        Log('Firing')
)


MoveLever = lambda: Sequential( 
        Log('Aligning with lever'),
        CenterLever(),
        Log('Moving lever'),
        MoveX(1),
        MoveY(3)
)


Full = \
lambda: Retry(
    lambda: Sequential(
        Log('Starting Stake'),
        Zero(),#
        SearchBoard(),#
        AlignAny(),
        SearchLower(),
        AlignLower(),
        ApproachLower(),
        CenterHeart(),#
        TargetTorpedos(),
        Backup(),
        ApproachLower(),
        AlignLower(),
        MoveLever(),#
        Backup(),
        SearchUpper(),
        AlignUpper(),
        CenterHole(),#
        TargetTorpedos(),
        Log('Stake complete')
    )
, attempts=5) #TODO: What do we do with the retry?
