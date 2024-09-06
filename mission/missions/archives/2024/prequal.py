#!/usr/bin/env python3
from mission.framework.base import AsyncBase
from mission.framework.position import move_x
from mission.framework.movement import *
# from mission.framework.position import *
from mission.framework.targeting import *
from vision.modules.base import ModuleBase
import shm
from mission.framework.consistency import SHMConsistencyTracker
import asyncio
from mission.framework.search import *

class goAroundBuoy(AsyncBase):

    
    def __init__(self):

        self.buoyGroup = shm.red_buoy_results
        self.gateGroup = shm.gate_vision
        
        buoyVisibility = lambda buoyGroup: (self.buoyGroup.heuristic_score.get() > 0.5)
        isBuoyCentered = lambda buoyGroup: (abs(self.buoyGroup.center_x.get()) < 0.05 and abs(self.buoyGroup.center_y.get()) < 0.05)
        gateLeftVisible = lambda gateGroup: (self.gateGroup.leftmost_visible.get() ==1)
        gateRightVisible = lambda gateGroup: (self.gateGroup.rightmost_visible.get() ==1)

        self.trackerBuoyVisibility = SHMConsistencyTracker(self.buoyGroup, buoyVisibility, (4, 5), (4, 5), False)
        self.trackerBuoyCentered = SHMConsistencyTracker(self.buoyGroup, isBuoyCentered, (3, 5), (3, 5), False)
        self.trackerLeftGateVisibility = SHMConsistencyTracker(self.gateGroup, gateLeftVisible,  (3, 5), (3, 5), False)
        self.trackerRightGateVisibility = SHMConsistencyTracker(self.gateGroup, gateRightVisible,  (3, 5), (3, 5), False)
        
        print('heuristic score', self.buoyGroup.heuristic_score)
        self.first_task = self.goForward(7.5)
        # self.first_task = self.swaySearchBuoy()

    async def goForward(self,meters):
        await move_x(meters,tolerance = 0.08)
        return self.swaySearchBuoy()

    async def swaySearchBuoy(self):
        shm.vision_modules.FindGate.set(0)
        shm.vision_modules.FindRedBuoy.set(1)
        await asyncio.sleep(2)
        print(self.buoyVisible())
        if self.buoyVisible():
            print('buoy visible')
            return self.centerBuoy()
        else:
            searchResult = await sway_search(lambda: self.buoyVisible(), width=1, stride = 1)
            if searchResult == False:
                print('cannot find buoy')
                return
            return self.centerBuoy()
        
    async def searchGate(self):
        shm.vision_modules.FindGate.set(1)
        shm.vision_modules.FindRedBuoy.set(0)
        await move_x(4, tolerance = 0.08)
        visible = False
        if self.trackerRightGateVisibility.consistent:
            visible = True
        
     
        elif await self.sideSearchGate(-1) == True:
            visible = True

        
        elif await self.sideSearchGate(1) == True:
            visible = True
       
        if visible == True:
            return self.centerGate()
        
        else:
            print("cannot find gate") 


    async def sideSearchGate(self, dir):       
        moveYCorountine1 = asyncio.create_task(move_y(2*dir))
        while not moveYCorountine1.done():
            await asyncio.sleep(0.01)
            if self.trackerRightGateVisibility.consistent:
                moveYCorountine1.cancel()
                return True
            
        await moveYCorountine1
        await move_y(-2*dir)
        return False
    
    def gateVisible(self):
        return self.trackerRightGateVisibility.consistent

    
    async def centerGate(self):
        target = (0,0)
        centered = await forward_target(self.gatePoint, target, self.gateVisible, tolerance=(0.06, 0.06))
        if centered == False:
            print("lost gate")
            return
        print("can see gate")
        return self.throughGate()
    
    async def throughGate(self):
        await move_x(4)
        shm.switches.soft_kill.set(1)
        return True 
       

    def buoyPoint(self):
        buoyGroup = shm.red_buoy_results.get()
        point = (buoyGroup.center_x,buoyGroup.center_y)
        return point
    
    def gatePoint(self):
        gate = shm.gate_vision.get()
        point = (gate.middle_x, gate.middle_y)
        return point
        
    
    def buoyVisible(self):
        print('from visible function', self.trackerBuoyVisibility.consistent)
        return self.trackerBuoyVisibility.consistent
    

    async def centerBuoy(self):
        target = (0,0)
        centered = await forward_target(self.buoyPoint,target,self.buoyVisible, tolerance=(0.05, 0.05))
    
        if centered == False:
            print("lost buoy")
            return
        print("centerd?",centered)
        return self.approachAndRam()
    
    def isBuoyCentered(self):
        return self.trackerCentered
    
    def areaFilledRatio(self):
        buoyGroup = shm.red_buoy_results.get()
        buoy_area = buoyGroup.area
        frame_area = buoyGroup.frame_height * buoyGroup.frame_width
        area_filled = buoy_area/frame_area
        return area_filled


    async def approachAndRam(self):
        print('approaching buoy')

        # while area_filled < .0055 and self.visible() == True:
        while self.areaFilledRatio() < .0250:
            await move_x(0.5,tolerance = 0.08)

        # if area_filled > .010 and self.visible():
        if self.areaFilledRatio() > .0250 and self.buoyVisible():
            print("turning!")
            return self.circleBuoy()


    async def circleBuoy(self):
        await relative_to_initial_heading(-90)
        await move_x(1)

        for i in range(3):
            print(i)
            await relative_to_initial_heading(90)
            await move_x(2)

        await relative_to_initial_heading(90)
        await move_x(1)
        await relative_to_initial_heading(-90)

        return self.searchGate()

    

if __name__ == "__main__":
   goAroundBuoy().run()
