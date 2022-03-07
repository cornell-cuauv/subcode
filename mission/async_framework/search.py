import asyncio
from typing import Callable

import shm
from mission.async_framework.movement import velocity_x_for_secs, \
                                             velocity_y_for_secs
from mission.async_framework.position import move_x, move_y
from mission.async_framework.primitive import zero

async def velocity_sway_pattern(width : float, stride : float, speed : float,
                                right_first : bool, check_behind : bool) \
                                -> bool:
    sway_time = width / speed
    stride_time = stride / speed
    direction = 1 if right_first else -1
    while True:
        if check_behind:
            await velocity_x_for_secs(-speed, stride_time)
            await velocity_x_for_secs(speed, stride_time)
            await velocity_x(0)
        await velocity_y_for_secs(speed * direction, sway_time)
        await velocity_x_for_secs(speed, stride_time)
        await velocity_y_for_secs(-speed * direction, 2 * sway_time)
        await velocity_x_for_secs(speed, stride_time)
        await velocity_y_for_secs(speed * direction, sway_time)

async def velocity_sway_search(visible : Callable[[], bool], width : float = 1,
                               stride : float = 1, speed : float = 0.3,
                               right_first : bool = True,
                               check_behind : bool = False) -> bool:
    search = asyncio.create_task(velocity_sway_pattern(width, stride, speed,
                                                       right_first,
                                                       check_behind))
    while not visible():
        await asyncio.sleep(0.01)
    search.cancel()
    await zero()
