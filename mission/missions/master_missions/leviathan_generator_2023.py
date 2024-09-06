import shm

# Actual Leviathan Missions
from mission.missions.gate_2023 import Gate2023 as GateMission
from mission.missions.path_2023 import Path2023 as PathMission
from mission.missions.buoy_2023 import BuoyScoutInfantry as BuoyMission

# pre-coded enums
from mission.missions.master_missions.common import *
from mission.framework.movement import heading, velocity_x_for_secs

# movement for between missions
from mission.framework.dead_reckoning import (
    go_from_element_to_element,
    distance_from_element_to_element,
    heading_from_element_to_element)


async def generator():
    dead_reckoning = shm.dead_reckoning_virtual.get()
    # Only use go_from_element_to_element and
    # heading_from_element_to_element here

    # Gate
    # if dead_reckoning.gate_approach_in_pool:
    #     await go_from_element_to_element(SUB, GATE_APPROACH, 0.3)
    await heading(shm.master_mission_settings.gate_heading.get())
    yield GateMission(), INFINITE_TIME

    # Path and then Buoy
    # yield  PathMission(), INFINITE_TIME
    # only follow the path if there's a approach point. We want to stop 2 meters before
    # to allow anthony vision module to work its magic
    if dead_reckoning.buoy_approach_in_pool:
        distance = distance_from_element_to_element("gate", "buoy")
        await velocity_x_for_secs(0.3, max(0, distance - 2) / 0.3)


    yield BuoyMission(), INFINITE_TIME
    await velocity_x_for_secs(-.3, 5)

    yield END_OF_MISSION
