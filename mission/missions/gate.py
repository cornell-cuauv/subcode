from conf.vehicle import VEHICLE

from mission.framework.combinators import Sequential, Concurrent, MasterConcurrent, While
from mission.framework.movement import RelativeToCurrentHeading, RelativeToInitialHeading, Depth, VelocityX, VelocityY, Roll, Heading
from mission.framework.position import MoveX
from mission.framework.primitive import Log, NoOp, FunctionTask, Zero
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

DEPTH_TARGET                              = 0.3
initial_approach_target_percent_of_screen = 0.35
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

def gate_elems():
    if shm.gate.rightmost_visible.get():
        return 3
    if shm.gate.middle_visible.get():
        return 2
    if shm.gate.leftmost_visible.get():
        return 1
    return 0

def can_see_all_gate_elements():
    return gate_elems() == 3

def is_aligned():
    if not can_see_all_gate_elements():
        return False
    l = shm.gate.leftmost_len.get()
    r = shm.gate.rightmost_len.get()
    db = alignment_tolerance_fraction
    lbound = 1/(1+db)
    rbound = 1+db
    # print('{} <= {} <= {}'.format(lbound, l/r, rbound))
    return lbound <= l/r <= rbound

# tasks #######################################################################

class FinishIf(Task):
    def on_run(self, task, condition, **kwargs):
        success = condition()
        if success:
            self.finish(success=success)
        else:
            self.finished = False
            task()

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
    elem_x = elem_x()
    return HeadingTarget(
        point=[elem_x.get, 0],
        target=lambda: [shm.gate.img_width.get() / 2, 0],
        px=0.3,
        deadband=(20,1)
    )

focus_left = lambda: focus_elem(lambda: shm.gate.leftmost_x)
focus_middle = lambda: focus_elem(lambda: shm.gate.middle_x)

hold_depth = While(task_func=lambda: Depth(DEPTH_TARGET), condition=True)

def show():
    print(gate_elems())

align_on_two_elem = \
    Sequential(
        Log('Can see at least two elements (hopefully)'),
        ConsistentTask(
            # while we CAN NOT see all gates
            # Note: While only consistently succeeds if the inner task finishes and the condition is true
            FinishIf(
                task=Concurrent(
                     Log('Targeting smallest'),
                     # pick the element that is smallest
                     focus_elem(lambda: shm.gate.leftmost_x
                         if not shm.gate.middle_visible.get() or shm.gate.leftmost_len.get() < shm.gate.middle_len.get()
                         else shm.gate.middle_x),
                     VelocityX(-0.1),
                     FunctionTask(show),
                     finite=False,
                 ),
                 condition=lambda: can_see_all_gate_elements()
             )
        ),
        Log('Found all three elements'),
        Zero(),
        finite=False
    )

align_on_three_elem = \
    Sequential(
        Log('Can see all three elements'),
        ConsistentTask(
            # while we CAN see all gates
            FinishIf(
                task=Concurrent(
                    Log('Aligning normal to left and right'),
                    PIDLoop(
                        input_value=lambda: shm.gate.rightmost_len.get() / shm.gate.leftmost_len.get(),
                        target=1,
                        p=0.005,
                        db=0,
                        output_function=VelocityY()
                    ),
                    PIDLoop(
                        input_value=lambda: (shm.gate.leftmost_x.get() + shm.gate.rightmost_x.get()) / 2,
                        target=lambda: shm.gate.img_width.get() / 2,
                        p=0.001,
                        db=0,
                        output_function=RelativeToCurrentHeading()
                    ),
                    finite=False
                ),
                condition=lambda: can_see_all_gate_elements() and is_aligned()
            )
        ),
        Zero(),
        finite=False
    )

align_on_passageway = \
    ConsistentTask(
        PIDLoop(
            input_value=lambda: (shm.gate.leftmost_x.get() + shm.gate.middle_x.get()) / 2,
            target=lambda: shm.gate.img_width.get() / 2,
            p=1,
            output_function=VelocityY()
        ),
    )

hold_on_passageway = \
    While(
        PIDLoop(
            input_value=lambda: (shm.gate.leftmost_x.get() + shm.gate.middle_x.get()) / 2,
            target=shm.gate.img_width.get() / 2,
            p=1,
            output_function=VelocityY()
        ),
        condition=True
    )

align_task = \
    Sequential(
        Conditional(main_task=align_on_two_elem, on_success=align_on_three_elem, on_fail=Log('Aligning on two elements failed')),
        #align_on_passageway
        finite=False,
    )

approach_passageway_task = \
    MasterConcurrent(
            While(task_func=lambda: NoOp(), condition=shm.gate.middle_visible.get),
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
            ConsistentTask(MasterConcurrent(
                PIDLoop(
                    input_value=lambda: shm.gate.leftmost_len.get() / shm.gate.img_height.get(),
                    target=initial_approach_target_percent_of_screen,
                    output_function=VelocityX(),
                    p=3,
                    deadband=0.05
                ),
                ConsistentTask(focus_left()),
            )),

            Log('Approach to gate complete. Beginning alignment'),
            align_task,

            #Log('Approaching passageway'),
            #approach_passageway_task,

            #Log('Pre Spin Charging...'),
            #Timed(VelocityX(0.5 if is_mainsub else 0.2), pre_spin_charge_dist),

            #Log('Spin Charging...'),
            #rolly_roll,

            #Log('Post Spin Charging...'),
            #Timed(VelocityX(0.5 if is_mainsub else 0.2), post_spin_charge_dist),

            #Log('Through gate!')
        )
    )
)

class FinishIf(Task):

    def on_run(self, task, condition, **kwargs):
        success = condition()
        if success:
            self.finish(success=success)
        else:
            self.finished = False
            task()

