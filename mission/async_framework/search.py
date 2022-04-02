import math
import numpy as np
import asyncio
from typing import Callable, Optional

import shm
from mission.async_framework.movement import (velocity_x_for_secs,
        velocity_y_for_secs, roll_for_secs, heading)
from mission.async_framework.position import move_x, move_y, go_to_position
from mission.async_framework.primitive import zero


async def velocity_sway_pattern(width : float, stride : float, speed : float,
        right_first : bool, check_behind : bool):
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
        stride : float = 1, speed : float = 0.3, right_first : bool = True,
        check_behind : bool = False) -> bool:
    search = asyncio.create_task(velocity_sway_pattern(width, stride, speed,
            right_first, check_behind))
    while not visible():
        await asyncio.sleep(0.01)
    search.cancel()
    return await zero()


async def sway_pattern(width : float, stride : float, roll_extension : bool):

    async def maybe_roll(roll_direction : int):
        if roll_extension:
            await roll_for_secs(-roll_direction * 45, 1)

    await move_y(-width / 2)
    await maybe_roll(-1)
    while True:
        await move_y(width)
        await maybe_roll(1)
        await move_x(stride)
        await maybe_roll(1)
        await move_y(-width)
        await maybe_roll(-1)
        await move_x(stride)
        await maybe_roll(-1)


async def sway_search(visible : Callable[[], bool], width : float = 1,
        stride : float = 1, roll_extension : bool = False) -> bool:
    search = asyncio.create_task(sway_pattern(width, stride, roll_extension))
    while not visible():
        await asyncio.sleep(0.01)
    search.cancel()
    return await zero()


async def spiral_pattern(meters_per_revolution : float, deadband : float,
        spin_ratio : float, relative_depth_range : float,
        heading_change_scale : Optional[float], optimize_heading : bool,
        min_spin_radius : Optional[float]):

    def sub_position():
        return np.array([shm.kalman.north.get(), shm.kalman.east.get(),
                shm.kalman.depth.get()])

    theta = 0
    start_position = [shm.kalman.north.get(), shm.kalman.east.get(),
            shm.kalman.depth.get()]
    started_heading = False

    def calc_position():
        delta = np.array([radius * math.cos(math.radians(theta)),
                radius * math.sin(math.radians(theta)),
                relative_depth_range * math.sin(math.radians(theta))])
        return start_position + delta

    while True:
        radius = meters_per_revolution * theta / 360
        target = calc_position()
        delta = target - sub_position()
        await go_to_position(target[0], target[1], depth=target[2])
        desired_heading = spin_ratio * theta + 90
        if heading_change_scale != None:
            desired_heading *= min(1, radius) * heading_change_scale
        if optimize_heading:
            desired_heading = math.degrees(math.atan2(delta[1], delta[0]))
            if min_spin_radius != None:
                if ((not abs_heading_sub_degrees(shm.kalman.heading.get(),
                        desired_heading) < 10 or not radius > min_spin_radius)
                        and not started_heading):
                    desired_heading = shm.navigation_desires.heading.get()
                else:
                    started_heading = True
        await heading(desired_heading % 360)
        if np.linalg.norm(sub_position() - target) < deadband:
            theta += 10


async def spiral_search(visible : Callable[[], bool],
        meters_per_revolution : float = 1.3,
        deadband : float = 0.2, spin_ratio : float = 1,
        relative_depth_range : float = 0.0,
        heading_change_scale : Optional[float] = None,
        optimize_heading : bool = False,
        min_spin_radius : Optional[float] = None) -> bool:
    search = asyncio.create_task(spiral_pattern(meters_per_revolution, deadband,
            spin_ratio, relative_depth_range, heading_change_scale,
            optimize_heading, min_spin_radius))
    while not visible():
        await asyncio.sleep(0.01)
    search.cancel()
    return await zero()

