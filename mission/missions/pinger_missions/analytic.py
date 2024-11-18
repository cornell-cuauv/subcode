#!/usr/bin/env python3

##############################################################################################################
# Adapted from https://math.stackexchange.com/questions/2598811/calculate-the-point-closest-to-multiple-rays #
##############################################################################################################

import numpy as np
from scipy.optimize import least_squares

def locate(rays):
    ray_start_positions = []
    for ray in rays:
        ray_start_positions.append(ray[0])
    starting_P = np.stack(ray_start_positions).mean(axis=0).ravel()
    ans = least_squares(angular_distance, starting_P, kwargs={'rays': rays})
    return ans

def angular_distance(P, rays):
    errors = []
    for ray in rays:
        heading_to_p = math.atan2(P[1] - ray[0][1], P[0] - ray[0][0])
        heading_of_ray = ray[1]
        error = abs(heading_to_p - heading_of_ray) ** 2
        errors.append(error)
    return np.array(errors)


############################################################################################################
# Original code                                                                                            #
############################################################################################################

import asyncio
import math
import shm
from mission.core.base import AsyncBase
from mission.framework.position import move_x, move_y, go_to_position
from mission.framework.movement import velocity_x_for_secs, velocity_y_for_secs

class AnalyticPinger(AsyncBase):
    def __init__(self):
        self.first_task = self.main()
        self.pings = []

    def collect_ping(self):
        self.pings.append(np.array([
            np.array([shm.kaklman.north.get(), shm.kalman.east.get()]),
            shm.hydrophones_pinger_results.heading.get() * math.pi / 180
        ]))
    
    async def collect_pings(self):
        while True:
            heading = shm.hydrophones_pinger_results.heading.get()
            while shm.hydrophones_pinger_results.heading.get() == heading:
                await asyncio.sleep(0.1)
            self.collect_ping()
    
    def estimate_pinger_location(self):
        location = locate(self.pings).x
        print(f'Estimated location: ({location[0]}, {location[1]})')
        return location

    async def main(self):
        collect_pings_task = asyncio.create_task(self.collect_pings())

        await velocity_y_for_secs(0.2, 15)
        await velocity_x_for_secs(0.2, 15)
        await velocity_y_for_secs(-0.2, 15)
        await velocity_x_for_secs(-0.2, 15)

        pinger_location = self.estimate_pinger_location()
        await go_to_position(*location)

        # print("Set the packet number to 1 to start the mission.")
        # while shm.hydrophones_pinger_status.packet_number.get() == 0:
        #     await asyncio.sleep(0.1)
        # collect_pings_task.cancel()
        # pinger_location = self.estimate_pinger_location()
        # await go_to_position(*pinger_location)



if __name__ == '__main__':
    AnalyticPinger().run()