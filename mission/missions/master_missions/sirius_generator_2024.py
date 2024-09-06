import shm
import time

# pre-coded enums
from mission.framework.base import AsyncBase
from mission.missions.master_missions.common import *
from mission.framework.movement import *
from mission.framework.position import *
from mission.framework.dead_reckoning import *
from mission.framework.primitive import *
from mission.framework.actuation import *

from mission.missions.buoy_new_sirius import goAroundBuoy
from mission.missions.barrel_roll_sam import BarrelRoll
import asyncio

# movement for between missions
from mission.framework.dead_reckoning import (
    go_from_element_to_element,
    distance_from_element_to_element,
    heading_from_element_to_element)


from mission.framework.logger import mission_logger
from mission.framework.master_common import MASTER_LOGGER

SIRIUS_LOGGER = getattr(mission_logger, ":::: Sirius 2024 ::::")

def sirius_print(msg):
    if True:
        MASTER_LOGGER(msg)
    else:
        SIRIUS_LOGGER(msg)

class ArbMission(AsyncBase):
    def __init__(self, name, task):
        self.mission_name = name
        self.first_task = task

async def heading_spin():
    for i in range(7):
        await relative_to_initial_heading(120, tolerance=10)

async def generator(initial_heading):

    buoy_priority = False

    sirius_print('### TRANSFORMING DEAD TO REAL ###')
    sirius_print(f'using initial_heading {initial_heading}')
    initial_ne = (shm.kalman.north.get(), shm.kalman.east.get())
    transform_coords_to_real_space(initial_heading)

    sirius_print('### STARTING CALIBRATION WHILE LOOP ###')

    while True:
        curr_depth = shm.kalman.depth.get()
        sirius_print(f'Depth Reading: {curr_depth}')
        if abs(curr_depth) < 0.125:
            sirius_print('### CALIBRATION COMPLETE ###')
            break
        recommended_offset = curr_depth + shm.depth.offset_mainsub.get()
        shm.depth.offset_mainsub.set(recommended_offset)
        await asyncio.sleep(5)

    yield ArbMission(
        "depth(1.4)", 
        depth(1.4)
    ), 10

    yield ArbMission(
        "heading(initial_heading)", 
        heading(initial_heading)
    ), 10
    
    yield ArbMission(
        "asyncio.sleep(2)", 
        asyncio.sleep(2)
    ), 3
    
    sirius_print('### GO THROUGH GATE ###')
    yield ArbMission(
        "move_xy_from_initial(initial_heading, initial_ne, (8, 0))", 
        move_xy_from_initial(initial_heading, initial_ne, (8, 0))
    ), 30

    yield ArbMission(
        "go_to_element('gate_approach')", 
        go_to_element('gate_approach')
    ), 15

    yield ArbMission(
        "heading_spin()", 
        heading_spin()
    ), 30

    if not buoy_priority:
        sirius_print('### DEAD RECKON TO OCTAGON ###')
        yield ArbMission(
            "go_to_element('octagon')", 
            go_to_element('octagon')
        ), 80

        yield ArbMission(
            "depth(.5)", 
            depth(.5)
        ), 5

        shm.switches.soft_kill.set(1)
        yield ArbMission(
            "asyncio.sleep(15)", 
            asyncio.sleep(15)
        ), 11

        shm.switches.soft_kill.set(0)
        yield ArbMission(
            "depth(1.4)", 
            depth(1.4)
        ), 5

        yield ArbMission(
            "go_to_element('bin')".
            go_to_element('bin')
        ), 40

        yield ArbMission(
            "heading(heading_of_element('bin'))".
            heading(heading_of_element('bin'))
        ), 10

        yield ArbMission(
            "sleep(5)",
            asyncio.sleep(5)
        ), 6

        for i in range(5):
            yield ArbMission(
                "fire_dropper()",
                fire_dropper()
            ), 10

    sirius_print('### PREPARE FOR BUOY ###')
    yield ArbMission(
        "go_to_element('buoy_approach')", 
        go_to_element('buoy_approach')
    ), 30

    yield ArbMission(
        "heading(heading_to_element('buoy'))", 
        heading(heading_to_element('buoy'))
    ), 5
    
    sirius_print('### GO AROUND BUOY ###')
    #yield goAroundBuoy(), 180

    buoy_ne = (shm.kalman.north.get(), shm.kalman.east.get())
    buoy_heading = shm.kalman.heading.get()

    yield ArbMission(
        "Move XY Bottom Right", 
        move_xy_from_initial(
            initial_heading=buoy_heading,
            initial_ne=buoy_ne,
            delta=(0, 2)
        )
    ), 10
    
    yield ArbMission(
        "Move XY Top Right", 
        move_xy_from_initial(
            initial_heading=buoy_heading,
            initial_ne=buoy_ne,
            delta=(4, 2)
        )
    ), 10
    
    yield ArbMission(
        "Move XY Top Left", 
        move_xy_from_initial(
            initial_heading=buoy_heading,
            initial_ne=buoy_ne,
            delta=(4, -2)
        )
    ), 10

    yield ArbMission(
        "Move XY Bottom Left", 
        move_xy_from_initial(
            initial_heading=buoy_heading,
            initial_ne=buoy_ne,
            delta=(0, -2)
        )
    ), 10

    yield ArbMission(
        "Move XY Bottom", 
        move_xy_from_initial(
            initial_heading=buoy_heading,
            initial_ne=buoy_ne,
            delta=(0, 0)
        )
    ), 10

    yield ArbMission(
        "point at buoy",
        heading(heading_to_element('buoy'))
    ), 10

    yield goAroundBuoy(), 60

    if buoy_priority:
        sirius_print('### DEAD RECKON TO OCTAGON ###')
        yield ArbMission(
            "go_to_element('octagon')", 
            go_to_element('octagon')
        ), 60
        
        yield ArbMission(
            "depth(.5)", 
            depth(.5)
        ), 5

        shm.switches.soft_kill.set(1)
        yield ArbMission(
            "asyncio.sleep(10)", 
            asyncio.sleep(10)
        ), 11

        shm.switches.soft_kill.set(0)
        yield ArbMission(
            "depth(1.4)", 
            depth(1.4)
        ), 5

    sirius_print('### PREPARE FOR BARREL ROLL ###')
    yield ArbMission(
        "go_to_element('gate_approach')", 
        go_to_element('gate_approach')
    ), 60

    yield BarrelRoll(3), 60

    sirius_print('### CELEBRATE 🎉 ###')
    yield END_OF_MISSION
