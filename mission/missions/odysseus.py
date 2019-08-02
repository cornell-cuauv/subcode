# CASTOR MASTER MISSION
# CUAUV ROBOSUB 2018

import shm

from mission.framework.task import Task
from mission.framework.combinators import Sequential, MasterConcurrent, Conditional, Either, Retry
from mission.framework.primitive import FunctionTask, Zero, NoOp, InvertSuccess, Fail, Log
from mission.framework.timing import Timer
from mission.framework.movement import RelativeToCurrentHeading, Depth, VelocityX

from mission.missions.master_common import RunAll, MissionTask  # , TrackerGetter, TrackerCleanup, DriveToSecondPath

from mission.missions.will_common import BigDepth, Consistent, FakeMoveX
from mission.missions.attilus_garbage import PositionMarkers, SetMarker, GoToMarker

from mission.missions.gate import gate as Gate
# from mission.missions.path import get_path as PathGetter
from mission.missions.stake import Full as Stake, SearchBoard, BOARD_DEPTH
from mission.missions.vampire import SearchAnyVampire as SearchVampire
from mission.missions.pinger_tracker import TrackPinger

from mission.constants.timeout import timeouts

markers = PositionMarkers()

# TODO: TIMEOUTS

gate = MissionTask(
    name='Gate',
    cls=Gate,
    modules=[shm.vision_modules.Gate],
    surfaces=False,
    timeout=timeouts['gate'],
)

# get_path = lambda bend_right: lambda: MissionTask(
#     name='Path',
#     cls=PathGetter(bend_right),
#     modules=[shm.vision_modules.Pipes],
#     surfaces=False,
#     timeout=timeouts['path'],
#     on_timeout=RelativeToInitialHeading(45 if bend_right else -45),
# )

# highway = MissionTask(
#     name='Highway',
#     cls=DriveToSecondPath,
#     modules=None,
#     surfaces=False,
#     timeout=timeouts['highway'],
# )

stake = MissionTask(
    name='Stake',
    cls=lambda: Stake(),
    modules=[shm.vision_modules.Stake],
    surfaces=False,
    timeout=timeouts['stake'],
)

Surface = lambda: Sequential(Zero(), Depth(0))

surface = MissionTask(
        name='Surface',
        cls=lambda: Surface(),
        modules=[],
        surfaces=True,
        timeout=timeouts['surface'],
)

track_pinger = lambda: MissionTask(
        name='Track',
        cls=lambda: TrackPinger(),
        modules=[],
        surfaces=False,
        timeout=timeouts['track_pinger']
)

# TODO: Recovery + Pinger
Recovery = None
    # MissionTask(
    # name="SurfaceCashIn",
    # cls=lambda: SurfaceCashIn(),
    # modules=None,
    # surfaces=True,
# )


# Which task have we found at random pinger?

#ROULETTE = 1
#CASH_IN = -1
#found_task = 0

#cash_in_surfaced = False

#def find_task(task):
#    global found_task, cash_in_surfaced
#    found_task = task

#def get_found_task():
#    global cash_in_surfaced

#    if found_task == ROULETTE:
#        cash_in_surfaced = True
#        return roulette
#    else:
#        #found_task == CASH_IN:
#        if cash_in_surfaced:
#            return cash_in
#        else:
#            cash_in_surfaced = True
#            return surface_cash_in

    # print('found_task:', found_task)
    # print('cash_in_surfaced:', cash_in_surfaced)
    # return surface_cash_in

    #else:
    #    return MissionTask(name="Failure", cls=NoOp(), modules=None, surfaces=False)

# pinger task should be a function that returns a task
# TODO: MAKE SURE THIS WORKS
pinger_task = None
pinger_tasks = [surface, stake]

def set_pinger_task(task):
    global pinger_task
    pinger_task = task
    return True

def set_second_task_if_possible():
    global pinger_task
    print(pinger_task)
    if pinger_task is not None:
        for p in pinger_tasks:
            if pinger_task != p:
                pinger_task = p
                print(p)
                return True
    return False

def get_pinger_task():
    global pinger_task
    if pinger_task is None:
        return Fail()
    return pinger_task

# This is semi psuedocode
def TrackerSearch():
    global get_pinger_task
    global stake
    return Retry(lambda: \
        Sequential(
                Sequential(
                    Depth(BOARD_DEPTH, error=0.2),
                    Either(
                        TrackPinger(),
                        # Consistent(lambda: get_pinger_task() == stake and shm.torpedoes_stake.board_visible.get(), count=2, total=3, invert=False, result=True)),
                        Consistent(shm.torpedoes_stake.board_visible.get, count=2, total=3, invert=False, result=True)),
                    VelocityX(0, error=40),
                    Log('dafuq'),
                    Conditional(FunctionTask(set_second_task_if_possible), on_fail= \
                        Conditional(SearchBoard(), on_success=FunctionTask(lambda: set_pinger_task(stake)), on_fail= \
                                Sequential(
                                    Log('we cant see jack'),
                                    FunctionTask(lambda: set_pinger_task(surface))
                                )
                        )
                    )
                )
            ), attempts=3
    )

track = lambda: MissionTask(
    name="Track",
    cls=lambda: TrackerSearch(),
    modules=[shm.vision_modules.Vampire, shm.vision_modules.Stake],
    surfaces=False,
    timeout=timeouts['track_pinger'],
)


set_gate = lambda: MissionTask(
    name="SetGate",
    cls=lambda: SetMarker('gate'),
    modules=[],
    surfaces=False,
    timeout=20
)


goto_gate = lambda: MissionTask(
    name="GoToGate",
    cls=lambda: GoToMarker('gate'),
    modules=[],
    surfaces=False,
    timeout=60
)

path = lambda: MissionTask(
    name="path",
    cls=lambda: RelativeToInitialHeading(45),
    modules=[],
    surface=False,
    timeout=30
)



tasks_nonrandom = [
    lambda: gate,
    path,
    track_pinger,
    lambda: stake,
    track_pinger,
    lambda: surface,
]

tasks = [
    lambda: gate,
    path,
    set_gate,
    track,
    get_pinger_task,
    goto_gate,
    track,
    get_pinger_task
]

Master_Backup = RunAll(tasks_nonrandom)
Master = RunAll(tasks)
