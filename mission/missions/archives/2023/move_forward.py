import time
from mission.framework.base import AsyncBase
from mission.framework.position import move_x
from mission.framework.movement import velocity_x_for_secs

class X(AsyncBase):
    def __init__(self):
        self.first_task = self.move()

    async def move(self):
        #await move_x(0)
        #time.sleep(20)
        await velocity_x_for_secs(0, 100)


if __name__ == "__main__":
    x = X()
    x.run('move')
    
