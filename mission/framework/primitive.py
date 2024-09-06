import asyncio
import time
import subprocess
import os
from typing import Any
from conf.vehicle import is_mainsub

import shm

from typing import List
from termcolor import colored


async def zero_without_heading(pitch: bool = True, roll: bool = True):
    """Set navigation desires to match current values (except for heading).

    Arguments:
    pitch -- should the pitch desire be set to 0 instead of its current value
    roll  -- should the roll desire be set to 0 instead of its current value
    """
    desires, current = shm.navigation_desires, shm.kalman
    desires.depth.set(current.depth.get())
    desires.north.set(current.north.get())
    desires.east.set(current.east.get())
    desires.pitch.set(0 if pitch else current.pitch.get())
    desires.roll.set(0 if roll else current.roll.get())
    desires.speed.set(0)
    desires.sway_speed.set(0)


async def zero(pitch: bool = True, roll: bool = True):
    """Set navigation desires to match current values so the sub stops moving.

    Arguments:
    pitch -- should the pitch desire be set to 0 instead of its current value
    roll  -- should the roll desire be set to 0 instead of its current value
    """
    shm.navigation_desires.heading.set(shm.kalman.heading.get())
    await zero_without_heading(pitch, roll)


def disable_controller():
    """Disable the controller and every PID loop."""
    print("Disabling controller and all PID loops.")
    control = shm.settings_control
    control.enabled.set(0)
    control.heading_active.set(0)
    control.pitch_active.set(0)
    control.roll_active.set(0)
    control.velx_active.set(0)
    control.vely_active.set(0)
    control.depth_active.set(0)

def enable_controller():
    """Enable the controller and every PID loop."""
    print("Enabling controller and all PID loops.")
    control = shm.settings_control
    control.enabled.set(1)
    control.heading_active.set(1)
    control.pitch_active.set(1)
    control.roll_active.set(1)
    control.velx_active.set(1)
    control.vely_active.set(1)
    control.depth_active.set(1)

async def start_modules(modules: List[str]):
    """Starts all shm managed vision modules in `modules`."""

    for name in modules:
        if hasattr(shm.vision_modules, name):
            group = getattr(shm.vision_modules, name)
            group.set(True)
            print(
                f'Now enabling vision module: {colored(name, "green", attrs=["bold"])}')
        else:
            print(f'Module {name} not managed by shm.')


async def kill_modules(ignored_modules: List[str] = ['Record', 'Poster', 'AutoCalibrate']):
    """Stops all modules managed by a shm group except for those specified
    in `ignored_modules` which are turned on."""

    await start_modules(ignored_modules)

    all_modules = [getattr(shm.vision_modules, x) for (
        x, typ) in shm.vision_modules._fields if x not in ignored_modules]

    for module in all_modules:
        module.set(False)
        print(
            f'Now disabling vision module: {colored(module.__name__, "red", attrs=["bold"])}')
    
async def run_with_timeout(coroutine : Any, seconds: float):
    """Run a coroutine until it completes or sufficient time passes.

    Arguments:
    coroutine -- the coroutine to run
    seconds   -- the number of seconds after which to give up

    Returns True if the coroutine runs to completion and False if it times out
    """
    task = asyncio.create_task(coroutine)
    try:
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < seconds and not task.done():
            await asyncio.sleep(0.01)
        if task.done():
            return True
        task.cancel()
        await asyncio.sleep(0)
        await zero()
        return False
    except asyncio.CancelledError:
        task.cancel()
        await asyncio.sleep(0)
        await zero()

async def enable_downcam():
    if is_mainsub:
        os.system("ssh -o StrictHostKeychecking=no software@192.168.0.93 -p 2222 'sudo ip link set hydroc down'") == 0
        subprocess.run(['trogdor', 'stop', 'pingerd'])
        time.sleep(1)
        subprocess.run(['trogdor', 'start', 'zed'])

async def enable_hydrophones():
    if is_mainsub:
        subprocess.run(['trogdor', 'stop', 'zed'])
        time.sleep(1)
        os.system("ssh -o StrictHostKeychecking=no software@192.168.0.93 -p 2222 'sudo ip link set hydroc up'") == 0
        subprocess.run(['trogdor', 'start', 'pingerd'])
