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

class Torpedo(AsyncBase):
    def __init__(self):
        print('init')
        self.buoyGroup = shm.red_buoy_results

        self.gaol1Group = shm.depth_goal_1
        self.gaol2Group = shm.depth_goal_2
        self.gaol3Group = shm.depth_goal_3
        self.gaol4Group = shm.depth_goal_4

        self.yoloBoardGroup = shm.yolo_torpedos_board
        self.depthBoardGroup = shm.depth_torpedos_board
        
        yoloBoardVisibility = lambda yoloBoardGroup: (self.yoloBoardGroup.visible.get() == 1)
        depthBoardVisibility = lambda depthBoardGroup: (self.depthBoardGroup.visible.get() == 1)
        isYoloBoardCentered = lambda buoyGroup: (abs(self.yoloBoardGroup.center_x.get()) < 0.05 and abs(self.yoloBoardGroup.center_y.get()) < 0.05)


        
        self.trackerYoloBoardVisibility = SHMConsistencyTracker(self.yoloBoardGroup, yoloBoardVisibility, (3, 5), (3, 5), False)
        self.trackerDepthBoardVisibility= SHMConsistencyTracker(self.depthBoardGroup, depthBoardVisibility, (3, 5), (3, 5), False)
        self.YoloBoardCentered = SHMConsistencyTracker(self.yoloBoardGroup, isYoloBoardCentered, (3, 5), (3, 5), False)


        self.first_task = self.main()


    async def main(self):
        print('MAIN')
        
        # change later
        shm.vision_modules.RedBuoy.set(1)

        if not await self.init_search():
            print('CANNOT FIND BOARD')
            return
        
        while not await self.rough_center_and_approach():
            if not await self.spin(400):
                print("SPIN SEARCH FAILED")

        print("LOW TOLERANCE CENTER")
        await self.center_board_yolo()
        print("aligh and fire")
        await self.align_and_fire_no_goal_vision()
        
        shm.vision_modules.RedBuoy.set(0)

    async def left_and_right_search(self):
        dist = 0
        # move to right
        while dist < 1:
            await move_y(0.15)
            await relative_to_initial_heading(-15)
            dist +=0.15
        # move to left

    async def align_and_fire_no_vision(self):
        await move_z(-0.2)
        await move_y(-0.2)
        await fire_torpedo()
        # currently not even using depth. want to see how it works in the water
            


    async def init_search(self):
        print('init search')

        # comment out for now:
        print('SWAY')
        
        if not await sway_search(self.yolo_board_visible()):
            print('SWAY SEARCH FAILED')
        if not await self.spin(80):
            print('SWAY SEARCH FAILED')
            print('MISSION FAILED')
            # maybe add another bakup
        return True
        

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
        while self.area_filled_ratio() < 0.01:
            if not self.yolo_board_visible():
                return False
            elif not self.yolo_board_centered():
                max_iterations -= 1
                
                point = self.yolo_board_point()
                print(f"Buoy Point: (outbound) {max_iterations} Left")
                print(f"    x: {point[0]}")
                print(f"    y: {point[1]}")
                await zero()
                
                if not await self.center_board_yolo(tolerance=(0.2,0.2)):
                    return False
                
                if max_iterations <= 0:
                    return False
            else:
                point = self.yolo_board_point()
                print(f"Buoy Point: (inbound)")
                print(f"    x: {point[0]}")
                print(f"    y: {point[1]}")
                await velocity_x(0.2, tolerance=float('inf'))
                await asyncio.sleep(0.1)

        await zero()        
        return True

    async def center_board_yolo(self,tolerance = (0.07,0.07)):
        print('CENTER BUOY')
        target = (0, 0)
        return await forward_target(self.yolo_board_point, target, self.yolo_board_visible, tolerance=tolerance)
    
    def area_filled_ratio(self):
        buoy_group = shm.red_buoy_results.get()
        buoy_area = buoy_group.area
        frame_area = buoy_group.frame_height * buoy_group.frame_width
        area_filled = buoy_area/frame_area
        return area_filled

    async def circumnavigate(self):
        print('circumnavigate')
        await move_y(1,tolerance=0.6)
        await move_x(2,tolerance=0.6)
        await move_y(-2,tolerance=0.6)
        await move_x(-2,tolerance=0.6)
        await move_y(1,tolerance=0.6)


    def yolo_board_visible(self):
        # return True
        # print('yolo_board_visible',self.trackerBuoyVisibility.consistent)
        return self.trackerYoloBoardVisibility.consistent

    def yolo_board_point(self):
        yolo_group = shm.yolo_torpedos_board.get()
        return (yolo_group.center_x, yolo_group.center_y)
        # return (0,0)

    def yolo_board_centered(self):
        print('buoy_center',self.trackerBuoyCentered.consistent)
        return self.trackerBuoyCentered.consistent
    

    def depth_board_visible(self):
        pass
    
    def depth_goals_visible(self):
        pass

if __name__ == "__main__":
   Torpedo().run()
