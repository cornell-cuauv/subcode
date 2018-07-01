from mission.framework.combinators import Sequential, Concurrent
from mission.framework.movement import RelativeToInitialHeading, Depth
from mission.framework.position import MoveX
from mission.framework.primitive import Log

from mission.missions.gate import gate

RunGate = lambda: gate

RunPole = lambda: Sequential(
    MoveX(3),
    RelativeToInitialHeading(90),
    MoveX(1),
    RelativeToInitialHeading(90),
    MoveX(1),
)

Qualify = Sequential(
    Depth(1.0),
    RunGate(),
    GoAroundPole(),
    RunGate(),
)
