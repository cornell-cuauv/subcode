#!/usr/bin/env python3

import asyncio
import shm
from mission.framework.base import AsyncBase
from mission.framework.contexts import PositionalControls
from mission.framework.position import go_to_position

class DVLChartedCourse(AsyncBase):
    def __init__(self):
        self.first_task = self.main()
    
    async def watch_dvl(self):
        prev = False
        while True:
            if ((shm.dvl.low_amp_1.get() or shm.dvl.low_correlation_1.get())
                    and (shm.dvl.low_amp_2.get() or shm.dvl.low_correlation_2.get())
                    and (shm.dvl.low_amp_3.get() or shm.dvl.low_correlation_3.get())
                    and (shm.dvl.low_amp_4.get() or shm.dvl.low_correlation_4.get())):
                if prev:
                    shm.switches.soft_kill.set(1)
                    return
                else:
                    prev = True
            await asyncio.sleep(0.5)
    
    async def main(self):
        positions = []
        while input('>') == '':
            positions.append((shm.kalman.north.get(), shm.kalman.east.get(), shm.kalman.depth.get()))
        watch_dvl_task = asyncio.create_task(self.watch_dvl())
        shm.navigation_settings.position_controls.set(0)
        shm.settings_control.depth_active.set(0)
        shm.settings_control.velx_active.set(0)
        shm.settings_control.vely_active.set(0)
        await asyncio.sleep(120)
        shm.settings_control.depth_active.set(1)
        shm.settings_control.velx_active.set(1)
        shm.settings_control.vely_active.set(1)
        shm.navigation_settings.position_controls.set(1)
        with PositionalControls():
            shm.navigation_desires.north.set(positions[0][0])
            shm.navigation_desires.east.set(positions[0][1])
            shm.navigation_desires.depth.set(positions[0][2])
            while (abs(shm.kalman.north.get() - positions[0][0]) > 0.1
                    or abs(shm.kalman.east.get() - positions[0][1]) > 0.1
                    or abs(shm.kalman.depth.get() - positions[0][2]) > 0.1):
                await asyncio.sleep(0.1)
            shm.navigation_settings.position_controls.set(0)
            shm.settings_control.depth_active.set(0)
            shm.settings_control.velx_active.set(0)
            shm.settings_control.vely_active.set(0)
            await asyncio.sleep(30)
            shm.settings_control.depth_active.set(1)
            shm.settings_control.velx_active.set(1)
            shm.settings_control.vely_active.set(1)
            shm.navigation_settings.position_controls.set(1)
            for pos in positions:
                shm.navigation_desires.north.set(pos[0])
                shm.navigation_desires.east.set(pos[1])
                shm.navigation_desires.depth.set(pos[2])
                while (abs(shm.kalman.north.get() - pos[0]) > 0.1
                        or abs(shm.kalman.east.get() - pos[1]) > 0.1
                        or abs(shm.kalman.depth.get() - pos[2]) > 0.1):
                    await asyncio.sleep(0.1)
        shm.switches.soft_kill.set(1)

if __name__ == '__main__':
    DVLChartedCourse().run()
