# CASTOR MASTER MISSION
# CUAUV ROBOSUB 2018

import shm

from mission.framework.combinators import Sequential
from mission.framework.movement import MoveX

from mission.missions.master_common import RunAll, MissionTask

from mission.missions.gate import gate as Gate
from mission.missions.path import path as Path

DriveToSecondPath = Sequential(
    MoveX(4),
)

gate = MissionTask(
    name='Gate',
    cls=Gate,
    modules=[shm.vision_modules.BicolorGate],
    surfaces=False,
)

path1 = MissionTask(
    name='Path1',
    cls=Path,
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
    cls=Path,
    modules=[shm.vision_modules.Pipes],
    surfaces=False,
)

tasks = [
    gate,
    path1,
    highway,
    path2,
]

Master = RunAll(tasks)
