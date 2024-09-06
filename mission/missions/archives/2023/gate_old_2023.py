#!/usr/bin/env python3

import asyncio
import time
import shm
from mission.framework.primitive import start_modules, kill_modules, zero
from mission.framework.base import AsyncBase
from mission.framework.consistency import SHMConsistencyTracker
from mission.framework.search import velocity_sway_search
from mission.framework.movement import velocity_x, velocity_y, heading, relative_to_initial_heading, relative_to_initial_depth, velocity_x_for_secs, depth
from mission.framework.position import move_x
from mission.framework.targeting import forward_target, heading_target
import conf.vehicle as vehicle_conf
from mission.framework.dead_reckoning import heading_to_element
gate_left_visible_tracker = SHMConsistencyTracker(group=shm.gate_vision,
                                                  test=lambda gate: gate.leftmost_visible
                                                  and gate.middle_visible, count_true=(18, 20), count_false=(5, 10))
gate_right_visible_tracker = SHMConsistencyTracker(group=shm.gate_vision,
        test=lambda gate: gate.rightmost_visible
        and gate.middle_visible, count_true=(18, 20), count_false=(5, 10))
gate_left_point = lambda: ((shm.gate_vision.leftmost_x.get() + shm.gate_vision.middle_x.get()) / 2,
                            (shm.gate_vision.leftmost_y.get() + shm.gate_vision.middle_y.get()) / 2)
gate_right_point = lambda: ((shm.gate_vision.rightmost_x.get() + shm.gate_vision.middle_x.get()) / 2,
                            (shm.gate_vision.rightmost_y.get() + shm.gate_vision.middle_y.get()) / 2 + (shm.gate_vision.middle_len.get() + shm.gate_vision.rightmost_len.get()) / 4)

direction = "left"

shm_bin = shm.gate_vision

if direction == "left":
    bar = gate_left_visible_tracker
    point = gate_left_point

    left_len = shm_bin.leftmost_len
    left_x, left_y = shm_bin.leftmost_x, shm_bin.leftmost_y

    right_len = shm_bin.middle_len
    right_x, right_y = shm_bin.middle_x, shm_bin.middle_y

    align_vel = -0.15

else:
    bar = gate_right_visible_tracker
    point = gate_right_point
    
    left_len = shm_bin.middle_len
    left_x, left_y = shm_bin.middle_x, shm_bin.middle_y

    right_len = shm_bin.rightmost_len
    right_x, right_y = shm_bin.rightmost_x, shm_bin.rightmost_y

    align_vel = 0.15

class Gate2023(AsyncBase):
    def __init__(self):
        self.first_task = self.dead_reckon()

    async def dead_reckon(self):
        print("GOING FORWARD")
        await start_modules(['CompGateVision'])
        await depth(1.5)
        await heading(heading_to_element("gate"))
        await move_x(3)

        return self.search()

    async def search(self):
        print("SEARCH")
        await asyncio.sleep(4)
        def visible(): return (gate_left_visible_tracker.consistent
                               or gate_right_visible_tracker.consistent)
        await velocity_sway_search(visible)
        return self.align()

    async def align(self):
        print("ALIGN")
        await velocity_x_for_secs(0.2, 2)
    
        if bar.consistent:
            return self.target()
        
        print(" > strafing left... ")
        await velocity_y(align_vel)
        while not bar.consistent:
            await asyncio.sleep(0.1)
        print("> bar found")
        await velocity_y(0)
        return self.target()

    async def target(self):
        print("TARGET")
        await zero()
        success = await forward_target(point=point,
                                       target=(0, -0.1),
                                       visible=lambda: bar.consistent, tolerance=(0.06, 0.06))
        if success:
            return self.approach()
        return self.relocate()

    async def relocate(self):
        print("RELOCATING")
        await velocity_x(-0.2)
        start_time = time.time()
        while time.time() - start_time < 5000:
            await asyncio.sleep(0.1)
            if (gate_left_visible_tracker.consistent
                    or gate_right_visible_tracker.consistent):
                await velocity_x(0)
                return self.align()
        await velocity_x(0)
        return self.search()

    async def approach(self):
        print("APPROACHING")
        def distance():
            return abs(left_x.get() - right_x.get())
        await velocity_x_for_secs(0.2, 1)
        await velocity_x(0.2)
        print(" > approaching", str(distance()))
        while distance() < 0.4 or not bar.consistent:
                print(" > approaching", str(distance()))
                await asyncio.sleep(1)
        return self.proceed(distance())

    async def proceed(self, val):
        print("PROCEEDING")
        # 0.2 = 30
        # 0.5 = 15
        time = -50 * (val - 0.5) + 15
        if time < 5:
            time = 5
        print(" > Moving forward for" + str(time) + " seconds")
        await velocity_x_for_secs(0.2, time)
        return self.spin()

    async def spin(self):
        print("SPIN")
        initial_heading = shm.kalman.heading.get()
        for _ in range(8):
            await relative_to_initial_heading(90)
        await heading(initial_heading)
        await kill_modules()
        await depth(3)
        return None

if __name__ == '__main__':
    Gate2023().run()