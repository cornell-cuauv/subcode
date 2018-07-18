
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
    Pitch,
    Roll,
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
                        px=0.005,
                        py=0.0005,
                        max_out=.3,
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
        SEARCH_DEPTH_2 = 2.25
        SEARCH_DEPTH_3 = 2.5
        START_PICKUP_DEPTH = 3.0

        def downward_target_task(pt, deadband=(0.1, 0.1)):
            return DownwardTarget(
                point=(shm_group.center_x.get, shm_group.center_y.get),
                target=norm_to_vision_downward(*pt),
                deadband=norm_to_vision_downward(-1.0 + deadband[0], -1.0 + deadband[1]),
                px=0.0005,
                py=0.001,
                max_out=0.04,
            )

        def stop():
            return Concurrent(
                VelocityX(0),
                VelocityY(0),
            )

        def timed(task, timeout=2):
            return Timed(task, timeout)

        self.use_task(
            Sequential(
                cons(Depth(SEARCH_DEPTH)),
                Log("At depth"),
                cons(
                    downward_target_task((0.0, 0.0), deadband=(0.1, 0.1)),
                    debug=True,
                ),
                stop(),
                Log("Found  at top"),
                timed(cons(Depth(SEARCH_DEPTH_2)), 20),
                cons(
                    downward_target_task((0.0, 0.0), deadband=(0.05, 0.05)),
                    debug=True,
                ),
                stop(),
                Log("Found at mid"),
                timed(cons(Depth(SEARCH_DEPTH_3)), 20),
                cons(
                    Concurrent(
                        # downward_target_task((-0.75, 0.1), (0.025, 0.025)),
                        downward_target_task((0.6, 0.1), (0.025, 0.025)),
                        Depth(SEARCH_DEPTH_3),
                        finite=True,
                    ),
                    debug=True,
                ),
                stop(),
                Log("Found at bottom"),
                timed(Depth(2.6)),
                timed(Depth(2.7)),
                timed(Depth(2.8)),
                timed(Depth(2.9)),
                timed(Depth(3.0)),
                timed(Depth(3.1)),
                timed(Depth(3.2)),
                timed(
                    Concurrent(
                        Depth(3.2),
                        Roll(-7.5),
                        Pitch(-7.5),
                    )
                ),
                Log("PICKING UP??"),
                timed(Depth(3.5)),
                timed(Depth(3.0)),
                timed(Depth(2.5)),
                timed(
                    cons(
                        Concurrent(
                            Depth(SEARCH_DEPTH),
                            Roll(0),
                            Pitch(0),
                        )
                    ),
                    15
                ),
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


class ResetDepthPIDs(Task):
    def on_run(self, *args, **kwargs):
        from conf.vehicle import control_settings
        for dof, dof_settings in control_settings.items():
            group = getattr(shm, "settings_" + dof)
            for var, value in dof_settings.items():
                getattr(group, var).set(value)

        self.finish()

class MakeControlGreatAgain2018(Task):
    def on_run(self, *args, **kwargs):
        shm.settings_depth.kP.set(1.25)
        shm.settings_depth.kI.set(0.09)
        shm.settings_depth.kD.set(0.30)
        shm.settings_depth.rD.set(0.30)
        self.finish()

    def on_finish(self, *args, **kwargs):
        self.logw("Depth is now tired of winning")


reset = ResetDepthPIDs()
make_control_great_again = MakeControlGreatAgain2018()


approach_red = ApproachAndTargetFunnel(shm.recovery_vision_forward_red)
approach_green = ApproachAndTargetFunnel(shm.recovery_vision_forward_green)


pickup_red = PickupFromBin(shm.recovery_vision_downward_bin_red)
pickup_green = PickupFromBin(shm.recovery_vision_downward_bin_green)

attempt_red = AttemptColor(approach_red, pickup_red)
attempt_green = AttemptColor(approach_green, pickup_green)
