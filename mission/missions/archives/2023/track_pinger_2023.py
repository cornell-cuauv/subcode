#!/usr/bin/env python3

import asyncio
from math import radians, degrees, atan2, sin, cos

from shm import (hydrophones_pinger_results as results,
                 navigation_desires as desires, kalman,
                 dead_reckoning_virtual)

from mission.framework.base import AsyncBase
from mission.framework.movement import velocity_x, heading, depth
from mission.framework.dead_reckoning import go_to_element, heading_to_element
from mission.framework.logger import mission_logger
import time

logger = mission_logger.track_pinger

def angle_diff(a, b):
    return degrees(abs(atan2(
        sin(radians(a) - radians(b)),
        cos(radians(a) - radians(b)))))


def pinger_heading():
    return (degrees(results.heading.get()) + 180) % 360


class TrackPinger2023(AsyncBase):
    def __init__(self):
        super().__init__()
        self.first_task = self.track_pinger()
        self.large_swings = []

    async def track_pinger(self):


        logger('going to depth 1.5')
        await depth(1.5) # TODO: Uncomment this
        logger('going to octagon approach')
        if dead_reckoning_virtual.octagon_approach_in_pool.get():
            await go_to_element('octagon_approach')

        logger('go to octagon')
        if dead_reckoning_virtual.octagon_in_pool.get():
            await go_to_element('octagon', 10)

        logger('starting to track pinger')
        await velocity_x(0.3)
        self.latest_reading = pinger_heading()
        while True:
            while pinger_heading() == self.latest_reading:
                await asyncio.sleep(0.01)
            self.latest_reading = pinger_heading()
            if angle_diff(kalman.heading.get(), pinger_heading()) > 90:
                await velocity_x(0)
                logger('> large swing detected')
                recent_count = sum((time.time() - swing < 40) for swing in self.large_swings)
                logger('>>> recent count: ' + str(recent_count))
                self.large_swings.append(time.time())
                if recent_count > 3:
                    return None
                await heading(pinger_heading())
                await velocity_x(0.3)
            else:
                desires.heading.set(pinger_heading())


if __name__ == '__main__':
    TrackPinger2023().run()
