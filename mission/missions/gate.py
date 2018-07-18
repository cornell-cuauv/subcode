from conf.vehicle import VEHICLE

from mission.framework.combinators import Sequential, Concurrent
from mission.framework.movement import RelativeToInitialHeading, Depth, VelocityX, VelocityY
from mission.framework.position import MoveX
from mission.framework.primitive import Log
from mission.framework.targeting import PIDLoop
from mission.framework.timing import Timed
from mission.framework.task import Task

from .ozer_common import ConsistentTask

import shm

results_groups = shm.bicolor_gate_vision

is_castor = VEHICLE == 'castor'

XTarget = lambda: PIDLoop(input_value=results_groups.red_center_x.get, target=0,
                          output_function=VelocityY(), negate=True, p=1.25, deadband=0.01875)

last_width = 0

def get_width():
    global last_width
    width = results_groups.width.get()
    # Don't update width if it's 0
    if width > 0:
        last_width = width
    return last_width
    
#WidthTarget = lambda width: PIDLoop(input_value=get_width, target=width,
#                                    output_function=VelocityX(), negate=False, p=1.0, deadband=0.03)

target = ConsistentTask(Concurrent(Depth(1.5), XTarget(), finite=False))
center = ConsistentTask(Concurrent(Depth(1.5), XTarget(), WidthTarget(0.6), finite=False))
charge = Timed(VelocityX(0.3 if is_castor else 0.1), 20)


gate = Sequential(target, Log("Targetted"), center, Log("Centered"), charge)
