import math
import numpy as np
import asyncio
from typing import Callable, Any

from auv_python_helpers.angles import abs_heading_sub_degrees
from mission.framework.movement import (velocity_x, velocity_x_for_secs,
        velocity_y_for_secs, roll_for_secs, heading,
        relative_to_initial_heading)
from mission.framework.position import move_x, move_y, go_to_position
from mission.framework.primitive import zero
from mission.constants.sub import Tolerance
from conf.vehicle import dvl_present

async def search(visible : Callable[[], bool], pattern: Any):
    """Move in a given pattern until finding something.

    Arguments:
    visible -- a function that returns true if the object has been found
    pattern -- a coroutine that will move the sub along the desired pattern

    Returns True if the object has been found and False if the search pattern
    terminated prematurely (generally because of a timeout)
    """
    search = asyncio.create_task(pattern)
    try:
        while not visible() and not search.done():
            await asyncio.sleep(0.01)
        return True if visible() else False
    except asyncio.CancelledError:
        raise
    finally:
        search.cancel()
        await asyncio.sleep(0)
        await zero()
    

async def spin_pattern(interval_size : float, clockwise : bool,
        timeout_degrees : float):
    """Rotate continuously.

    Note that this function will never terminate naturally besides by timeout.

    Arguments:
    interval_size   -- how many degrees the sub should rotate at a time
    clockwise       -- if the sub should spin clockwise
    timeout_degrees -- how many degrees the sub should rotate before giving up
    """
    direction = 1 if clockwise else -1
    total_degrees = 0
    while True:
        await relative_to_initial_heading(offset = direction  * interval_size)
        total_degrees += interval_size
        if total_degrees >= timeout_degrees:
            return

async def spin_search(visible : Callable[[], bool], interval_size : float = 20,
        clockwise : bool = True, timeout_degrees : float = float('inf')):
    """Rotate continuously until finding something.

    Arguments:
    visible -- a function that returns True if the object has been found
    ...     -- same as spin_pattern

    Returns True if the object is found and False if the the sub spins
    [timeout_degrees] degrees without finding it
    """
    return await search(visible, spin_pattern(interval_size, clockwise,
            timeout_degrees))

async def heading_rotation(direction, amplitude, splits):
    """Rotate a little bit at a time one way and then back.

    Arguments:
    direction -- -1 to start counterclockwise, 1 to start clockwise
    amplitude -- the number of degrees to rotate in total in each direction
    splits    -- the number of small rotations which make up the whole
    """
    for i in range(splits):
        await relative_to_initial_heading(direction * amplitude / splits)
    for i in range(splits):
        await relative_to_initial_heading(-direction * amplitude / splits)

async def sway_pattern(width : float, stride : float, tolerance : float,
        right_first : bool, heading_search : bool, heading_amplitude : float,
        splits: int, timeout_distance : float):
    """Sway left and right intermittently while generally moving forward.

    Requires the DVL. Note that this function will never terminate naturally
    besides by timeout.

    Arguments:
    width             -- the width of the sub's sways
    stride            -- the distance the sub moves forward between sways
    tolerance         -- the tolerance in each movement's length
    right_first       -- the sub can start by swaying either left of right
    heading_search    -- if the sub should perform a heading search at the end
                         of each stride
    heading_amplitude -- the angle of rotation of the heading search
    splits            -- the number of splits on each heading rotation,
                         increase for slower rotation
    timeout_distance  -- how far forward the sub should travel before giving up
    """
    if not dvl_present:
        print("Error: sway_pattern requires the DVL. Skipping task. Use"
                " velocity_sway_pattern instead.")
        return False
    direction = 1 if right_first else -1
    total_distance = 0
    await move_y(0.5 * width * direction, tolerance)
    while True:
        await move_x(stride, tolerance)
        if heading_search:
            await heading_rotation(direction, heading_amplitude, splits)
        await move_y(-width * direction, tolerance)
        direction *= -1
        total_distance += stride
        if total_distance >= timeout_distance:
            return

async def sway_search(visible : Callable[[], bool], width : float = 2,
        stride : float = 1, tolerance : float = Tolerance.POSITION,
        right_first : bool = True, heading_search : bool = False,
        heading_amplitude : float = 45.0, splits : int = 1,
        timeout_distance : float = float('inf')):
    """Move in a forward sway pattern until finding something.

    Requires the DVL.

    Arguments:
    visible -- a function that returns true if the object has been found
    ...     -- same as sway_pattern

    Returns True if the object is found and False if the sub travels
    [timeout_distance] meters forward without finding it
    """
    if not dvl_present:
        print("Error: sway_search requires the DVL. Skipping task. Use"
                " velocity_sway_search instead.")
        return False
    return await search(visible, sway_pattern(width, stride, tolerance, right_first,
            heading_search, heading_amplitude, splits, timeout_distance))

async def velocity_sway_pattern(width : float, stride : float, speed : float,
        right_first : bool, heading_search : bool, heading_amplitude : float,
        splits : int, timeout_distance : float):
    """Sway left and right intermittently while generally moving forward.

    Designed for minisub. Note that this function will never terminate
    naturally besides by timeout.

    Arguments:
    width             -- the width of the sub's sways
    stride            -- the distance the sub moves forward between sways
    speed             -- how fast the sub moves in each direction
    right_first       -- the sub can start by swaying either left or right
    heading_search    -- if the sub should perform a heading search at the end
                         of each stride
    heading_amplitude -- the angle of rotation of the heading search
    splits            -- the number of splits on each heading rotation,
                         increase for slower rotation
    timeout_distance  -- how far forward the sub should travel before giving up
    """
    if dvl_present:
        print("Warning: sway_pattern is preferable to velocity_sway_pattern"
                " when the DVL is available.")
    direction = 1 if right_first else -1
    total_distance = 0
    await velocity_y_for_secs(speed * direction, 0.5 * width / speed)
    while True:
        await velocity_x_for_secs(speed, stride / speed)
        if heading_search:
            await heading_rotation(direction, heading_amplitude, splits)
        await velocity_y_for_secs(-speed * direction, width / speed)
        direction *= -1
        total_distance += stride
        if total_distance >= timeout_distance:
            return

async def velocity_sway_search(visible : Callable[[], bool], width : float = 2,
        stride : float = 1, speed : float = 0.3, right_first : bool = True,
        heading_search : bool = False, heading_amplitude : float = 45.0,
        splits : int = 1, timeout_distance : float = float('inf')):
    """Move in a forward sway pattern until finding something.
    
    Designed for minisub.

    Arguments:
    visible -- a function that returns true if the object has been found
    ...     -- same as velocity_sway_pattern

    Returns True if the object is found and False if the sub travels
    timeout_distance forward without finding it
    """
    if dvl_present:
        print("Warning: sway_search is preferable to velocity_sway_search when"
                " the DVL is available.")
    return await search(visible, velocity_sway_pattern(width, stride, speed,
            right_first, heading_search, heading_amplitude, splits,
            timeout_distance))

async def square_pattern(first_dist : float, dist_increase : float,
        tolerance : float, constant_heading : bool, timeout_radius : float):
    """Move in an outwardly-expanding square spiral.

    Requires the DVL. Note that this function will never terminate naturally
    besides by timeout. It will only time out after traversing a multiple of 4
    sides.

    Arguments:
    first_dist       -- the length of the first two sides of the first square
    dist_increase    -- the increase in sidelength of the squares
    tolerance        -- the tolerance in the sidelength of the squares
    constant_heading -- if the sub should maintain a constant heading
    timeout_radius   -- how far from its origin the sub should travel before
                        giving up
    """
    if not dvl_present:
        print("Error: square_pattern requires the DVL. Skipping task. Use"
                " velocity_square_pattern instead.")
        return False
    distance = first_dist
    while True:
        if constant_heading:
            await move_x(distance, tolerance)
            await move_y(distance, tolerance)
            distance += dist_increase
            await move_x(-distance, tolerance)
            await move_y(-distance, tolerance)
            distance += dist_increase
        else:
            for _ in range(2):
                await move_x(distance, tolerance)
                await relative_to_initial_heading(90)
                await move_x(distance, tolerance)
                await relative_to_initial_heading(90)
                distance += dist_increase
        if ((distance - dist_increase) / 2) * math.sqrt(2) >= timeout_radius:
            return

async def square_search(visible: Callable[[], bool], first_dist : float = 0.5,
        dist_increase : float = 1, tolerance : float = Tolerance.POSITION,
        constant_heading : bool = False,
        timeout_radius : float = float('inf')):
    """Move in a square spiral pattern until finding something.

    Requires the DVL. This function will only time out after traversing a
    multiple of 4 sides.

    Arguments:
    visible -- a function that returns true if the object has been found
    ...     -- same as square_pattern

    Returns True if the object is found and False if the sub travels
    [timeout_radius] meters from its starting point without finding it
    """
    if not dvl_present:
        print("Error: square_search requires the DVL. Skipping task. Use"
                " velocity_square_search instead.")
        return False
    return await search(visible, square_pattern(first_dist, dist_increase, tolerance,
            constant_heading, timeout_radius))

async def velocity_square_pattern(first_dist : float,
        dist_increase : float, speed : float, constant_heading : bool,
        timeout_radius : float):
    """Move in an outwardly-expanding square spiral.

    Designed for minisub. Note that this function will never terminate
    naturally besides by timeout. It will only time out after traversing a
    multiple of 4 sides.

    Arguments:
    first_dist       -- the length of the first two sides of the first square
    dist_increase    -- the increase in side length of the squares
    speed            -- how fast the sub moves in each direction
    constant_heading -- if the sub should maintain a constant heading
    timeout_radius   -- how far from its origin the sub should travel before
                        giving up
    """
    if dvl_present:
        print("Warning: square_pattern is preferable to velocity_square_pattern"
                " when the DVL is available.")
    distance = first_dist
    while True:
        if constant_heading:
            await velocity_x_for_secs(speed, distance / speed)
            await velocity_y_for_secs(speed, distance / speed)
            distance += dist_increase
            await velocity_x_for_secs(-speed, distance / speed)
            await velocity_y_for_secs(-speed, distance / speed)
            distance += dist_increase
        else:
            for _ in range(2):
                await velocity_x_for_secs(speed, distance / speed)
                await relative_to_initial_heading(90)
                await velocity_x_for_secs(speed, distance / speed)
                await relative_to_initial_heading(90)
                distance += dist_increase
        if ((distance - dist_increase) / 2) * math.sqrt(2) >= timeout_radius:
            return

async def velocity_square_search(visible : Callable[[], bool],
        first_dist : float = 0.5, dist_increase : float = 1,
        speed : float = 0.3, constant_heading : bool = False,
        timeout_radius : float = float('inf')):
    """Move in an outwardly-expanding square spiral until finding something.

    Designed for minisub. This function will only time out after traversing a
    multiple of 4 sides.

    Arguments:
    visible -- a function that returns true if the thing has been found
    ...     -- same as velocity_square_pattern

    Returns True if the object is found and False if the sub travels
    [timeout_radius] meters from its starting point without finding it
    """
    if dvl_present:
        print("Warning: square_search is preferable to velocity_square_search"
                " when the DVL is available.")
    return await search(visible, velocity_square_pattern(first_dist, dist_increase,
            speed, constant_heading, timeout_radius))
