"""Defines async functions for moving the sub in each degree of freedom*.

Each of the first four generalized functions in this file (setter,
setter_for_secs, relative_to_initial_setter, and relative_to_current_setter) is
used repeatedly to build many more functions specific to a given degree of
freedom of the sub.

The generate_setters function below uses these generalized setters to create
four specific setters for a given degree of freedom. It is then called once for
each of the eight degrees of freedom to create a total of 32 specific setters.

* Degree of freedom is used loosely here.
"""

import asyncio
from typing import Any, Callable, Optional

import shm
from conf.vehicle import dvl_scaling_factor
from mission.utils.helpers import within_deadband
from mission.core.contexts import PositionalControls
from mission.constants.sub import Tolerance

async def setter(target : float,
                 desire_var : Any,
                 current_var : Any,
                 tolerance : float = 0,
                 modulo_error : bool = False):
    """
    Set a desire and then await until it is achieved.

    Arguments:
    target       -- the desired value
    desire_var   -- the SHM variable to which the desire can be written
    current_var  -- the SHM variable from which the current value can be read
    tolerance    -- the tolerance in the desired value
    modulo_error -- if the tolerance should "wrap around" between 0 and 360

    Example usage:
    await setter(180, shm.navigation_desires.heading, shm.kalman.heading,
            tolerance=5, modulo_error=True)
    Instructs the sub to turn to the direction in which its heading is 180 degrees
    (due south) plus or minus 5 degrees.
    """
    desire_var.set(target)
    while not within_deadband(target, current_var.get(), tolerance,
            modulo_error):
        await asyncio.sleep(0.01)

async def setter_for_secs(target : float,
                          desire_var : Any,
                          current_var : Any,
                          duration : float,
                          tolerance : float = 0,
                          modulo_error : bool = False):
    """
    Set a desire and then unset it after some time has passed.
    
    Arguments:
    target       -- the temporarily desired value
    desire_var   -- the SHM variable to which the desire can be written
    current_var  -- the SHM variable from which the current value can be read
    duration     -- how long the desired value should be held
    tolerance    -- the tolerance in the temporarily desired value
    module_error -- if the tolerance should "wrap around" between 0 and 360

    Example usage:
    await setter_for_secs(0.4, shm.navigation_desires.speed, shm.kalman.velx,
            duration=10, tolerance=0.1, modulo_error=False)
    Instructs the sub to move forward at 0.4 meters per second plus or minus 0.1
    meters per second for 10 seconds (thus travelling approximately 4 meters).
    """
    init = desire_var.get()
    await setter(target, desire_var, current_var, tolerance, modulo_error)
    await asyncio.sleep(duration)
    await setter(init, desire_var, current_var, tolerance, modulo_error)

async def relative_to_initial_setter(offset : float,
                                     desire_var : Any,
                                     current_var : Any,
                                     tolerance : float = 0,
                                     modulo_error : bool = False):
    """
    Set a desire relative to the current value of a variable.

    Arguments:
    offset       -- how much higher should the value be than it currently is
    desire_var   -- the SHM variable to which the desire can be written
    current_var  -- the SHM variable from which the current value can be read
    tolerance    -- the tolerance in the desired value
    modulo_error -- if the tolerance should "wrap around" between 0 and 360

    Example usage:
    await relative_to_initial_setter(2, shm.navigation_desires.north,
            shm.kalman.north, tolerance=0.3, modulo_error=False)
    Instructs the sub to move 2 meters plus or minus 0.3 meters north of where
    it is now. (Note that in this specific example, positional controls would
    need to be enabled. See how to do that in contexts.py.)
    """
    target = current_var.get() + offset
    desire_var.set(target)
    while not within_deadband(target, current_var.get(), tolerance,
            modulo_error):
        await asyncio.sleep(0.01)

async def relative_to_current_setter(offset : Callable[[], float],
                                     desire_var : Any,
                                     current_var : Any,
                                     tolerance : float = 0,
                                     modulo_error : bool = False):
    """
    Set and hold a desire at a changing offset from the value of a variable.

    Think of this function as defining a "moving target." A previous version of
    this docstring made the claim that this function is never used. That is
    quite untrue. In particular, it is used by targeting functions to indirectly
    control the sub's depth and angular velocities.

    Arguments:
    offset       -- a function which returns how much higher the sub should try
                    to get the value
    desire_var   -- the SHM variable to which the desire can be written
    current_var  -- the SHM variable from which the current value can be read
    tolerance    -- the tolerance in the desired value
    module_error -- if the tolerance should "wrap around" between 0 and 360

    Example usage:
    offset = lambda: 15 if shm.kalman.heading.get() < 180 else 0
    await relative_to_current_setter(offset, shm.navigation_desires.roll,
            shm.kalman.roll, tolerance=5, modulo_error=True)
    
    Instructs the sub to roll clockwise until it is upside down and then stop.
    None of the above functions could achieve this in a single call, since
    simply setting the roll desire to 180 would allow the sub to roll either
    clockwise or counter-clockwise.
    """
    target = current_var.get() + offset()
    desire_var.set(target)
    while not within_deadband(target, current_var.get(), tolerance, modulo_error):
        await asyncio.sleep(0.01)
        target = current_var.get() + offset()
        desire_var.set(target)

def generate_setters(desire_var : Any,
                     current_var : Any,
                     default_tolerance : float,
                     modulo_error : bool = False,
                     positional_controls : Optional[bool] = None):
    """
    Create setter functions specific to a given degree of freedom.

    For the given degree of freedom (specified through desire_var and
    current_var), define and return four functions, one corresponding to each of
    the generalized functions above.

    Arguments:
    desire_var          -- the SHM variable to which desires can be written
    current_var         -- the SHM variable from which the current value can be
                           read
    default_tolerance   -- the tolerance in the desired value used if no
                           specific error is specified
    modulo_error        -- if the tolerance should "wrap around" between 0 and
                           360
    positional_controls -- if positional controls need to be enabled when
                           manipulating this degree of freedom
    """
    
    # Corresponds to setter() above.
    async def s(target : float, tolerance : float = default_tolerance):
        with PositionalControls(positional_controls):
            await setter(target, desire_var, current_var, tolerance,
                    modulo_error)

    # Corresponds to setter_for_secs() above.
    async def sfs(target : float, duration : float,
            tolerance : float = default_tolerance):
        with PositionalControls(positional_controls):
            await setter_for_secs(target, desire_var, current_var, duration,
                    tolerance, modulo_error)

    # Corresponds to relative_to_initial_setter() above.
    async def rtis(offset : float, tolerance : float = default_tolerance):
        with PositionalControls(positional_controls):
            await relative_to_initial_setter(offset, desire_var, current_var,
                    tolerance, modulo_error)

    # Corresponds to relative_to_current_setter() above.
    async def rtcs(offset : Callable[[], float],
            tolerance : float = default_tolerance):
        with PositionalControls(positional_controls):
            await relative_to_current_setter(offset, desire_var, current_var,
                    tolerance, modulo_error)

    # Return all four specific setters.
    return (s, sfs, rtis, rtcs)

class Scalar:
    """A highly jank utility class to allow for DVL input / output scaling.

    An instance of this class impersonates a shm variable, providing get and set
    methods which call the real shm variable's get and set methods but with
    values multiplied by some factor.

    Hopefully the need for this will be eliminated very soon. Someone should
    figure out how to recalibrate the DVL, or at least how to perform the
    necessary scaling at a lower level.
    """
    def __init__(self, shm_var, factor):
        self.shm_var = shm_var
        self.factor = factor

    def get(self):
        return self.shm_var.get() * self.factor

    def set(self, value):
        self.shm_var.set(value * self.factor)

(_heading, _heading_for_secs, _relative_to_initial_heading,
        _relative_to_current_heading) = generate_setters(
        shm.navigation_desires.heading, shm.kalman.heading, Tolerance.HEAD,
        modulo_error=True)

(_pitch, _pitch_for_secs, _relative_to_initial_pitch,
        _relative_to_current_pitch) = generate_setters(
        shm.navigation_desires.pitch, shm.kalman.pitch, Tolerance.PITCH,
        modulo_error=True)

(_roll, _roll_for_secs, _relative_to_initial_roll,
        _relative_to_current_roll) = generate_setters(
        shm.navigation_desires.roll, shm.kalman.roll, Tolerance.ROLL,
        modulo_error=True)

(_depth, _depth_for_secs, _relative_to_initial_depth,
        _relative_to_current_depth) = generate_setters(
        shm.navigation_desires.depth, shm.kalman.depth, Tolerance.POSITION)

(_position_n, _position_n_for_secs, _relative_to_initial_position_n,
        _relative_to_current_position_n) = generate_setters(
        Scalar(shm.navigation_desires.north, dvl_scaling_factor),
        Scalar(shm.kalman.north, 1 / dvl_scaling_factor), Tolerance.POSITION,
        positional_controls=True)

(_position_e, _position_e_for_secs, _relative_to_initial_position_e,
        _relative_to_current_position_e) = generate_setters(
        Scalar(shm.navigation_desires.east, dvl_scaling_factor),
        Scalar(shm.kalman.east, 1 / dvl_scaling_factor), Tolerance.POSITION,
        positional_controls=True)

"""
These velocity setters automatically turn off and hold off positional controls
while they are running. But the setters not of the for_secs variety terminate as
soon as the sub has achieved the desired velocity, releasing control of
positional controls. If the mission writer expects the sub to continue moving at
the desired velocity once it has been achieved, they are responsible for making
sure that positional controls remain off. Learn more about positional controls
in contexts.py.
"""

(_velocity_x, _velocity_x_for_secs, _relative_to_initial_velocity_x,
        _relative_to_current_velocity_x) = generate_setters(
        shm.navigation_desires.speed, shm.kalman.velx, Tolerance.VELOCITY,
        positional_controls=False)

(_velocity_y, _velocity_y_for_secs, _relative_to_initial_velocity_y,
        _relative_to_current_velocity_y) = generate_setters(
        shm.navigation_desires.sway_speed, shm.kalman.vely, Tolerance.VELOCITY,
        positional_controls=False)

"""
We wrap these generators in explicit function calls, for compatibility with the
API generator.
"""

async def heading(target: float, tolerance: float = Tolerance.HEAD):
    """Set the desired heading.

    Args:
        target: The desired heading in degrees.
        tolerance: The allowable error in the heading. Defaults to Tolerance.HEAD.

    Returns:
        Result of the asynchronous heading setter.
    """
    return await _heading(target, tolerance)

async def heading_for_secs(target: float, duration: float, tolerance: float = Tolerance.HEAD):
    """Set the desired heading for a specific duration.

    Args:
        target: The desired heading in degrees.
        duration: The time in seconds to hold the heading.
        tolerance: The allowable error in the heading. Defaults to Tolerance.HEAD.

    Returns:
        Result of the asynchronous heading setter for a specific duration.
    """
    return await _heading_for_secs(target, duration, tolerance)

async def relative_to_initial_heading(offset: float, tolerance: float = Tolerance.HEAD):
    """Set the desired heading relative to the initial heading.

    Args:
        offset: The change in heading relative to the initial value.
        tolerance: The allowable error in the heading. Defaults to Tolerance.HEAD.

    Returns:
        Result of the asynchronous relative-to-initial heading setter.
    """
    return await _relative_to_initial_heading(offset, tolerance)

# async def relative_to_current_heading(offset: Callable[[], float], tolerance: float = Tolerance.HEAD):
#     """Set the desired heading relative to the current heading.

#     Args:
#         offset: A callable that returns the change in heading.
#         tolerance: The allowable error in the heading. Defaults to Tolerance.HEAD.

#     Returns:
#         Result of the asynchronous relative-to-current heading setter.
#     """
#     return await _relative_to_current_heading(offset, tolerance)

async def pitch(target: float, tolerance: float = Tolerance.PITCH):
    """Set the desired pitch.

    Args:
        target: The desired pitch in degrees.
        tolerance: The allowable error in the pitch. Defaults to Tolerance.PITCH.

    Returns:
        Result of the asynchronous pitch setter.
    """
    return await _pitch(target, tolerance)

async def pitch_for_secs(target: float, duration: float, tolerance: float = Tolerance.PITCH):
    """Set the desired pitch for a specific duration.

    Args:
        target: The desired pitch in degrees.
        duration: The time in seconds to hold the pitch.
        tolerance: The allowable error in the pitch. Defaults to Tolerance.PITCH.

    Returns:
        Result of the asynchronous pitch setter for a specific duration.
    """
    return await _pitch_for_secs(target, duration, tolerance)

async def relative_to_initial_pitch(offset: float, tolerance: float = Tolerance.PITCH):
    """Set the desired pitch relative to the initial pitch.

    Args:
        offset: The change in pitch relative to the initial value.
        tolerance: The allowable error in the pitch. Defaults to Tolerance.PITCH.

    Returns:
        Result of the asynchronous relative-to-initial pitch setter.
    """
    return await _relative_to_initial_pitch(offset, tolerance)

# async def relative_to_current_pitch(offset: Callable[[], float], tolerance: float = Tolerance.PITCH):
#     """Set the desired pitch relative to the current pitch.

#     Args:
#         offset: A callable that returns the change in pitch.
#         tolerance: The allowable error in the pitch. Defaults to Tolerance.PITCH.

#     Returns:
#         Result of the asynchronous relative-to-current pitch setter.
#     """
#     return await _relative_to_current_pitch(offset, tolerance)

async def roll(target: float, tolerance: float = Tolerance.ROLL):
    """Set the desired roll.

    Args:
        target: The desired roll in degrees.
        tolerance: The allowable error in the roll. Defaults to Tolerance.ROLL.

    Returns:
        Result of the asynchronous roll setter.
    """
    return await _roll(target, tolerance)

async def roll_for_secs(target: float, duration: float, tolerance: float = Tolerance.ROLL):
    """Set the desired roll for a specific duration.

    Args:
        target: The desired roll in degrees.
        duration: The time in seconds to hold the roll.
        tolerance: The allowable error in the roll. Defaults to Tolerance.ROLL.

    Returns:
        Result of the asynchronous roll setter for a specific duration.
    """
    return await _roll_for_secs(target, duration, tolerance)

async def relative_to_initial_roll(offset: float, tolerance: float = Tolerance.ROLL):
    """Set the desired roll relative to the initial roll.

    Args:
        offset: The change in roll relative to the initial value.
        tolerance: The allowable error in the roll. Defaults to Tolerance.ROLL.

    Returns:
        Result of the asynchronous relative-to-initial roll setter.
    """
    return await _relative_to_initial_roll(offset, tolerance)

# async def relative_to_current_roll(offset: Callable[[], float], tolerance: float = Tolerance.ROLL):
#     """Set the desired roll relative to the current roll.

#     Args:
#         offset: A callable that returns the change in roll.
#         tolerance: The allowable error in the roll. Defaults to Tolerance.ROLL.

#     Returns:
#         Result of the asynchronous relative-to-current roll setter.
#     """
#     return await _relative_to_current_roll(offset, tolerance)

async def depth(target: float, tolerance: float = Tolerance.POSITION):
    """
    Set the desired depth.

    Args:
        target: The desired depth in meters.
        tolerance: The allowable error in the depth. Defaults to Tolerance.POSITION.

    Returns:
        Result of the asynchronous depth setter.
    """
    return await _depth(target, tolerance)

async def depth_for_secs(target: float, duration: float, tolerance: float = Tolerance.POSITION):
    """
    Set the desired depth for a specific duration.

    Args:
        target: The desired depth in meters.
        duration: The time in seconds to hold the depth.
        tolerance: The allowable error in the depth. Defaults to Tolerance.POSITION.

    Returns:
        Result of the asynchronous depth setter for a specific duration.
    """
    return await _depth_for_secs(target, duration, tolerance)

async def relative_to_initial_depth(offset: float, tolerance: float = Tolerance.POSITION):
    """
    Set the desired depth relative to the initial depth.

    Args:
        offset: The change in depth relative to the initial value.
        tolerance: The allowable error in the depth. Defaults to Tolerance.POSITION.

    Returns:
        Result of the asynchronous relative-to-initial depth setter.
    """
    return await _relative_to_initial_depth(offset, tolerance)

# async def relative_to_current_depth(offset: Callable[[], float], tolerance: float = Tolerance.POSITION):
#     """Set the desired depth relative to the current depth.

#     Args:
#         offset: A callable that returns the change in depth.
#         tolerance: The allowable error in the depth. Defaults to Tolerance.POSITION.

#     Returns:
#         Result of the asynchronous relative-to-current depth setter.
#     """
#     return await _relative_to_current_depth(offset, tolerance)

# async def position_n(target: float, tolerance: float = Tolerance.POSITION):
#     """Set the desired position in the northward direction.

#     Args:
#         target: The desired northward position in meters.
#         tolerance: The allowable error in the position. Defaults to Tolerance.POSITION.

#     Returns:
#         Result of the asynchronous northward position setter.
#     """
#     return await _position_n(target, tolerance)

# async def position_n_for_secs(target: float, duration: float, tolerance: float = Tolerance.POSITION):
#     """Set the desired position in the northward direction for a specific duration.

#     Args:
#         target: The desired northward position in meters.
#         duration: The time in seconds to hold the position.
#         tolerance: The allowable error in the position. Defaults to Tolerance.POSITION.

#     Returns:
#         Result of the asynchronous northward position setter for a specific duration.
#     """
#     return await _position_n_for_secs(target, duration, tolerance)

# async def relative_to_initial_position_n(offset: float, tolerance: float = Tolerance.POSITION):
#     """Set the desired position in the northward direction relative to the initial position.

#     Args:
#         offset: The change in position relative to the initial value.
#         tolerance: The allowable error in the position. Defaults to Tolerance.POSITION.

#     Returns:
#         Result of the asynchronous relative-to-initial northward position setter.
#     """
#     return await _relative_to_initial_position_n(offset, tolerance)

# async def relative_to_current_position_n(offset: Callable[[], float], tolerance: float = Tolerance.POSITION):
#     """Set the desired position in the northward direction relative to the current position.

#     Args:
#         offset: A callable that returns the change in position.
#         tolerance: The allowable error in the position. Defaults to Tolerance.POSITION.

#     Returns:
#         Result of the asynchronous relative-to-current northward position setter.
#     """
#     return await _relative_to_current_position_n(offset, tolerance)

# async def position_e(target: float, tolerance: float = Tolerance.POSITION):
#     """Set the desired position in the eastward direction.

#     Args:
#         target: The desired eastward position in meters.
#         tolerance: The allowable error in the position. Defaults to Tolerance.POSITION.

#     Returns:
#         Result of the asynchronous eastward position setter.
#     """
#     return await _position_e(target, tolerance)

# async def position_e_for_secs(target: float, duration: float, tolerance: float = Tolerance.POSITION):
#     """Set the desired position in the eastward direction for a specific duration.

#     Args:
#         target: The desired eastward position in meters.
#         duration: The time in seconds to hold the position.
#         tolerance: The allowable error in the position. Defaults to Tolerance.POSITION.

#     Returns:
#         Result of the asynchronous eastward position setter for a specific duration.
#     """
#     return await _position_e_for_secs(target, duration, tolerance)

# async def relative_to_initial_position_e(offset: float, tolerance: float = Tolerance.POSITION):
#     """Set the desired position in the eastward direction relative to the initial position.

#     Args:
#         offset: The change in position relative to the initial value.
#         tolerance: The allowable error in the position. Defaults to Tolerance.POSITION.

#     Returns:
#         Result of the asynchronous relative-to-initial eastward position setter.
#     """
#     return await _relative_to_initial_position_e(offset, tolerance)

# async def relative_to_current_position_e(offset: Callable[[], float], tolerance: float = Tolerance.POSITION):
#     """Set the desired position in the eastward direction relative to the current position.

#     Args:
#         offset: A callable that returns the change in position.
#         tolerance: The allowable error in the position. Defaults to Tolerance.POSITION.

#     Returns:
#         Result of the asynchronous relative-to-current eastward position setter.
#     """
#     return await _relative_to_current_position_e(offset, tolerance)

