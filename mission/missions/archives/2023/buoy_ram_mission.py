#!/usr/bin/env python3

import shm

from mission.missions.abstract_ram_mission import AbstractRamMission

MAX_AREA = 100000
BUOY = shm.red_buoy_results

class BuoyRamMission(AbstractRamMission):
    
    def __init__(self):
        super().__init__(
            period = 1.0 / 20.0,
            
            done_condition = lambda: (BUOY.get().area > MAX_AREA),

            max_angle_error = 5.0, # deg
            max_forward_speed = 0.5, # m/s 

            is_visible = lambda: (BUOY.get().heuristic_score > 0.5),

            yaw_provider = lambda: (BUOY.get().center_x),
            pitch_provider = lambda: (BUOY.get().center_y + shm.gx4.roll.get()),
            distance_provider = lambda: (6.0)
	)

if __name__ == "__main__":
    BuoyRamMission().run()
