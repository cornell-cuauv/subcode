#!/usr/bin/env python3

from mission.framework.base import AsyncBase
from mission.framework.movement import *

from mission.framework.primitive import *
from mission.framework.contexts import *

from math import exp, cos, sin, tan, pi, radians

SPEED = 0.5
BIG_ANGLE = 90
BIG_SWINGS_NEEDED = 3

import asyncio
import shm
from hydrocode.modules.pinger.angles import wrap_angle
from mission.framework.abstract_drive_towards import *
from math import *

PINGER_OFFSET = -55.1

def get_heading():
    heading_radians = shm.hydrophones_pinger_results.heading.get()
    heading_radians = wrap_angle(heading_radians - radians(PINGER_OFFSET))
    heading_degrees = degrees(heading_radians)
    return -heading_degrees
    

class StraightforwardPinger(AsyncBase):
    def __init__(self):
        self.dry_run = False

        self.max_error = 10
        self.max_passed = 60
        self.max_noise = 45
        self.speed = 0.2
        self.time = 2.0
        self.sleep_time = 1.0

        self.last_heading = get_heading()
        self.first_task = self.main()
        self.driving = False

    async def get_new_heading(self):
        heading_read = self.last_heading
        await asyncio.sleep(self.sleep_time)
        while heading_read == self.last_heading:
            await asyncio.sleep(0.1)
            heading_read = get_heading()
        self.difference = heading_read - self.last_heading
        self.last_heading = heading_read
        return self.last_heading

    async def print_heading_debug(self):
        while True:
            heading_b = await self.get_new_heading()
            print(f"Measured Heading: {heading_b}deg")

    async def main(self):
        while True:
            print()
            print(f"New Loop: ")

            print(f" - Measuring Heading: ")

            print(f" +-- Zeroing for {self.sleep_time}s...")
            
            if not self.dry_run:
                await zero()

            await self.get_new_heading()
            
            if self.driving:
                init_heading = shm.kalman.heading.get()
                await relative_to_initial_heading(90)

                await self.get_new_heading()

                await heading(init_heading)

                await self.get_new_heading()
            
            heading_a = await self.get_new_heading()
            print(f" +-- Measured Heading A: {heading_a}deg")

            heading_b = await self.get_new_heading()
            print(f" +-- Measured Heading B: {heading_b}deg")

            heading_avg = (heading_a + heading_b) / 2
            print(f" +-- Measured Heading: {heading_avg}deg")

            noise = abs(heading_a - heading_b)
            print(f" +-- Measured Noise: ±{noise}")

            consistent = noise < self.max_noise
            print(f" - ±{noise} < {self.max_noise}: {consistent}")

            if not consistent:
                print(f" +-- Noise is too High, assuming pinger is below us")
                break


            if self.driving:
                not_passed = abs(heading_avg) < self.max_passed

                print(f" - abs({heading_avg}) < {self.max_passed}: {not_passed}")

                if not not_passed:
                    break

            aligned = abs(heading_avg) < self.max_error

            print(f" - abs({heading_avg}) < {self.max_error}: {aligned}")

            if aligned:
                self.driving |= True
                await self.drive_forward(heading_avg)
            else:
                await self.align(heading_avg)

        print("FINISHED")

        if not self.dry_run:
            await zero()

    async def align(self, turn_degrees):
        print(f" - Align Sub:")
        print(f" +-- Turning: {turn_degrees}deg...")
        if not self.dry_run:
            await relative_to_initial_heading(turn_degrees, tolerance=self.max_error)
        print(f" +-- Waiting: {self.sleep_time}s...")
        if not self.dry_run:
            await asyncio.sleep(self.sleep_time)
        print(f" +-- Finished!")
        return

    async def drive_forward(self, turn_degrees):
        print(f" - Align + Drive:")
        print(f" +-- Turning: {turn_degrees}deg...")
        if not self.dry_run:
            await relative_to_initial_heading(turn_degrees, tolerance=self.max_error)
        print(f" +-- Driving at {self.speed} m/s for {self.time}s...")
        if not self.dry_run:
            await velocity_x_for_secs(self.speed, self.time)
        await zero()
        print(f" +-- Waiting: {self.sleep_time}s...")
        await asyncio.sleep(self.sleep_time)
        print(f" +-- Finished!")
        return

if __name__ == '__main__':
    StraightforwardPinger().run()
