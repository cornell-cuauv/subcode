# POLLUX MASTER MISSION
# CUAUV ROBOSUB 2018

import shm

from mission.framework.combinators import Sequential

from mission.missions.master_common import RunAll, MissionTask

from mission.missions.gate import gate as Gate
from mission.missions.path import path as Path
from mission.missions.dice import Full as Dice

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

dice = MissionTask(
    name='Dice',
    cls=Dice,
    modules=[shm.vision_modules.Dice],
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
    dice,
    path2,
]

Master = RunAll(tasks)
