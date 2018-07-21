# CASTOR MASTER MISSION
# CUAUV ROBOSUB 2018

import shm

from mission.framework.task import Task
from mission.framework.combinators import Sequential, MasterConcurrent, Conditional, Either
from mission.framework.primitive import FunctionTask, Zero, NoOp

from mission.missions.master_common import RunAll, MissionTask

from mission.missions.will_common import BigDepth, Consistent, FakeMoveX

from mission.missions.gate import gate as Gate
from mission.missions.path import get_path as PathGetter
from mission.missions.hydrophones import Full as Hydrophones
from mission.missions.roulette import Full as Roulette

DriveToSecondPath = Sequential(
    BigDepth(1.0),
    FakeMoveX(dist=6, speed=0.4),
    BigDepth(1.2),
)

gate = MissionTask(
    name='Gate',
    cls=Gate,
    modules=[shm.vision_modules.BicolorGate],
    surfaces=False,
)

path1 = MissionTask(
    name='Path1',
    cls=PathGetter(),
    modules=[shm.vision_modules.Pipes],
    surfaces=False,
)

highway = MissionTask(
    name='Highway',
    cls=DriveToSecondPath,
    modules=None,
    surfaces=False,
)

path2 = MissionTask(
    name='Path2',
    cls=PathGetter(),
    modules=[shm.vision_modules.Pipes],
    surfaces=False,
)

roulette = MissionTask(
    name='Roulette',
    cls=Roulette,
    modules=[shm.vision_modules.Roulette],
    surfaces=False,
)

cash_in = MissionTask(
    name='CashIn',
    cls=NoOp(),
    modules=[shm.vision_modules.CashInDownward, shm.vision_modules.CashInForward],
    surfaces=True,
)

# Which task have we found at random pinger?

ROULETTE = 1
CASH_IN = -1
found_task = 0

def find_task(task):
    global found_task
    found_task = task

def get_found_task():
    if found_task == ROULETTE:
        return roulette
    elif found_task == CASH_IN:
        return cash_in
    else:
        return MissionTask(name="Failure", cls=NoOp(), modules=None, surfaces=False)

VisionFramePeriod = lambda period: FunctionTask(lambda: shm.vision_module_settings.time_between_frames.set(period))

ConfigureHydromath = lambda enable: FunctionTask(lambda: shm.hydrophones_settings.enabled.set(enable))

TrackerGetter = lambda: Sequential(
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
            on_success=FunctionTask(lambda: find_task(ROULETTE)),
            # Failure is cash-in
            on_fail=FunctionTask(lambda: find_task(CASH_IN)),
        ),
        # Track with hydrophones
        Hydrophones(),
    ),
    Zero(),
    # Turn off hydromathd
    ConfigureHydromath(False),
    # Go back to normal vision settings
    VisionFramePeriod(0.1),
)

track1 = MissionTask(
    name="Track1",
    cls=TrackerGetter(),
    modules=[shm.vision_modules.CashInDownward, shm.vision_modules.Roulette],
    surfaces=False,
)

track2 = MissionTask(
    name="Track2",
    cls=TrackerGetter(),
    modules=[shm.vision_modules.CashInDownward, shm.vision_modules.Roulette],
    surfaces=False,
)

tasks = [
    gate,
    #path1,
    highway,
    #path2,
    track1,
    get_found_task,
    #track2,
    #get_found_task,
]

Master = RunAll(tasks)
