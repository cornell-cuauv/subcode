#!/usr/bin/env python3
from mission.framework.base import AsyncBase
# from mission.framework.position import move_x
from mission.framework.movement import *
# from mission.framework.position import *
from mission.framework.targeting import *
from vision.modules.base import ModuleBase
import shm
from mission.framework.consistency import *
import asyncio
from mission.framework.search import *
from mission.framework.actuation import *
import math
import asyncio

class Torpedo(AsyncBase):
    def __init__(self):
        print('init')

        self.depthBoardGroup = shm.depth_torpedos_board.get()
        depthBoardVisibility = lambda depthBoardGroup: (self.depthBoardGroup.visible.get() == 1)
        isDepthBoardCentered = lambda depthBoardGroup: (abs(self.depthBoardGroup.center_x.get()) < 0.05 and abs(self.depthBoardGroup.center_y.get()) < 0.05)
        self.trackerDepthBoardVisibility= SHMConsistencyTracker(self.depthBoardGroup, depthBoardVisibility, (3, 5), (3, 5), False)

        self.first_task = self.main()

    async def main(self):
        print('MAIN')
        
        # shm.vision_modules.RedBuoy.set(1)

        # if not await self.init_search():
        #     print('CANNOT FIND BOARD')
        #     return

        while not self.depth_board_visible():
            asyncio.sleep(0.1)
        
        while not await self.rough_center_and_approach():
            if not await self.spin(400):
                print("SPIN SEARCH FAILED")

        print("LOW TOLERANCE CENTER")
        await self.center_board_depth()
        print("align and fire")
        await fire_torpedo()
        await fire_torpedo()
        await fire_torpedo()
        await fire_torpedo()
        await fire_torpedo()
        await fire_torpedo()
        await fire_torpedo()
        await fire_torpedo()

        
        # shm.vision_modules.RedBuoy.set(0)


    async def init_search(self):
        print('init search')

        if await spin(80):
            return True
        if await spin(-80):
            return True
        if await spin(-80):
            return True
        if await spin(80):
            return True

        return False
        
    async def spin(self, deg):
        while abs(deg) > 5:
            if self.yolo_board_visible():
                print("SPIN SEARCH: Buoy visible, exiting spin search")

                return True
            
            if abs(deg) > 20:
                temp_deg = math.copysign(20, deg)
            else:
                temp_deg = deg
                
            deg = deg-temp_deg
            
            print(f"SPIN SEARCH: Buoy not visible spinning {temp_deg} degrees")
            await relative_to_initial_heading(temp_deg)

        return False


    async def rough_center_and_approach(self, max_iterations = 5):
        print('ROUGH CENTER AND APPROACH')
                
        await zero()
        while self.area_filled_ratio() < 0.5:
            if not self.depth_board_visible():
                return False

            elif not self.yolo_board_centered():
                max_iterations -= 1
                
                point = self.depth_board_point()
                await zero()
                
                if not await self.center_board_depth(tolerance=(0.2,0.2)):
                    return False
                
                if max_iterations <= 0:
                    return False
            else:
                point = self.depth_board_point()
                await velocity_x(0.2, tolerance=float('inf'))
                await asyncio.sleep(0.1)

        await zero()        
        return True


    def area_filled_ratio(self):
        buoy_group = shm.red_buoy_results.get()
        buoy_area = buoy_group.area
        frame_area = buoy_group.frame_height * buoy_group.frame_width
        area_filled = buoy_area/frame_area
        return area_filled


    def depth_board_visible(self):
        return self.trackerDepthBoardVisibility.consistent

    def depth_board_point(self):
        depth_group = shm.yolo_torpedos_board.get()
        return (depth_group.center_x, depth_group.center_y)

    def center_board_depth(self):
        # await forward_target(self.depth_board_point, (0,0), self.depth_board_visible, tolerance=(0.05,0.05))
        pass
            
    def depth_goals_visible(self):

        return (self.trackerGoal1Visibility.consistent,
                self.trackerGoal2Visibility.consistent,
                self.trackerGoal3Visibility.consistent,
                self.trackerGoal4Visibility.consistent)
        

if __name__ == "__main__":
   Torpedo().run()
