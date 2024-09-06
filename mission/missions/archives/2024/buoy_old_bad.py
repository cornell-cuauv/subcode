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

buoy_visible_consistency = SHMConsistencyTracker(shm.red_buoy_results, lambda group: group.heuristic_score > 0.5, (3, 5), (3, 5))

def buoy_visible():
    return buoy_visible_consistency.consistent

def buoy_point():
    buoy_group = shm.red_buoy_results.get()
    return (buoy_group.center_x, buoy_group.center_y)

def buoy_point_error():
    point = buoy_point()
    return math.hypot(point[0], point[1])

def buoy_centered():
    return buoy_point_error() < 0.2

class goAroundBuoy(AsyncBase):
    def __init__(self):
        self.first_task = self.main()

    async def main(self):
        
        shm.vision_modules.RedBuoy.set(1)

        if not await self.init_search():
            print('CANNOT FIND BUOY')
            return
        
        while not await self.rough_center_and_approach():
            if not await self.spin(400):
                print("SPIN SEARCH FAILED")
            
        self.circumnavigate()
        
        shm.vision_modules.RedBuoy.set(0)

    async def init_search(self):
        if not await sway_search(lambda: buoy_visible(),speed=0.4):
            print('SWAY SEARCH FAILED')
        if not await self.spin():
            print('SWAY SEARCH FAILED')
            print('MISSION FAILED')
            # maybe add another bakup
        

    async def spin(self, deg):
        while abs(deg) > 5:
            if buoy_visible():
                zero()
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
            if not buoy_visible():
                return False
            elif not buoy_centered():
                max_iterations -= 1
                
                point = buoy_point()
                print(f"Buoy Point: (outbound) {max_iterations} Left")
                print(f"    x: {point[0]}")
                print(f"    y: {point[1]}")
                await zero()
                
                if not await self.center_buoy():
                    return False
                
                if max_iterations <= 0:
                    return False
            else:
                point = buoy_point()
                print(f"Buoy Point: (inbound)")
                print(f"    x: {point[0]}")
                print(f"    y: {point[1]}")
                await velocity_x(0.2, tolerance=float('inf'))
                await asyncio.sleep(0.1)

        await zero()        
        return True

    async def center_buoy(self):
        print('CENTER BUOY')
        target = (0, 0)
        return forward_target(buoy_point, target, buoy_visible, tolerance=(0.1,0.1))
    
    def area_filled_ratio(self):
        buoy_group = shm.red_buoy_results.get()
        buoy_area = buoy_group.area
        frame_area = buoy_group.frame_height * buoy_group.frame_width
        area_filled = buoy_area/frame_area
        return area_filled

    async def circumnavigate(self):
        await velocity_y_for_secs(0.3,2)
        # await zero()
        await velocity_x_for_secs(0.3,4)
        # await zero()
        await velocity_y_for_secs(-0.3,4)
        # await zero()
        await velocity_x_for_secs(-0.3,4)
        # await zero()
        await velocity_y_for_secs(0.3,2)

if __name__ == "__main__":
   goAroundBuoy().run()