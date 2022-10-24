import asyncio
from typing import Any, Callable, Optional

import shm
from mission.framework.helpers import within_deadband
from mission.async_framework.contexts import PositionalControls


async def setter(target : float, desire_var : Any, current_var : Any,
        error : float = 0, modulo_error : bool = False) -> bool:
    desire_var.set(target)
    while not within_deadband(target, current_var.get(), error, modulo_error):
        await asyncio.sleep(0.01)
    return True


async def setter_for_secs(target : float, desire_var : Any, current_var : Any,
        duration : float, error : float = 0, modulo_error : bool = False) -> bool:
    init = current_var.get()
    await setter(target, desire_var, current_var, error, modulo_error)
    await asyncio.sleep(duration)
    await setter(init, desire_var, current_var, error, modulo_error)
    return True


async def relative_to_initial_setter(offset : float, desire_var : Any,
        current_var : Any, error : float = 0, modulo_error : bool = False) -> bool:
    target = current_var.get() + offset
    desire_var.set(target)
    while not within_deadband(target, current_var.get(), error, modulo_error):
        await asyncio.sleep(0.01)
    return True


async def relative_to_current_setter(offset : Callable[[], float],
        desire_var : Any, current_var : Any, error : float = 0,
        modulo_error : bool = False) -> bool:
    target = current_var.get() + offset()
    desire_var.set(target)
    while not within_deadband(target, current_var.get(), error, modulo_error):
        await asyncio.sleep(0.01)
        target = current_var.get() + offset()
        desire_var.set(target)
    return True


def generate_setters(desire_var : Any, current_var : Any,
        default_error : float, modulo_error : bool = False,
        positional_controls : Optional[bool] = None):

    async def s(target : float, error : float = default_error) -> bool:
        with PositionalControls(positional_controls):
            return await setter(target, desire_var, current_var, error,
                    modulo_error)

    async def sfs(target : float, duration : float,
            error : float = default_error) -> bool:
        with PositionalControls(positional_controls):
            return await setter_for_secs(target, desire_var, current_var,
                    duration, error, modulo_error)

    async def rtis(offset : float, error : float = default_error) -> bool:
        with PositionalControls(positional_controls):
            return await relative_to_initial_setter(offset, desire_var,
                    current_var, error, modulo_error)

    async def rtcs(offset : Callable[[], float],
            error : float = default_error) -> bool:
        with PositionalControls(positional_controls):
            return await relative_to_current_setter(offset, desire_var,
                    current_var, error, modulo_error)

    return (s, sfs, rtis, rtcs)

heading, heading_for_secs, relative_to_initial_heading, relative_to_current_heading = \
    generate_setters(shm.navigation_desires.heading, shm.kalman.heading, 3,
            modulo_error=True)

pitch, pitch_for_secs, relative_to_initial_pitch, relative_to_current_pitch = \
    generate_setters(shm.navigation_desires.pitch, shm.kalman.pitch, 10,
            modulo_error=True)

roll, roll_for_secs, relatitve_to_initial_pitch, relative_to_current_pitch = \
    generate_setters(shm.navigation_desires.pitch, shm.kalman.pitch, 10,
            modulo_error=True)

depth, depth_for_secs, relative_to_initial_depth, relative_to_current_depth = \
    generate_setters(shm.navigation_desires.depth, shm.kalman.depth, 0.07)

velocity_x, velocity_x_for_secs, relative_to_initial_velocity_x, relative_to_current_velocity_x = \
    generate_setters(shm.navigation_desires.speed, shm.kalman.velx, 0.05,
            positional_controls=False)

velocity_y, velocity_y_for_secs, relative_to_initial_velocity_y, relative_to_current_velocity_y = \
    generate_setters(shm.navigation_desires.sway_speed, shm.kalman.vely, 0.05,
            positional_controls=False)

position_n, position_n_for_secs, relative_to_initial_position_n, relative_to_current_position_n = \
    generate_setters(shm.navigation_desires.north, shm.kalman.north, 0.05,
            positional_controls=True)

position_e, position_e_for_secs, relative_to_initial_position_e, relative_to_current_position_e = \
    generate_setters(shm.navigation_desires.east, shm.kalman.east, 0.05,
            positional_controls=True)