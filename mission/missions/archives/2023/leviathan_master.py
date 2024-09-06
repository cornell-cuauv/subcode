#!/usr/bin/env python3

import sys
import asyncio
import shm
from mission.runner import run
from mission.framework.primitive import zero
from mission.framework.movement import depth, heading
from mission.missions.gate_2023 import AaronGate
from mission.missions.path_2023 import AaronPath
from mission.missions.FPE_2023 import anthony_buoy

async def leviathan_master():

    # Startup procedure
    if len(sys.argv) < 2 or int(sys.argv[1]) <= 0:
        input("Press enter when the sub is facing towards the gate.")
        initial_heading = shm.kalman.heading.get()
        print("Turn the sub away from the gate and then softkill it.")
        while shm.switches.soft_kill.get() != 1:
            await asyncio.sleep(0.1)
        input("Press enter to start the mission.")

        # Submerge and face the gate
        await zero()
        shm.switches.soft_kill.set(0)
        await depth(1.5)
        await heading(initial_heading)
        
    # Pass through the gate
    if len(sys.argv) < 2 or int(sys.argv[1]) <= 1:
        print('Starting gate mission')
        #shm.vision_modules.CompGateVision.set(1)
        await AaronGate().run_headless()
        #shm.vision_modules.CompGateVision.set(0)

    # Follow the path
    if len(sys.argv) < 2 or int(sys.argv[1]) <= 2:
        print('Starting path mission')
        #shm.vision_modules.AaronPath.set(1)
        await AaronPath().run_headless()
        #shm.vision_modules.AaronPath.set(0)

    # Ram the buoy
    if len(sys.argv) < 2 or int(sys.argv[1]) <= 3:
        print('Starting buoy mission')
        #shm.vision_modules.GlyphVision.set(1)
        await anthony_buoy()
        #shm.vision_modules.GlyphVision.set(0)

    print('Finished; softkilling.')
    shm.switches.soft_kill.set(1)

if __name__ == '__main__':
    run(leviathan_master(), 'leviathan_master')
