# POLLUX MASTER MISSION
# CUAUV ROBOSUB 2018

import shm

from mission.framework.combinators import MasterConcurrent, Sequential
from mission.framework.timing import Timer
from mission.framework.primitive import Log, Zero, NoOp
from mission.framework.targeting import DownwardTarget

from mission.missions.will_common import BigDepth, FakeMoveX

from mission.missions.master_common import RunAll, MissionTask, TrackerGetter, TrackerCleanup, DriveToSecondPath

from mission.missions.gate import gate as Gate
from mission.missions.path import get_path as PathGetter
from mission.missions.dice import Full as Dice

from mission.missions.cash_in import norm_to_vision_downward

def time_left():
    # TODO test this?
    #time_in = Master.this_run_time - Master.first_run_time
    return 0 #20 * 60 - time_in

WaitForTime = Sequential(
    Zero(),
    Log('Waiting until five minutes left...'),
    Log('Time left: {}, so waiting {} seconds.'.format(time_left(), max(time_left() - 5 * 60, 0))),
    # Wait until five minutes left
    Timer(max(time_left() - 5 * 60, 0)),
)

CASH_IN_GROUPS = [(group.center_x, group.center_y) for group in [shm.recovery_vision_downward_bin_red, shm.recovery_vision_downward_bin_green]]

cash_in_center = lambda: tuple(sum([val.get() for val in dimen]) for dimen in CASH_IN_GROUPS)

# TODO test this
SurfaceAtCashIn = Sequential(
    Zero(),
    Timer(3),
    Log('Aligning with cash-in'),
    #DownwardTarget(
    #    cash_in_center,
    #    target=norm_to_vision_downward(0, 0),
    #    deadband=norm_to_vision_downward(-0.5, -0.5),
    #    px=0.0005, py=0.001,
    #),
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

path = lambda: MissionTask(
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
    cls=DriveToSecondPath,
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
        enable_roulette=False,
    ),
    modules=[shm.vision_modules.CashInDownward],
    surfaces=False,
    on_exit=TrackerCleanup(),
)

surface_cash_in = MissionTask(
    name='SurfaceCashIn',
    cls=SurfaceAtCashIn,
    modules=[shm.vision_modules.CashInDownward],
    surfaces=True,
)

tasks = [
    gate,
    path,
    dice,
    highway,
    path,
    wait_for_track,
    track,
    surface_cash_in,
]

Master = RunAll(tasks)

