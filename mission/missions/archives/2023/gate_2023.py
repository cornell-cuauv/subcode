#!/usr/bin/env python3

import asyncio
import time
import shm
from math import dist
from mission.framework.primitive import start_modules, kill_modules, zero, run_with_timeout
from mission.framework.base import AsyncBase
from mission.framework.contexts import PositionalControls
from mission.framework.consistency import SHMConsistencyTracker
from mission.framework.search import velocity_sway_search
from mission.framework.movement import velocity_x, velocity_y, heading, relative_to_initial_heading, relative_to_initial_depth, velocity_x_for_secs, depth
from mission.framework.position import move_x, move_y
from mission.framework.targeting import forward_target, heading_target
import conf.vehicle as vehicle_conf
from mission.framework.dead_reckoning import heading_to_element
gate_left_visible_tracker = SHMConsistencyTracker(group=shm.gate_vision,
                                                  test=lambda gate: gate.leftmost_visible
                                                  and gate.middle_visible, count_true=(13, 15), count_false=(5, 10))
gate_right_visible_tracker = SHMConsistencyTracker(group=shm.gate_vision,
        test=lambda gate: gate.rightmost_visible
        and gate.middle_visible, count_true=(13, 15), count_false=(5, 10))
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
        self.target_status = False

    async def dead_reckon(self):
        print("DEAD RECKON")
        await start_modules(['CompGateVision'])
        print(" > submerging and pointing")
        await depth(1.5)
        await heading(heading_to_element("gate"))
        print(" > moving forward")
        await move_x(4) # dist from dock to gate minus 6
        await asyncio.sleep(10)

        return self.align()

    async def align(self):
        print("ALIGN")
        print('left:', gate_left_visible_tracker.consistent)
        print('right:', gate_right_visible_tracker.consistent)
        if gate_left_visible_tracker.consistent or gate_right_visible_tracker.consistent:
            if bar.consistent:
                return self.target()
            print(" > strafing left... ")
            init_n, init_e = shm.kalman.north.get(), shm.kalman.east.get()

            async def strafe():
                await velocity_y(align_vel)
                while not bar.consistent:
                    await asyncio.sleep(0.1)

            found = await run_with_timeout(strafe(), 15)     
            if found:       
                print(" > bar found")
                await velocity_y(0)
                return self.target()
            else:
                print(' > returning')
                shm.navigation_desires.north.set(init_n)
                shm.navigation_desires.east.set(init_e)
                with PositionalControls():
                    while dist((shm.kalman.north.get(), shm.kalman.east.get()), (init_n, init_e)) > 0.05:
                        await asyncio.sleep(0.1)
                return self.proceed()
        print(' > neither bar found, proceeding')
        return self.proceed()

    async def target(self):
        print("TARGET")
        await zero()
        success = await forward_target(point=point, target=(0, -0.1), visible=lambda: bar.consistent, tolerance=(0.06, 0.06))
        if success:
            self.target_status = True
        else:
            await move_y(-0.15, tolerance=0.05)
        print(" > forward target result is", success)
        return self.proceed()

    async def proceed(self):
        print("PROCEED")
        await move_x(5)
        return self.spin()

    async def spin(self):
        print("SPIN")
        initial_heading = shm.kalman.heading.get()
        for _ in range(8):
            await relative_to_initial_heading(90)
        await heading(initial_heading)
        await kill_modules()
        await depth(3)
        if self.target_status:
            await move_y(3, tolerance=0.1)
        return None

if __name__ == '__main__':
    Gate2023().run()
