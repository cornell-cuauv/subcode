'''
   _______    _     _      _________         __        _     _  __          __
  /  _____\  | \   / |    /  _    _ \       /  \      | \   / | \ \        / /
  | |        | |   | |   /  | \__  \ \     / /\ \     | |   | |  \ \      / /
  | |        | |   | |  | / |    \  | |   / /  \ \    | |   | |   \ \    / /
  | |        | |   | |  | |  \__  | / |  / /    \ \   | |   | |    \ \  / /
  | |______  | |___| |   \ \_   \_|  /  / /      \ \  | |___| |     \ \/ /
  \_______/  \_______/    \_________/  /_/        \_\ \_______/      \__/


   ___       __                 __     ___  ___ _______
  / _ \___  / /  ___  ___ __ __/ /    |_  |/ _ <  /_  /
 / , _/ _ \/ _ \/ _ \(_-</ // / _ \  / __// // / / / /
/_/|_|\___/_.__/\___/___/\_,_/_.__/ /____/\___/_/ /_/

'''

import os
import shm
import datetime
import traceback

from mission.framework.task import Task
from mission.opt_aux.aux import *
from mission.framework.combinators import Sequential, Retry, Concurrent
from mission.missions.opt import Opt, assertModules, killAllModules
from mission.missions.start import WaitForUnkill
from mission.framework.movement import *
from mission.framework.position import *
from mission.framework.timing import Timer
from mission.framework.primitive import FunctionTask, HardkillGuarded, \
                                        EnableController, ZeroWithoutHeading, Zero, Succeed, \
                                        Log, Fail
from mission.constants.region import *
from mission.missions.hydrophones import Full as Hydrophones

from sensors.kalman.set_zero_heading import set_zero_heading

from mission.missions.leds import AllLeds

from collections import namedtuple

MIN_DEPTH = 0.6

class RunTask(Task):
  def on_first_run(self, task, *args, **kwargs):
    # Kind of hacky, but should let us arbitrarily pick MissionTasks for random pinger
    if callable(task):
      task = task()
    self.task = task
    self.taskCls = task.cls()
    if not callable(self.taskCls):
      self.taskCls = task.cls
    self.exceptionCount = 0
    self.maxExceptionCount = 3 #TODO: make settable or more logical
    self.timeout = task.timeout
    self.on_exit = task.on_exit


    self.logi('Starting {} task!'.format(task.name))

  def on_run(self, *args, **kwargs):
    #Block non-surfacing tasks from surfacing
    if not self.task.surfaces and (shm.desires.depth.get() < MIN_DEPTH or shm.kalman.depth.get() < MIN_DEPTH):
      Depth(max(MIN_DEPTH, shm.desires.depth.get()))()
      self.logw('Task attempted to rise above min depth, {}!'.format(MIN_DEPTH))

    #start only required modules
    assertModules(self.task.modules, self.logi)

    if self.timeout is not None and this_run_time - first_run_time > self.timeout:
      self.logw('Task timed out! Finishing task...'),
      self.finish()

    #actually run the bloody mission
    try:
      self.taskCls()
    except Exception as e:
      self.exceptionCount += 1
      if self.exceptionCount < self.maxExceptionCount:
        self.logw('Task {} threw exception: {}! Exception {} of {} before that task is killed!'.format(self.task.name, \
          e, self.exceptionCount, self.maxExceptionCount))
        traceback.print_exc()
      else:
        self.loge('Task {} threw exception: {}! Task has reached exception threshold, will no longer be attempted!'.format( \
          self.task.name, e))
        self.finish()
    if self.taskCls.finished:
      if self.task.name == 'EndMission':
        self.finish(success=False)
      else:
        self.finish()

  def on_finish(self):
    if self.on_exit is not None:
      self.logv('Running task on_exit...')
      self.on_exit()

    #self.logi("Task {} was finished!".format(self.task.name))
    self.logv('{} task finished in {} seconds!'.format(
            self.task.name,
            self.this_run_time - self.first_run_time))
    Zero()()
    killAllModules(self.logi)
    EnableController()()
    shm.settings_control.quat_pid.set(False)

# MissionTask = namedtuple('MissionTask', [
#   'name',
#   'cls',
#   'modules',
#   'surfaces',
#   'timeout',
# ])

class MissionTask():
  def __init__(self, name, cls, modules=None, surfaces=False, timeout=None, on_exit=None):
    self.name = name
    self.cls = cls
    self.modules = modules
    self.surfaces = surfaces
    self.timeout = timeout
    self.on_exit = on_exit

class RunAll(Task):
  def on_first_run(self, tasks, *args, **kwargs):
    #tasks.insert(0, BeginMission)
    tasks.append(EndMission)

    self.use_task(Retry(lambda: Sequential(
      RunTask(BeginMission),
      Concurrent(
        Fail(Sequential(subtasks=[RunTask(t) for t in tasks],)),
        Fail(WaitForUnkill(killed=False, wait=1)),

      ),
      ), float('inf'))
    )

class Begin(Task):
  def on_first_run(self, *args, **kwargs):
    self.killed = shm.switches.hard_kill.get()

    self.use_task(Sequential(
      FunctionTask(lambda: shm.switches.soft_kill.set(1)),
      FunctionTask(lambda: shm.deadman_settings.enabled.set(False)),
      Log('Disabling Record vision module'),
      FunctionTask(lambda: shm.vision_modules.Record.set(0)),
      AllLeds('orange'),

      Log('Wating for alignment...'),
      WaitForUnkill(wait=1.0),
      ZeroHeading(),
      Log('Aligned heading!'),
      AllLeds('cyan'),

      Log('Waiting for re-kill...'),
      WaitForUnkill(killed=False, wait=0.5),
      AllLeds('blue'),

      Log('Waiting for unkill signal to start mission...'),
      WaitForUnkill(wait=5.0),
      Log('Starting mission!'),
      AllLeds('red'),

      Log('Zeroing'),
      Zero(),
      FunctionTask(lambda: shm.switches.soft_kill.set(0)),
      EnableController(),
      Heading(0), # This will revert to the aligned heading
      Log('Enabling Record vision module'),
      FunctionTask(lambda: shm.vision_modules.Record.set(1)),
    ))


class End(Task):
  def on_first_run(self, *args, **kwargs):
    self.use_task(Sequential(
      Log('Ending Run! Surfacing and softkilling'),
      Zero(),
      Depth(0),
      FunctionTask(lambda: shm.switches.soft_kill.set(1)),
      FunctionTask(lambda: shm.deadman_settings.enabled.set(True)),
    ))

# Not used in 2018, perhaps this was 2017?
class HydrophonesWithVision(Task):
  # TODO use a ConcurrentOr combinator instead?
  def on_first_run(self, vision, *args, **kwargs):
    self.hydro = Hydrophones()
    self.vision = vision

  def on_run(self, *args, **kwargs):
    self.hydro()
    self.vision()
    if self.hydro.finished:
      self.logi('Hydrophones finished without seeing anything')
      self.finish()
    elif self.vision.finished:
      self.logi('Hydrophones finished after seeing mission element in vision')
      self.finish()

VisionFramePeriod = lambda period: FunctionTask(lambda: shm.vision_module_settings.time_between_frames.set(period))

ConfigureHydromath = lambda enable: FunctionTask(lambda: shm.hydrophones_settings.enabled.set(enable))

TrackerGetter = lambda found_roulette, found_cash_in: Sequential(
  # Reset found task
  FunctionTask(lambda: find_task(0)),
  # Turn on hydromathd
  ConfigureHydromath(True),
  # Don't kill CPU with vision
  VisionFramePeriod(0.5),
  MasterConcurrent(
    Conditional(
      # Find either roulette or cash-in
      Either(
        Consistent(test=lambda: shm.bins_vision.board_visible.get(),
                   count=4, total=5, invert=False, result=True),
        Consistent(test=lambda: shm.recovery_vision_downward_bin_red.probability.get() > 0,
                   count=4, total=5, invert=False, result=False),
      ),
      # Success is roulette
      on_success=found_roulette,
      # Failure is cash-in
      on_fail=found_cash_in,
    ),
    # Track with hydrophones
    Hydrophones(),
  ),
  Zero(),
  # This should end up getting run twice because we call it in on_exit... but just in case
  TrackerCleanup(),
)

TrackerCleanup = lambda: Sequential(
  # Turn off hydromathd
  ConfigureHydromath(False),
  # Go back to normal vision settings
  VisionFramePeriod(0.1),
)

BeginMission = MissionTask(
  name = 'BeginMission', #DON'T CHANGE THIS!!!!
  cls = Begin,
  modules = None,
  surfaces = True
)

EndMission = MissionTask(
  name = 'EndMission', #DON'T CHANGE THIS!!!!
  cls = End,
  modules = None,
  surfaces = True
)

ZeroHeading = lambda: FunctionTask(set_zero_heading)
