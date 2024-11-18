#!/usr/bin/env python3
from mission.core.base import AsyncBase
from mission.framework.position import move_x, move_y, move_xy
from mission.framework.velocity import velocity_y_for_secs, velocity_x_for_secs
from mission.framework.movement import depth, relative_to_initial_heading

class Mission(AsyncBase):

    def __init__(self):
        self.first_task = self.move_forward()

    async def move_forward(self):
        
        await velocity_y_for_secs(0.3, 5)
        await velocity_x_for_secs(0.3, 5)

        await move_y(-5)
        await move_x(4)

        await depth(2)
        await relative_to_initial_heading(60)

if __name__ == "__main__":
    Mission().run()
