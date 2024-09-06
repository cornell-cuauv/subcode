#!/usr/bin/env python3
"""
DOES NOT WORK IN PRACTICE POSSIBLY DUE TO BAD IMPLEMENTATION OF ''go_to_position''
"""


import asyncio
import time
from mission import runner

from mission.framework.FPE.find import sway_search, rotate_search, find_harness
from mission.framework.FPE.position import center_on_object, approach, position_harness
from mission.framework.FPE.execute import go_around_square, ram, go_around, execute_harness
from mission.framework.FPE.task import FPE_Task
from mission.framework.FPE.object import QualGate, Buoy

from mission.framework.movement import velocity_y_for_secs, heading, relative_to_initial_heading
from mission.framework.position import move_x, move_y, go_to_position
from mission.framework.movement import relative_to_initial_heading, velocity_x_for_secs, velocity_y_for_secs, velocity_y, depth
from mission.framework.primitive import zero
import shm
    

async def main():


    print("Please type selected task: ")
    selected_task = input()

    if selected_task == 'record':
        with open('mission/missions/position_and_heading.csv', 'w') as f:
            f.close()
        # Record position and heading and depth every 1 second to csv file till q pressed
        while True:
            north_val = shm.kalman.north.get()
            east_val = shm.kalman.east.get()
            heading_val = shm.kalman.heading.get()
            depth_val = shm.kalman.depth.get()
            print("North: " + str(north_val) + " East: " + str(east_val) + " Heading: " + str(heading_val) + " Depth: " + str(depth_val))

            # input()
            with open('mission/missions/position_and_heading.csv', 'a') as f:
                f.write(str(north_val) + "," + str(east_val) + "," + str(heading_val) + "," + str(depth_val) + "\n")
                f.close()

            input()
    elif selected_task == 'replay':
        # Replay position and heading from csv file
        with open('mission/missions/position_and_heading.csv', 'r') as f:
            lines = f.readlines()
            for line in lines:
                north_val, east_val, heading_val, depth_val = line.split(",")
                print("step")
                await go_to_position(north=float(north_val), east=float(east_val), heading=float(heading_val), depth=float(depth_val), tolerance=0.2, heading_tolerance=5)


if __name__ == "__main__":
    runner.run(main(), "main")
