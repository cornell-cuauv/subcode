#!/usr/bin/env python3

from mission.runner import run
import asyncio
import shm
from mission.framework.movement import roll, relative_to_current_roll

async def BarrelRoll():
    roll_kP = shm.settings_roll.kP.get()
    pitch_kP = shm.settings_pitch.kP.get()
    depth_kP = shm.settings_depth.kP.get()
    depth_kI = shm.settings_depth.kI.get()
    heading_kP = shm.settings_heading.kP.get()
    shm.settings_roll.kP.set(0.7)
    #shm.settings_pitch.kP.set(1.5)
    shm.settings_depth.kP.set(10)
    shm.settings_depth.kI.set(0.04)
    shm.settings_heading.kP.set(0.5)
    try:
        #for i in range(8):
        #    await roll(i * 90)
        #shm.navigation_desires.roll.set(-120)
        #while shm.kalman.roll.get() > -60:
        #    await asyncio.sleep(0.1)
        #await roll(0)
        #shm.navigation_desires.speed.set(0.5)
        passed_100 = False
        while not (passed_100 and -50 < shm.kalman.roll.get() < 50):
            #await relative_to_current_roll(lambda: 50)
            shm.navigation_desires.roll.set(shm.kalman.roll.get() + 90)
            if shm.kalman.roll.get() > 100:
                passed_100 = True
    except:
        pass
    finally:
        shm.settings_roll.kP.set(roll_kP)
        shm.settings_pitch.kP.set(pitch_kP)
        shm.settings_depth.kP.set(depth_kP)
        shm.settings_depth.kI.set(depth_kI)
        shm.settings_heading.kP.set(heading_kP)
        shm.navigation_desires.speed.set(0)
    #while True:
        #await roll((shm.kalman.roll.get() + 90) % 360)
    #await relative_to_current_roll(lambda: 20)

run(BarrelRoll(), 'barrel_roll')
