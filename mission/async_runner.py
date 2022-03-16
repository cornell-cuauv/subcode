#!/usr/bin/env python3

import argparse
import os
import time
import sys
import signal as _signal
import asyncio
from typing import Coroutine, Any

import shm
from auvlog.client import log
from misc.utils import register_exit_signals
from mission.framework.task import Task
from mission.async_framework.primitive import zero

def run(mission : Coroutine[Any, Any, None]):
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-record", help="Don't record any logs", action="store_true")
    args = parser.parse_args()

    logger = log.mission.main

    # Save running vision module state.
    vision_state = shm.vision_modules.get()
    print('Saved running vision module state. Will restore on Ctrl-C or mission completion.')

    # Save control settings state.
    control_settings = shm.settings_control.get()
    navigation_settings = shm.navigation_settings.get()

    # Ensure only one mission can run at a time.
    LOCK_NAME = ".mission_lock"
    lock_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), LOCK_NAME)
    try:
        os.mkdir(lock_dir)
        # Inform control helm that the current user is running a mission.
        with open('/home/software/cuauv/workspaces/worktrees/master/control/control_helm2/activity/mission.csv', 'w') as f:
            f.write(os.getenv('AUV_ENV_ALIAS'))
    except OSError:
        print("A MISSION IS ALREADY RUNNING! Aborting...")
        print("If I am mistaken, delete %s or check permissions" % lock_dir)
        sys.exit(1)

    # Store the time.
    start_time = time.time()

    def release_lock():
        os.rmdir(lock_dir)
        # Inform control helm that the no mission is currently running.
        with open('/home/software/cuauv/workspaces/worktrees/master/control/control_helm2/activity/mission.csv', 'w') as f:
            f.truncate(0)

    def cleanup():
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(zero())
        except RuntimeError:
            asyncio.run(zero())
        release_lock()
        shm.vision_modules.set(vision_state)
        shm.settings_control.set(control_settings)
        shm.navigation_settings.set(navigation_settings)

        end_time = time.time()
        duration = end_time - start_time
        print("Mission finished in %i seconds!" % (duration))

    global has_caught_sigint
    has_caught_sigint = False
    def exit_handler(signal, frame):
        global has_caught_sigint
        if not has_caught_sigint and signal == _signal.SIGINT:
            has_caught_sigint = True
            print('Caught Ctrl-C. Mission paused. Ctrl-C again to quit, enter to resume.')
            while True:
                ch = sys.stdin.readline()
                has_caught_sigint = False
                print('Resuming mission!')
                return
        else:
            cleanup()
            sys.exit(0)

    register_exit_signals(exit_handler)

    asyncio.run(mission)

    cleanup()

async def run_task(task : Task):
    while not task.has_ever_finished:
        start_time = time.time()
        task()
        duration = time.time() - start_time
        await asyncio.sleep(max(1 / 60 - duration, 0))
