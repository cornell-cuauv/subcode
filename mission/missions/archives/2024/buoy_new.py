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
        print("LOW TOLERANCE CENTER")
        await self.center_buoy()
        await self.circumnavigate()

        # if not await self.rough_center_and_approach():
        #     print('CANNOT FIND BUOY TO FIRE TORPEDOS')
        #     return
        # print("Firing actuators")
        # await fire_torpedo()
        
        shm.vision_modules.RedBuoy.set(0)

    async def init_search(self):
        print('init search')

        # comment out for now:
        print('SWAY')
        if not await velocity_sway_search(lambda: self.buoy_visible(), width=1.3, stride = 0.7,speed=0.2):
            print('SWAY SEARCH FAILED')
        if not await self.spin(80):
            print('SWAY SEARCH FAILED')
            print('MISSION FAILED')
            # maybe add another bakup
        return True
        

    async def spin(self, deg):
        while abs(deg) > 5:
            if self.buoy_visible():
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
            if not self.buoy_visible():
                return False
            elif not self.buoy_centered():
                max_iterations -= 1
                
                point = self.buoy_point()
                print(f"Buoy Point: (outbound) {max_iterations} Left")
                print(f"    x: {point[0]}")
                print(f"    y: {point[1]}")
                await zero()
                
                if not await self.center_buoy(tolerance=(0.2,0.2)):
                    return False
                
                if max_iterations <= 0:
                    return False
            else:
                point = self.buoy_point()
                print(f"Buoy Point: (inbound)")
                print(f"    x: {point[0]}")
                print(f"    y: {point[1]}")
                await velocity_x(0.2, tolerance=float('inf'))
                await asyncio.sleep(0.1)

        await zero()        
        return True

    async def center_buoy(self,tolerance = (0.07,0.07)):
        print('CENTER BUOY')
        target = (0, 0)
        return await forward_target(self.buoy_point, target, self.buoy_visible, tolerance=tolerance)
    
    def area_filled_ratio(self):
        buoy_group = shm.red_buoy_results.get()
        buoy_area = buoy_group.area
        frame_area = buoy_group.frame_height * buoy_group.frame_width
        area_filled = buoy_area/frame_area
        return area_filled

    async def circumnavigate(self):
        print('circumnavigate')
        await velocity_y_for_secs(0.3,3)
        # await zero()
        await velocity_x_for_secs(0.3,6)
        # await zero()
        await velocity_y_for_secs(-0.3,6)
        # await zero()
        await velocity_x_for_secs(-0.3,6)
        # await zero()
        await velocity_y_for_secs(0.3,6)

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
   goAroundBuoy().run('buoy')
