#!/usr/bin/env python3

import asyncio
from math import radians, degrees, atan2, sin, cos
from mission.framework.consistency import SHMConsistencyTracker
from mission.framework.search import square_search
from mission.framework.targeting import downward_target

from shm import (hydrophones_pinger_results as results,
                 navigation_desires as desires, kalman,
                 dead_reckoning_virtual)

from mission.framework.base import AsyncBase
from mission.framework.movement import relative_to_initial_setter, velocity_x, heading, depth
from mission.framework.dead_reckoning import go_to_element
import shm

SEARCH_DEPTH = 2 # TODO: Set this

class OctagonSurface(AsyncBase):
    def __init__(self):
        super().__init__()
        self.first_task = self.search()
        self.shm_octagon = shm.yolo_octagon
        self.shm_chevrons = [shm.yolo_chevron_1, shm.yolo_chevron_2,shm.yolo_chevron_3, shm.yolo_chevron_4]
        self.num_of_chevrons = len(self.shm_chevrons)

        self.octagon_visible = SHMConsistencyTracker(group=self.shm_octagon, test=lambda octagon: octagon.visible, count_true=(8, 10), count_false=(9, 10), default=False)
        self.chevron_visible_list = [
            SHMConsistencyTracker(group=chev, test=lambda chevron: chevron.visible, count_true=(8, 10), count_false=(9, 10), default=False) for chev in self.shm_chevrons
        ]

    async def search(self):
        shm.vision_modules.OctagonChevronsVision.set(1)

        await depth(SEARCH_DEPTH)
        success = await square_search(lambda: self.octagon_visible.consistent,
                constant_heading=True)
        if success:
            return self.target()
        return False

    async def target(self):
        def octagon_point():
            return (self.shm_octagon.center_x.get(), self.shm_octagon.center_y.get())

        success = await downward_target(point=octagon_point, target=(0, 0), visible=lambda: self.octagon_visible.consistent, tolerance=(0.1, 0.1))

        if success:
            return self.surface()
        else:
            return self.search()

    async def surface(self):
        await depth(1)
        return None
        

if __name__ == '__main__':
    OctagonSurface().run()
