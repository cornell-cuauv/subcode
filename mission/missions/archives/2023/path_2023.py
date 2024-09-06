#!/usr/bin/env python3

import asyncio
import shm
from mission.framework.base import AsyncBase
from mission.framework.consistency import SHMConsistencyTracker
from mission.framework.search import velocity_square_search
from mission.framework.targeting import downward_target, downward_align
from mission.framework.movement import heading, velocity_x, depth
from mission.framework.primitive import start_modules, kill_modules, zero

class Path2023(AsyncBase):
    def __init__(self):
        self.first_task = self.search()
        self.visible = SHMConsistencyTracker(group=shm.path_results,
                test=lambda path: path.visible, count_true=(8, 10))
        self.center = lambda: (shm.path_results.center_x.get(),
                shm.path_results.center_y.get())
        self.angle = shm.path_results.angle.get
        self.initial_heading = shm.kalman.heading.get()

    async def search(self):
        await start_modules(['AaronPath'])
        await depth(2)
        await velocity_square_search(visible=lambda: self.visible.consistent,
                constant_heading=True)
        return self.target()

    async def target(self):
        success = await downward_target(point=self.center, target=(0, 0),
                visible=lambda: self.visible.consistent, tolerance=(0.1, 0.1))
        if success:
            return self.align()
        return self.search()

    async def align(self):
        await heading(self.initial_heading)
        success = await downward_align(angle=self.angle, target=0,
                visible=lambda: self.visible.consistent)
        if success:
            return None
            #return self.continue_forward()
        return self.search()

    async def continue_forward(self):
        await velocity_x(0.3)
        await asyncio.sleep(10)
        await velocity_x(0)

if __name__ == '__main__':
    Path2023().run(debug=True)

