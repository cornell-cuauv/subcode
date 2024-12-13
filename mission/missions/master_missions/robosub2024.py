#!/usr/bin/env python3

import os
import shm
import sys
import time

import conf.vehicle as vehicle_conf
import mission.framework.dead_reckoning as dead

#from mission.missions.master_missions.leviathan_generator import generator as leviathan
from mission.missions.master_missions.sirius_generator_2024 import generator as sirius

from mission.core.master_common import MasterMission
import asyncio


def initialize_mission_dummy(is_mainsub):
    time.sleep(2)
    input("Press enter when the sub's heading is correct...")
    initial_heading = shm.kalman.heading.get()
    return initial_heading


def initialize_mission(is_mainsub):
    # initialize dead reckoning if on mainsub
    # else, initialize intial gate heading!
    if is_mainsub:
        print("detected mainsub")
        _ = input(
            'ensure sub is pointed in the same direction as specified in the dead reckoning tool. [enter]')

        initial_heading = shm.kalman.heading.get()
        while input(f'\tis heading = {initial_heading:5.2f} correct? [y/n]') != "y":
            initial_heading = shm.kalman.heading.get()
        print('\n\n')
        while True:
            print('Transforming Dead Reckoning Coordinates. Looks good? [y/n]:')
            dead.transform_coords_to_real_space(initial_heading)

            for element in dead.elements:
                blanks = ' ' * max(0, 25 - len(element))
                print(
                    f'\t element {element} with status ... {blanks}{"PRESENT" if dead.check_element_validity(element) else "ABSENT"}')

            if input() == 'y':
                break
    else:
        print("detected minisub")
        _ = input(
            'ensure sub is pointed towards the gate [enter]')

        initial_heading = shm.kalman.heading.get()
        while input(f'\tis heading = {initial_heading:5.2f} correct? [y/n]') != "y":
            initial_heading = shm.kalman.heading.get()
        shm.master_mission_settings.gate_heading.set(initial_heading)
        print('\n\n')
 
    # calibrate depth
    print('\n\n')
    while True:
        curr_depth = shm.kalman.depth.get()
        if input(f'The current depth is {curr_depth}. Correct? [y/n]') == 'y':
            break

        if vehicle_conf.is_mainsub:
            recommended_offset = curr_depth + shm.depth.offset_mainsub.get()
        else:
            recommended_offset = curr_depth + shm.depth.offset_minisub.get()

        print(f'Recommended offset is {recommended_offset}.')

        if vehicle_conf.is_mainsub:
            shm.depth.offset_mainsub.set(recommended_offset)
        else:
            shm.depth.offset_minisub.set(recommended_offset)

        time.sleep(4)

if __name__ == '__main__':
    is_mainsub = vehicle_conf.is_mainsub 

    mission = MasterMission(
        prerun_check = lambda: initialize_mission_dummy(is_mainsub),
        generator = sirius,
        submerge_depth = 1
    )

    mission_name = "SiriusMasterMission" if is_mainsub else "PolarisMasterMission"
    mission.run(mission_name)