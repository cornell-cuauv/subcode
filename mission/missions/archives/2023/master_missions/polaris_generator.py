import shm

# Actual Polaris Missions
from mission.missions.gate_2023 import Gate2023 as GateMission
from mission.missions.bins_2023 import JoshBins as BinsMission
from mission.missions.decision_point_2023 import DecisionPoint2023 as DecisionPoint
from mission.missions.track_pinger_2023 import TrackPinger2023 as TrackPinger
from mission.missions.torpedoes_2023 import Torpedoes2023 as TorpedoesMission
from mission.missions.octagon_surface_2023 import OctagonSurface
from mission.missions.buoy_2023 import BuoyScoutInfantry as BuoyMission

# for debugging purposes
from mission.missions.move_forward import X as MoveTest 

# pre-coded enums
from mission.missions.master_missions.common import *

# movement for between missions
from mission.framework.movement import heading, depth, relative_to_initial_heading
from mission.framework.position import move_x, move_y
from mission.framework.dead_reckoning import (go_to_element,
                                              heading_to_element,
                                              )
from mission.framework.primitive import enable_hydrophones, enable_downcam

from mission.framework.base import AsyncBase

class A(AsyncBase):
    def __init__(self):
        self.first_task = move_x(1, 0.10)

class B(AsyncBase):
    def __init__(self):
        self.first_task = move_x(-1, 0.10)


class DRGate(AsyncBase):
    def __init__(self):
        self.first_task = self.main()

    async def main(self):
        head = heading_to_element(GATE)
        await heading(head)
        await go_to_element(GATE)
        for i in range(8):
            await relative_to_initial_heading(90)
        await heading(head)
        await move_x(2, 0.1)
        return None

class MeasuredGate(AsyncBase):
    def __init__(self):
        self.first_task = self.main()

    async def main(self):
        head = heading_to_element(GATE)
        await heading(head)
        await move_x(9.7) # 9.7
        for i in range(8):
            await relative_to_initial_heading(90)
        await heading(head)


async def generator():
    #yield A(), 20
    #yield A(), 1
    #yield B(), 20 
    #yield B(), 20 
    #yield END_OF_MISSION

    dead_reckoning = shm.dead_reckoning_virtual.get()
    # Use go_to_element and heading_to_element here
    # yield MoveTest(), 20
    # yield END_OF_MISSION
    # Gate
    #if dead_reckoning.gate_approach_in_pool:
    #    await go_to_element(GATE_APPROACH)
    if shm.master_mission_settings.dead_reckon_gate().get():
        yield MeasuredGate(), INFINITE_TIME
    else:
        yield GateMission(), INFINITE_TIME
    
    # Buoys
    yield BuoyMission(), INFINITE_TIME

    # Octagon
    #await enable_hydrophones()
    yield TrackPinger(), INFINITE_TIME
    #await enable_downcam()
    shm.master_mission_settings.can_surface.set(1)
    shm.switches.soft_kill.set(1)

    # Bins
    # await go_to_element(BINS)
    # yield BinsMission(), 240

    # Decision point
    # if dead_reckoning.octagon_approach_in_pool:
    #     await go_to_element(OCTAGON_APPROACH)
    #     first_pinger_task = yield DecisionPoint(), INFINITE_TIME
    # else:
    #     first_pinger_task = TORPEDOES

    # Torpedoes and then Octagon
    # if first_pinger_task == TORPEDOES:
    #     if dead_reckoning.torpedoes_approach_in_pool:
    #         await go_to_element(TORPEDOES_APPROACH)
    #     yield TorpedoesMission(), 240
    #     await move_x(-3)
    #     yield TrackPinger(), INFINITE_TIME
    #     yield OctagonMission(), INFINITE_TIME

    # Octagon and then Torpedoes
    # else:
    #     yield TrackPinger(), 90
    #     yield OctagonMission(), 240
    #     if dead_reckoning.torpedoes_approach_in_pool:
    #         await go_to_element(TORPEDOES_APPROACH)
    #     yield TorpedoesMission(), INFINITE_TIME
    #     await move_x(-3)

    yield END_OF_MISSION
