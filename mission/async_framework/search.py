import asyncio
from typing import Callable

import shm
from mission.async_framework.movement import velocity_x_for_secs, velocity_y_for_secs
from mission.async_framework.position import move_x, move_y

async def velocity_sway_search(width : float = 1, stride : float = 1,
                               speed : float = 0.3, right_first : bool = True,
                               check_behind : bool = False,
                               visible : Callable[[], bool]) -> bool:
    sway_time = width / speed
    stride_time = stride / speed
    direction = 1 if right_first else 0
    while True:
        if check_behind:
            await velocity_x_for_secs(-speed, stride_time)
            if visible(): return True
            await velocity_x_for_secs(speed, stride_time)
            if visible(): return True
            await velocity_x(0)
            if visible(): return True
        await velocity_y_for_secs(speed * dir, sway_time)
        if visible(): return True
        await velocity_x_for_secs(speed, stride_time)
        if visible(): return True
        await velocity_y_for_secs(-speed * dir, 2 * sway_time)
        if visible(): return True
        await velocity_x_for_secs(speed, stride_time)
        if visible(): return True
        await velocity_y_for_secs(speed * dir, sway_time)
        if visible(): return True

async def sway_search(width : float = 1, stride : float = 1,
                      visible : Callable[[], bool]) -> bool:
    await move_y(width / 2, deadband=0.2)
    while True:
        if visible(): return True
        await move_y(-width, deadband=0.2)
        if visible(): return True
        await move_x(stride, deadband=0.2)
        if visible(): return True
        await move_y(width, deadband=0.2)
        if visible(): return True
        await move_x(stride, deadband=0.2)
