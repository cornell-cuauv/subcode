import os

from mission.framework.combinators import Sequential, Concurrent
from mission.framework.movement import RelativeToInitialHeading, Depth
from mission.framework.position import MoveX
from mission.framework.primitive import Log

# MoveX for minisub w/o a DVL
def fake_move_x(d):
    v = 0.2
    if d < 0:
        d *= -1
        v *= -1
    return Sequential(MasterConcurrent(Timer(d / v), VelocityX(v)), Zero())

def InterMoveX(d):
    #return MoveX(d) if os.environ['CUAUV_VEHICLE'] == 'castor' else fake_move_x(d)
    # changed because Castor's DVL is currently not functioning
    return fake_move_x(d)

Qualify = Sequential(
    Depth(1.0),

    InterMoveX(12),
    RelativeToInitialHeading(90),
    InterMoveX(1),
    RelativeToInitialHeading(90),
    InterMoveX(12),
)
