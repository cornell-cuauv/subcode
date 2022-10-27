import math
import numpy as np
import asyncio
from typing import Callable, Optional, Any

from auv_python_helpers.angles import abs_heading_sub_degrees
from mission.async_framework.movement import (velocity_x, velocity_x_for_secs,
        velocity_y_for_secs, roll_for_secs, heading,
        relative_to_initial_heading)
from mission.async_framework.position import move_x, move_y, go_to_position
from mission.async_framework.primitive import zero
from mission.async_framework.logger import timeline
from mission.constants.sub import Tolerance
from conf import vehicle

@timeline()
async def search(visible : Callable[[], bool], pattern: Any):
    """Move in a given pattern until finding something.

    Arguments:
    visible -- a function that returns true if the object has been found
    pattern -- a coroutine that will move the sub along the desired pattern
    """
    search = asyncio.create_task(pattern)
    try:
        while not visible():
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        raise
    finally:
        search.cancel()
        await asyncio.sleep(0)
        await zero()

@timeline()
async def spin_pattern(interval_size : float, clockwise : bool = True):
    """Rotate continuously.

    Note that this function will never terminate if not interrupted.

    Arguments:
    interval_size -- how many degrees the sub should rotate at a time
    clockwise     -- if the sub should spin clockwise
    """
    direction = 1 if clockwise else -1
    while True:
        await relative_to_initial_heading(offset = direction  * interval_size)

async def spin_search(visible : Callable[[], bool], interval_size : float,
        clockwise : bool = True):
    """Rotates continuously until finding something.

    Arguments:
    visible -- a function that returns True if the object has been found
    ...     -- same as spin_pattern
    """
    await search(visible, spin_pattern(interval_size, clockwise))

async def heading_rotation(direction, amplitude, splits):
    """Rotate a little bit at a time.

    Arguments:
    direction -- -1 for counterclockwise, 1 for clockwise
    amplitude -- the number of degrees to rotate in total
    splits    -- the number of small rotations which make up the whole
    """
    for i in range(splits):
        await relative_to_initial_heading(rection * amplitude / splits)

@timeline()
async def velocity_sway_pattern(width : float, stride : float, speed : float,
        right_first : bool, check_behind : bool, heading_search : bool,
        heading_amplitude : float, splits : int):
    """Sway left and right intermittently while generally moving forward.

    Designed for minisub. Note that this function will never terminate if not
    interrupted.

    Arguments:
    width             -- the width of the sub's sways
    stride            -- the distance the sub moves forward between sways
    speed             -- how fast the sub moves in each direction
    right_first       -- the sub can start by swaying either left or right
    check_behind      -- if the sub should move backward briefly before swaying
    heading_search    -- if the sub should perform a heading search at the end
                         of each stride
    heading_amplitude -- the angle of rotation the heading search does
    splits            -- the number of splits on each heading rotation, increase
                         for slower rotation
    """
    sway_time = width / speed
    stride_time = stride / speed
    direction = 1 if right_first else -1
    while True:
        await zero()
        if check_behind:
            await velocity_x_for_secs(-speed, stride_time)
            await velocity_x_for_secs(speed, stride_time)
            await velocity_x(0)
        await velocity_y_for_secs(speed * direction, sway_time)
        await velocity_x_for_secs(speed, stride_time)
        if heading_search:
            await heading_rotation(direction, heading_amplitude, splits)
        await velocity_y_for_secs(-speed * direction, 2 * sway_time)
        await velocity_x_for_secs(speed, stride_time)
        if heading_search:
            await heading_rotation(-direction, heading_amplitude, splits)    
        await velocity_y_for_secs(speed * direction, sway_time)

@timeline()
async def velocity_sway_search(visible : Callable[[], bool], width : float = 1,
        stride : float = 1, speed : float = 0.3, right_first : bool = True,
        check_behind : bool = False, heading_search : bool = False,
        heading_amplitude : float = 45.0, split : int = 1):
    """Move in a forward sway pattern until finding something.
    
    Designed for minisub.

    Arguments:
    visible -- a function that returns true if the object has been found
    ...     -- same as velocity_sway_pattern
    """
    if vehicle.is_mainsub:
        split = 2
    await search(visible, velocity_sway_pattern(width, stride, speed,
        right_first, check_behind, heading_search, heading_amplitude, split))


@timeline()
async def sway_pattern(width : float, stride : float, roll_extension : bool,
        tolerance : float = Tolerance.POSITION):
    """Sway left and right intermittently while generally moving forward.

    Requires the DVL. Note that this function will never terminate if not
    interrupted.

    Arguments:
    width          -- the width of the sub's sways
    stride         -- the distance the sub moves forward between sways
    roll_extension -- if the sub should roll briefly between movements
    tolerance      -- the tolerance in each movement's length
    """
    async def maybe_roll(roll_direction : int):
        if roll_extension:
            await roll_for_secs(-roll_direction * 45, 1)

    await move_y(-width / 2, tolerance=tolerance)
    await maybe_roll(-1)
    while True:
        await move_y(width, tolerance=tolerance)
        await maybe_roll(1)
        await move_x(stride, tolerance=tolerance)
        await maybe_roll(1)
        await move_y(-width, tolerance=tolerance)
        await maybe_roll(-1)
        await move_x(stride, tolerance=tolerance)
        await maybe_roll(-1)


@timeline()
async def sway_search(visible : Callable[[], bool], width : float = 1,
        stride : float = 1, roll_extension : bool = False,
        tolerance : float = Tolerance.POSITION):
    """Move in a forward sway pattern until finding something.

    Requires the DVL.

    Arguments:
    visible -- a function that returns true if the object has been found
    ...     -- same as sway_pattern
    """
    await search(visible, sway_pattern(width, stride, roll_extension,
            tolerance))

async def square_pattern(first_dist : float = 0.5, dist_increase : float = 1,
        tolerance : float = 0.25, constant_heading : bool = False):
    """Move in an outwardly-expanding square spiral.

    Requires the DVL. Note that this function will never terminate if not
    interrupted.

    Arguments:
    first_dist       -- the length of the first two sides of the first square
    dist_increase    -- the increase in sidelength of the squares
    tolerance        -- the tolerance in the sidelength of the squares
    constant_heading -- if the sub should maintain a constant heading
    """
    distance = first_dist
    while True:
        if constant_heading:
            await move_x(distance, tolerance=tolerance)
            await move_y(distance, tolerance=tolerance)
            distance += dist_increase
            await move_x(-distance, tolerance=tolerance)
            await move_y(-distance, tolerance=tolerance)
            distance += dist_increase
        else:
            await move_x(distance, tolerance=tolerance)
            await relative_to_initial_heading(90)
            await move_x(distance, tolerance=tolerance)
            await relative_to_initial_heading(90)
            distance += dist_increase

@timeline()
async def square_search(visible: Callable[[], bool], first_dist : float = 0.5,
        dist_increase : float = 1, tolerance : float = 0.25,
        constant_heading : bool = False):
    """Move in a square spiral pattern until finding something.

    Requires the DVL.

    Arguments:
    visible -- a function that returns true if the object has been found
    ...     -- same as square_pattern
    """
    await search(visible, square_pattern(first_dist, dist_increase, tolerance,
            constant_heading))
