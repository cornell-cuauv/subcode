import asyncio
from typing import Tuple

import shm
from auv_math.math_utils import rotate
from mission.async_framework.movement import position_n, position_e, heading, depth


async def move_xy(vector : Tuple[float, float], deadband : float = 0.01) -> bool:
    delta_north, delta_east = rotate(vector, shm.kalman.heading.get())
    n_position = relative_to_initial_position_n(offset=delta_north, error=deadband)
    e_position = relative_to_initial_position_e(offset=delta_east, error=deadband)
    return await asyncio.gather(n_position, e_position)


async def move_x(distance : float, deadband : float = 0.01) -> bool:
    return await move_xy((distance, 0), deadband=deadband)


async def move_y(distance : float, deadband : float = 0.01) -> bool:
    return await move_xy((0, distance), deadband=deadband)


async def move_angle(angle : float, distance : float, deadband : float = 0.01) -> bool:
    vector = rotate((distance, 0), angle)
    return await move_xy(vector, deadband=deadband)


async def go_to_position(north : float, east : float, heading : float = None,
                         depth : float = None, optimize : bool = False,
                         rough : bool = False, deadband : float = 0.05) -> bool:
    with PositionalControls(optimize=optimize):
        if heading == None:
            heading = shm.kalman.heading.get()
        if depth == None:
            depth = shm.kalman.depth.get()
        return await asyncio.gather(
            position_n(north, deadband=deadband),
            position_e(east, deadband=deadband),
            heading(heading, deadband=deadband),
            depth(depth, deadband=deadband)
        )


async def check_distance(distance : float) -> bool:
    init_n = shm.kalman.north.get()
    init_e = shm.kalman.east.get()
    while (shm.kalman.north.get() - init_n) ** 2 + (shm.kalman.east.get() - init_e) ** 2 < distance ** 2:
        await asyncio.sleep(0.01)
    return True
