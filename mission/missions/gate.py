from conf.vehicle import VEHICLE

from mission.framework.combinators import Sequential, Concurrent, MasterConcurrent, While
from mission.framework.movement import RelativeToInitialHeading, Depth, VelocityX, VelocityY, Roll, Heading
from mission.framework.position import MoveX
from mission.framework.primitive import Log, NoOp, FunctionTask
from mission.framework.targeting import PIDLoop, HeadingTarget, ForwardApproach
from mission.framework.timing import Timed
from mission.framework.task import Task
from mission.framework.helpers import ConsistencyCheck, call_if_function
from mission.framework.search import SearchFor

from .ozer_common import ConsistentTask, StillHeadingSearch, GradualHeading

from mission.missions.will_common import BigDepth, is_mainsub

import shm
shm.gate = shm.gate_vision

# settings ####################################################################

DEPTH_TARGET                              = 1.0
initial_approach_target_percent_of_screen = 0.45
alignment_tolerance_fraction              = 0.05
gate_width_threshold                      = 0.4
pre_spin_charge_dist                      = 16 if is_mainsub else 12
spin_charge_dist                          = 16 if is_mainsub else 12
post_spin_charge_dist                     = 16 if is_mainsub else 12


# flags /indicators ###########################################################

init_heading = None
def save_init_heading():
    global init_heading
    init_heading = shm.kalman.heading.get()

def biggest_gate_element():
    '''the size of the biggest gate element currently visible'''
    return max([
        shm.gate.leftmost_len.get() if shm.gate.leftmost_visible.get() else 0,
        shm.gate.middle_len.get() if shm.gate.middle_visible.get() else 0,
        shm.gate.rightmost_len.get() if shm.gate.rightmost_visible.get() else 0
    ])

def can_see_all_gate_elements():
    return shm.gate.rightmost_visible.get()

def is_aligned():
    if not can_see_all_gate_elements():
        return False
    l = shm.gate.leftmost_len.get()
    r = shm.gate.rightmost_len.get()
    db = alignment_tolerance_fraction
    lbound = 1/(1+db)
    rbound = 1+db
    print('{} <= {} <= {}'.format(lbound, l/r, rbound))
    return lbound <= l/r <= rbound

# tasks #######################################################################

rolly_roll = \
    Concurrent(
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

def focus_elem(elem_x):
    return HeadingTarget(
        point=[elem_x.get, 0],
        target=lambda: [shm.gate.img_width.get() / 2, 0],
        px=0.2,
        deadband=(20,1)
    )

focus_left = lambda: focus_elem(shm.gate.leftmost_x)
focus_middle = lambda: focus_elem(shm.gate.middle_x)

hold_depth = While(task_func=lambda: Depth(DEPTH_TARGET), condition=True)

align_on_two_elem = \
    ConsistentTask(MasterConcurrent(
        # while we CAN NOT see all gates
        While(task_func=lambda: NoOp(), condition=lambda: not can_see_all_gate_elements()),
        # pick the element that is smallest
        While(task_func=lambda: \
            Sequential(
                focus_elem(shm.gate.leftmost_x
                    if shm.gate.leftmost_len.get() < shm.gate.middle_len.get()
                    else shm.gate.middle_x),
                VelocityX(-0.1),
            ), condition=True)
        , finite=False)
    )

align_on_three_elem = \
    ConsistentTask(MasterConcurrent(
        # while we CAN see all gates
        While(NoOp, condition=lambda: can_see_all_gate_elements() and not is_aligned()),
        PIDLoop(
            input_value=lambda: shm.gate.leftmost_len.get() / shm.gate.rightmost_len.get(),
            target=1,
            output_function=VelocityY()
        ),
        HeadingTarget(
            point=lambda: [(shm.gate.leftmost_x.get() + shm.gate.rightmost_x.get()) / 2, 0],
            target=lambda: [shm.gate.img_width.get() / 2, 0],
            px=0.3,
            deadband=(0,1)
        )
    ))

align_on_passageway = \
    ConsistentTask(
        PIDLoop(
            input_value=lambda: (shm.gate.leftmost_x.get() + shm.gate.middle_x.get()) / 2,
            target=shm.gate.img_width.get() / 2,
            px=1,
            output_function=VelocityY()
        ),
    )

hold_on_passageway = \
    While(
        PIDLoop(
            input_value=lambda: (shm.gate.leftmost_x.get() + shm.gate.middle_x.get()) / 2,
            target=shm.gate.img_width.get() / 2,
            px=1,
            output_function=VelocityY()
        ),
        condition=True
    )

align_task = \
    Sequential(
        While(
            task_func=lambda: Sequential(
                Log('Can see at least two elements (hopefully)'),
                align_on_two_elem,
                Log('Can see all three elements'),
                align_on_three_elem
            ),
            condition=lambda: not is_aligned()
        ),
        align_on_passageway
    )

approach_passageway_task = \
    MasterConcurrent(
        While(NoOp, condition=shm.gate.middle_visible.get),
        VelocityX(0.3),
        hold_on_passageway
    )

# lineup_task = \

search_task = \
    SearchFor(
        Sequential(
            # manual list of "check here first, then just StillHeadingSearch"
            FunctionTask(save_init_heading),
            Log('Searching for gate: using manual turning to right'),
            Heading(lambda: init_heading + 90),
            Heading(lambda: init_heading + 180),
            Log('Searching for gate: fuck didn\'t find it turn back'),
            Heading(lambda: init_heading + 90),
            Heading(lambda: init_heading + 0),
            Log('Searching for gate: fuck didn\'t find it spin'),
            Heading(lambda: init_heading + 90),
            Heading(lambda: init_heading + 180),
            Heading(lambda: init_heading + 270),
            Heading(lambda: init_heading + 0),
            Log('Searching for gate: fall back on StillHeadingSearch'),
            StillHeadingSearch()
        ),
        shm.gate.leftmost_visible.get
    )

# main task ###################################################################

gate = Sequential(
    Log('Depthing...'),
    Depth(DEPTH_TARGET, error=0.12),

    Concurrent(
        hold_depth,
        Sequential(
            Log('Searching for gate'),
            search_task,

            Log('Gate is located, HeadingTarget on (leftmost) leg of gate'),
            ConsistentTask(focus_left()),

            Log('Forward Approach...'),
            ConsistentTask(
                PIDLoop(
                    input_value=lambda: shm.gate.leftmost_len.get() / shm.gate.img_height.get(),
                    target=initial_approach_target_percent_of_screen,
                    output_function=VelocityX(),
                    p=3,
                    deadband=0.05
                ),
            ),

            Log('Approach to gate complete. Beginning alignment'),
            align_task,

            Log('Approaching passageway'),
            approach_passageway_task,

            Log('Pre Spin Charging...'),
            Timed(VelocityX(0.5 if is_mainsub else 0.2), pre_spin_charge_dist),

            Log('Spin Charging...'),
            rolly_roll,

            Log('Post Spin Charging...'),
            Timed(VelocityX(0.5 if is_mainsub else 0.2), post_spin_charge_dist),

            Log('Through gate!')
        )
    )
)
