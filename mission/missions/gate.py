from conf.vehicle import VEHICLE

from mission.framework.combinators import Sequential, Concurrent, MasterConcurrent, While
from mission.framework.movement import RelativeToInitialHeading, Depth, VelocityX, VelocityY
from mission.framework.position import MoveX
from mission.framework.primitive import Log, NoOp
from mission.framework.targeting import PIDLoop, HeadingTarget
from mission.framework.timing import Timed
from mission.framework.task import Task
from mission.framework.helpers import ConsistencyCheck, call_if_function

from .ozer_common import ConsistentTask, StillHeadingSearch, GradualHeading

from mission.missions.will_common import BigDepth, is_mainsub

from mission.constants.config import gate as settings

import shm

# results_groups = shm.bicolor_gate_vision

# class Consistent(Task):
#     def on_first_run(self, test, count, total, invert, result):
#         # Multiple by 60 to specify in seconds
#         self.checker = ConsistencyCheck(count * 60, total * 60, default=False)

#     def on_run(self, test, count, total, invert, result):
#         test_result = call_if_function(test)
#         if self.checker.check(not test_result if invert else test_result):
#             self.finish(success=result)

# # TODO fix target
# XTarget = lambda x, db: PIDLoop(input_value=x, target=0,
#                                 output_function=VelocityY(), negate=True,
#                                 p=0.4 if is_mainsub() else 0.4, deadband=db)

DEPTH_TARGET = settings.depth

rolly_roll =
    Concurent(
        VelocityX(0.1),
        Sequential(
            Log('initiating rolly roll'),
            Roll(90),
            Roll(180),
            Roll(270),
            Roll(0),
            Roll(90),
            Roll(180),
            Roll(270),
            Roll(0),
            Log('rolly roll completed')
        )
    )

def biggest_gate_element():
    '''the size of the biggest gate element currently visible'''
    return sorted([
        shm.gate.leftmost_len if shm.gate.leftmost_visible else 0,
        shm.gate.middle_len if shm.gate.middle_visible else 0,
        shm.gate.rightmost_len if shm.gate.rightmost_visible else 0
    ])[-1]

def can_see_all_gate_elements():
    return shm.gate.rightmost_visible()

def is_aligned():
    if not can_see_all_gate_elements():
        return False
    l = shm.gate.leftmost_len()
    r = shm.gate.rightmost_len()
    db = setting.alignment_tolerance_fraction
    return 1/(1+db) <= l/r <= 1+db

align_task = \
    While(
        Sequential(
            MasterConcurent(
                While(NoOp, conditiona=lambda: not can_see_all_gate()),
                PIDLoop(input_value=lambda, output_value=VelocityY)
            )
            on_fail=
        ),
        condition=
    )

#gate = Sequential(target, Log("Targetted"), center, Log("Centered"), charge)
init_heading = None
def save_init_heading():
    global init_heading
    init_heading = shm.kalman.heading.get()

# This is the unholy cross between my (Will's) and Zander's styles of mission-writing
gate = Sequential(
    Log('Depthing...'),
    BigDepth(DEPTH_TARGET),

    Log('Searching for gate'),
    SearchFor(
        Sequential(
            # manual list of "check here first, then just StillHeadingSearch"
            FunctionTask(save_init_heading),
            Log('Searching for gate: using manual turning to right'),
            GradualHeading(init_heading + 90),
            GradualHeading(init_heading + 180),
            Log('Searching for gate: fuck didn\'t find it turn back'),
            GradualHeading(init_heading + 90),
            GradualHeading(init_heading + 0),
            Log('Searching for gate: fuck didn\'t find it spin'),
            GradualHeading(init_heading + 90),
            GradualHeading(init_heading + 180),
            GradualHeading(init_heading + 270),
            GradualHeading(init_heading + 0),
            Log('Searching for gate: fall back on StillHeadingSearch'),
            StillHeadingSearch()
        ),
        shm.gate.leftmost_visible.get
    ),

    Log('Gate is located, HeadingTarget on (leftmost) leg of gate'),
    ConsistentTask(Concurrent(
        Depth(DEPTH_TARGET),
        HeadingTarget(x=shm.gate.leftmost_x)
        finite=False
    )),

    Log('Forward Approach...'),
    ForwardApproach(
        current_size=shm.leftmost_len,
        current_x=shm.leftmost_x,
        target_size=setting.initial_approach_target_len,
        depth_bounds=(DEPTH_TARGET, DEPTH_TARGET)
    ),

    Log('Approach to gate complete. Beginning alignment'),
    While(
        task_func=align_task,
        cond=lambda: not is_aligned()
    ),
    Timed(VelocityX(0 if is_mainsub() else -0.1), 2),
    VelocityX(0),
    Log('Lining up with red side...'),
    ConsistentTask(Concurrent(
        Depth(DEPTH_TARGET),
        XTarget(x=results_groups.gate_center_x.get, db=0.05),
        finite=False,
    )),
    Log('Pre Spin Charging...'),
    Timed(VelocityX(0.5 if is_mainsub() else 0.2), settings.pre_spin_charge_dist),
    Log('Spin Charging...'),
    Concurent(
        Timed(VelocityX(0.25 if is_mainsub() else 0.1), settings.spin_charge_dist),
        )
    ),
    Log('Post Spin Charging...'),
    Timed(VelocityX(0.5 if is_mainsub() else 0.2), settings.post_spin_charge_dist),
    Log('Through gate!'),
)
