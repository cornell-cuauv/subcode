#!/usr/bin/env python3
from mission.framework.base import AsyncBase
from mission.framework.position import move_x
from mission.framework.movement import *
from mission.framework.targeting import *
from vision.modules.base import ModuleBase
import shm
from mission.framework.consistency import SHMConsistencyTracker
import asyncio
from mission.framework.search import *


class BuoyRam(AsyncBase):

    
    
    def __init__(self):
        group = shm.red_buoy_results
        # self.first_task = self.search()
<<<<<<< Updated upstream
        visibility = lambda group: (group.heuristic_score > 0)
=======
        visibility = lambda group: (group.heuristic_score > 0.65)
>>>>>>> Stashed changes
        self.tracker = SHMConsistencyTracker(group, visibility, (3, 5), (3, 5), False)

        
        self.first_task = self.swaySearch()

    async def submerge(self):
        await depth(1)
        return self.search()


    async def search(self):
        print(self.visible())
        if self.visible():
                print('found buoy')
                return self.centerAndRamBuoy()
        

        spinBackground = asyncio.create_task(self.spinFullCircle())
        while not spinBackground.done():
            velocity_y_for_secs(0.5,2)
            await asyncio.sleep(0.01)
            print('corountine running')
            if self.visible():
                print('foundbuoy')
                spinBackground.cancel()
                await zero()
                return self.centerAndRamBuoy()


    async def spinFullCircle(self):
        await relative_to_initial_heading(90)
        await relative_to_initial_heading(90)
        await relative_to_initial_heading(90)
        await relative_to_initial_heading(90)

    async def swaySearch(self):
        await asyncio.sleep(5)
        print(self.visible())
        if self.visible():
            print('found buoy')
            return self.centerAndRamBuoy()
        else:
            searchResult = await sway_search(lambda: self.visible())
            if searchResult == False:
                print('buoyNotFound')
                return
            return self.center()

        
       
    def point(self):
        group = shm.red_buoy_results.get()
        point = (group.center_x,group.center_y)
        return point
        

    
    def visible(self):
        
        print('from visible function', self.tracker.consistent)
        return self.tracker.consistent
        # if group.heuristic_score > 0:

        #     return True
        # else:
        #     refturn False

    async def centerAndRamBuoy(self):
        print('running centerRamBuoy')
        target = (0,0)


        background_center = asyncio.create_task(forward_target(self.point,target,self.visible))
        background_move_forward = asyncio.create_task(velocity_x_for_secs(.15,40))

        while not background_move_forward.done():
            await asyncio.sleep(0.1)
            print('in while loop')
            if self.visible() == False:
                print('lost buoy')
                background_center.cancel()
                background_move_forward.cancel()

                return self.swaySearch()


            group = shm.red_buoy_results.get()
            buoy_area = group.area
            frame_area = group.frame_height * group.frame_width
            area_filled = buoy_area/frame_area


            if area_filled > 0.4:
                print('succesfully rammed buoy')
                
                background_move_forward.done()
                background_move_forward.done()
                await zero()
        

    async def center(self):
        target = (0,0)
        centered = await forward_target(self.point,target,self.visible)
    
        if centered == False:
            return self.swaySearch()
        
        print('can see buoy')
        return self.approach_and_ram()


    async def approach_and_ram(self):
        group = shm.red_buoy_results.get()
        buoy_area = group.area
        frame_area = group.frame_height * group.frame_width
        area_filled = buoy_area/frame_area
        print('frame area', frame_area)


        while area_filled < .3 and self.visible() == True:
            await move_x(1)

        if area_filled > .3 and self.visible():
            return


        else:
            self.swaySearch()
        

        



if __name__ == "__main__":
   BuoyRam().run()