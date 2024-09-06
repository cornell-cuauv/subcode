#!/usr/bin/env python3
from mission.framework.base import AsyncBase
from mission.framework.position import move_x
from mission.framework.movement import *
# from mission.framework.position import *
from mission.framework.targeting import *
from vision.modules.base import ModuleBase
import shm
from mission.framework.consistency import SHMConsistencyTracker
import asyncio
from mission.framework.search import *


class prequalSerius(AsyncBase):
    def __init__(self):
        self.first_task = self.main()

    async def main(self):
        await move_x(10)
        await self.draw_square()
        await move_x(-10)

    async def draw_square(self):
        await move_y(5)
        await move_x(10)
        await move_y(-10)
        await move_x(-10)
        await move_y(5)
