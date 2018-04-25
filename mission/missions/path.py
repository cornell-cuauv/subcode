#!/usr/bin/env python3

import math

import shm

from mission.framework.combinators import Sequential, Concurrent, Retry, Conditional
from mission.framework.helpers import get_downward_camera_center, ConsistencyCheck
from mission.framework.movement import Depth, Heading, Pitch, VelocityX, VelocityY, RelativeToCurrentHeading
from mission.framework.position import PositionalControl
from mission.framework.primitive import Zero, Log, FunctionTask, Fail
from mission.framework.search import SearchFor, VelocityTSearch, SwaySearch, PitchSearch
from mission.framework.targeting import DownwardTarget, PIDLoop, HeadingTarget
from mission.framework.task import Task
from mission.framework.timing import Timer, Timed
from mission.framework.jank import TrackMovementY, RestorePosY

PATH_FOLLOW_DEPTH = .6
PATH_SEARCH_DEPTH = .6
PATH_RIGHT_FIRST = True

class center(Task):
    def update_data(self):
        self.path_results = shm.path_results_1.get()

    def on_first_run(self):
        self.update_data()

        path_found = self.path_results.visible > 0

        self.centered_checker = ConsistencyCheck(8, 10)

        self.center = DownwardTarget(lambda self=self: (self.path_results.center_x, self.path_results.center_y),
                                     target=(0,0),
                                     deadband=(.05,.05), px=0.5, py=0.5, dx=0.02, dy=0.02,
                                     valid=path_found)
        self.logi("Beginning to center on the path")


    def on_run(self):
        self.update_data()
        self.center()

        if not check_seen():
            self.finish(success=False)

        if self.centered_checker.check(self.center.finished):
            self.center.stop()
            self.finish()

class align(Task):
    def update_data(self):
        self.path_results = shm.path_results_1.get()

    def on_first_run(self):
        self.update_data()

        self.align = Heading(lambda: self.path_results.angle + shm.kalman.heading.get() + 90, deadband=0.1)
        #self.align = RelativeToCurrentHeading(1)

        self.alignment_checker = ConsistencyCheck(49, 50)

        path_found = self.path_results.visible > 0

        self.center = DownwardTarget(lambda self=self: (self.path_results.center_x, self.path_results.center_y),
                                     target=(0,0),
                                     deadband=(.05,.05), px=0.2, py=0.2, dx=0.02, dy=0.02,
                                     valid=path_found)

    def on_run(self):
        self.update_data()

        self.align()
        print("kal")
        print(self.path_results.angle)
        # self.center()

        if not check_seen():
            self.finish(success=False)

        if self.alignment_checker.check(False):
            self.finish()

search_task_behind = lambda: SearchFor(VelocityTSearch(forward=2,stride = 3, rightFirst=PATH_RIGHT_FIRST, checkBehind=True),
                                lambda: shm.path_results_1.visible.get() > 0,
                                consistent_frames=(10, 10))

search_task= lambda: SearchFor(VelocityTSearch(forward=2,stride = 3, rightFirst=PATH_RIGHT_FIRST),
                                lambda: shm.path_results_1.visible.get() > 0,
                                consistent_frames=(10, 10))

pitch_search_task = lambda: SearchFor(PitchSearch(30),
                                      lambda: shm.path_results_1.visible.get() > 0,
                                      consistent_frames=(6, 6))

path_test = lambda: Sequential(Depth(PATH_SEARCH_DEPTH),
                               search_task(), center(), align(),
                               Depth(PATH_FOLLOW_DEPTH))

pitch_path_test = lambda: Sequential(Depth(PATH_SEARCH_DEPTH),
                          pitch_search_task(), Zero(),
                          Concurrent(center(), Pitch(0)), Zero(),
                          center(), align(), Depth(PATH_FOLLOW_DEPTH))

def check_seen():
    visible = shm.path_results_1.visible.get()

    #print(visible)
    if visible > 0:
        return True
    else:
        #print('Lost Path!')
        return False

class Timeout(Task):
    def on_first_run(self, time, task, *args, **kwargs):
        self.timer = Timer(time)

    def on_run(self, time, task, *args, **kwargs):
        task()
        self.timer()
        if task.finished:
          self.finish()
        elif self.timer.finished:
          self.logw('Task timed out in {} seconds!'.format(time))
          self.finish()

def one_path(grp):
    return Timeout(45, Sequential(
        Log('Going to Search Depth'),
        Depth(PATH_SEARCH_DEPTH),
        Zero(),
        Log('Sway searching for path with Behind'),
        TrackMovementY(search_task_behind()),
          Retry(lambda: Sequential(
            Zero(),
            Log('Sway searching for path; may have been lost'),
            TrackMovementY(search_task(), shm.jank_pos.y.get()),
            Log('Centering on path'),
            Conditional(
              center(),

              on_fail=Fail(Sequential(
                Log("Path lost, Attempting to Restore Y pos"),
                Zero(),
                TrackMovementY(RestorePosY(.3), shm.jank_pos.y.get()),
              ))
            ),

            Depth(PATH_FOLLOW_DEPTH),
            Log('Aligning with path'),
            Concurrent(
                align(),
                center(),
                finite=False
            ),
            ), float("inf")),

        Zero(),
        Log('Aligned, moving forward'),
        Timed(VelocityX(.4),3),
        Zero()
        #Depth(PATH_FOLLOW_DEPTH)
    ))

def test_path(grp):
    return Timeout(45, Sequential(
        # Log('Going to Search Depth'),
        # Depth(PATH_SEARCH_DEPTH),
        # Zero(),
        # Log('Sway searching for path with Behind'),
        # TrackMovementY(search_task_behind()),
          Retry(lambda: Sequential(
            Zero(),
            Log('Centering on path'),
            center(),
            Depth(PATH_FOLLOW_DEPTH),
            Log('Aligning with path'),
            Heading(shm.path_results_1.angle.get() + shm.kalman.heading.get() + 90, deadband=0.1),
            Zero(),
            Log('Aligned, I hope')
            ), float("inf")),

        Zero(),
        # Log('Aligned, moving forward'),
        # Timed(VelocityX(.4),3),
        # Zero()
        # #Depth(PATH_FOLLOW_DEPTH)
    ))

full = test_path(shm.desires)

def second_path(grp):
    return Sequential(
        Log('Going to Search Depth'),
        Depth(PATH_SEARCH_DEPTH),
        Retry(lambda: Sequential(
            Zero(),
            Log('Sway searching for path'),
            search_task(),
            Log('Centering on path'),
            center(),

            Depth(PATH_FOLLOW_DEPTH),
            Log('Aligning with path'),
            Concurrent(
                align(),
                center(),
                finite=False
            ),
            ), float("inf")),
        Zero(),
        Log('Aligned, moving forward'),
        Timed(VelocityX(.4),3),
        Zero()
        #Depth(PATH_FOLLOW_DEPTH)
    )

#paths_mission = second_path(shm.desires)

def pitch_path(grp):
    return Sequential(
             Depth(PATH_SEARCH_DEPTH),
             pitch_search_task(),
             Zero(),
             center(),
             Pitch(0),
             center(),

             Depth(PATH_FOLLOW_DEPTH),

             Concurrent(
                 #center(),
                 align(),
                 finite=False,
             ),
             PositionalControl(),
             Zero(),
    )

pitch_path_mission = pitch_path(shm.desires)



class OptimizablePath(Task):
  def desiredModules(self):
    return [shm.vision_modules.Paths]

  def on_first_run(self, grp):
    self.subtask = one_path(grp)
    self.has_made_progress = False

  def on_run(self, grp):
    self.subtask()
    if self.subtask.finished:
      self.finish()
