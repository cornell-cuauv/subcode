from mission.framework.combinators import Sequential, Retry
from mission.framework.movement import RelativeToInitialHeading 
from mission.framework.position import MoveYRough
from mission.framework.primitive import Log, Fail, Succeed

from mission.missions.will_common import FakeMoveY

sides = 6

polygon = Succeed(
    Retry(
        lambda: Fail(
            Sequential(
                MoveYRough(-0.7),
                RelativeToInitialHeading(360 / sides),
                MoveYRough(-0.7),
            ),
        ), sides
    )
)
