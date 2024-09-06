#!/usr/bin/env python3
import math
from mission.framework.primitive import zero, run_with_timeout
from mission.framework.base import AsyncBase
from mission.framework.consistency import SHMConsistencyTracker

from mission.framework.movement import velocity_x_for_secs, velocity_x, heading, depth
from mission.framework.contexts import PositionalControls
from mission.framework.position import move_x
from mission.framework.search import velocity_sway_search
from mission.framework.targeting import forward_target
from vision.modules.ODJ_Vision.helpers import name_to_shm
from mission.framework.dead_reckoning import heading_to_element
from mission import runner

import shm
import asyncio


glyphs = ["faucet", "dipper", "nozzle", "wishbone"]

shm_bin = {}
for name in glyphs:
    shm_bin[name] = name_to_shm(name)

trackers = {}
for name in glyphs:
    trackers[name] = SHMConsistencyTracker(group=name_to_shm(name),
                                            test=lambda glyph: glyph.visible == 1 or glyph.visible == 0.5,
                                            count_true=(9,10), count_false=(8, 10))

glyph_indicator = SHMConsistencyTracker(group=shm.dipper_glyph,
                                        test=lambda glyph: glyph.heuristic > 0,
                                        count_true=(2,3), count_false=(3,3))

def coordinates(bin):
            return (bin.center_x.get(), bin.center_y.get())

class BuoyScoutInfantry(AsyncBase):
            
    def __init__(self):
        self.first_task = self.startup()

    async def dist_timeout(self):
        init_n, init_e = shm.kalman.north.get(), shm.kalman.east.get()
        while math.dist((init_n, init_e), (shm.kalman.north.get(), shm.kalman.east.get())) < 15:
            await asyncio.sleep(0.1)
        return 1 / 0

    async def startup(self):

        self.killer_task = asyncio.create_task(self.dist_timeout())

        """
        Sets the vision module to scout is on, and infantry is off.
        """
        self.glyphs = ["dipper", "faucet", "nozzle", "wishbone"]
        self.target = self.glyphs.pop(0)

        for bin in [shm.faucet_glyph, shm.wishbone_glyph, shm.dipper_glyph, shm.nozzle_glyph]:
            pass
        vision_modules = shm.vision_modules.get()
        vision_modules.GlyphScout = 1
        vision_modules.GlyphInfantry = 0
        print("GlyphScout is set to ", vision_modules.GlyphScout)
        print("GlyphInfantry is set to ", vision_modules.GlyphInfantry)
        shm.vision_modules.set(vision_modules)
        return self.scout()

    async def scout(self):
        print("\n>> SCOUT MODE <<\n")
        await asyncio.sleep(5)
        await velocity_sway_search(lambda : glyph_indicator.consistent, width = 2.5)

        print(" > glyph mapping found. moving to infantry")
        await zero()
        return self.startup_2()

    async def startup_2(self):
        print("\n>> INFANTRY MODE <<\n")
        """
        Sets the vision module to infantry is on, and scout is off.
        """
        vision_modules = shm.vision_modules.get()
        vision_modules.GlyphScout= 0
        vision_modules.GlyphInfantry = 1
        print("GlyphScout is set to ", vision_modules.GlyphScout)
        print("GlyphInfantry is set to ", vision_modules.GlyphInfantry)
        shm.vision_modules.set(vision_modules)
        return self.find_sway()
    
    async def find_sway(self):
        """
        Find the buoy with a sway search.
        """
        print("FIND SWAY")
        print("> searching for target glyph with sway search")
        print("  target glyph:", self.target)
        await velocity_sway_search(lambda : trackers[self.target].consistent and shm_bin[self.target].error != 0.5)
        await zero()
        return self.position()
    
    async def find(self):
        """
        Find the buoy with a sway search.
        """
        print("FIND")
        print("> searching for target glyph by moving forward")
        print("  target glyph:", self.target)
        await asyncio.sleep(4)
        with PositionalControls(False):
            await velocity_x(0.1)
            while not trackers[self.target].consistent:
                await asyncio.sleep(1)
        await zero()
        return self.position()
        
    
    async def position(self):
        """
        Approach the buoy until it is a given area.
        """
        print("POSITION")
        await forward_target(lambda: coordinates(shm_bin[self.target]), target=(0, 0),
                                               visible = lambda: trackers[self.target].consistent,
                                               tolerance=(0.08, 0.08))
        print("Going to await vel_x")
        await velocity_x(0.15)
        print("Awaited vel x")
        while shm_bin[self.target].area.get() < 0.08:
            coords = coordinates(shm_bin[self.target])
            if not trackers[self.target].consistent:
                sum = 0
                for g in glyphs:
                    if shm_bin[g].error.get() == 0 and shm_bin[g].visible.get() == 1 and shm_bin[self.target].area.get() > 0.065:
                        sum += 1
                    if sum <= 1:
                        print("only one in sight. assuming it is our target. executing...")
                        return self.execute((0, 0))
                else:
                    print("when approaching, lost sight. recovering...")
                    return self.recover()
            elif (0.5 - abs(coords[0])) < 0.2 or 0.5 - abs(coords[1]) < 0.2:
                print("zeroing desires")
                await zero()
                print(" > adjustment")
                success = await forward_target(lambda: coordinates(shm_bin[self.target]), target=(0, 0),
                                               visible = lambda: trackers[self.target].consistent,
                                               tolerance=(0.08, 0.08))
                await asyncio.sleep(1)
                if not success:
                    sum = 0
                    for g in glyphs:
                         if shm_bin[g].error.get() == 0 and shm_bin[g].visible.get() == 1:
                             sum += 1
                    if sum <= 1:
                        print("only one in sight. assuming it is our target. executing...")
                        return self.execute()
                    else:
                        print("when approaching, lost sight. recovering...")
                        return self.recover()
            await asyncio.sleep(0.1)
            print(" > iteration:", str(shm_bin[self.target].area.get()))
        await zero()

        print(" > final target")
        coord = (0, 0)
        success = await forward_target(lambda: coordinates(shm_bin[self.target]), target=coord,
                                               visible = lambda: trackers[self.target].consistent, tolerance=(0.04, 0.04))
        print(" > final target success:", success)
        return self.execute(coord)

    async def execute(self, coord):
        """
        Ram the buoy, and if there are still glyphs remaining, go back to find.
        """
        print("EXECUTE")
        await velocity_x(0.10)
        while trackers[self.target].consistent:
            print(" > going forward: ", str(shm_bin[self.target].area.get()))
            await asyncio.sleep(1)
            if abs(shm_bin[self.target].center_x.get() - coord[0]) > 0.3 or abs(shm_bin[self.target].center_y.get() - coord[1]) > 0.3:
                print(" > centering")
                await forward_target(lambda: coordinates(shm_bin[self.target]), target=coord,
                                               visible = lambda: trackers[self.target].consistent,
                                               tolerance=(0.04, 0.04))
        await zero()
        area = shm_bin[self.target].area.get()
        time = 12.25 - 9.5 * area
        if time < 4:
            time = 4
        print("> going forward for " + str(time) + " seconds")
        await velocity_x_for_secs(0.2, time)
        if len(self.glyphs) > 0:
            self.target = self.glyphs.pop(0)
            print("new target:", self.target)
            async def backup():
                await velocity_x(-0.2)
                print("backing up")
                while not (trackers['dipper'].consistent and trackers['faucet'].consistent and trackers['nozzle'].consistent and trackers['wishbone'].consistent):
                    await asyncio.sleep(0.1)
                await asyncio.sleep(2)
            success = await run_with_timeout(backup(), 16)
            print("backup result:", success)
            await zero()
            if success:
                return self.find()
            else:
                await velocity_x_for_secs(0.2, 16)
        await move_x(-2)
        vision_modules = shm.vision_modules.get()
        vision_modules.GlyphScout = 0
        vision_modules.GlyphInfantry = 0
        print("GlyphScout is set to ", vision_modules.GlyphScout)
        print("GlyphInfantry is set to ", vision_modules.GlyphInfantry)
        shm.vision_modules.set(vision_modules)

    async def recover(self):
        """
        If the buoy is out of bounds, back up a little.
        """
        print("RECOVER")
        await velocity_x_for_secs(-0.2, 5)
        return self.find()
    
if __name__ == "__main__":
    BuoyScoutInfantry().run(debug=True)
