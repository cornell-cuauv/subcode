#!/usr/bin/env python3
from mission.framework.base import AsyncBase
from mission.framework.movement import *
from mission.framework.targeting import *
from vision.modules.base import ModuleBase
import shm
from mission.framework.consistency import SHMConsistencyTracker
import asyncio
from mission.framework.search import *

class GateMission(AsyncBase):
    
    def __init__(self):
        self.gateGroup = shm.gate_vision
        
        gateLeftVisible = lambda gateGroup: (self.gateGroup.leftmost_visible.get() == 1)
        gateMiddleVisible = lambda gateGroup: (self.gateGroup.middle_visible.get() == 1)
        gateRightVisible = lambda gateGroup: (self.gateGroup.rightmost_visible.get() == 1)

        self.leftVisible = SHMConsistencyTracker(self.gateGroup, gateLeftVisible,  (3, 5), (3, 5), False)
        self.middleVisible = SHMConsistencyTracker(self.gateGroup, gateMiddleVisible,  (3, 5), (3, 5), False)
        self.rightVisible = SHMConsistencyTracker(self.gateGroup, gateRightVisible,  (3, 5), (3, 5), False)
       
        self.repeatSearch = 0
        #self.first_task = self.goForward()
        self.first_task = self.searchGate()

    async def goForward(self):
        print("moving forward")
        await move_x(4)
        print("turn on gate vision")
        #shm.vision_modules.GateVision.set(1)
        return await self.searchGate()

    async def searchGate(self):
        await asyncio.sleep(1)
        stopTime = 1
        angle = 5
        while self.repeatSearch<20:
            if self.fullVisible():
                print("left middle right")
                return await self.centerGate()
            elif self.partVisible():
                print("middle right")
                return await self.centerGate()
            elif self.leftVisible.consistent and self.middleVisible.consistent:
                print("left middle")
                curr_vision = lambda: self.leftVisible.consistent and self.middleVisible.consistent
                improved_vision = lambda: self.middleVisible.consistent and self.rightVisible.consistent
                move_left, move_right, turn_left, turn_right = False, True, False, True
            elif self.leftVisible.consistent and self.rightVisible.consistent:
                print("left right")
                curr_vision = lambda: self.leftVisible.consistent and self.rightVisible.consistent
                improved_vision = lambda: (self.middleVisible.consistent and self.rightVisible.consistent) or (self.leftVisible.consistent and self.middleVisible.consistent)
                move_left, move_right, turn_left, turn_right = True, True, True, True
            elif self.leftVisible.consistent:
                print("left")
                curr_vision = lambda: self.leftVisible.consistent
                improved_vision = lambda: self.middleVisible.consistent or self.rightVisible.consistent
                move_left, move_right, turn_left, turn_right = True, True, True, True
            else:
                print("none")
                curr_vision = lambda: True
                improved_vision = lambda: self.leftVisible.consistent or self.middleVisible.consistent or self.rightVisible.consistent
                move_left, move_right, turn_left, turn_right = True, True, True, True
            await self.moveRotate(curr_vision, improved_vision, move_left, move_right, turn_left, turn_right)
            self.repeatSearch += 1

    async def moveRotate(self, curr_vision : Callable[[],bool], improved_vision : Callable[[],bool], move_left, move_right, turn_left, turn_right):
        position = 0.2
        angle = 5
        stopTime = 1
        init_n, init_e = shm.kalman.north.get(), shm.kalman.east.get()
        init_heading = shm.kalman.heading.get()
        if turn_left:
            for i in range(10):
                print("turning left")
                await relative_to_initial_heading(-angle)
                await zero()
                await asyncio.sleep(stopTime)
                if improved_vision():
                    return
                if not curr_vision():
                    break
            print("returning")
            await heading(init_heading)
        if turn_right:
            for i in range(10):
                print("turning right")
                await relative_to_initial_heading(angle)
                await zero()
                await asyncio.sleep(stopTime)
                if improved_vision():
                    return
                if not curr_vision():
                    break
            print("returning")
        distance = 0
        if move_left:
            for i in range(10):
                distance += position
                print("moving left")
                await move_y(-position)
                await zero()
                await asyncio.sleep(stopTime)
                if improved_vision():
                    return
                if not curr_vision():
                    break
            print("returning")
            await move_y(distance)
        distance = 0
        if move_right:
            for i in range(10):
                distance += position
                print("moving right")
                await move_y(position)
                await zero()
                await asyncio.sleep(stopTime)
                if improved_vision():
                    return
                if not curr_vision():
                    break
            print("returning")
            await move_y(-distance)
        shm.navigation_desires.north.set(init_n)
        shm.navigation_desires.east.set(init_e)
        await heading(init_heading)

    async def centerGate(self):
        gate = shm.gate_vision.get()
        centered = False
        target = (0,-0.15)
        if self.middleVisible.consistent and self.rightVisible.consistent:
            print("centering on middle right")
            centered = await forward_target(self.gateCenter, target, self.partVisible, tolerance=(0.06, 0.06))
        elif self.leftVisible.consistent and self.rightVisible.consistent:
            print("centering on left right")
            centered = await forward_target(lambda: (gate.leftmost_x*0.35+gate.rightmost_x*0.65, (gate.leftmost_y+gate.rightmost_y)/2), target, lambda: self.leftVisible.consistent and self.rightVisible.consistent, tolerance=(0.06, 0.06))
        elif self.leftVisible.consistent and self.middleVisible.consistent:
            print("centering on left middle")
            centered = await forward_target(lambda: ((gate.leftmost_x+gate.middle_x)/2, (gate.leftmost_y+gate.rightmost_y)/2), target, lambda: self.leftVisible.consistent and self.middleVisible.consistent, tolerance=(0.06, 0.06))
        elif self.leftVisible.consistent:
            print("centering on left")
            target = (-0.15,0)
            centered = await forward_target(lambda: (gate.leftmost_x, gate.leftmost_y), target, lambda: self.leftVisible.consistent, tolerance=(0.06, 0.06))
        if centered == False:
            print("lost gate")
            self.repeatSearch += 1
            return await self.searchGate()
        print("centered")
        return await self.goThroughGate()
    
    async def goThroughGate(self):
        print("turn off gate vision")
        #shm.vision_modules.GateVision.set(0)
        print("moving through gate")
        await move_x(10)
        return

    def gateCenter(self):
        gate = shm.gate_vision.get()
        center = ((gate.middle_x+gate.rightmost_x)/2, (gate.middle_y+gate.rightmost_y)/2)
        return center

    def fullVisible(self):
        visible = self.leftVisible.consistent and self.middleVisible.consistent and self.rightVisible.consistent
        return visible

    def partVisible(self):
        visible = self.middleVisible.consistent and self.rightVisible.consistent
        return visible


if __name__ == "__main__":
   GateMission().run()
