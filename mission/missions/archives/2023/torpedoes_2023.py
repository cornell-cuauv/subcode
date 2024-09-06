#!/usr/bin/env python3

##### Remember to turn off autocalibrate before this mission (and back on after)!!!
# This mission was tuned when the DVL scaling factor was 0.3481225539. Then DVL_DESCALE was added.
SEARCH_DEPTH = 3.35 # 1.5 in the simulator, 3.35 at Transdec
SATISFACTORY_RATIO = 1.05 # TODO make this consistent
CAMERA_TO_TORPEDOES = 0.254 # Real distance is 0.225, should prob change this
DVL_DESCALE = 0.348
DVL_DESCALE_TOL = DVL_DESCALE

import asyncio
import time
from math import degrees

from shm import (torpedoes_board_vision as board,
        torpedoes_hole_vision as hole, actuator_desires as actuators,
        hydrophones_pinger_results as hydrophones,
        vision_modules)
from auv_python_helpers.angles import (average_headings_degrees,
        heading_sub_degrees)
from mission.framework.base import AsyncBase
from mission.framework.primitive import enable_hydrophones
from mission.framework.consistency import SHMConsistencyTracker
from mission.framework.movement import (depth, relative_to_initial_depth,
        velocity_x, heading)
from mission.framework.position import move_x, move_y
from mission.framework.search import sway_search, spin_search
from mission.framework.targeting import forward_target, heading_target
from mission.framework.actuation import fire_left_torpedo, fire_right_torpedo


board_visible = SHMConsistencyTracker(group = board,
        test = lambda board: board.visible, count_true = (3, 10))
hole_visible = SHMConsistencyTracker(group = hole,
        test = lambda hole: hole.visible, count_true = (8, 9))

class Torpedoes2023(AsyncBase):
    def __init__(self):
        self.first_task = self.start()
    
    async def start(self):
        # await enable_hydrophones()
        vision_modules.TorpedoesBoard2023.set(True)
        vision_modules.TorpedoesHole2023.set(False)
        return self.rotate_toward_board()
    
    def hydrophones_reading(self):
        return (degrees(hydrophones.heading.get()) + 180) % 360

    async def rotate_toward_board(self):
        readings = [self.hydrophones_reading()]
        while True:
            while self.hydrophones_reading() == readings[-1]:
                await asyncio.sleep(0.1)
            readings.append(self.hydrophones_reading())
            if len(readings) >= 3:
                average = average_headings_degrees(readings[-3:])
                max_diff = max(abs(heading_sub_degrees(reading, average))
                        for reading in readings[-3:])
                if max_diff < 3:
                    await heading(average)
                    return self.search_forward()
    
    async def search_forward(self):
        """TODO: Change direction if the hydrophones heading changes
        significantly."""
        await depth(SEARCH_DEPTH)
        await sway_search(visible=lambda: board_visible.consistent)
        await move_x(1 * DVL_DESCALE, tolerance=0.3 * DVL_DESCALE_TOL)
        return self.target_board_far()
    
    async def target_board_far(self):
        success = await forward_target(
                point=lambda: (board.center_x.get(), board.center_y.get()),
                target=(0, 0), visible=lambda: board_visible.consistent)
        if success:
            return self.approach_board_far()
        return self.search_forward()
    
    async def approach_board_far(self):
        if board.width.get() > 0.3:
            return self.strafe_and_rotate()
        await move_x(1.2 * DVL_DESCALE, tolerance=0.3 * DVL_DESCALE_TOL)
        return self.target_board_far()
    
    async def strafe_and_rotate(self):
        while True:
            ratio = board.left_sidelength.get() / board.right_sidelength.get()
            if 1 / SATISFACTORY_RATIO < ratio < SATISFACTORY_RATIO:
                return self.approach_board_near()
            if ratio < 1:
                await move_y(-1 * DVL_DESCALE, tolerance=0.3 * DVL_DESCALE_TOL)
            elif ratio > 1:
                await move_y(1 * DVL_DESCALE, tolerance=0.3 * DVL_DESCALE_TOL)
            success = await heading_target(
                point=lambda: (board.center_x.get(), board.center_y.get()),
                target=(0, 0), visible=lambda: board_visible.consistent)
            if not success:
                return self.search_forward()
    
    async def approach_board_near(self):
        if board.width.get() > 0.5:
            return self.dead_reckon_hole()
        await move_x(1 * DVL_DESCALE, tolerance=0.3 * DVL_DESCALE_TOL)
        return self.target_board_near()
    
    async def target_board_near(self):
        success = await forward_target(
                point=lambda: (board.center_x.get(), board.center_y.get()),
                target=(0, 0), visible=lambda: board_visible.consistent)
        if success:
            return self.approach_board_near()
        return self.relocate_board_near()
    
    async def relocate_board_near(self):
        await velocity_x(-0.2)
        start_time = time.perf_counter()
        while (time.perf_counter() - start_time < 15
                and not board_visible.consistent):
            await asyncio.sleep(0.1)
        if board_visible.consistent:
            return self.target_board_near()
        success = await spin_search(visible=lambda: board_visible.consistent,
                interval_size=5, clockwise=False, timeout_degrees=20)
        if success:
            return self.target_board_near()
        success = await spin_search(visible=lambda: board_visible.consistent,
                interval_size=5, clockwise=True, timeout_degrees=40)
        if success:
            return self.target_board_near()
        vision_modules.TorpedoesBoard2023.set(False)
        vision_modules.TorpedoesHole2023.set(False)
        return False

    async def dead_reckon_hole(self):
        vision_modules.TorpedoesBoard2023.set(False)
        vision_modules.TorpedoesHole2023.set(True)
        await relative_to_initial_depth(-0.3)
        await move_x(1 * DVL_DESCALE, tolerance=0.1 * DVL_DESCALE_TOL)
        await asyncio.sleep(5)
        return self.target_hole()
    
    async def target_hole(self):
        success = await forward_target(
                point=lambda: (hole.center_x.get(), hole.center_y.get()),
                target=(0, 0), visible=lambda: hole_visible.consistent)
        if success:
            return self.approach_hole()
        return self.relocate_hole()
    
    async def approach_hole(self):
        if hole.radius.get() > 0.2:
            return self.final_dead_reckon()
        await move_x(0.2 * DVL_DESCALE, tolerance=0.1 * DVL_DESCALE_TOL)
        return self.target_hole()
    
    async def relocate_hole(self):
        await move_x(-0.75 * DVL_DESCALE, tolerance=0.3 * DVL_DESCALE_TOL)
        if hole_visible.consistent:
            return self.target_hole()
        vision_modules.TorpedoesBoard2023.set(False)
        vision_modules.TorpedoesHole2023.set(True)
        return self.relocate_board_near()

    async def final_dead_reckon(self):
        await relative_to_initial_depth(-CAMERA_TO_TORPEDOES)
        print('Shooting in 3...')
        await asyncio.sleep(1)
        print('Shooting in 2...')
        await asyncio.sleep(1)
        print('Shooting in 1...')
        await asyncio.sleep(1)
        print('Fire!')
        return self.shoot()
    
    async def shoot(self):
        await fire_left_torpedo()
        await fire_right_torpedo()
        vision_modules.TorpedoesBoard2023.set(True)
        vision_modules.TorpedoesHole2023.set(True)
        return True
    
if __name__ == '__main__':
    Torpedoes2023().run(debug=True)
