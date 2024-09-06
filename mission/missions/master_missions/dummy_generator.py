import shm

from mission.framework.base import AsyncBase
from mission.framework.movement import velocity_x_for_secs

# Example AsyncBase Mission
class Dummy(AsyncBase):
    def __init__(self):
        self.first_task = self.exec()

    async def exec(self):
        await velocity_x_for_secs(0.2, 3)
        return None

async def generator():
    yield Dummy(), 10
    yield None, 0

