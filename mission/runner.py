#!/usr/bin/env python3

import os
import time
import sys
import glob
import subprocess
import signal as _signal
import asyncio
import traceback
from typing import Coroutine, Any

import shm
from auvlog.client import log
from misc.utils import register_exit_signals
from mission.combinator_framework.task import Task
from mission.framework.primitive import zero

has_caught_sigint = False
def run(mission : Coroutine[Any, Any, None], name : str):
    # Create an auvlog client.
    logger = log.mission.main

    # Get new log directory name.
    cuauv_log = os.environ['CUAUV_LOG']
    initially_recording = shm.vision_modules.Record.get()

    # Get the run number.
    # This looks for other log directories named after this same mission, which
    # correspond to previous runs. By taking the numbers off the ends of their
    # names, the number belonging to this run can be deduced.
    try:
        dirs = glob.glob(os.path.join(cuauv_log, 'current', name) +
                '[0-9][0-9]*')
        nums = [int(os.path.basename(dir_name)[len(name):]) for dir_name in
                dirs]
        highest_run_num = max([1] + nums)
    except subprocess.CalledProcessError as ls_except:
        if ls_except.returncode == 2:
            highest_run_num = 0
        else:
            raise ls_except
    this_run_num = highest_run_num + 1
    log_path = "%s/current/%s%02d" % (cuauv_log, name, this_run_num)

    # Make the log directory.
    subprocess.call("mkdir -p %s" % log_path, shell=True)

    # Record shmlog.
    cmd = "auv-shmlogd --filename=%s/shmlog.shmlog" % log_path
    shmlog_proc = subprocess.Popen("exec " + cmd, stdout=subprocess.PIPE,
            shell=True)

    # Store the time.
    start_time = time.time()

    # Set active mission.
    active_mission = shm.active_mission.get()
    active_mission.active = True
    active_mission.log_path = bytes(log_path, encoding="utf-8")
    active_mission.name = bytes(name, encoding="utf-8")
    active_mission.start_time = start_time
    shm.active_mission.set(active_mission)

    # Save running vision module state.
    vision_state = shm.vision_modules.get()
    logger("Saved running vision module state. Will restore on Ctrl-C or"
            " mission completion.", copy_to_stdout=True)

    # Save control settings state.
    control_settings = shm.settings_control.get()
    navigation_settings = shm.navigation_settings.get()

    # Ensure only one mission can run at a time.
    LOCK_NAME = ".mission_lock"
    lock_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),
            LOCK_NAME)
    try:
        os.mkdir(lock_dir)
        # Inform control helm that the current user is running a mission.
        with open("/home/software/cuauv/workspaces/worktrees/master/control/"
                "control_helm2/activity/mission.csv", 'w') as f:
            f.write(os.getenv('AUV_ENV_ALIAS'))
    except OSError:
        logger("A MISSION IS ALREADY RUNNING! Aborting...",
                copy_to_stdout=True)
        logger("If I am mistaken, delete %s or check permissions" % lock_dir,
                copy_to_stdout=True)
        sys.exit(1)

    def release_lock():
        os.rmdir(lock_dir)
        # Inform control helm that the no mission is currently running.
        with open("/home/software/cuauv/workspaces/worktrees/master/control/"
                "control_helm2/activity/mission.csv", 'w') as f:
            f.truncate(0)

    def cleanup():
        try:
            loop = asyncio.get_running_loop()
            for task in asyncio.all_tasks():
                task.cancel()
            loop.create_task(zero())
        except RuntimeError:
            asyncio.run(zero())
        release_lock()
        shm.vision_modules.set(vision_state)
        shm.settings_control.set(control_settings)
        shm.navigation_settings.set(navigation_settings)

        end_time = time.time()
        duration = end_time - start_time
        logger("Mission finished in %i seconds!" % (duration),
                copy_to_stdout=True)

        # Unset active mission.
        active_mission = shm.active_mission.get()
        active_mission.active = False
        shm.active_mission.set(active_mission)

    global has_caught_sigint
    has_caught_sigint = False
    def exit_handler(signal, frame):
        global has_caught_sigint
        if not has_caught_sigint and signal == _signal.SIGINT:
            has_caught_sigint = True
            logger("Caught Ctrl-C. Mission paused. Ctrl-C again to quit, enter"
                    " to resume.", copy_to_stdout=True)
            while True:
                ch = sys.stdin.readline()
                has_caught_sigint = False
                logger("Resuming mission!", copy_to_stdout=True)
                return
        else:
            cleanup()
            sys.exit(0)
    register_exit_signals(exit_handler)

    try:
        asyncio.run(mission)
    except RuntimeError:
        print("Runtime error -- cleaning up.")
        traceback.print_exc()
    finally:
        cleanup()

async def run_task(task : Task):
    while not task.has_ever_finished:
        start_time = time.time()
        task()
        duration = time.time() - start_time
        await asyncio.sleep(max(1 / 60 - duration, 0))
