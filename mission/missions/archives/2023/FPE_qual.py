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
import shm

# FPE objects
qual_gate = QualGate(shm.gate_vision)
red_buoy = Buoy(shm.red_buoy_results)

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

async def missions():
    await sleep_start()
    
    print("\nTask 1: ------------")
    task_1 = FPE_Task(qual_gate, find_harness,
                    qual_gate, position_harness, (0, -0.1),
                    qual_gate, ram, 14)
    task_1.run_headless()

    print("\nTask 2: ------------")
    task_2 = FPE_Task(red_buoy, sway_search,
                    red_buoy, approach, 30000,
                    red_buoy, go_around_square, None) # could be go_around or go_around_square
    task_2.run_headless()

    print("\nTask 3: ------------")
    task_3 = FPE_Task(qual_gate, sway_search,
                    qual_gate, approach, 1000,
                    qual_gate, ram, 8)
    task_3.run_headless()

async def main():
    while True:
        print("waiting for unkill")
        while(shm.switches.hard_kill.get() == 1):
            time.sleep(1)
        print("unhardkill received..starting mission")
        time.sleep(5)

        shm.switches.soft_kill.set(0)

        goto = asyncio.create_task(missions())
        while not goto.done():
            if shm.switches.hard_kill.get() == 1:
                goto.cancel()
                await asyncio.sleep(0)
                cancel_background_tasks()
                

        shm.switches.soft_kill.set(1)
        shm.switches.hard_kill.set(1)


if __name__ == "__main__":
    runner.run(main(), "main")
