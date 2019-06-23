from mission.framework.combinators import Sequential, Retry, While
from mission.framework.movement import RelativeToInitialHeading 
from mission.framework.position import MoveY
from mission.framework.primitive import Log, Fail, Succeed, FunctionTask

from mission.missions.will_common import FakeMoveY

sides = 6
attempt = iter((x for x in range(0,sides+1)))

def loop_state():
    current = -1
    def iterate():
        nonlocal current
        current += 1
        return current < sides
    return iterate

polygon = Sequential(
    While(
        lambda: Sequential(
            MoveY(-0.7),
            RelativeToInitialHeading(360 / sides),
            MoveY(-0.7),
            ), loop_state()
    )
)
