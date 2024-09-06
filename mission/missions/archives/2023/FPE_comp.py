#!/usr/bin/env python3
import asyncio
from mission import runner

from mission.framework.FPE.find import foward_search, sway_search, rotate_search, find_harness
from mission.framework.FPE.position import center_on_object, approach, position_harness
from mission.framework.FPE.execute import ram, go_around, execute_harness, ram_back
from mission.framework.FPE.task import FPE_Task
from mission.framework.FPE.object import QualGate, Buoy, Path

from mission.framework.movement import velocity_y_for_secs, heading, relative_to_initial_heading
import shm

# FPE objects
qual_gate = QualGate(shm.gate_vision)
red_buoy = Buoy(shm.red_buoy_results)
path = Path(shm.path_results)

heading_initial_value = 0

# Hard coded functions ------------------------------------------


async def get_heading():
    global heading_initial_value
    heading_initial_value = shm.kalman.heading.get()
    await asyncio.sleep(1)


async def rotate():
    destination = heading_initial_value
    if destination > 180:
        destination -= 360
    while (abs(abs(destination) - abs(shm.kalman.heading.get())) > 1.5):
        await heading(destination)
        await asyncio.sleep(2)

async def sleep_start():
    await asyncio.sleep(1)


# Create and execute all tasks ----------------------------

if __name__ == "__main__":
    runner.run(sleep_start(), "start")
    runner.run(get_heading(), "start")

    """
    print("\nTask 1 (Gate): ------------")
    task_1 = FPE_Task(qual_gate, rotate_search,
                      qual_gate, center_on_object, (0, -0.1),
                      qual_gate, ram, 0)
    task_1.run()
    """

    print("\nTask 2 (Gate-Path-Buoy): ------------")
    path_task = FPE_Task(path, foward_search,
                    path, center_on_object, (0, 0),
                    path, execute_harness, None)
    path_task.run()

    """
    print("\nTask 3 (Buoy): ------------")
    bouy_task = FPE_Task(red_buoy, sway_search,
                    red_buoy, approach, 5000,
                    red_buoy, ram_back, 3)
    bouy_task.run()

    print("\nTask 4 (Buoy-Path-Bins): ------------")
    path_task = FPE_Task(path, foward_search,
                    path, position_harness, (0, 0),
                    path, execute_harness, None)
    
    path_task.run()
        
    print("\nTask 4.5 (Reorient): ------------")
    async_runner.run(rotate(), "rotate")

    path_task = FPE_Task(path, foward_search,
                    path, center_on_object, (0, 0),
                    path, execute_harness, None)
    """

    path_task.run()

    
