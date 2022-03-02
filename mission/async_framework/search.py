import asyncio
from typing import Callable

import shm
from mission.async_framework.movement import velocity_x, velocity_y

async def velocity_sway_search(width : float = 1, stride : float = 1,
                               speed : float = 0.3, right_first : bool = True,
                               check_behind : bool = False,
                               visible : Callable[[], bool]) -> bool:
    sway_time = width / speed
    stride_time = stride / speed
    direction = 1 if right_first else 0
    await velocity_x(-speed)
    await asyncio.sleep(stride_time)
    await velocity_x(0)
    await velocity_y(speed * direction)
    await velocity_y(0)
    await velocity_x(speed)
