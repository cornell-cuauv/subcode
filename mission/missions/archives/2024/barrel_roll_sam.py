#!/usr/bin/env python3

from mission.framework.base import AsyncBase
from mission.runner import run
import asyncio
from mission.framework.position import go_to_position
import shm
from mission.framework.movement import roll, relative_to_current_roll
import shm.settings_control

class BarrelRoll(AsyncBase): 
    # CHANGED
    def __init__(self,num_flips):
        self.delta_time = 0.05
        self.num_flips = num_flips
        self.direction = -90

        self._flipped = False
        self.first_task = self.barrel_roll()

    def log(self, msg):
        print(f"[BARREL ROLL] {msg}")

    def get_roll(self):
        return shm.kalman.roll.get()

    def set_roll(self, roll):
        shm.navigation_desires.roll.set(roll)
        shm.navigation_desires.pitch.set(0)

    def get_roll_desire(self):
        return shm.navigation_desires.roll.get()

    def is_flipped(self):
        roll = self.get_roll()

        # Check Rightside Up
        if -60 < roll < 60:
            self._flipped = False

        # Check Upside Down
        if roll < -120 or 120 < roll:
            self._flipped = True

        return self._flipped

    async def roll_changed(self, delta):
        start = self.get_roll()
        while abs(start - self.get_roll()) < delta:
            await asyncio.sleep(self.delta_time)

    def init_pid(self):
        self.pitch_active = shm.settings_control.pitch_active.get()
        self.heading_active = shm.settings_control.heading_active.get()
        self.velx_active = shm.settings_control.velx_active.get()
        self.vely_active = shm.settings_control.vely_active.get()

        shm.settings_control.pitch_active.set(True)
        shm.settings_control.heading_active.set(True)
        shm.settings_control.velx_active.set(True)
        shm.settings_control.vely_active.set(True)

    def reset_pid(self):
        shm.navigation_desires.speed.set(0)

        shm.settings_control.pitch_active.set(self.pitch_active)
        shm.settings_control.heading_active.set(self.heading_active)
        shm.settings_control.velx_active.set(self.velx_active)
        shm.settings_control.vely_active.set(self.vely_active)

    def log_roll(self):
        self.log(f"")
        self.log(f"Logging Roll:")
        self.log(f" - roll .......... {self.get_roll():6.1f} deg")
        self.log(f" - roll_desire ... {self.get_roll_desire():6.1f} deg")
        self.log(f" - is_flipped .... {self.is_flipped()}")
        self.log(f" - speed ......... {shm.navigation_desires.speed.get()}")

    def do_roll(self, cap_roll=False):
        roll = self.get_roll()
        desire = roll + self.direction

        if self.direction < 0:
            if cap_roll and 0 < roll:
                desire = max(desire, 0)
        else:
            if cap_roll and roll < 0:
                desire = min(desire, 0)

        self.set_roll(desire)

    def stop_roll(self):
        self.set_roll(0)

    def stop_moving(self):
        shm.navigation_desires.speed.set(0)

    async def barrel_roll(self):
        self.north = shm.kalman.north.get()
        self.east = shm.kalman.east.get()

        try:
            for _ in range(self.num_flips):
                self.init_pid()
                self.log(f"Beginning Barrel Roll (init)")
                while not self.is_flipped():
                    self.do_roll()
                    self.log_roll()
                    await self.roll_changed(5)

                self.log(f"Continuing Barrel Roll (unflip)")
                while self.is_flipped():
                    self.do_roll(cap_roll=True)
                    self.log_roll()
                    await self.roll_changed(5)
            
                self.log(f"Finishing Barrel Roll")
                self.stop_roll()
                self.reset_pid()
                await asyncio.sleep(5.0)
            self.stop_moving()
            await go_to_position(self.north,self.east)
        except:
            pass
        finally:
            self.reset_pid()

if __name__ == "__main__":
   BarrelRoll().run()
