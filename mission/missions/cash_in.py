
import time
from collections import deque
import itertools

import shm
from mission.constants.config import recovery as constants
from mission.constants.region import WALL_TOWER_HEADING
from shm.watchers import watcher
from mission.framework.task import Task
from mission.framework.search import SpiralSearch, VelocitySwaySearch
from mission.framework.combinators import (
    Sequential,
    MasterConcurrent,
    Concurrent,
    Retry,
    Conditional,
    While,
    Defer,
)
from mission.framework.movement import (
    Depth,
    RelativeToInitialDepth,
    RelativeToCurrentDepth,
    VelocityX,
    VelocityY,
    Heading,
)
from mission.framework.timing import Timer, Timeout, Timed
from mission.framework.primitive import (
    Zero,
    FunctionTask,
    NoOp,
    Log,
    Succeed,
    Fail,
)
from mission.framework.helpers import (
    ConsistencyCheck,
    call_if_function,
    within_deadband,
)
from mission.framework.position import (
    MoveX,
    MoveXRough,
    GoToPositionRough,
    WithPositionalControl,
    PositionalControl,
)
from mission.framework.targeting import (
    DownwardTarget,
    ForwardTarget,
    PIDLoop,
)
from mission.framework.track import (
    Matcher,
    Match,
    Observation,
    ComplexColor,
    HeadingInvCameraCoord,
    HeadingInvAngle,
    ConsistentObject
)
from mission.missions.ozer_common import (
    GlobalTimeoutError,
    GradualHeading,
    GradualDepth,
    SearchWithGlobalTimeout,
    CenterCentroid,
    Disjunction,
    ConsistentTask,
    PrintDone,
    Altitude,
    AlignAmlan,
    # AMLANS,
    Infinite,
    Except,
)


def vision_to_norm_downward(x, y=None):
    if y is None:
        x, y = call_if_function(x)
    else:
        x, y = call_if_function(x), call_if_function(y)

    w, h = shm.camera.downward_width.get(), shm.camera.downward_height.get()

    return ((x / w - 0.5) * 2, (y / h - 0.5) * 2)


def norm_to_vision_downward(x, y=None):
    if y is None:
        x, y = call_if_function(x)
    else:
        x, y = call_if_function(x), call_if_function(y)

    w, h = shm.camera.downward_width.get(), shm.camera.downward_height.get()

    return ((x / 2 + 0.5) * w, (y / 2 + 0.5) * h)

def vision_to_norm_forward(x, y=None):
    if y is None:
        x, y = call_if_function(x)
    else:
        x, y = call_if_function(x), call_if_function(y)

    w, h = shm.camera.forward_width.get(), shm.camera.forward_height.get()

    return ((x / w - 0.5) * 2, (y / h - 0.5) * 2)


def norm_to_vision_forward(x, y=None):
    if y is None:
        x, y = call_if_function(x)
    else:
        x, y = call_if_function(x), call_if_function(y)

    w, h = shm.camera.forward_width.get(), shm.camera.forward_height.get()

    return ((x / 2 + 0.5) * w, (y / 2 + 0.5) * h)


def cons(task, total=3*60, success=3*60*0.9, debug=False):
    return ConsistentTask(task, total=total, success=success, debug=debug)


class ApproachAndTargetFunnel(Task):
    def on_first_run(self, shm_group, *args, **kwargs):
        self.use_task(
            cons(
                Concurrent(
                    ForwardTarget(
                        point=(shm_group.center_x.get, shm_group.center_y.get),
                        target=norm_to_vision_forward(0, 0.6),
                        # depth_bounds=(.5, 1.5),
                        deadband=norm_to_vision_forward(-0.9, -0.9),
                        px=0.001,
                        py=0.0001,
                        max_out=.5,
                    ),
                    PIDLoop(
                        input_value=shm_group.area.get,
                        target=10000,
                        deadband=1000,
                        output_function=VelocityX(),
                        reverse=True,
                        p=0.00001,
                        max_out=.5,
                    ),
                    finite=False,
                ),
                total=3*60,
                success=3*60*0.9,
                debug=True,
            )
        )


class PickupFromBin(Task):
    def on_first_run(self, shm_group, *args, **kwargs):
        SEARCH_DEPTH = 2.0
        START_PICKUP_DEPTH = 3.0

        downward_target_task = DownwardTarget(
            point=(shm_group.center_x.get, shm_group.center_y.get),
            target=norm_to_vision_downward(0, 0),
            deadband=norm_to_vision_downward(-0.9, -0.9),
            px=0.0001,
            py=0.0001,
            max_out=.5,
        )

        self.use_task(
            Sequential(
                cons(Depth(SEARCH_DEPTH)),
                cons(downward_target_task),
                cons(
                    Concurrent(
                        downward_target_task,
                        Depth(START_PICKUP_DEPTH)
                    ),
                ),
                Log("PICKING UP??"),
                cons(Depth(SEARCH_DEPTH)),
            ),
        )


class AttemptColor(Task):
    def on_first_run(self, approach_task, pickup_task, *args, **kwargs):
        SURFACE_DEPTH = -1
        FUNNEL_DEPTH = 0

        self.use_task(
            Sequential(
                pickup_task,
                Log("Picked up!"),
                cons(Depth(SURFACE_DEPTH)),
                Log("Surfaced"),
                cons(Depth(FUNNEL_DEPTH)),
                Log("Prepared to drop"),
                approach_task,
                Log("Dropped"),
                Timed(VelocityX(-.3), 2),
            )
        )


class CashIn(Task):
    def on_run(self, *args, **kwargs):
        self.log("Cash In!", level="CASH")
        self.finish()



approach_red = ApproachAndTargetFunnel(shm.recovery_vision_forward_red)
approach_green = ApproachAndTargetFunnel(shm.recovery_vision_forward_green)


pickup_red = PickupFromBin(shm.recovery_vision_downward_bin_red)
pickup_green = PickupFromBin(shm.recovery_vision_downward_bin_green)

attempt_red = AttemptColor(approach_red, pickup_red)
attempt_green = AttemptColor(approach_green, pickup_green)
