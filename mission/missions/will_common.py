import math

from mission.framework.task import Task
from mission.framework.combinators import Sequential
from mission.framework.movement import Depth
from mission.framework.timing import Timer

import shm

# This lets us descend in depth steps rather than all at once
class BigDepth(Task):
    def interpolate_list(self, a, b, steps):
        return [a + (b - a) / steps * i for i in range(1, steps + 1)]

    def tasks_from_params(self, task, params):
        return [task(param) for param in params]

    def tasks_from_param(self, task, param, length):
        return [task(param) for i in range(length)]

    def interleave(self, a, b):
        return [val for pair in zip(a, b) for val in pair]

    def on_first_run(self, depth, largest_step=0.5, timeout=1):
        init_depth = shm.kalman.depth.get()
        steps = math.ceil(abs(depth - init_depth) / largest_step)
        depth_steps = self.interpolate_list(init_depth, depth, steps)
        self.use_task(Sequential(*self.interleave(self.tasks_from_params(Depth, depth_steps), self.tasks_from_param(Timer, 1, steps))))
