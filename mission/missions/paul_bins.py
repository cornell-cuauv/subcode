#!/usr/bin/env python3

import math

import shm

from conf.vehicle import VEHICLE

from mission.framework.combinators import Sequential, Concurrent, MasterConcurrent, Retry, Conditional, While, Either
from mission.framework.helpers import get_downward_camera_center, ConsistencyCheck
from mission.framework.movement import Depth, Heading, Pitch, VelocityX, VelocityY, RelativeToCurrentHeading, RelativeToInitialHeading
from mission.framework.position import PositionalControl
from mission.framework.primitive import Zero, Log, FunctionTask, Fail, NoOp
from mission.framework.search import SearchFor, VelocityTSearch, SwaySearch, PitchSearch, VelocitySwaySearch
from mission.framework.targeting import DownwardTarget, PIDLoop, HeadingTarget, ForwardTarget
from mission.framework.task import Task
from mission.framework.timing import Timer, Timed
from mission.framework.jank import TrackMovementY, RestorePosY
from mission.framework.actuators import FireActuator

from mission.constants.region import PATH_1_BEND_RIGHT, PATH_2_BEND_RIGHT

from mission.missions.will_common import Consistent, BigDepth, is_mainsub, FakeMoveX
from auv_python_helpers.angles import heading_sub_degrees
import numpy as np

def visible_test(count):
    return lambda: shm.path_results.num_lines.get() >= count

SearchTask = lambda: SearchFor(VelocitySwaySearch(width=settings.search_forward, stride=settings.search_stride, speed=settings.search_speed, rightFirst=settings.search_right_first),
                                visible_test(2),
                                consistent_frames=(60, 90))

def s(n):
    b = [' '] * 360
    b[180] = '+'
    b[n] = '#'
    return ''.join(b)
def s2(a, b, c):
    bl = [' '] * 360
    bl[180] = '+'
    bl[a] = 'A'
    bl[b] = 'B'
    bl[c] = 'D'
    return ''.join(bl)
def heading_to_vector(h):
    return np.exp([1j * h]).astype(np.complex128).view(np.float64)
def vector_to_heading(v):
    return math.atan2(v[1], v[0])
def hwrap(f):
    def _wrap(*args, **kwargs):
        print('c')
        return f(*args, **kwargs)
    return _wrap
DEADBAND = .06
def is_done(heading_vect, heading, pos, trg, dst, deadband):
    v = (np.float64([heading_vect()]).view(np.complex128) * -dst).view(np.float64)[0]
    pos_var = pos()
    #print(shm.bins_status.cover_x.get(), shm.bins_status.cover_y.get(), v)
    #print(pos_var)
    print(pos_var - v, trg, heading())
    vv = abs(heading_sub_degrees(trg, heading(), math.pi*2)) < math.radians(5) and \
            abs(pos_var[0] - v[0]) < deadband and \
            abs(pos_var[1] - v[1]) < deadband
    #print(vv)
    return vv


#ForwardTarget(point=centerf, target=CAM_CENTER, px=px, py=py, dx=d, dy=d, deadband=(db,db))

def PushLever():
    def TargetLever(py):
        return ForwardTarget(
            point=lambda: (shm.bins_status.lever_x.get(), shm.bins_status.lever_y.get()),
            #target=lambda: (0, .3 * min(100, shm.bins_status.lever_sz.get()) / 100),
            target=(0, .15),
            valid=shm.bins_status.lever_visible.get,
            deadband=(DEADBAND, DEADBAND), px=1, py=py, ix=.05, iy=.05
        )
    return Sequential(
        FunctionTask(VelocityX(.2)),
        MasterConcurrent(
            Consistent(lambda: shm.bins_status.lever_sz.get() > 30, count=.5, total=.75, invert=False, result=True),
            While(lambda: TargetLever(1.5), lambda: True),
            While(lambda: FunctionTask(
                    VelocityX(.2 / (1 + 2 * (abs(shm.bins_status.lever_x.get()) + abs(shm.bins_status.lever_y.get()-.15))))
                ), lambda: True)
        ),
        Log("Higher P"),
        MasterConcurrent(
            Consistent(lambda: shm.bins_status.lever_sz.get() > 100, count=.5, total=.75, invert=False, result=True),
            While(lambda: TargetLever(.8), lambda: True),
            While(lambda: FunctionTask(
                    VelocityX(.2 / (1 + 2 * (abs(shm.bins_status.lever_x.get()) + abs(shm.bins_status.lever_y.get()-.15))))
                ), lambda: True)
        ),
        #Log("targeting"),
        #TargetLever(),
        Log("zoom zoom"),
        FunctionTask(VelocityX(1)),
        Timer(3.5),
        #Timed(
        #    While(TargetLever, lambda: True),
        #    5
        #),
        Timed(VelocityX(-.8), .5),
        VelocityX(0),
        Timer(2.5),
        #RelativeToInitialHeading(0),
        Timed(VelocityX(-.8), 1),
        #RelativeToInitialHeading(0),
        FunctionTask(VelocityX(0)),
        Log("waiting"),
        Timer(5),
        #TargetLever()
    )

push_lever = PushLever()

def PipeAlign(get_center, heading_vect, heading, get_visible, trg, dst, deadband): return Sequential(
    Log("PipeAlign start"),
    MasterConcurrent(
        Consistent(lambda: is_done(heading_vect, heading, get_center, trg, dst, deadband), count=.5, total=.75, invert=False, result=True),
        While(
            lambda: Sequential(
                Log("attempt asdasd"),
                Concurrent(
                    DownwardTarget(
                        lambda: get_center(),
                        target=lambda: (np.float64([heading_vect()]).view(np.complex128) * -dst).view(np.float64)[0],
                        deadband=(deadband, deadband), px=1, py=1, ix=.15, iy=.15
                    ),
                    While(
                        lambda: Sequential(
                            FunctionTask(lambda: shm.navigation_desires.heading.set((shm.kalman.heading.get()-.95*math.degrees(heading_sub_degrees(trg, heading(), math.pi*2))) % 360) if get_visible() else None),
                            #Log('{:03d} '.format(int(shm.navigation_desires.heading.get())) + s2(int(math.degrees(trg)), int(math.degrees(heading())), int(shm.desires.heading.get()))),
                            Timer(.05)
                            ),
                        lambda: abs(heading_sub_degrees(trg, heading(), math.pi*2)) > math.radians(5)
                    )#, count=6, total=8, invert=False, result=True),
                )
            ),
            lambda: True #lambda: abs(heading_sub_degrees(trg, heading(), math.pi*2)) > math.radians(5) or abs(shm.path_results.center_x.get()) > .08 or abs(shm.path_results.center_y.get()) > .08
        ),

            #, count=3, total=4, invert=False, result=True),
        #While(lambda: Log("V: {} h: {} d: {} x: {} y: {} c: {}".format(shm.path_results.num_lines.get(), heading(), math.degrees(heading_sub_degrees(trg, heading(), math.pi*2)), shm.path_results.center_x.get(), shm.path_results.center_y.get(), heading_to_vector(heading()) * dst)), lambda: True),
        #While(lambda: Log(s(int(math.degrees(heading_sub_degrees(trg, heading(), math.pi*2))) + 180)), lambda: True),
         #While(lambda: Log(s2(int(math.degrees(trg)), int(math.degrees(heading()))) if shm.path_results.num_lines.get() == 2 else 'X'), lambda: True),
    ),
    Log("Centered on Pipe in PipeAlign!"),
    #FunctionTask(lambda: shm.navigation_desires.heading.set(-180/math.pi*heading()+shm.kalman.heading.get()))
)



FollowPipe = lambda h1, h2: Sequential(
    PipeAlign(h1), 
    Zero(),
    Log("Aligned To Pipe!"),
    DownwardTarget(lambda: (shm.path_results.center_x.get(), shm.path_results.center_y.get()),
                   target=(0,0),
                   deadband=(.1, .1), px=0.5, py=0.5),
    Zero(),
    Log("Centered on Pipe!"),
    FunctionTask(lambda: shm.navigation_desires.heading.set(-180/math.pi*h2()+shm.kalman.heading.get())),
    Timer(4),
    Log("Facing new direction!"),
    Zero(),
)

def t180(a): return (a + math.pi) % (2 * math.pi)

find_bins = Sequential(
    Depth(.5),
    FunctionTask(VelocityX(.5)),
    While(lambda: NoOp(),
          lambda: not shm.bins_status.cover_visible.get()
    ),
    VelocityX(0),
)

def get_cover_vect():
    return np.float32([shm.bins_status.cover_maj_x.get(), shm.bins_status.cover_maj_y.get()])
def get_cover_center():
    return shm.bins_status.cover_x.get(), shm.bins_status.cover_y.get()
def get_wolf_center():
    return (shm.bins_status.wolf_x.get(), shm.bins_status.wolf_y.get())
def get_bat_center():
    return (shm.bins_status.bat_x.get(), shm.bins_status.bat_y.get())

center_cover = lambda: PipeAlign(get_cover_center, get_cover_vect, lambda: vector_to_heading(get_cover_vect()), shm.bins_status.cover_visible.get, math.pi/2, 0, DEADBAND)
center_wolf = lambda: PipeAlign(get_wolf_center, lambda: heading_to_vector(shm.bins_status.wolf_angle.get()), shm.bins_status.wolf_angle.get, shm.bins_status.wolf_visible.get, math.pi/2, -.2j, DEADBAND)
center_bat = lambda: PipeAlign(get_bat_center, lambda: heading_to_vector(shm.bins_status.bat_angle.get()), shm.bins_status.bat_angle.get, shm.bins_status.bat_visible.get, math.pi/2, -.02-.15j, DEADBAND)

cb = center_bat()
full_wolf = Sequential(
        Depth(1),
        center_wolf(),
        Depth(2.3),
        center_wolf(),
        Timer(.4),
        FireActuator('right_marker', 0.5),
        FireActuator('left_marker', 0.5),
        # do dropper stuff
)

full_bat = Sequential(
        Depth(1),
        center_bat(),
        Depth(2),
        center_bat(),
        Timer(.4),
        FireActuator('right_marker', 0.25),
        FireActuator('left_marker', 0.25),
        # do dropper stuff
)

bins = Sequential(
    find_bins,
    center_cover(),
)

path2 = Sequential(
    Log("Searching for path..."),
    While(
        lambda: Conditional(
            FunctionTask(lambda: shm.path_results.num_lines.get() in (0, 1)),
            on_success=MasterConcurrent(
                While(lambda: NoOp(), lambda: shm.path_results.num_lines.get() < 2),
                Log("Centering on blob..."),
                DownwardTarget(
                    lambda: (shm.path_results.center_x.get(), shm.path_results.center_y.get()),
                    target=(0, 0),
                    deadband=(.1, .1), px=.5, py=.5, ix=.05, iy=.05
                ),
            ),
            on_fail=Sequential(Log("Blind search..."), SearchTask())
        ),
        lambda: shm.path_results.num_lines.get() < 2
    ),
    Zero(),
    Log("Found Pipe!"),
    #Conditional(
    #    FunctionTask(lambda: math.sin(shm.path_results.angle_1.get()) > math.sin(shm.path_results.angle_2.get())),
    #    on_success=gen_pipe("a", shm.path_results.angle_1.get, shm.path_results.angle_2.get),
    #    on_fail=gen_pipe("b", shm.path_results.angle_2.get, shm.path_results.angle_1.get),
    #)
)

get_path = lambda bend_right: FullPipe(bend_right)
