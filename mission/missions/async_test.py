#!/usr/bin/env python3

import asyncio

import shm
from mission.async_framework.search import *
from mission.async_framework.movement import *
from mission.async_framework.position import *
from mission.async_runner import run, run_task
from mission.framework.movement import *
from mission.framework.position import *

async def main():
    print("starting")
    await move_x(2)
    print("middle A")
    await relative_to_initial_heading(90)
    print("middle B")
    await move_x(2)
    print("ending")
    await run_task(Sequential(
        RelativeToInitialHeading(90),
        MoveX(5)
    ))

run(main())

#visible=lambda: shm.red_buoy_results.heuristic_score.get() == 1.0
#visible=lambda: False
#asyncio.run(spiral_search(visible))

#asyncio.run(go_to_position(2, 2, depth=2))

#asyncio.run(relative_to_initial_position_n(2.0))
