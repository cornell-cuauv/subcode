#!/usr/bin/env python3

from mission.framework.base import AsyncBase
from mission.framework.position import move_x
from mission.framework.movement import depth
import asyncio

class MyMission(AsyncBase):

    def __init__(self):
        self.first_task = self.main()

    async def main(self):
        await move_x(1)
        await depth(0)

if __name__ == "__main__":
    MyMission().run()
