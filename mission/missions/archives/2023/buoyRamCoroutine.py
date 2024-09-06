#!/usr/bin/env python3
from mission.framework.base import AsyncBase
from mission.framework.position import move_x
from mission.framework.movement import *
from mission.framework.targeting import *
from vision.modules.base import ModuleBase
import shm
import asyncio


class BuoyRam(AsyncBase):


    def __init__(self):
        
        self.first_task = self.search()


    # async def submerge(self):
    #     await depth(1)
    #     return self.search()


    async def search(self):
        #TODO:
        # check visibility first. if visible, skip to centerAndRamBuoy()
        # make sub spin around to look for the sub
        # once found a sub, call center and ram
        if self.visible():
            print('found buoy')
            return self.centerAndRamBuoy()
        print('before spin')
        background_spin = asyncio.create_task(self.spin())
        print('after spin')

        await background_spin
        
        # while not background_spin.done():
        #     if self.visible():
        #         print('found buoy while spinning')
        #         return self.centerAndRamBuoy()


        return "Buoy not found."
        
    def point(self):
        group = shm.red_buoy_results.get()


        point = (group.center_x,group.center_y)
        return point
    
    def visible(self):
        group = shm.red_buoy_results.get()


        if group.heuristic_score > 0:
            return True
        else:
            return False
        
    async def spin(self):
        await relative_to_initial_heading(180)
        await relative_to_current_heading(180)


        
    async def centerAndRamBuoy(self):
        print('running centerRamBuoy')
        target = (0,0)


        background_center = asyncio.create_task(forward_target(self.point,target,self.visible))
        background_move_forward = asyncio.create_task(velocity_x_for_secs(3,40))
        
        


        while not background_move_forward.done():
            print('aa')
            if self.visible() == False:
                print('lost buoy')
                background_move_forward.cancel()
                background_center.done()
                self.search()


            group = shm.red_buoy_results.get()
            buoy_area = group.area
            frame_area = group.frame_height * group.frame_width
            area_filled = buoy_area/frame_area


            if area_filled > 0.4:
                print('succesfully rammed buoy')
                background_move_forward.done()
                background_center.done()


        await background_move_forward
        await background_center


            


    # async def center(self):


    #     target = (0,0)
    #     centered = await forward_target(self.point,target,self.visible)
    
    #     if centered == False:
    #         return self.search()
        
    #     print('can see buoy')
    #     return self.approach_and_ram()


    # async def approach_and_ram(self):
    #     group = shm.red_buoy_results.get()
    #     buoy_area = group.area
    #     frame_area = group.frame_height * group.frame_width
    #     area_filled = buoy_area/frame_area
    #     print('frame area', frame_area)


    #     while area_filled < cand self.visible() == True:
    #         await move_x(0.5)
        
    #     if self.visible() == False:
    #         self.search()




if __name__ == "__main__":
    BuoyRam().run()
