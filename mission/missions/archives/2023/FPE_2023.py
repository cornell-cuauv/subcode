#!/usr/bin/env python3
import asyncio
from mission import runner

from mission.framework.FPE.find import sway_search, rotate_search, find_harness
from mission.framework.FPE.position import center_on_object, approach, position_harness, align_path
from mission.framework.FPE.execute import ram, go_around, execute_harness, ram_forward
from mission.framework.FPE.task import FPE_Task
from mission.framework.FPE.object import CompGate, CompGateLeft, Path, Glyph, GlyphIndicator

from mission.framework.movement import velocity_x_for_secs, velocity_y_for_secs, heading, relative_to_initial_heading, relative_to_initial_depth
import shm

mission_control = shm.vision_modules

# FPE objects
comp_gate = CompGate(shm.gate_vision)
comp_gate_left = CompGateLeft(shm.gate_vision)
path = Path(shm.path_results)

wishbone = Glyph(shm.wishbone_glyph)
faucet = Glyph(shm.faucet_glyph)
nozzle = Glyph(shm.nozzle_glyph)
dipper = Glyph(shm.dipper_glyph)

glyph_indicator = GlyphIndicator(shm.wishbone_glyph)

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

async def anthony_buoy():

    results = mission_control.get()
    results.GlyphScout = 1
    results.GlyphInfantry = 0
    mission_control.set(results)
    
    await asyncio.sleep(2)

    scout_task = FPE_Task(glyph_indicator, sway_search,
                          glyph_indicator, position_harness, None,
                          glyph_indicator, execute_harness, None)
    await scout_task.run_headless()

    results = mission_control.get()
    results.GlyphScout = 0
    results.GlyphInfantry = 1
    mission_control.set(results)
    
    buoy_task = FPE_Task(nozzle, sway_search,
                         nozzle, approach, 0.01,
                         nozzle, ram_forward, 5)
    await buoy_task.run_headless()
    await velocity_x_for_secs(-0.3, 15)
    await asyncio.sleep(2)
    buoy_task = FPE_Task(wishbone, sway_search,
                         wishbone, approach, 0.01,
                         wishbone, ram_forward, 5)
    await buoy_task.run_headless()

if __name__ == "__main__":
    runner.run(anthony_buoy(), 'anthony_buoy')

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
