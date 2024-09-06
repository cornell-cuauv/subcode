#!/usr/bin/env python3

from mission.framework.base import AsyncBase
from mission.framework.position import move_x
from mission.framework.movement import *

class Polygon(AsyncBase):
    def __init__(self, side):
        self.first_task = self.main()
        self.side = side

    async def main(self):
        angle = 180-(self.side-2)*(180/self.side)
        for i in range(self.side):
            await move_x(1)
            await relative_to_initial_heading(angle)


if __name__ == "__main__":
    Polygon(6).run()



