#!/usr/bin/env python3

import math

import shm

from conf.vehicle import VEHICLE

from mission.framework.combinators import Sequential, Concurrent, MasterConcurrent, Retry, Conditional, While
from mission.framework.helpers import get_downward_camera_center, ConsistencyCheck
from mission.framework.movement import Depth, Heading, Pitch, VelocityX, VelocityY, RelativeToCurrentHeading
from mission.framework.position import PositionalControl
from mission.framework.primitive import Zero, Log, FunctionTask, Fail
from mission.framework.search import SearchFor, VelocityTSearch, SwaySearch, PitchSearch, VelocitySwaySearch
from mission.framework.targeting import DownwardTarget, PIDLoop, HeadingTarget
from mission.framework.task import Task
from mission.framework.timing import Timer, Timed
from mission.framework.jank import TrackMovementY, RestorePosY

from mission.constants.config import path as settings

from mission.missions.will_common import BigDepth, is_mainsub

SearchTask = lambda: SearchFor(VelocitySwaySearch(forward=settings.search_forward, stride=settings.search_stride, speed=settings.search_speed, rightFirst=settings.search_right_first),
                                lambda: shm.path_results.num_lines.get() == 2,
                                consistent_frames=(60, 90))

class FirstPipeGroupFirst(Task):
    # Checks whether the first pipe group in shm is the first pipe we should follow.
    # Succeeds if the first pipe group is consistently the right one, fails otherwise
    def on_first_run(self): 
        self.angle_1_checker = ConsistencyCheck(6, 8)
        self.angle_2_checker = ConsistencyCheck(6, 8)

    def on_run(self):
        angle_1 = abs(shm.path_results.angle_1.get())
        angle_2 = abs(shm.path_results.angle_2.get())

        if self.angle_1_checker.check(angle_1 < angle_2):
            self.finish()
        if self.angle_2_checker.check(angle_2 < angle_1):
            self.finish(success=False)

PipeAlign = lambda heading: Concurrent(DownwardTarget(lambda: (shm.path_results.center_x.get(), shm.path_results.center_y.get()),
                                              target=(0, -.25),
                                              deadband=(.1, .1), px=0.5, py=0.5),
                                       Log("Centered on Pipe!"),
                                       FunctionTask(lambda: shm.navigation_desires.heading.set(-180/3.14*heading.get()+shm.kalman.heading.get())))


FollowPipe = lambda h1, h2: Sequential(PipeAlign(h1), 
                                       Zero(),
                                       Log("Aligned To Pipe!"),
                                       DownwardTarget(lambda: (shm.path_results.center_x.get(), shm.path_results.center_y.get()),
                                                      target=(0,0),
                                                      deadband=(.1, .1), px=0.5, py=0.5),
                                       Zero(),
                                       Log("Centered on Pipe!"),
                                       FunctionTask(lambda: shm.navigation_desires.heading.set(-180/3.14*h2.get()+shm.kalman.heading.get())),
				       Timer(4),
                                       Log("Facing new direction!"),
                                       Zero(),
                                       Timed(VelocityX(.1), settings.post_dist),
                                       Log("Done!"),
                                       Zero())

FullPipe = lambda: Sequential(BigDepth(settings.depth),
                              Zero(),
                              Log("At right depth!"),
                              SearchTask(),
                              Zero(),
                              Log("Found Pipe!"),
                              Conditional(FirstPipeGroupFirst(),
                                          on_success=FollowPipe(shm.path_results.angle_1, shm.path_results.angle_2),
                                          on_fail=FollowPipe(shm.path_results.angle_2, shm.path_results.angle_1)))


path = FullPipe()

get_path = lambda: FullPipe()
