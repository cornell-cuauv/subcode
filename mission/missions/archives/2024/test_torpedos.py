#!/usr/bin/env python3
from mission.framework.base import AsyncBase
from mission.framework.position import move_x
from mission.framework.movement import *
# from mission.framework.position import *
from mission.framework.targeting import *
from vision.modules.base import ModuleBase

from mission.framework.actuation import *


class testTorpedos(AsyncBase):
    def __init__(self):
        print('init')

        self.first_task = self.main()
        
    async def main(self):
       
        await fire_torpedo()
        await fire_torpedo()
        
        
if __name__ == "__main__":
   testTorpedos().run()
