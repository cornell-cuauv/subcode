"""Defines async functions for moving the sub precise distances or to positions.

Note that every function in this file requires the DVL and thus can only be used
on mainsub.
"""

import asyncio
from typing import Tuple

from shm import kalman
from auv_math.math_utils import rotate
from mission.framework.movement import (position_n as set_position_n,
        position_e as set_position_e, relative_to_initial_position_n,
        relative_to_initial_position_e, heading as set_heading,
        depth as set_depth)
from mission.framework.contexts import PositionalControls

async def move_xy(vector : Tuple[float, float], tolerance : float = 0.01):
    """Move some distance forward and some distance right.

    Requires the DVL.

    Arguments:
    vector    -- how far the sub should move in the form (foward, right)
    tolerance -- the tolerance in the sub's final position in each direction
    """
    delta_north, delta_east = rotate(vector, kalman.heading.get())
    n_position = asyncio.ensure_future(relative_to_initial_position_n(
            offset=delta_north, tolerance=tolerance))
    e_position = asyncio.ensure_future(relative_to_initial_position_e(
            offset=delta_east, tolerance=tolerance))
    try:
        await asyncio.gather(n_position, e_position)
    except asyncio.CancelledError:
        n_position.cancel()
        e_position.cancel()
        await asyncio.sleep(0)
        raise

async def move_x(distance : float, tolerance : float = 0.01):
    """Move some distance forward (or backward).

    Requires the DVL.

    Arguments:
    distance -- how far forward the sub should move (negative for backward)
    tolerance -- the tolerance in the sub's final position
    """
    await move_xy((distance, 0), tolerance=tolerance)

async def move_y(distance : float, tolerance : float = 0.01):
    """Move some distance to the right (or left).

    Requires the DVL.

    Arguments:
    distance -- how far right the sub should move (negative for leftward)
    deadbadn -- the tolerance in the sub's final position
    """
    await move_xy((0, distance), tolerance=tolerance)

async def move_angle(angle : float, distance : float, tolerance : float = 0.01):
    """Move some distance in some direction.

    Requires the DVL. Note that the angle is in absolute terms, not relative to
    the sub's current direction.

    Arguments:
    angle    -- the direction in which the sub should move
    distance -- how far the sub should move
    tolerance -- the tolerance in the sub's final position
    """
    vector = rotate((distance, 0), angle)
    await move_xy(vector, tolerance=tolerance)

async def go_to_position(north : float, east : float, heading : float = None,
        depth : float = None, tolerance : float = 0.05,
        heading_tolerance : float = 2):
    """Move the sub to a specific location in absolute space.

    Requires the DVL.

    Arguments:
    north             -- the desired final north coordinate of the sub
    east              -- the desired final east coordinate of the sub
    heading           -- the desired final direction in which the sub will face
    depth             -- the desired final depth coordinate of the sub
    tolerance         -- the tolerance in the sub's final position in each
                         dimension
    heading_tolerance -- the tolerance in the sub's final heading
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
