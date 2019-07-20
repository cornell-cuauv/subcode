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

from mission.constants.config import gate as settings

import shm
shm.gate = shm.gate_vision

# settings ####################################################################

DEPTH_TARGET = settings.depth
print(shm.gate.img_width.get() / 2)

# flags /indicators ###########################################################

init_heading = None
def save_init_heading():
    global init_heading
    init_heading = shm.kalman.heading.get()
    print('saved')

def biggest_gate_element():
    '''the size of the biggest gate element currently visible'''
    return sorted([
        shm.gate.leftmost_len if shm.gate.leftmost_visible else 0,
        shm.gate.middle_len if shm.gate.middle_visible else 0,
        shm.gate.rightmost_len if shm.gate.rightmost_visible else 0
    ])[-1]

def can_see_all_gate_elements():
    return shm.gate.rightmost_visible.get()

def is_aligned():
    if not can_see_all_gate_elements():
        return False
    l = shm.gate.leftmost_len.get()
    r = shm.gate.rightmost_len.get()
    db = setting.alignment_tolerance_fraction
    return 1/(1+db) <= l/r <= 1+db

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
        px=0.5,
        deadband=(20,1)
    )

focus_left = focus_elem(shm.gate.leftmost_x)
focus_middle = focus_elem(shm.gate.middle_x)

hold_depth = While(task_func=lambda: Depth(DEPTH_TARGET), condition=True)

align_on_two_elem = \
    MasterConcurrent(
        # while we CAN NOT see all gates
        While(NoOp, condition=lambda: not can_see_all_gate_elements()),
        PIDLoop(
            input_value=lambda: shm.gate.leftmost_len() / shm.gate.middle_len.get(),
            target=1,
            output_value=VelocityY
        ),
        ConsistentTask(Concurrent(
            Depth(DEPTH_TARGET),
            # pick the element that is smallest
            While(focus_elem(
                shm.gate.leftmost_x.get
                if shm.gate.leftmost_len.get() < shm.gate.middle_len.get()
                else shm.gate.middle_x.get
            ), condition=True)
        ))
    )

align_on_three_elem = \
    MasterConcurrent(
        # while we CAN see all gates
        While(NoOp, condition=lambda: can_see_all_gate()),
        PIDLoop(
            input_value=lambda: shm.gate.leftmost_len() / shm.gate.rightmost_len.get(),
            target=1,
            output_value=VelocityY
        ),
        ConsistentTask(Concurrent(
            hold_depth,
            focus_middle
        ))
    )

align_task = \
    While(
        Sequential(
            Log('Can see at least two elements (hopefully)'),
            align_on_two_elem,
            Log('Can see all three elements'),
            align_on_three_elem
        ),
        condition=lambda: not is_aligned()
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
    Depth(DEPTH_TARGET),

    Log('Searching for gate'),
    search_task,

    Log('Gate is located, HeadingTarget on (leftmost) leg of gate'),
    ConsistentTask(MasterConcurrent(
        focus_left,
        hold_depth,
        finite=False
    )),

    Log('Forward Approach...'),
    ConsistentTask(MasterConcurrent(
        PIDLoop(
            input_value=lambda: shm.gate.leftmost_len.get() / shm.gate.img_height.get(),
            target=settings.initial_approach_target_percent_of_screen,
            output_function=VelocityX,
            p=40,
            deadband=20
        ),
        focus_left,
        hold_depth,
        finite=False
    )),

    Log('Approach to gate complete. Beginning alignment'),
    align_task,

    Log('Aligned to gate, aligning to small section'),
    ConsistentTask(Concurrent(
        Depth(DEPTH_TARGET),
        HeadingTarget(
            point=[shm.gate.leftmost_x.get, 0],
            target=lambda: [shm.gate.img_width.get() / 2, 0],
            px=0.5,
            deadband=(40,1)
        ),
        finite=False
    )),

    Log('Pre Spin Charging...'),
    Timed(VelocityX(0.5 if is_mainsub else 0.2), settings.pre_spin_charge_dist),

    Log('Spin Charging...'),
    Concurrent(
        Timed(VelocityX(0.25 if is_mainsub else 0.1), settings.spin_charge_dist),
    ),

    Log('Post Spin Charging...'),
    Timed(VelocityX(0.5 if is_mainsub else 0.2), settings.post_spin_charge_dist),

    Log('Through gate!')
)
