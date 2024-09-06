#!/usr/bin/env python3
"""
   _______    _     _      _________         __        _     _  __          __
  /  _____\  | \   / |    /  _    _ \       /  \      | \   / | \ \        / /
  | |        | |   | |   /  | \__  \ \     / /\ \     | |   | |  \ \      / /
  | |        | |   | |  | / |    \  | |   / /  \ \    | |   | |   \ \    / /
  | |        | |   | |  | |  \__  | / |  / /    \ \   | |   | |    \ \  / /
  | |______  | |___| |   \ \_   \_|  /  / /      \ \  | |___| |     \ \/ /
  \_______/  \_______/    \_________/  /_/        \_\ \_______/      \__/


   ___       __                 __
  / _ \___  / /  ___  ___ __ __/ /
 / , _/ _ \/ _ \/ _ \(_-</ // / _ \ 
/_/|_|\___/_.__/\___/___/\_,_/_.__/

A master mission designed for AsyncBase Missions.
"""

import os
import shm
import time
import enum
import inspect
import asyncio
import traceback
import signal

from typing import Callable, AsyncGenerator, Tuple, Any

from mission.framework.logger import mission_logger
from mission.framework.base import AsyncBase
from mission.framework.movement import depth, heading
from mission.framework.primitive import zero, enable_controller, disable_controller, kill_modules
from mission.constants.config import NONSURFACE_MIN_DEPTH as MIN_DEPTH
import shm.master_mission_settings

# true if not running in simulator
DRY_RUN = False

IS_POOL = os.environ['CUAUV_LOCALE'] != 'simulator'
MASTER_LOGGER = getattr(mission_logger, ":::: MasterMission ::::")

class TaskExecutionFailure(enum.Enum):
    HARDKILL = 0
    TIMEOUT = 1
    UNPRIVELAGED_SURFACE = 2
    RUNTIME_EXCEPTION = 3
    DEACTIVATED = 4

# Utility functions used by the master mission
PROCESS_PID = os.getpid()

def get_process_pid():
    global PROCESS_PID
    return PROCESS_PID

def get_active_pid():
    return shm.master_mission_settings.active_pid.get()

def is_active_pid():
    return get_process_pid() == get_active_pid()

def _master_print(msg):
    MASTER_LOGGER(msg)

async def _cancel_background_tasks():
    """Cancels all background tasksk to prevent them from interfering with new mission."""

    _master_print("Executing cancel_background_task()")
    for t in asyncio.all_tasks():
        if 'Task-1' == t.get_name():
            _master_print(f'\tRunning tasks: Master Mission')
        elif 'block_surface_thread()' in f'{t}':
            _master_print(f'\tRunning tasks: block_surface_thread()')
        else:
            _master_print(
                f'\tRemoving dangling task {t.get_name()}')
            t.cancel()
            await asyncio.sleep(0)


async def _block_surface_thread():
    """Prevent all non-surfacing tasks from surfacing. If the task attempts
    to surface i.e. go above MIN_DEPTH without setting a flag, this function
    will terminate that task.

    Criteria for termination:
        1. navigation_desires < MIN_DEPTH 
        2. depth < MIN_DEPTH * 2
    """
    while True:
        depth = shm.kalman.depth.get()
        depth_desire = shm.navigation_desires.depth.get()

        if not shm.master_mission_settings.can_surface.get() \
                and (depth_desire <= MIN_DEPTH and depth <= MIN_DEPTH * 2):
            shm.navigation_desires.depth.set(MIN_DEPTH * 2)
            _master_print(
                f'WARNING. Task attempted to rise above min depth {MIN_DEPTH}. You have lost mission privilages')
            await _cancel_background_tasks()
        await asyncio.sleep(1/30)


async def _run_master_task(mission: AsyncBase, timeout_in_seconds: int):
    """Implements the following:
        1. error handling
        2. surface blocking 
        3. reset vision modules
        4. cleanup
    """

    # start block surface task
    # block_surface_future = asyncio.create_task(_block_surface_thread())

    # ensure all vision modules are turned off
    await kill_modules()

    # figure out how long the mission gets to run
    mission_hard_end_time = time.time() + timeout_in_seconds

    # execute mission

    hardkill_flag = False
    timeout_flag = False
    surface_flag = False
    exception_flag = False
    deactivated_flag = False

    if DRY_RUN:
        _master_print("Dry Run Enabled!")
        disable_controller()
    else:
        enable_controller()

    start = time.time()
    mission_name = mission.mission_name if hasattr(mission, 'mission_name') else mission.__class__.__name__
    header = f'----= Mission: {mission_name} =----'
    _master_print("")
    _master_print(header)
    _master_print(
        f'Executing with timeout {timeout_in_seconds:.2f} seconds...'
    )
    try:
        shm.master_mission_settings.can_surface.set(False)
        fut = asyncio.create_task(mission.run_headless())
        while not fut.done():
            # stop if AUV is hardkilled
            if shm.switches.hard_kill.get() == 1:
                fut.cancel()
                await asyncio.sleep(0)
                hardkill_flag = True
                break

            if not is_active_pid():
                fut.cancel()
                await asyncio.sleep(0)
                deactivated_flag = True
                break

            # stop if time is done
            if time.time() > mission_hard_end_time:
                fut.cancel()
                await asyncio.sleep(0)
                timeout_flag = True
                break

            await asyncio.sleep(0.01)

    except Exception as _:
        exception_flag = True
        _master_print(
            f'Runtime exception:\n\n{traceback.format_exc()}\n')

    finally:
        if fut.cancelled() and not exception_flag and not hardkill_flag and not timeout_flag and not deactivated_flag:
            surface_flag = True

        await _cancel_background_tasks()

        if fut.cancelled():
            await zero()
            await asyncio.sleep(1)
        
        if not DRY_RUN:
            enable_controller()

        # block_surface_future.cancel()
        await asyncio.sleep(0)

        end = time.time()

        if hardkill_flag:
            _master_print(
                f'Hard killed in {end - start:.2f} seconds!'
            )

            _master_print("-" * len(header))
            _master_print("")
            
            return TaskExecutionFailure.HARDKILL

        elif timeout_flag:
            _master_print(
                f'Timed out in {end - start:.2f} seconds!'
            )

            _master_print("-" * len(header))
            _master_print("")

            return TaskExecutionFailure.TIMEOUT

        elif surface_flag:
            _master_print(
                f'Unprivelaged surfaced at {end - start:.2f} seconds!'
            )

            _master_print("-" * len(header))
            _master_print("")
            
            return TaskExecutionFailure.UNPRIVELAGED_SURFACE

        elif exception_flag:
            _master_print(
                f'Raised Exception at {end - start:.2f} seconds!'
            )

            _master_print("-" * len(header))
            _master_print("")
            
            return TaskExecutionFailure.RUNTIME_EXCEPTION

        elif deactivated_flag:
            _master_print(
                f'Deactivated at {end - start:.2f} seconds!'
            )

            _master_print("-" * len(header))
            _master_print("")
            
            return TaskExecutionFailure.DEACTIVATED

        else:
            _master_print(
                f'Finished in {end - start:.2f} seconds!'
            )

            _master_print("-" * len(header))
            _master_print("")

            return fut.result()


class MasterMission(AsyncBase):
    """The Master Mission is a separation of concerns. It handles processes that 
    are relevant to the entire autonomous run and not just a single mission.

    In short, the master mission does the following:
      1. Chains together individual missions
      2. Handles potential errors i.e. crashes/timeouts/blocks surfacing 
      3. The master mission will turn off vision modules before running each 
        mission, but it is the responsibility of the mission writer to turn on
        any modules they want

    The mission itself should handle for getting to the task. Getting to the task
    is included in the timeout_in_seconds time.

    The master mission should be run in a screen so it can be detatched. 
    """

    def __init__(self,
                 prerun_check: Callable[[], None],
                 generator: Callable[[], AsyncGenerator[Tuple[AsyncBase, int], Any]],
                 submerge_depth: float
                 ):
        """
        ## Params:

            - prerun_check: Once called, it should prompt the user to verify 
            all mission settings (ensuring hardkill should not be considered as a 
            part of the prerun checklist.)

            - generator: the generator function (that yields all AsyncBase missions).

             - submerge_depth: the initial submerge.
        """
        _master_print(f"Master Mission Initializing with PID {get_process_pid()} (previously {get_active_pid()})")
        shm.master_mission_settings.active_pid.set(
            get_process_pid()
        )

        assert callable(prerun_check)
        # assert isinstance(generator, AsyncGenerator[Tuple[AsyncBase, int], Any])
        _master_print("Mission passed initialization check.")

        self.generator = generator
        self.submerge_depth = submerge_depth
        self.first_task = self.hardkill_logic()

        self.initial_heading = prerun_check()

    async def hardkill_logic(self):
        if IS_POOL:
            _master_print("Ensure sub is hardkilled.")

            while shm.switches.hard_kill.get() == 0:
                if not is_active_pid():
                    _master_print("Mission is no longer active Master Mission!")
                    return None

                await asyncio.sleep(0.05)
            
            _master_print("Hardkill detected!")
            _master_print(
                "Mission setup complete. Unplug ethernet, dummy plug, and unkill.")

            _master_print("Waiting for unkill.")

            while shm.switches.hard_kill.get() == 1:
                if not is_active_pid():
                    _master_print("Mission is no longer active Master Mission!")
                    return None

                await asyncio.sleep(0.05)

            _master_print("Unkill Received!")

            _master_print("3...")
            await asyncio.sleep(1)

            _master_print("2...")
            await asyncio.sleep(1)

            _master_print("1...")
            await asyncio.sleep(1)

            _master_print("GLHF")

            await zero()
            shm.switches.soft_kill.set(0)
        else:
            _master_print("Simulator detected. Skipping hardkill logic.")
        # below is edited
        if not DRY_RUN:
            enable_controller()
            shm.switches.soft_kill.set(0)
        # return self.submerge()
        return self.run_all_tasks()

    # async def submerge(self):
    #     if not DRY_RUN:
    #         _master_print("within submerge function")
    #         enable_controller()
    #         shm.switches.soft_kill.set(0)
    #         await depth(0.7)
    #         # await heading(self.angle)
            
    #     _master_print("moved to depth. About to run all tasks")
    #     return self.run_all_tasks()

    async def run_all_tasks(self):
        _master_print('reached run_all_tasks')

        generator = self.generator(self.initial_heading)
        result = None

        while True:
            mission, timeout_in_seconds = await generator.asend(result)
            if mission is None:
                return self.end_run()
            
            result = await _run_master_task(mission, timeout_in_seconds)

            if result == TaskExecutionFailure.HARDKILL:
                _master_print('Received hardkill signal. Resetting Mission.')
                return self.hardkill_logic()
            elif result == TaskExecutionFailure.TIMEOUT:
                _master_print('Task timed out. Better luck next time.')
            elif result == TaskExecutionFailure.UNPRIVELAGED_SURFACE:
                _master_print('Task was canceled because it tried to surface.')
            elif result == TaskExecutionFailure.RUNTIME_EXCEPTION:
                _master_print('Moving to next task')
            elif result == TaskExecutionFailure.DEACTIVATED:
                _master_print('Mission is no longer active Master Mission!')
                return None
            else:
                _master_print(f'Task Suceeded!!!!!!!!')


    async def end_run(self):
        _master_print('Ending Run:) Surfacing, sofkilling, and activating *mans')
        if IS_POOL:
            await depth(0.5, 0.5)
            shm.switches.soft_kill.set(1)
            shm.deadman_settings.enabled.set(True)
            await asyncio.sleep(5)
        else:
            await depth(0)

        return self.hardkill_logic()

