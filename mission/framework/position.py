"""Defines async functions for moving the sub precise distances or to positions.

Note that every function in this file requires the DVL and thus can only be used
on mainsub.
"""

import asyncio
from typing import Tuple

from shm import kalman
from auv_math.math_utils import rotate

from mission.framework.movement import (_position_n as set_position_n,
        _position_e as set_position_e, _relative_to_initial_position_n,
        _relative_to_initial_position_e, _heading as set_heading,
        _depth as set_depth)

from mission.core.contexts import PositionalControls

DEFAULT_TOLERANCE = 0.05

async def move_xy_from_initial(initial_heading: float,
                               initial_ne: Tuple[float, float],
                               delta : Tuple[float, float],
                               tolerance : float = DEFAULT_TOLERANCE) -> None:
    """
    Move some distance forward and some distance right. Requires the DVL.

    Args:
        vector:         how far the sub should move in the form (foward, right)
        tolerance:      the tolerance in the sub's final position in each direction
    
    Returns:
        None.
    """
    delta_north, delta_east = rotate(delta, initial_heading)
    initial_north, initial_east = initial_ne

    n_position = initial_north + delta_north 
    e_position = initial_east + delta_east

    await go_to_position(north=n_position,
                         east=e_position,
                         heading=initial_heading,
                         tolerance=tolerance)
    
async def move_xy(vector : Tuple[float, float],
                  tolerance : float = DEFAULT_TOLERANCE)  -> None:
    """
    Move some distance forward and some distance right. Requires the DVL.

    Args:
        vector:         how far the sub should move in the form (foward, right)
        tolerance:      the tolerance in the sub's final position in each direction
    
    Returns:
        None.
    """
    delta_north, delta_east = rotate(vector, kalman.heading.get())
    n_position = asyncio.ensure_future(_relative_to_initial_position_n(
            offset=delta_north, tolerance=tolerance))
    e_position = asyncio.ensure_future(_relative_to_initial_position_e(
            offset=delta_east, tolerance=tolerance))
    try:
        await asyncio.gather(n_position, e_position)
    except asyncio.CancelledError:
        n_position.cancel()
        e_position.cancel()
        await asyncio.sleep(0)
        raise

async def move_x(distance : float,
                 tolerance : float = DEFAULT_TOLERANCE) -> None:
    """
    Move some distance forward (or backward). Requires the DVL.

    Args:
        distance:       how far forward the sub should move (negative for backward)
        tolerance:      the tolerance in the sub's final position
    """
    await move_xy((distance, 0), tolerance=tolerance)

async def move_y(distance : float,
                 tolerance : float = DEFAULT_TOLERANCE):
    """
    Move some distance to the right (or left). Requires the DVL.

    Args:
        distance:       how far right the sub should move (negative for leftward)
        deadband:       the tolerance in the sub's final position
    
    Returns:
        None.
    """
    await move_xy((0, distance), tolerance=tolerance)

async def move_angle(angle : float,
                     distance : float,
                     tolerance : float = DEFAULT_TOLERANCE) -> None:
    """
    Move some distance in some direction. Requires the DVL. Note that the angle
    is in absolute terms, not relative to the sub's current direction.

    Args:
        angle:          the direction in which the sub should move
        distance:       how far the sub should move
        tolerance:      the tolerance in the sub's final position

    Returns:
        None.
    """
    vector = rotate((distance, 0), angle)
    await move_xy(vector, tolerance=tolerance)

async def go_to_position(north : float,
                         east : float,
                         heading : float = None,
                         depth : float = None,
                         tolerance : float = 0.05,
                         heading_tolerance : float = 2) -> None:
    """
    Move the sub to a specific location in absolute space. Requires the DVL.

    Args:
        north:              the desired final north coordinate of the sub
        east:               the desired final east coordinate of the sub
        heading:            the desired final direction in which the sub will face
        depth:              the desired final depth coordinate of the sub
        tolerance:          the tolerance in the sub's final position in each dimension
        heading_tolerance:  the tolerance in the sub's final heading
    
    Returns:
        None.
    """
    with PositionalControls():
        position_n_task = asyncio.ensure_future(set_position_n(north,
                tolerance=tolerance))
        position_e_task = asyncio.ensure_future(set_position_e(east,
                tolerance=tolerance))
        heading_task = asyncio.ensure_future(set_heading(
                heading or kalman.heading.get(), tolerance=heading_tolerance))
        depth_task = asyncio.ensure_future(set_depth(
                depth or kalman.depth.get(), tolerance=tolerance))
        try:
            await asyncio.gather(position_n_task, position_e_task, heading_task,
                   depth_task)
        except asyncio.CancelledError:
            position_n_task.cancel()
            position_e_task.cancel()
            heading_task.cancel()
            depth_task.cancel()
            raise 
