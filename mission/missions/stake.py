#!/usr/bin/env python3
from mission.framework.primitive import (
        Zero,
        Log,
        AlwaysLog,
        Succeed,
        Fail,
        FunctionTask,
        # NoOp
)
from mission.framework.combinators import (
        Sequential,
        Concurrent,
        MasterConcurrent,
        Retry,
        Conditional,
        While
)
from mission.framework.targeting import ForwardTarget, HeadingTarget
from mission.framework.search import SearchFor, SwaySearch
from mission.framework.movement import RelativeToCurrentDepth, VelocityY, VelocityX
from mission.framework.position import MoveX, MoveY
from mission.framework.timing import Timeout
# from mission.missions.ozer_common import StillHeadingSearch
from mission.missions.will_common import Consistent
from mission.missions.attilus_garbage import PIDStride, PIDSway, StillHeadingSearch

import shm

CAM_CENTER = (shm.torpedoes_stake.camera_x.get(), shm.torpedoes_stake.camera_y.get())

# At the moment, 90% of the mission is fudged and untested. Proceed with caution.

TARGETS = {"upper": "lower", "lower": "upper"}
current_target = ""


def heart():
    return (shm.torpedoes_stake.heart_x.get(), shm.torpedoes_stake.heart_y.get())

def left_hole():
    return (shm.torpedoes_stake.left_hole_x.get(), shm.torpedoes_stake.left_hole_y.get())

def lever():
    return (shm.torpedoes_stake.lever_origin_x.get(), shm.torpedoes_stake.lever_origin_y.get())

def align_h():
    return shm.torpedoes_stake.board_align_h.get()

def visible():
    return shm.torpedoes_stake.board_visible.get()

def size():
    return shm.torpedoes_stake.board_size.get()

def board_center():
    return (shm.torpedoes_stake.board_center_x.get(), shm.torpedoes_stake.board_center_y.get())

SearchBoard = lambda: Sequential(
        Log('Searching for torpedo board'),
        SearchFor(
            StillHeadingSearch(speed=10),
            visible,
            consistent_frames=(1.7*60, 2.0*60)
            ),
        Log('Found!'),
        Zero()
)

BackUpSway = lambda backx=1.5: Sequential(
        Log('Backing up'),
        MoveX(-backx),
        Log('Sway Search in Progress'),
        SwaySearch(width=2.5, stride=2)
        )

ReSearchBoardOnFail = lambda backx=1.5, timeout=30: Sequential(  #TODO: Make it sway left if left before else right
    Timeout(SearchFor(
            BackUpSway(backx),
            visible,
            consistent_frames=(1.8*60, 2.0*60)
            ), timeout),
    Log('Found!'),
    Zero(),
    ApproachAlign()
    )

def withReSearchBoardOnFail(task):
    return lambda *args, **kwargs: Retry(lambda: Conditional(task(*args, **kwargs), on_fail=Fail(ReSearchBoardOnFail())), attempts=2)

def withAlignHeartOnFail(task):
    return lambda *args, **kwargs: Retry(lambda: Conditional(task(*args, **kwargs), on_fail=Fail(AlignHeart())), attempts=2)

def withAlignBoardOnFail(task):
    return lambda *args, **kwargs: Retry(lambda: Conditional(task(*args, **kwargs), on_fail=Fail(AlignBoard())), attempts=2)



# IMPORTANT: MAKE SURE U CHANGE THIS FOR TEAGLE/TRANSDECK/WHATEVER so the sub doesn't hit the bottom of the pool
# MAX_DEPTH = 3.4
# def DepthSearch(min_depth=0.2, max_depth=3.4, speed=0.05):
#     return Sequential(
#             MasterConcurrent(
#                 FunctionTask(lambda: shm.desires.depth.get() >= max_depth, finite=False),
#                 RelativeToCurrentDepth(offset=speed, min_target=min_depth, max_target=max_depth)),
#             Zero(),
#             Fail()
#     )


# def SearchHalf(target, speed=0.15):
#     target = target or which_visible(invert=True)
#     direction = -speed if target=="upper" else speed
#     return Sequential(
#             SearchFor(
#                 search_task=DepthSearch(speed=direction),
#                 visible=getattr(shm.torpedoes_stake, "%s_visible"%target).get,
#                 consistent_frames=(2.7*60, 3*60)
#                 ),
#             Zero()
#         )

# def SearchUpper():
#     return SearchHalf('upper')
# def SearchLower():
#     return SearchHalf('lower')


close_to = lambda point1, point2, db=10: abs(point1[0]-point2[0]) < db and abs(point1[1]-point2[1]) < db
aligned = lambda align, db=4: abs(align) < db

@withReSearchBoardOnFail
def Align(centerf, alignf, visiblef, px=0.11, py=0.004, p=0.007, d=0.0005, db=0):
    return MasterConcurrent(
            Consistent(lambda: close_to(centerf(), CAM_CENTER) and aligned(alignf()), count=1.5, total=2, invert=False, result=True),
            Consistent(visiblef, count=1.5, total=2.0, invert=True, result=False),
            HeadingTarget(point=centerf, target=CAM_CENTER, px=px, py=py, dy=d, dx=d, deadband=(db,db)),
            PIDSway(alignf, p=p, d=d, db=db),
            AlwaysLog(lambda: "align_h: %d" % (alignf(),)))

# def AlignUpper():
#     return Align(upper_center, align_h, visible)
# def AlignLower():
#     return Align(lower_center, align_h, visible)
def AlignBoard():
    return Align(board_center, align_h, visible)
def AlignHeart():
    return Align(heart, align_h, visible)
def AlignLeftHole():
    return Align(left_hole, align_h, visible)

Center = lambda centerf,  visiblef, targetf=CAM_CENTER, px=0.0018, py=0.004, d=0.005, db=0, closedb=5: MasterConcurrent(
            Consistent(lambda: close_to(centerf(), targetf, db=closedb), count=1.5, total=2.0, invert=False, result=True),
            Consistent(visiblef, count=1.5, total=2.0, invert=True, result=False),
            ForwardTarget(point=centerf, target=targetf, px=px, py=py, dx=d, dy=d, deadband=(db,db)), 
            AlwaysLog(lambda: "center: {}, target: {}".format(targetf, centerf())))

def CenterHeart():
    return Center(centerf=heart, visiblef=visible)
def CenterLeftHole():
    return Center(centerf=left_hole, visiblef=visible)
def CenterLever():
    return Center(centerf=lever, visiblef=visible)
def CenterBoard():
    return Center(centerf=board_center, visiblef=visible)

# TODO: tune everything
APPROACH_SIZE = 20000
def ApproachSize(sizef, centerf, alignf, visiblef, size_thresh, db=300):
    return MasterConcurrent(
            Consistent(lambda: abs(sizef()-size_thresh) < db and close_to(centerf(), CAM_CENTER) and aligned(alignf(), db=7), count=2.7, total=3.0, invert=False, result=True),
            Consistent(visiblef, count=1.5, total=2.0, invert=True, result=False),
            While(lambda: Align(centerf, alignf, visiblef), True),
            PIDStride(lambda: sizef()-size_thresh),
            AlwaysLog(lambda: "center: {}, target: {}, align: {}, size{}".format(CAM_CENTER, centerf(), alignf(), sizef())))

@withAlignHeartOnFail
def ApproachHeart():
    return ApproachSize(size, heart, align_h, visible, APPROACH_SIZE)
@withAlignBoardOnFail
def ApproachLeftHole():
    return ApproachSize(size, left_hole, align_h, visible, APPROACH_SIZE)

def ApproachAlign():
    return ApproachSize(size, board_center, align_h, visible, ALIGN_SIZE)

def DeadReckonHeart():
    pass
def DeadReckonLever():
    pass
def DeadReckonLeftHole():
    pass


ALIGN_SIZE = 9000
@withReSearchBoardOnFail
def Backup(speed=0.2):
    return Sequential(
            Timeout(SearchFor(
                search_task=While(lambda: VelocityX(-speed), True),
                visible=lambda: visible() and size() < ALIGN_SIZE,
                consistent_frames=(1.7*60, 2.0*60),
                ), 15),
            Zero(),
            )


TargetTorpedos = lambda: Sequential(
        Log('Aligning shot'),
        Log('Firing')
)




Full = \
    lambda: Sequential(
        Log('Starting Stake'),
        SearchBoard(),  # Timeout
        AlignHeart(),
        ApproachHeart(),
        DeadReckonHeart(),
        Backup(),
        AlignBoard(),
        CenterLever(),  # Approach?
        DeadReckonLever(),
        Backup(),
        AlignLeftHole(),
        DeadReckonLeftHole(),  # Approach?
        Backup(),
        Log('Stake complete')
    )
