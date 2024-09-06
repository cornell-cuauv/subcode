# Generic imports
import os
import subprocess
import sys
import shm
from mission.framework.base import AsyncBase
from mission.framework.dead_reckoning import go_to_element, heading_to_element
from mission.framework.movement import heading
from mission.framework.position import move_x

# Actual missions
from mission.missions.gate_2023 import Gate2023 as GateMission
from mission.missions.path_2023 import Path2023 as PathMission
from mission.missions.buoy_2023 import BuoyScoutInfantry as BuoyMission
from mission.missions.bins_2023 import JoshBins as BinsMission
from mission.missions.decision_point_2023 import DecisionPoint2023 as DecisionPoint
from mission.missions.track_pinger_2023 import TrackPinger2023 as TrackPinger
from mission.missions.torpedoes_2023 import Torpedoes2023 as TorpedoesMission
from mission.missions.octagon_2023 import OctagonSurface2023 as OctagonMission


# To avoid any heat-of-the-moment spelling errors
GATE_APPROACH = 'gate_approach'
GATE = 'gate'
BUOY_APPROACH = 'buoy_approach'
BUOY = 'buoy'
BINS_APPROACH = 'earth_bin_approach'
BINS = 'earth_bin'
TORPEDOES_APPROACH = 'torpedoes_approach'
TORPEDOES = 'torpedoes'
OCTAGON_APPROACH = 'octagon_approach'
OCTAGON = 'octagon'

INFINITE_TIME = float('inf')
END_OF_MISSION = (None, 0)


async def polaris_generator():
    dead_reckoning = shm.dead_reckoning_virtual.get()

    # Gate
    if dead_reckoning.gate_approach_in_pool:
        await go_to_element(GATE_APPROACH)
    await heading(heading_to_element(GATE))
    yield GateMission(), INFINITE_TIME
    
    # Bins
    await go_to_element(BINS)
    yield BinsMission(), 240

    # Decision point
    if dead_reckoning.octagon_approach_in_pool:
        await go_to_element(OCTAGON_APPROACH)
        first_pinger_task = yield DecisionPoint(), INFINITE_TIME
    else:
        first_pinger_task = TORPEDOES
    
    # Torpedoes and then Octagon
    if first_pinger_task == TORPEDOES:
        if dead_reckoning.torpedoes_approach_in_pool:
            await go_to_element(TORPEDOES_APPROACH)
        yield TorpedoesMission(), 240
        await move_x(-3)
        yield TrackPinger(), INFINITE_TIME
        yield OctagonMission(), INFINITE_TIME
    
    # Octagon and then Torpedoes
    else:
        yield TrackPinger(), 90
        yield OctagonMission(), 240
        if dead_reckoning.torpedoes_approach_in_pool:
            await go_to_element(TORPEDOES_APPROACH)
        yield TorpedoesMission(), INFINITE_TIME
        await move_x(-3)
    
    yield END_OF_MISSION


async def leviathan_generator():
    dead_reckoning = shm.dead_reckoning_virtual.get()

    # Gate
    if dead_reckoning.gate_approach_in_pool:
        await go_to_element(GATE_APPROACH)
    await heading(heading_to_element(GATE))
    yield GateMission(), INFINITE_TIME

    # Path and then Buoy
    yield PathMission(), INFINITE_TIME
    yield BuoyMission(), INFINITE_TIME
    await move_x(-3)

    yield END_OF_MISSION