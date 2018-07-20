# POLLUX MASTER MISSION
# CUAUV ROBOSUB 2018

import shm

from mission.framework.combinators import Sequential

from mission.missions.will_common import BigDepth, FakeMoveX

from mission.missions.master_common import RunAll, MissionTask

from mission.missions.gate import gate as Gate
from mission.missions.path import get_path as PathGetter
from mission.missions.dice import Full as Dice

GoToSecondPath = Sequential(
    BigDepth(1.0),
    FakeMoveX(dist=2, speed=0.2),
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

path2 = MissionTask(
    name='Path2',
    cls=PathGetter(),
    modules=[shm.vision_modules.Pipes],
    surfaces=False,
)

tasks = [
    gate,
    path1,
    dice,
    highway,
    path2,
]

Master = RunAll(tasks)
