from mission.framework.combinators import Sequential, Retry
from mission.framework.movement import RelativeToInitialHeading 
from mission.framework.position import MoveY
from mission.framework.primitive import Log, Fail, Succeed

from mission.missions.will_common import FakeMoveY

sides = 6

polygon = Succeed(
    Retry(
        lambda: Fail(
            Sequential(
                MoveY(-0.7),
                RelativeToInitialHeading(360 / sides),
                MoveY(-0.7),
            ),
        ), sides
    )
)
