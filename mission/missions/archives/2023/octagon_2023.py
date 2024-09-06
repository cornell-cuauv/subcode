#!/usr/bin/env python3

import asyncio
from shm import master_mission_settings, chevrons_results_0 as chevron
from mission.framework.base import AsyncBase
from mission.framework.consistency import SHMConsistencyTracker
from mission.framework.movement import depth, relative_to_initial_depth
from mission.framework.search import square_search
from mission.framework.targeting import downward_target, downward_align

class OctagonSurface2023(AsyncBase):
    def __init__(self):
        self.first_task = self.surface()
    
    async def surface(self):
        master_mission_settings.can_surface.set(True)
        await depth(0)
        await asyncio.sleep(5)
        await depth(2)
        master_mission_settings.can_surface.set(False)
        return None

SEARCH_DEPTH = 2.5 # TODO: Set this

chevron_visible = SHMConsistencyTracker(group=chevron,
        test=lambda chevron: chevron.visible, count_true=(8, 10))

class OctagonChevrons2023(AsyncBase):
    def __init__(self):
        self.first_task = self.search()
    
    async def search(self):
        await depth(SEARCH_DEPTH)
        success = await square_search(lambda: chevron_visible.consistent,
                constant_heading=True, timeout_radius=4)
        if success:
            await relative_to_initial_depth(0.75)
            return self.target()
        return False
    
    async def target(self):
        success = await downward_target(point=lambda: (chevron.center_x.get(),
                chevron.center_y.get()), target=(0, 0),
                visible=lambda: chevron_visible.consistent)
        if success:
            return self.align()
        return self.search()
    
    async def align(self):
        success = await downward_align(angle=lambda: chevron.angle.get(),
                target=0, visible=lambda: chevron_visible.consistent)
        if success:
            return self.descend()
        return self.search()
    
    async def descend(self):
        if chevron.width.get() * chevron.height.get() > 0.05:
            return self.final_dead_reckon()
        await relative_to_initial_depth(0.3)
    
    async def final_dead_reckon(self):
        return None #TODO



if __name__ == '__main__':
    OctagonSurface2023().run()
    