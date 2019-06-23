from mission.framework.combinators import Sequential
from mission.framework.position import MoveX, MoveY
from mission.framework.movement import RelativeToInitialHeading, VelocityX, VelocityY, Depth
from mission.framework.timing import Timed
from mission.framework.primitive import Zero


MainSub = Sequential(Depth(2), MoveX(13, deadband=0.4), MoveY(1), MoveX(-13, deadband=0.4))

MiniSub = Sequential(Depth(2), 
        Timed(VelocityX(1), 13), Zero(), 
        Timed(VelocityY(0.5), 2), Zero(), 
        Timed(VelocityX(-1), 13), Zero())
