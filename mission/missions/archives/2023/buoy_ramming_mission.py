#!/usr/bin/env python3

from mission.framework.base import AsyncBase
from mission.framework.position import *
from mission.framework.movement import *
from mission.framework.targeting import *
import shm
import asyncio

class BuoyRam(AsyncBase):
    def __init__(self):
        self.first_task = self.center()

    async def center(self):
        print("target")
        target = 0,0
        forward = await forward_target(self.point, target, self.visible)
        await zero()
        print("forward_target")
        while (self.visible):
            print("move_x")
            await move_x(1)
        await zero()
        print("zero")
        return

    def point(self):
        results = shm.red_buoy_results.get()
        point = -results.center_x, -results.center_y
        return point

    def visible(self):
        results = shm.red_buoy_results.get()
        return results.heuristic_score > 0

if __name__ == "__main__":
    BuoyRam().run()
