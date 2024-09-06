#!/usr/bin/env python3
import asyncio
import time
from mission import runner

from mission.framework.FPE.find import sway_search, rotate_search, find_harness
from mission.framework.FPE.position import center_on_object, approach, position_harness
from mission.framework.FPE.execute import go_around_square, ram, go_around, execute_harness
from mission.framework.FPE.task import FPE_Task
from mission.framework.FPE.object import QualGate, Buoy

from mission.framework.movement import velocity_y_for_secs, heading, relative_to_initial_heading
from mission.framework.position import move_x, move_y, go_to_position
from mission.framework.movement import relative_to_initial_heading, velocity_x_for_secs, velocity_y_for_secs, velocity_y, depth
from mission.framework.primitive import zero
import shm

# FPE objects

heading_initial_value = 0

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


async def sleep_start():
    await asyncio.sleep(1)

async def cancel_background_tasks():
    for t in asyncio.all_tasks():
        t.cancel()
        await asyncio.sleep(0)

# Create and execute all tasks ----------------------------

async def go_around_square():
    """go_around_square: goes around [object] in a square"""

    await relative_to_initial_heading(45, tolerance=5)
    for i in range(3):
        print("move")
        await move_x(2.5, tolerance=0.5)
        print("turn")
        await relative_to_initial_heading(-90, tolerance=5)
    await move_x(2.5, tolerance=0.5)
    await relative_to_initial_heading(45, tolerance=5)
    await zero()

async def missions():    
    print("\nTask 1: ------------")
    
async def missions():    
    print("\nTask 1: ------------")
    await get_heading()

    print("\nTask 2: ------------")
    await depth(3)

    print("\nTask 3: ------------")
    await move_x(5)

    await depth(1.5)

    await move_x(8)

    print("\nTask 4: ------------")
    await go_around_square()

    await depth(3)

    await move_x(15)
    

async def main():
    while True:
        print("waiting for unkill")
        while(shm.switches.hard_kill.get() == 1):
            time.sleep(1)
            
            
        print("unhardkill received..starting mission")
        shm.switches.soft_kill.set(0)


        await missions()
        
        shm.switches.soft_kill.set(1)
        shm.switches.hard_kill.set(1)


if __name__ == "__main__":
    runner.run(main(), "main")
