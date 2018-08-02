# CASTOR MASTER MISSION
# CUAUV ROBOSUB 2018

import shm

from mission.framework.task import Task
from mission.framework.combinators import Sequential, MasterConcurrent, Conditional, Either
from mission.framework.primitive import FunctionTask, Zero, NoOp
from mission.framework.timing import Timer

from mission.missions.master_common import RunAll, MissionTask, TrackerGetter, TrackerCleanup, DriveToSecondPath

from mission.missions.will_common import BigDepth, Consistent, FakeMoveX

from mission.missions.gate import gate as Gate
from mission.missions.path import get_path as PathGetter
from mission.missions.hydrophones import Full as Hydrophones
from mission.missions.roulette import Full as Roulette

from mission.constants.region import PATH_1_BEND_RIGHT, PATH_2_BEND_RIGHT

gate = MissionTask(
    name='Gate',
    cls=Gate,
    modules=[shm.vision_modules.BicolorGate],
    surfaces=False,
    timeout=None,
)

get_path = lambda bend_right: lambda: MissionTask(
    name='Path',
    cls=PathGetter(bend_right),
    modules=[shm.vision_modules.Pipes],
    surfaces=False,
    timeout=None,
)

highway = MissionTask(
    name='Highway',
    cls=DriveToSecondPath,
    modules=None,
    surfaces=False,
    timeout=None,
)

roulette = MissionTask(
    name='Roulette',
    cls=Roulette,
    modules=[shm.vision_modules.Roulette],
    surfaces=False,
    timeout=None,
)

cash_in = MissionTask(
    name='CashIn',
    cls=Timer(30),
    modules=[shm.vision_modules.CashInDownward, shm.vision_modules.CashInForward],
    surfaces=True,
    timeout=None,
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

track = lambda: MissionTask(
    name="Track",
    cls=TrackerGetter(
        found_roulette=FunctionTask(lambda: find_task(ROULETTE)),
        found_cash_in=FunctionTask(lambda: find_task(CASH_IN)),
        enable_roulette=not found_task == ROULETTE,
        enable_cash_in=not found_task == CASH_IN,
    ),
    modules=[shm.vision_modules.CashInDownward, shm.vision_modules.Roulette],
    surfaces=False,
    timeout=None,
    on_exit=TrackerCleanup()
)

TestTrack = Sequential(
    TrackerGetter(
        # found_roulette=FunctionTask(lambda: find_task(ROULETTE)),
        # found_cash_in=FunctionTask(lambda: find_task(CASH_IN)),
        found_roulette=FunctionTask(lambda: False),
        found_cash_in=FunctionTask(lambda: False),
        enable_roulette=True,
        enable_cash_in=True,
    ),
    # TrackCleanup(),
)

tasks = [
    gate,
    get_path(PATH_1_BEND_RIGHT),
    highway,
    get_path(PATH_2_BEND_RIGHT),
    track,
    get_found_task,
    track,
    get_found_task,
]

Master = RunAll(tasks)
