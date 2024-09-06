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
        self.first_task = self.goForward()

    '''async def chain(self):
        await self.goForward()
        shm.vision_modules.GateVision.set(1)
        await self.searchGate()
        await self.centerGate()
        await self.goThroughGate()
        return'''

    async def goForward(self):
        print("moving forward")
        await velocity_x_for_secs(0.1, 3)
        print("turn on gate vision")
        shm.vision_modules.GateVision.set(1)
        return await self.searchGate()

    async def searchGate(self):
        if self.repeatSearch>10:
            return await self.goThroughGate()
        stopTime = 1
        angle = 5
        if self.fullVisible():
            print("left middle right")
            return await self.centerGate()
        elif self.partVisible():
            print("middle right")
            initHeading = shm.kalman.heading.get()
            for i in range(10):
                print("turning left")
                await relative_to_initial_heading(-angle)
                await zero()
                await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                if not self.partVisible():
                    break
            print("returning to initial heading")
            await heading(initHeading)
            count = 0
            for i in range(10):
                print("moving left")
                count += 1
                await velocity_y_for_secs(-0.1, 2)
                await zero()
                await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                if not self.partVisible():
                    break
            print("returning to initial position")
            for i in range(count):
                await velocity_y_for_secs(0.1, 2)
                await zero()
                if self.partVisible():
                    return await self.centerGate()
            count = 0
            for i in range(20):
                if i%2==0:
                    print("moving left")
                    count += 1
                    await velocity_y_for_secs(-0.1, 2)
                    await zero()
                    await asyncio.sleep(stopTime)
                else:
                    print("turning right")
                    await relative_to_initial_heading(angle)
                    await zero()
                    await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                if not self.partVisible():
                    break
            print("returning to initial heading and position")
            await heading(initHeading)
            for i in range(count):
                await velocity_y_for_secs(0.1, 2)
                await zero()
        if self.leftVisible.consistent and self.rightVisible.consistent:
            print("left right")
            count = 0
            for i in range(5):
                print("moving forward")
                count += 1
                await velocity_x_for_secs(0.1, 2)
                await zero()
                await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                if not (self.leftVisible.consistent and self.rightVisible.consistent):
                    break
            print("returning to initial position")
            for i in range(count):
                await velocity_x_for_secs(-0.1, 2)
                await zero()
            initHeading = shm.kalman.heading.get()
            count = 0
            for i in range(20):
                if i%2==0:
                    print("moving right")
                    count += 1
                    await velocity_y_for_secs(0.1, 2)
                    await zero()
                    await asyncio.sleep(stopTime)
                else:
                    print("turning left")
                    await relative_to_initial_heading(-angle)
                    await zero()
                    await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                if not (self.leftVisible.consistent and self.rightVisible.consistent):
                    break
            print("returning to initial heading and position")
            await heading(initHeading)
            for i in range(count):
                await velocity_y_for_secs(-0.1, 2)
                await zero()
            count = 0
            for i in range(20):
                if i%2==0:
                    print("moving left")
                    count += 1
                    await velocity_y_for_secs(-0.1, 2)
                    await zero()
                    await asyncio.sleep(stopTime)
                else:
                    print("turning right")
                    await relative_to_initial_heading(angle)
                    await zero()
                    await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                if not (self.leftVisible.consistent and self.rightVisible.consistent):
                    break
            print("returning to initial heading and position")
            await heading(initHeading)
            for i in range(count):
                await velocity_y_for_secs(0.1, 2)
                await zero()
        if self.leftVisible.consistent and self.middleVisible.consistent:
            print("left middle")
            initHeading = shm.kalman.heading.get()
            for i in range(10):
                print("turning right")
                await relative_to_initial_heading(angle)
                await zero()
                await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                elif self.partVisible():
                    print("middle right")
                    self.repeatSearch += 1
                    return await self.searchGate()
                if not (self.leftVisible.consistent and self.middleVisible.consistent):
                    break
            print("returning to initial heading")
            await heading(initHeading)
            count = 0
            for i in range(10):
                print("moving right")
                count += 1
                await velocity_y_for_secs(0.1, 2)
                await zero()
                await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                elif self.partVisible():
                    print("middle right")
                    self.repeatSearch += 1
                    return await self.searchGate()
                if not (self.leftVisible.consistent and self.middleVisible.consistent):
                    break
            print("returning to initial position")
            for i in range(count):
                await velocity_y_for_secs(-0.1, 2)
                await zero()
            count = 0
            for i in range(20):
                if i%2==0:
                    print("moving right")
                    count += 1
                    await velocity_y_for_secs(0.1, 2)
                    await zero()
                    await asyncio.sleep(stopTime)
                else:
                    print("turning left")
                    await relative_to_initial_heading(-angle)
                    await zero()
                    await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                if not (self.leftVisible.consistent and self.rightVisible.consistent):
                    break
            print("returning to initial heading and position")
            await heading(initHeading)
            for i in range(count):
                await velocity_y_for_secs(-0.1, 2)
                await zero()
        if self.leftVisible.consistent:
            print("left")
            initHeading = shm.kalman.heading.get()
            for i in range(10):
                print("turning right")
                await relative_to_initial_heading(angle)
                await zero()
                await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                elif self.partVisible():
                    print("middle right")
                    self.repeatSearch += 1
                    return await self.searchGate()
                elif self.middleVisible.consistent:
                    print("left middle")
                    self.repeatSearch += 1
                    return await self.searchGate()
                elif self.rightVisible.consistent:
                    print("left right")
                    self.repeatSearch += 1
                    return await self.searchGate()
                if not self.leftVisible.consistent:
                    break
            print("returning to initial heading")
            await heading(initHeading)
            for i in range(10):
                print("turning left")
                await relative_to_initial_heading(-angle)
                await zero()
                await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                elif self.partVisible():
                    print("middle right")
                    self.repeatSearch += 1
                    return await self.searchGate()
                elif self.middleVisible.consistent:
                    print("left middle")
                    self.repeatSearch += 1
                    return await self.searchGate()
                elif self.rightVisible.consistent:
                    print("left right")
                    self.repeatSearch += 1
                    return await self.searchGate()
                if not self.leftVisible.consistent:
                    break
            print("returning to initial heading")
            await heading(initHeading)
            count = 0
            for i in range(10):
                print("moving right")
                count += 1
                await velocity_y_for_secs(0.1, 2)
                await zero()
                await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                elif self.partVisible():
                    print("middle right")
                    self.repeatSearch += 1
                    return await self.searchGate()
                elif self.middleVisible.consistent:
                    print("left middle")
                    self.repeatSearch += 1
                    return await self.searchGate()
                elif self.rightVisible.consistent:
                    print("left right")
                    self.repeatSearch += 1
                    return await self.searchGate()
                if not self.leftVisible.consistent:
                    break
            print("returning to initial position")
            for i in range(count):
                await velocity_y_for_secs(-0.1, 2)
                await zero()
            count = 0
            for i in range(10):
                print("moving left")
                count += 1
                await velocity_y_for_secs(-0.1, 2)
                await zero()
                await asyncio.sleep(stopTime)
                if self.fullVisible():
                    print("left middle right")
                    return await self.centerGate()
                elif self.partVisible():
                    print("middle right")
                    self.repeatSearch += 1
                    return await self.searchGate()
                elif self.middleVisible.consistent:
                    print("left middle")
                    self.repeatSearch += 1
                    return await self.searchGate()
                elif self.rightVisible.consistent:
                    print("left right")
                    self.repeatSearch += 1
                    return await self.searchGate()
                if not self.leftVisible.consistent:
                    break
            print("returning to initial position")
            for i in range(count):
                await velocity_y_for_secs(0.1, 2)
                await zero()
        else:
            print("no gate detected")
            initHeading = shm.kalman.heading.get()
            for i in range(10):
                print("turning right")
                await relative_to_initial_heading(angle)
                await zero()
                await asyncio.sleep(stopTime)
                if self.leftVisible.consistent:
                    print("left")
                    self.repeatSearch += 1
                    return await self.searchGate()
            print("returning to initial heading")
            await heading(initHeading)
            for i in range(10):
                print("turning left")
                await relative_to_initial_heading(-angle)
                await zero()
                await asyncio.sleep(stopTime)
                if self.leftVisible.consistent:
                    print("left")
                    self.repeatSearch += 1
                    return await self.searchGate()
            print("returning to initial heading")
            await heading(initHeading)
            count = 0
            for i in range(10):
                print("moving right")
                count += 1
                await velocity_y_for_secs(0.1, 2)
                await zero()
                await asyncio.sleep(stopTime)
                if self.leftVisible.consistent:
                    print("left")
                    self.repeatSearch += 1
                    return await self.searchGate()
            print("returning to initial position")
            for i in range(count):
                await velocity_y_for_secs(-0.1, 2)
                await zero()
            count = 0
            for i in range(10):
                print("moving left")
                count += 1
                await velocity_y_for_secs(-0.1, 2)
                await zero()
                await asyncio.sleep(stopTime)
                if self.leftVisible.consistent:
                    print("left")
                    self.repeatSearch += 1
                    return await self.searchGate()
            print("returning to initial position")
            for i in range(count):
                await velocity_y_for_secs(0.1, 2)
                await zero()
        self.repeatSearch += 1
        return await self.searchGate()

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
        shm.vision_modules.GateVision.set(0)
        print("moving through gate")
        await velocity_x_for_secs(0.2, 20)
        return


if __name__ == "__main__":
   GateMission().run()
