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
from mission.combinator_framework.helpers import within_deadband
from mission.framework.contexts import PositionalControls
from mission.constants.sub import Tolerance

async def setter(target : float, desire_var : Any, current_var : Any,
        tolerance : float = 0, modulo_error : bool = False):
    """Set a desire and then await until it is achieved.

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
    while not within_deadband(target, current_var.get(), tolerance, modulo_error):
        await asyncio.sleep(0.01)

async def setter_for_secs(target : float, desire_var : Any, current_var : Any,
        duration : float, tolerance : float = 0, modulo_error : bool = False):
    """Set a desire and then unset it after some time has passed.
    
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
    init = current_var.get()
    await setter(target, desire_var, current_var, tolerance, modulo_error)
    await asyncio.sleep(duration)
    await setter(init, desire_var, current_var, tolerance, modulo_error)

async def relative_to_initial_setter(offset : float, desire_var : Any,
        current_var : Any, tolerance : float = 0, modulo_error : bool = False):
    """Set a desire relative to the current value of a variable.

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
        desire_var : Any, current_var : Any, tolerance : float = 0,
        modulo_error : bool = False):
    """Set and hold a desire at a changing offset from the value of a variable.

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

def generate_setters(desire_var : Any, current_var : Any,
        default_tolerance : float, modulo_error : bool = False,
        positional_controls : Optional[bool] = None):
    """Create setter functions specific to a given degree of freedom.

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

(heading, heading_for_secs, relative_to_initial_heading,
        relative_to_current_heading) = generate_setters(
        shm.navigation_desires.heading, shm.kalman.heading, Tolerance.HEAD,
        modulo_error=True)

(pitch, pitch_for_secs, relative_to_initial_pitch,
        relative_to_current_pitch) = generate_setters(
        shm.navigation_desires.pitch, shm.kalman.pitch, Tolerance.PITCH,
        modulo_error=True)

(roll, roll_for_secs, relatitve_to_initial_pitch,
        relative_to_current_pitch) = generate_setters(
        shm.navigation_desires.roll, shm.kalman.roll, Tolerance.ROLL,
        modulo_error=True)

(depth, depth_for_secs, relative_to_initial_depth,
        relative_to_current_depth) = generate_setters(
        shm.navigation_desires.depth, shm.kalman.depth, Tolerance.POSITION)

(position_n, position_n_for_secs, relative_to_initial_position_n,
        relative_to_current_position_n) = generate_setters(
        Scalar(shm.navigation_desires.north, dvl_scaling_factor),
        Scalar(shm.kalman.north, 1 / dvl_scaling_factor), Tolerance.POSITION,
        positional_controls=True)

(position_e, position_e_for_secs, relative_to_initial_position_e,
        relative_to_current_position_e) = generate_setters(
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

(velocity_x, velocity_x_for_secs, relative_to_initial_velocity_x,
        relative_to_current_velocity_x) = generate_setters(
        shm.navigation_desires.speed, shm.kalman.velx, Tolerance.VELOCITY,
        positional_controls=False)

(velocity_y, velocity_y_for_secs, relative_to_initial_velocity_y,
        relative_to_current_velocity_y) = generate_setters(
        shm.navigation_desires.sway_speed, shm.kalman.vely, Tolerance.VELOCITY,
        positional_controls=False)
