#!/usr/bin/env python3

import asyncio

import shm
from mission.framework.position import move_x, move_y
from mission.framework.base import AsyncBase
from mission.framework.consistency import SHMConsistencyTracker
from mission.framework.movement import (depth, heading,
                                        relative_to_current_depth, relative_to_initial_depth,
                                        relative_to_current_setter, velocity_x, velocity_x_for_secs, velocity_y_for_secs)
from mission.framework.primitive import zero
from mission.framework.search import (velocity_square_search,
                                      velocity_sway_search)
from mission.framework.targeting import downward_align, downward_target
from mission.framework.primitive import enable_downcam

class ChevronsOctagon2023(AsyncBase):
    def __init__(self):
        self.first_task = self.search()
        self.shm_chevrons = [shm.yolo_chevron_1, shm.yolo_chevron_2,shm.yolo_chevron_3, shm.yolo_chevron_4]
        self.num_of_chevrons = len(self.shm_chevrons)

        self.visible_list = [
            SHMConsistencyTracker(group=chev, test=lambda chevron: chevron.visible, count_true=(8, 10), count_false=(9, 10), default=False) for chev in self.shm_chevrons
        ]

        self.visible = self.visible_list[0]
        self.shm_object = self.shm_chevrons[0]

        # VARIABLES
        # self.desired_target = (-0.2, 0)
    
    def shm_object_coordinates(self):
        return (self.shm_object.center_x.get(), self.shm_object.center_y.get())

    async def surface(self, next_method):
        shm.navigation_desires.roll.set(20)
        current_depth = shm.kalman.depth.get()
        await depth(11)
        print("SOFTKILL")
        shm.switches.soft_kill.set(1)
        await asyncio.sleep(10)
        print("UNSOFTKILL")        
        shm.switches.soft_kill.set(0)
        await depth(12.5)
       
        shm.navigation_desires.roll.set(0)

        return next_method

    # async def initial_task(self):
    #     await depth(1)
    #     await velocity_sway_search(lambda: self.visible.consistent)
    #     await downward_target(point=self.shm_object_coordinates, target=(0, 0), visible=self.shm_object.visible, tolerance=(0.1, 0.1))
    #     await zero()
    #     print("SOFTKILL")
    #     shm.switches.soft_kill.set(1)
    #     await asyncio.sleep(20)
    #     print("UNSOFTKILL")
    #     shm.switches.soft_kill.set(0)
    #     await depth(12)
    #     return self.search()
        
    async def search(self):
        shm.vision_modules.OctagonChevronsVision.set(1)
        await depth(4, tolerance=0.5)
        print(self.visible.consistent, self.shm_chevrons[0].visible.get())
        await asyncio.sleep(2)
        await velocity_sway_search(lambda: self.visible.consistent)
        return self.target_1(desired_area=40000, desired_target=(0.15, 0.15))

    async def target_1(self, desired_area, desired_target=(0.1, 0.1), tolerance=(0.1, 0.1)):
        print(f"Targeting with desired target {desired_target} and tolerance {tolerance}")
        success = await downward_target(point=self.shm_object_coordinates, target=desired_target, visible=self.shm_object.visible, tolerance=tolerance)
        if success:
            print(self.shm_object.area.get() > desired_area)
            if self.shm_object.area.get() > desired_area:
                return self.align()
            else:
                return self.get_closer(desired_area=desired_area, desired_target=desired_target)
        return self.search()

    async def target_2(self, desired_target=(0.2, 0), tolerance=(0.03, 0.03)):
        print(f"Targeting with desired target {desired_target} and tolerance {tolerance}")
        success = await downward_target(point=self.shm_object_coordinates, target=desired_target, visible=self.shm_object.visible, tolerance=tolerance)
        if success:
            return self.dead_reck()
        return self.search()

    async def get_closer(self, desired_area, adjustment_tolerance = 0.08, desired_target=(0, 0)):
        while self.shm_object.area.get() < desired_area:
            coords = self.shm_object_coordinates()
            if not self.visible.consistent:
                return self.search()
            elif (abs(desired_target[0] - coords[0]) > adjustment_tolerance or abs(desired_target[1] - coords[1]) > adjustment_tolerance):
                print("Adjustment tolerance reached")
                return self.target_1(desired_area=desired_area, desired_target=desired_target)
            else:
                print("Moving closer")
                await relative_to_initial_depth(0.07)

        return self.target_1(desired_area=desired_area)

    # Do Align when area is half of specificed in target_2
    async def align(self):
        print("ANGLE ALIGN", self.shm_object.angle.get())
        success = True
        # success = await downward_align(angle=self.shm_object.angle, target=0,
        #         visible=lambda: self.visible.consistent, tolerance=10, hold_time=0)        
        if success:
            return self.target_2(desired_target=(0.15, 0.15))
        else:
            return self.search()

    async def dead_reck(self):
        await zero()

        print("moving foward")
        await move_x(0.25, tolerance=0.08)

        print("moving downward")
        await relative_to_initial_depth(0.2)
        await relative_to_initial_depth(0.1)
        await relative_to_initial_depth(0.1)
        await relative_to_initial_depth(0.05)
        await relative_to_initial_depth(0.05)

        await asyncio.sleep(2)

        print("moving upwards just a bit")
        await relative_to_initial_depth(-0.03)

        await asyncio.sleep(2)

        shm.settings_depth.kI.set(0.2)

        print("moving lefward")
        await velocity_y_for_secs(-0.1, 3.2)

        shm.settings_depth.kI.set(0.04)

        print("moving upward")
        await relative_to_initial_depth(-1)

        return self.surface(self.roll())

    async def roll(self):
        for i in range(2):
            shm.navigation_desires.roll.set(60)
            await asyncio.sleep(2)
            shm.navigation_desires.roll.set(-60)
            await asyncio.sleep(2)

        shm.navigation_desires.roll.set(0)

        return self.search()
        

if __name__ == '__main__':
    ChevronsOctagon2023().run(debug=True)