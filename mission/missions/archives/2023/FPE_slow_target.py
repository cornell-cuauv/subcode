#!/usr/bin/env python3
import asyncio

import shm
from mission import runner
from mission.framework.actuation import *
from mission.framework.FPE.execute import (execute_harness, go_around, ram,
                                           ram_forward)
from mission.framework.FPE.find import find_harness, rotate_search, sway_search
from mission.framework.FPE.object import (CompGate, CompGateLeft, Glyph, Path,
                                          Yolo)
from mission.framework.FPE.position import (approach_align_chevron, approach,
                                            center_on_object, position_harness)
from mission.framework.FPE.task import FPE_Task
from mission.framework.movement import (heading, relative_to_initial_depth,
                                        relative_to_initial_heading,
                                        velocity_x_for_secs,
                                        velocity_y_for_secs)
from mission.framework.targeting import downward_target, forward_target

# FPE objects
buoy_glyph = Yolo(shm.yolo_chevron_1)

# Hard coded functions ------------------------------------------


async def get_heading():
    global heading_initial_value
    heading_initial_value = shm.kalman.heading.get()
    await asyncio.sleep(1)


async def rotate():
    destination = heading_initial_value + 180
    if destination > 180:
        destination -= 360
    while (abs(abs(destination) - abs(shm.kalman.heading.get())) > 1.5):
        await heading(destination)
        await asyncio.sleep(2)

async def set_state(num):
    pull = shm.green_buoy_results.get()
    pull.heuristic_score = num
    shm.green_buoy_results.set(pull)
    pass

async def submerge():
    await relative_to_initial_depth(1)
    pass

async def slow_target():
    await asyncio.sleep(2)
    thing = shm.buoy_glyph

    def get_coords():
        return (thing.center_x.get(), thing.center_y.get())

    await forward_target(get_coords, (0, 0), visible=lambda: thing.visible.get()==1, tolerance=(0.05, 0.05))

async def FPE_slow_target():
    align = FPE_Task(buoy_glyph, rotate_search,
                    buoy_glyph, center_on_object, (0, 0),
                    buoy_glyph, ram_forward, 8).run()


if __name__ == "__main__":
    # runner.run(FPE_slow_target(), 'slow_target')

    # align = FPE_Task(buoy_glyph, rotate_search,
    #                 buoy_glyph, approach, 100000,
    #                 buoy_glyph, ram_forward, 4).run()

    runner.run(asyncio.sleep(3), "start")
    # asyncio.run(deploy_arm())
    runner.run(asyncio.sleep(5), "deploy arm")
    asyncio.run(open_claw())


    align = FPE_Task(buoy_glyph, sway_search,
                    buoy_glyph, approach_align_chevron, 150000,
                    buoy_glyph, execute_harness, None).run("FPE_slow_target")

# Create and execute all tasks ----------------------------

# if __name__ == "__main__":
#     runner.run(sleep(), "start")

#     # gate_align_1 = FPE_Task(comp_gate, rotate_search,
#     #                 comp_gate, center_on_object, (0, 0),
#     #                 comp_gate_left, execute_harness, None).run()

#     # gate_align_2 = FPE_Task(comp_gate, position_harness,
#     #                 comp_gate_left, center_on_object, (0, 0),
#     #                 comp_gate_left, ram_forward, 8).run()

#     # path =  FPE_Task(path, sway_search,
#     #                 path, align_path, None,
#     #                 path, execute_harness, None).run()

#     buoy_task = FPE_Task(faucet, sway_search,
#                          faucet, approach, 30000,
#                          faucet, ram_forward, 5).run()
