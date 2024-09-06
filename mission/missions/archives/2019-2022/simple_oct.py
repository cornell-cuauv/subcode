#!/usr/bin/env python3

import asyncio
import shm
from mission.framework.base import AsyncBase
from mission.framework.consistency import SHMConsistencyTracker
from mission.framework.search import velocity_square_search
from mission.framework.targeting import downward_target
from mission.framework.movement import depth
from mission.framework.primitive import zero


class SimpleOct(AsyncBase):
    def __init__(self):
        self.first_task = self.search()
        self.visible = SHMConsistencyTracker(group = shm.chev_results, test = lambda chev : chev.visible, count_true = (3,5))
        self.center = lambda : (shm.chev_results.x.get(), shm.chev_results.y.get())

    async def search(self):
        await velocity_square_search(visible = lambda : self.visible.consistent, constant_heading = True)
        return self.target()

    async def target(self):
        success = await downward_target(point = self.center, target=(0,0), visible = lambda : self.visible.consistent, tolerance = (0.5, 0.5))
        if success:
            return self.execute()
        return self.search()

    async def execute(self):
        await depth(1)
        shm.switches.soft_kill.set(True)
        await asyncio.sleep(5)
        await zero()
        shm.switches.soft_kill.set(False)
        await depth(2)

if __name__ == '__main__':
    SimpleOct().run()
