# CASTOR MASTER MISSION
# CUAUV ROBOSUB 2018

import shm

from mission.framework.task import Task
from mission.framework.combinators import Sequential, MasterConcurrent, Conditional, Either
from mission.framework.primitive import FunctionTask, Zero, NoOp
from mission.framework.timing import Timer
from mission.framework.movement import RelativeToCurrentHeading

from mission.missions.master_common import RunAll, MissionTask, TrackerGetter, TrackerCleanup, DriveToSecondPath

from mission.missions.will_common import BigDepth, Consistent, FakeMoveX

from mission.missions.gate import gate as Gate
from mission.missions.path import get_path as PathGetter
from mission.missions.hydrophones import Full as Hydrophones
from mission.missions.roulette import Full as Roulette
from mission.missions.cash_in import Full as CashIn

from mission.missions.stupid import *

from mission.constants.region import PATH_1_BEND_RIGHT, PATH_2_BEND_RIGHT
from mission.constants.timeout import timeouts

# gate & dead reckon
dist1 = 45
dist2 = 10

DeadReckon = Sequential(
    BigDepth(1.5),
    Timed(VelocityX(0.4), dist1),
    # MoveXRough(20),
    VelocityX(0),
    Heading(37),
    Timed(VelocityX(0.4), dist2),
    VelocityX(0),
    finite=True
)

SurfaceCashIn = Sequential(
    Zero(),
    Timer(l.3),
    BigDepth(1.2),
)

gate = MissionTask(
    name='Gate',
    cls=Gate,
    modules=[shm.vision_modules.BicolorGate],
    surfaces=False,
    timeout=timeouts['gate'],
)

gate_dead_reckon = MissionTask(
    name='GateDead',
    cls=GateDeadReckon,
    modules=None,
    surfaces=False,
)

get_path = lambda bend_right: lambda: MissionTask(
    name='Path',
    cls=PathGetter(bend_right),
    modules=[shm.vision_modules.Pipes],
    surfaces=False,
    timeout=timeouts['path'],
    on_timeout=RelativeToInitialHeading(45 if bend_right else -45),
)

highway = MissionTask(
    name='Highway',
    cls=DriveToSecondPath,
    modules=None,
    surfaces=False,
    timeout=timeouts['highway'],
)

roulette = MissionTask(
    name='Roulette',
    cls=Roulette,
    modules=[shm.vision_modules.Roulette],
    surfaces=False,
    timeout=timeouts['roulette'],
)

cash_in = MissionTask(
    name='CashIn',
    cls=CashIn,
    modules=[shm.vision_modules.CashInDownward, shm.vision_modules.CashInForward],
    surfaces=True,
    timeout=timeouts['cash_in'],
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

track = lambda roulette=True, cash_in=False: MissionTask(
    name="Track",
    cls=TrackerGetter(
        found_roulette=FunctionTask(lambda: find_task(ROULETTE)),
        found_cash_in=FunctionTask(lambda: find_task(CASH_IN)),
        enable_roulette=not found_task == ROULETTE,
        enable_cash_in=not found_task == CASH_IN,
    ),
    modules=[shm.vision_modules.CashInDownward, shm.vision_modules.Roulette],
    surfaces=False,
    timeout=timeouts['track'],
    on_exit=TrackerCleanup()
)

# This is used for testing, not used in the actual master mission
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
    lambda: track(cash_in=False),
    get_found_task,
    lambda: track(roulette=False),
    surface_cash_in,
    get_found_task,
]

Master = RunAll(tasks)

# Dead = RunAll([
#     MissionTask(
#         name="stupid1",
#         cls=stupid_castor,
#         modules=[shm.vision_modules.Roulette],
#         on_exit=Zero()
#     ),
#     roulette,
#     MissionTask(
#         name="stupid2",
#         cls=stupid_castor_2,
#         modules=[shm.vision_modules.CashInDownward],
#         on_exit=Zero()
#     ),
#     cash_in
# ])
