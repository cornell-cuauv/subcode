#!/usr/bin/env python3

from mission.framework.position import move_y, go_to_position, move_x
from mission.framework.movement import depth, relative_to_initial_depth, velocity_y_for_secs, velocity_x, velocity_y
from mission.framework.targeting import downward_target, downward_align
from mission.framework.search import square_search
from mission.framework.consistency import SHMConsistencyTracker
from mission.framework.base import AsyncBase
from mission.framework.primitive import enable_downcam
import shm
import asyncio



class JoshBins(AsyncBase):
    def __init__(self):
        self.first_task = self.start()
        self.cover_visible = SHMConsistencyTracker(
            group=shm.bin1_lid_results, test=lambda lid: lid.certainty > 0, count_true=(8, 10))
        self.frame_visible = SHMConsistencyTracker(group=shm.bin1_frame_results, test = lambda lid: lid.certainty > 0, count_true = (8, 10))
        self.center = lambda: (shm.bin1_lid_results.x.get(),
                               shm.bin1_lid_results.y.get())
        self.frame_center = lambda: (shm.bin1_frame_results.x.get(), shm.bin1_frame_results.y.get())
        self.des_depth = 1.75
        #self.north = None
        #self.east = None
        self.POOL_DEPTH = 4.8768
        self.DIVE_MAX = 4.8  # In meters: Transdeck = 4.8768
        self.KNOCK_HEIGHT = 4.94 
        self.precise = False
    
    async def start(self):
        await enable_downcam()
        #Do the weird calibration thing?
        shm.vision_modules.BinsCover.set(True)
        return self.search()

    async def search(self):
        await depth(self.des_depth)
        await square_search(visible=lambda: self.cover_visible.consistent, constant_heading=True)
        return self.target(False)

    async def target(self, rotated):
        if (not self.precise):
            success = await downward_target(point=self.frame_center, target=(0,0), visible = lambda: self.frame_visible, tolerance=(0.05, 0.05), final_zero=False)
        else:
            success = await downward_target(point=self.center, target=(-0.1, 0), visible=lambda: self.cover_visible.consistent, tolerance=(0.03, 0.03), final_zero=False)
        await velocity_x(0)
        await velocity_y(0)
        if success:
            if rotated:
                return self.dive()
            return self.rotate()
        return self.search()

    async def rotate(self):
        angle = shm.bin1_lid_results.angle.get
        success = await downward_align(angle, 0, lambda: self.cover_visible.consistent, final_zero=False)
        if success:
            return self.target(True)
        return self.search()

    async def dive(self):
        if shm.kalman.depth.get() == self.DIVE_MAX:  # Should be 1/2 meter above floor after 4 dives
            #return self.save()
            return self.knock()
        if not self.precise:
            self.des_depth = self.des_depth + 0.75
            if self.des_depth >= 4:
                self.precise = True
        else:
            self.des_depth = self.des_depth + 0.2
        await depth(self.des_depth, tolerance=0.02)
        return self.target(False)

    # async def save(self):
    #     self.north = shm.kalman.north.get()
    #     self.east = shm.kalman.east.get()
    #     return self.knock()

    # async def knock(self):
    #     print("Move Over")
    #     await move_y(-1, tolerance=0.25)
    #     await move_x(0.0366, tolerance=0.03)
    #     # 6in bin + 1in clearance + sub height
    #     print("Move Down")
    #     await depth(KNOCK_HEIGHT, tolerance=0.01)
    #     print("Attempting Knock")
    #     shm.settings_depth.kI.set(0.2)
    #     await velocity_y_for_secs(0.2, 25)
    #     shm.settings_depth.kI.set(0.04)
    #     await depth(POOL_DEPTH - 2.5)
    #     return self.go_back()

    async def knock(self):
        print("Move x")
        await velocity_x(0.1)
        await asyncio.sleep(2)
        await velocity_x(0)
        print("Move d")
        await depth(self.KNOCK_HEIGHT, tolerance=0.1)
        print("Move y")
        await velocity_y(-0.2)
        await asyncio.sleep(4)
        print("Up and away")
        shm.navigation_desires.depth.set(self.KNOCK_HEIGHT - 1)
        await asyncio.sleep(10)
        await velocity_y(0)
        #await asyncio.gather(move_y(-2, tolerance=0.25), depth(self.KNOCK_HEIGHT - 1, tolerance = 0.125))
        return self.drop_cover()
    
    async def drop_cover(self):
        for i in range(3):
            shm.navigation_desires.roll.set(-60)
            await asyncio.sleep(2)
            shm.navigation_desires.roll.set(60)
            await asyncio.sleep(2)
        shm.navigation_desires.roll.set(-60)
        await asyncio.sleep(2)
        shm.navigation_desires.roll.set(0)
        await asyncio.sleep(2)
        return self.go_back()

    async def go_back(self):
        # await go_to_position(self.north, self.east, depth=3.5)
        #await asyncio.gather(move_y(2, tolerance=0.25), depth(self.DIVE_MAX, tolerance = 0.125))
        shm.navigation_desires.sway_speed.set(0.2)
        await asyncio.sleep(14)
        await velocity_y(0)
        shm.vision_modules.BinsCover.set(False)
        return None

if __name__ == '__main__':
    JoshBins().run(debug=True)
