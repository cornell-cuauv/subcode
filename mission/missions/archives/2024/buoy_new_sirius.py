#!/usr/bin/env python3
from mission.framework.base import AsyncBase
from mission.framework.position import move_x
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

class goAroundBuoy(AsyncBase):
    def __init__(self):
        print('init')
        self.buoyGroup = shm.red_buoy_results
        
        buoyVisibility = lambda buoyGroup: (self.buoyGroup.heuristic_score.get() > 0.5)
        isBuoyCentered = lambda buoyGroup: (abs(self.buoyGroup.center_x.get()) < 0.05 and abs(self.buoyGroup.center_y.get()) < 0.05)

        self.trackerBuoyVisibility = SHMConsistencyTracker(self.buoyGroup, buoyVisibility, (3, 5), (3, 5), False)
        self.trackerBuoyCentered = SHMConsistencyTracker(self.buoyGroup, isBuoyCentered, (3, 5), (3, 5), False)

        self.first_task = self.main()
    async def main(self):
        print('MAIN')
        
        shm.vision_modules.RedBuoy.set(1)

        if not await self.init_search():
            print('CANNOT FIND BUOY')
            return 
        
        while not await self.rough_center_and_approach():
            if not await self.spin(400):
                print("SPIN SEARCH FAILED")
        print("HIGH TOLERANCE CENTER")
        await self.center_buoy()
        # await self.circumnavigate()

        # if not await self.rough_center_and_approach():
        #     print('CANNOT FIND BUOY TO FIRE TORPEDOS')
        #     return

        # CHANGED
        # await self.rough_center_and_approach(stop_area = 0.03,forward_step=0.3)
        # await self.center_buoy()
        await fire_torpedo()
        await fire_torpedo()
        await fire_torpedo()
        await fire_torpedo()
        
        shm.vision_modules.RedBuoy.set(0)

    async def init_search(self):
        print('init search')
        if self.buoy_visible() == True:
            return True

        if await self.spin(80):
            return True
        if await self.spin(-80):
            return True
        if await self.spin(-80):
            return True
        if await self.spin(80):
            return True
    
        return False


    async def spin(self, deg):

        while abs(deg) > 5:
            if self.buoy_visible():
                print("SPIN SEARCH: Buoy visible, exiting spin search")
                x,y = self.buoy_point()
                print(f'spinning {x * 45}')
                await relative_to_initial_heading(x * 45)
                return True
            
            if abs(deg) > 15:
                temp_deg = math.copysign(15, deg)
            else:
                temp_deg = deg
                
            deg = deg-temp_deg
            
            print(f"SPIN SEARCH: Buoy not visible spinning {temp_deg} degrees")
            await relative_to_initial_heading(temp_deg,tolerance=5)

        return False

    # CHANGED stop area from 0.03 to 0.015
    async def rough_center_and_approach(self, stop_area= 0.03,forward_step=0.4,max_iterations = 30):
        print('ROUGH CENTER AND APPROACH')
                
        await zero()
        print('area_ratio',self.area_filled_ratio())
        while self.area_filled_ratio() < stop_area:
            print('LOOP ROUGH CENTER AND APPROACH')
            if not self.buoy_visible():
                return False
            elif not self.buoy_centered():
                max_iterations -= 1
                
                point = self.buoy_point()
                print(f"Buoy Point: (outbound) {max_iterations} Left")
                print(f"    x: {point[0]}")
                print(f"    y: {point[1]}")
                await zero()
                
                if not await self.center_buoy(tolerance=(0.17,0.17)):
                    return False
                
                if max_iterations <= 0:
                    return False
            else:
                point = self.buoy_point()
                # print(f"Buoy Point: (inbound)")
                # print(f"    x: {point[0]}")
                # print(f"    y: {point[1]}")
                # await velocity_x(0.2, tolerance=float('inf'))
                await move_x(forward_step,tolerance=0.04)
                await asyncio.sleep(0.1)

        await zero()        
        return True

    async def center_buoy(self,tolerance = (0.05,0.05)):
        if self.buoy_centered():
            return True
        print('CENTER BUOY')
        target = (0,0)
        return await forward_target(self.buoy_point, target, self.buoy_visible, tolerance=tolerance)
    
    def area_filled_ratio(self):
        buoy_group = shm.red_buoy_results.get()
        buoy_area = buoy_group.area
        frame_area = buoy_group.frame_height * buoy_group.frame_width
        area_filled = buoy_area/frame_area
        return area_filled

    async def circumnavigate(self):
        print('circumnavigate')
        # await velocity_y_for_secs(0.3,4)
        # await velocity_x_for_secs(0.3,8)
        # await velocity_y_for_secs(-0.3,8)
        # await velocity_x_for_secs(-0.3,8)
        # await velocity_y_for_secs(0.3,4)
        await move_y(2,tolerance=0.04)
        await move_x(4,tolerance=0.04)
        await move_y(-4,tolerance=0.04)
        await move_x(-4,tolerance=0.04)
        await move_y(2,tolerance=0.04)

    def buoy_visible(self):
        # return True
        # print('buoy_visible',self.trackerBuoyVisibility.consistent)
        return self.trackerBuoyVisibility.consistent

    def buoy_point(self):
        buoy_group = shm.red_buoy_results.get()
        return (buoy_group.center_x, buoy_group.center_y)
        # return (0,0)

    def buoy_centered(self):
        print('buoy_center',self.trackerBuoyCentered.consistent)
        return self.trackerBuoyCentered.consistent

if __name__ == "__main__":
   goAroundBuoy().run()

