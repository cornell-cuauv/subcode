from collections import namedtuple
from math import atan2
import shm
from mission.framework.task import Task
from mission.framework.combinators import (
    Sequential,
    Concurrent,
    MasterConcurrent,
    Retry,
    Conditional,
    While
)
from mission.framework.helpers import call_if_function
from mission.framework.targeting import DownwardTarget
from mission.framework.timing import Timeout
from mission.framework.movement import (
    RelativeToInitialDepth,
    RelativeToCurrentDepth,
    VelocityX,
    VelocityY,
    Depth,
)
from mission.framework.position import MoveY
from mission.framework.primitive import (
    Zero,
    Log,
    Succeed,
    Fail,
    FunctionTask,
    NoOp,
)
from mission.framework.track import ConsistentObject


Predicate = namedtuple('Predicate', ['condition', 'action'])


class LocateBoard(Task):
    # TODO
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)

    def on_run(self, *args, **kwargs):
        pass

    def on_finish(self):
        Zero()()


class CenterBoard(Task):
    """ Centers on the center of the roulette wheel """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.coreqs = [Predicate(shm.bins_vision.board_visible.get, LocateBoard())]
        self.center_task = DownwardTarget((shm.bins_vision.center_x, shm.bins_vision.center_y),
                                          target=(0, 0))

    def on_run(self, *args, **kwargs):
        for coreq in self.coreqs:
            if not call_if_function(coreq.condition):
                coreq.action()
                return
        self.center_task()
        if self.center_task.finished:
            self.finish()

    def on_finish(self):
        Zero()()


class DropBall(NoOp):
    pass


class AlignAndDropBall(Task):
    """ Waits at the center of the roulette wheel until the target bin is in a predetermined
    dropping position, and then moves towards the bin to drop a ball """

    BIN_ANGLE_ALIGNMENT_THRESHOLD = 5 * 3.14 / 180  # 5 degrees
    BIN_ANGLE_TARGET = 0  # 0 degrees (right)

    def __init__(self, target_bin, target_angle=0):
        super().__init__()
        self.target_bin = target_bin
        self.target_angle = target_angle
        self.prereqs = [Predicate(shm.bins_vision.board_visible.get, LocateBoard())]
        self.prereqs_satisifed = False
        self.center_task = CenterBoard()
        self.drop_task = Sequential(Concurrent(RelativeToCurrentDepth(1), MoveY(1)),
                                    DropBall(),
                                    Concurrent(RelativeToCurrentDepth(-1), MoveY(-1)))
        self.task = Sequential(While(self.center_task, self.bin_out_of_position),
                               self.drop_task)

    def on_run(self, *args, **kwargs):
        if not self.prereqs_satisfied:
            for prereq in self.prereqs:
                if not call_if_function(prereq.condition):
                    prereq.action()
                    break
            else:
                self.prereqs_satisfied = True
        self.task()

    def bin_out_of_position(self):
        if not shm.bins_vision.board_visible.get()\
                or not self.target_bin.visible.get()\
                or not self.target_bin.predicted_location.get():
            return False
        center_x = shm.bins_vision.center_x.get()
        center_y = shm.bins_vision.center_y.get()
        target_bin_x = self.target_bin.predicted_x.get()
        target_bin_y = self.target_bin.predicted_y.get()
        diff_x = target_bin_x - center_x
        diff_y = target_bin_y - center_y
        bin_angle = atan2(diff_y, diff_x)
        return abs(bin_angle - self.BIN_ANGLE_TARGET) < self.BIN_ANGLE_ALIGNMENT_THRESHOLD

Full = lambda: None
