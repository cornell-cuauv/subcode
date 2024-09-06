#!/usr/bin/env python3

"""
This file acts as the main master mission file which should be directly run to
start the master mission on either sub. It first initializes the dead
reckoning system and then calibrates the sub's depth. Finally, it runs either
Polaris's or Leviathan's individual master mission as found in
missions/master_missions/polaris_generator.py and
missions/master_missions/leviathan_generator.py, respectively.

This functionality is not located in the mission_common.py because the
details of how it interfaces with dead reckoning and shm settings, and the
names of the two subs may change from year to year.
"""

import os
import shm
import sys
import time

import conf.vehicle as vehicle_conf
import mission.framework.dead_reckoning as dead_reckoning
from mission.missions.master_missions.dummy_generator import generator as dummy

from mission.framework.master_common import MasterMission

def initialize_dead_reckoning():
    """"When on Mainsub, transform the coordinates of mission elements from the coordinate space
    used in the dead reckoning mapping tool to those of the real world, by assuming the real sub's
    location and direction in the water match those shown in the mapping tool."""

    input('Ensure the sub is facing in the same direction as specified in the dead reckoning map. [enter]')
    initial_heading = shm.kalman.heading.get()
    print('\n\n')
    while True:
        print('Transforming Dead Reckoning Coordinates. Look good? [y/n] ')
        dead_reckoning.transform_coords_to_real_space(initial_heading)

        # Print out which mission elements were marked via the mapping tool as being present in the pool,
        # as a final sanity check. During competition, they should probably all appear "PRESENT".
        for element in dead_reckoning.elements:
            blanks = ' ' * max(0, 25 - len(element))
            status = "PRESENT" if dead_reckoning.check_element_validity(element) else "ABSENT"
            print(f'\tElement {element} with status ... {blanks}{status}')

        if input() == 'y':
            break

def initialize_direction():
    """On Minisub, save the direction to the sub is currently facing so it can return to this direction
    after starting its run (and after the coin flip). If unchanged from 2023, the sub should be facing
    in the direction it will have to face once in the water in order to reach the gate."""

    input('Ensure the sub is facing in direction it will have to face once in the water to reach the gate. [enter]')
    initial_heading = shm.kalman.heading.get()
    shm.master_mission_settings.gate_heading.set(initial_heading)

def calibrate_depth():
    """Chooses and sets the depth offset such that the depth reading in the kalman group is acceptably
    close to zero."""

    while True:
        curr_depth = shm.kalman.depth.get()
        if input(f'The current depth is {curr_depth}. Correct? [y/n]') == 'y':
            break

        offset_var = shm.depth.offset_mainsub if vehicle_conf.is_mainsub else shm.depth.offset_minisub
        curr_offset = offset_var.get()
        recommended_offset = curr_depth + curr_offset
        print(f'the recommended depth offset is {recommended_offset}.')
        offset_var.set(recommended_offset)

        time.sleep(4)

def initialize_mission(is_mainsub):
    if is_mainsub:
        print("Detected Mainsub")
        initialize_dead_reckoning()
    else:
        print("Detected minisub")
        initialize_direction()
        
    print('\n\n')
    calibrate_depth()

## Driver code ##

if __name__ == '__main__':
    is_mainsub = vehicle_conf.is_mainsub 

    mission = MasterMission(
        prerun_check= lambda: initialize_mission(is_mainsub),   # initialization script. the one provided is pretty adequate.
        generator= dummy if is_mainsub else dummy,              # choose your generator (scripted like this)
        submerge_depth=3.0                                      # initial depth do you want to submerge to.
    )

    mission_name = "PolarisMasterMission" if is_mainsub else "LeviathanMasterMission" # name is for logging purposes only.
    mission.run(mission_name)
