# POLLUX MASTER MISSION
# CUAUV ROBOSUB 2018

import shm

from mission.framework.combinators import Sequential
from mission.framework.timing import Timer

from mission.missions.will_common import BigDepth, FakeMoveX

from mission.missions.master_common import RunAll, MissionTask, TrackerGetter, TrackerCleanup

from mission.missions.gate import gate as Gate
from mission.missions.path import get_path as PathGetter
from mission.missions.dice import Full as Dice

GoToSecondPath = Sequential(
    BigDepth(1.0),
    FakeMoveX(dist=2, speed=0.2),
    BigDepth(1.2),
)

def time_left():
    # TODO test this?
    time_in = Master.this_run_time - Master.first_run_time
    return 20 * 60 - time_in

WaitForTime = Sequential(
    Zero(),
    Log('Waiting until five minutes left...'),
    Log('Time left: {}, so waiting {} seconds.'.format(time_left(), max(time_left - 5 * 60, 0))),
    # Wait until five minutes left
    lambda: Timer(max(time_left() - 5 * 60, 0)),
)

SurfaceAtCashIn = Sequential(
    Log('Surfacing at cash-in!'),
    BigDepth(0),
)

# --------

gate = MissionTask(
    name='Gate',
    cls=Gate,
    modules=[shm.vision_modules.BicolorGate],
    surfaces=False,
)

path = MissionTask(
    name='Path',
    cls=PathGetter(),
    modules=[shm.vision_modules.Pipes],
    surfaces=False,
)

dice = MissionTask(
    name='Dice',
    cls=Dice,
    modules=[shm.vision_modules.Dice],
    surfaces=False,
)

highway = MissionTask(
    name='Highway',
    cls=GoToSecondPath,
    modules=None,
    surfaces=False,
)

wait_for_track = MissionTask(
    name='StuckInTraffic',
    cls=WaitForTime,
    modules=None,
    surfaces=False,
)

track = MissionTask(
    name='Track',
    cls=TrackerGetter(
        # We can't actually find roulette because the vision module is disabled
        found_roulette=NoOp(),
        found_cash_in=NoOp(),
    ),
    modules=[shm.vision_modules.CashInDownward],
    surfaces=False,
    on_exit=TrackerCleanup(),
)

surface_cash_in = MissionTask(
    name='SurfaceCashIn',
    cls=SurfaceAtCashIn,
    modules=None,
    surfaces=True,
)

tasks = [
    gate,
    path,
    dice,
    highway,
    path,
    wait_for_track,
    surface_cash_in,
]

Master = RunAll(tasks)
