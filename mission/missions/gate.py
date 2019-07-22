from conf.vehicle import VEHICLE

from mission.framework.combinators import Sequential, Concurrent, MasterConcurrent, While, Conditional
from mission.framework.movement import RelativeToCurrentHeading, RelativeToInitialHeading, Depth, VelocityX, VelocityY, Roll, Heading, RelativeToCurrentRoll
from mission.framework.position import MoveX
from mission.framework.primitive import Log, NoOp, FunctionTask, Zero, Fail
from mission.framework.targeting import PIDLoop, HeadingTarget, ForwardApproach
from mission.framework.timing import Timed, Timer
from mission.framework.task import Task
from mission.framework.helpers import ConsistencyCheck, call_if_function
from mission.framework.search import SearchFor

from .ozer_common import ConsistentTask, StillHeadingSearch, GradualHeading

from mission.missions.will_common import BigDepth, is_mainsub

from mission.missions.roll import RollDegrees

import shm
shm.gate = shm.gate_vision

# settings ####################################################################

DEPTH_TARGET                              = 1.5
initial_approach_target_percent_of_screen = 0.35
alignment_tolerance_fraction              = 0.05
gate_width_threshold                      = 0.4
pre_spin_charge_dist                      = 3 if is_mainsub else 3
post_spin_charge_dist                     = 1 if is_mainsub else 2
pre_spin_charge_vel                       = 1 if is_mainsub else 1
post_spin_charge_vel                      = 1 if is_mainsub else 1


# flags /indicators ###########################################################

saved_heading = None
def save_heading():
    global saved_heading
    saved_heading = shm.kalman.heading.get()

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

pv = shm.settings_roll.kP.get()
rolly_roll = \
    Sequential(
        FunctionTask(lambda: shm.settings_roll.kP.set(.6)),
        MasterConcurrent(
            RollDegrees(360 * 2 - 180),
            RelativeToCurrentRoll(90),
            VelocityX(.35)
        ),
        Timer(1),
        FunctionTask(lambda: shm.settings_roll.kP.set(pv))
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
        Log('Targeting smallest'),
        ConsistentTask(
            # while we CAN NOT see all gates
            # Note: While only consistently succeeds if the inner task finishes and the condition is true
            FinishIf(
                task=Concurrent(
                     # pick the element that is smallest
                     focus_elem(lambda: shm.gate.leftmost_x
                         if not shm.gate.middle_visible.get() or shm.gate.leftmost_len.get() < shm.gate.middle_len.get()
                         else shm.gate.middle_x),
                     VelocityX(-0.1),
                     FunctionTask(show),
                     finite=False,
                 ),
                 condition=lambda: gate_elems() != 2
             )
        ),
        Log('Found all three elements'),
        Zero(),
        finite=False
    )

align_on_three_elem = \
    Sequential(
        Log('aligning on three elems'),
        ConsistentTask(
            # while we CAN see all gates
            FinishIf(
                task=Concurrent(
                    PIDLoop(
                        input_value=lambda: shm.gate.rightmost_len.get() / shm.gate.leftmost_len.get(),
                        target=1,
                        p=0.5,
                        db=0,
                        output_function=VelocityY()
                    ),
                    PIDLoop(
                        input_value=lambda: (shm.gate.leftmost_x.get() + shm.gate.rightmost_x.get()) / 2,
                        target=lambda: shm.gate.img_width.get() / 2,
                        p=0.2,
                        db=alignment_tolerance_fraction,
                        output_function=RelativeToCurrentHeading(),
                        negate=True
                    ),
                    finite=False
                ),
                condition=lambda: gate_elems() < 3 or is_aligned()
            )
        ),
        Conditional(
            FunctionTask(lambda: gate_elems() < 3),
            on_success=Sequential(
                Log('cannot see all gate_elem'),
                Fail()
            ),
            on_fail= Log('is aligned to 3 elems')
        ),
        # finite=False
    )

align_on_passageway = \
    ConsistentTask(
        PIDLoop(
            input_value=lambda: (shm.gate.leftmost_x.get() + shm.gate.middle_x.get()) / 2,
            target=lambda: shm.gate.img_width.get() / 2,
            p=0.002,
            output_function=VelocityY(),
            negate=True
        ),
    )

align_task = \
    Sequential(
        While(
            Sequential(
                Conditional(
                    main_task=FunctionTask(lambda: gate_elems() == 2),
                    on_success=align_on_two_elem,
                    on_fail=Conditional(
                        main_task=FunctionTask(lambda: gate_elems() == 3),
                        on_success=align_on_three_elem,
                        on_fail=Sequential(
                            Log('we see less than two elems, failed'),
                            Fail()
                        )
                    )
                ),
                Zero(),
                Timer(1),
                finite=False
            ),
            condition=lambda: is_aligned()
        ),
        finite=False,
    )

approach_passageway_task = \
    MasterConcurrent(
        PIDLoop(
            input_value=lambda: shm.gate.middle_x.get() - shm.gate.leftmost_x.get(),
            target=lambda: shm.gate.img_width.get() * 0.6,
            deadband=lambda: shm.gate.img_width.get() * 0.05,
            p=0.002,
            output_function=VelocityX()
            # negate=True
        ),
        PIDLoop(
            input_value=lambda: (shm.gate.leftmost_x.get() + shm.gate.middle_x.get()) / 2,
            target=shm.gate.img_width.get() / 2,
            p=0.3,
            deadband=0,
            output_function=RelativeToCurrentHeading(),
            negate=True
        )
    )

search_task = \
    SearchFor(
        Sequential(
            # manual list of "check here first, then just StillHeadingSearch"
            FunctionTask(save_heading),
            Log('Searching for gate: using manual turning to right'),
            Heading(lambda: saved_heading + 90),
            Heading(lambda: saved_heading + 180),
            Log('Searching for gate: fuck didn\'t find it turn back'),
            Heading(lambda: saved_heading + 90),
            Heading(lambda: saved_heading + 0),
            Log('Searching for gate: fuck didn\'t find it spin'),
            Heading(lambda: saved_heading + 90),
            Heading(lambda: saved_heading + 180),
            Heading(lambda: saved_heading + 270),
            Heading(lambda: saved_heading + 0),
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
                    deadband=lambda: shm.gate.img_height.get() * 0.05
                ),
                ConsistentTask(focus_left()),
            )),

            Log('Approach to gate complete. Beginning alignment'),
            align_task,

            Log('Approaching passageway'),
            approach_passageway_task,

            Log('Pre Spin Charging...'),
            FunctionTask(save_heading),
            Timed(VelocityX(pre_spin_charge_vel), pre_spin_charge_dist),

            Log('Spin Charging...'),
            rolly_roll,

            Log('Spin Complete, pausing...'),
            Zero(),
            Timer(1),

            Log('Post Spin Charging...'),
            Timed(VelocityX(post_spin_charge_vel), post_spin_charge_dist),
            Zero(),
            Timer(1),
            Heading(lambda: saved_heading),

            Log('Through gate!')
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

