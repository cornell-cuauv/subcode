import shm

from typing import Optional

class PositionalControls():
    enable_locked = False
    optimize_locked = False

    def __init__(self, enable : Optional[bool] = True,
            optimize : Optional[bool] = False):
        self.enable = enable
        self.optimize = optimize

    def __enter__(self):
        self.init_enable = shm.navigation_settings.position_controls.get()
        self.enable_cancelled = PositionalControls.enable_locked
        if (PositionalControls.enable_locked and
                self.enable == not self.init_enable):
            raise Exception("Attempted PositionalControls contradiction.")
        if self.enable != None and not PositionalControls.enable_locked:
            PositionalControls.enable_locked = True
            shm.navigation_settings.position_controls.set(self.enable)

        self.init_optimize = shm.navigation_settings.optimize.get()
        self.optimize_cancelled = PositionalControls.optimize_locked
        if (PositionalControls.optimize_locked and
                self.optimize == not self.init_optimize):
            raise Exception("Attempted PositionalControls contradiction.")
        if self.optimize != None and not PositionalControls.optimize_locked:
            PositionalControls.optimize_locked = True
            shm.navigation_settings.optimize.set(self.optimize)

    def __exit__(self, type, value, traceback):
        if self.enable != None and not self.enable_cancelled:
            PositionalControls.enable_locked = False
            shm.navigation_settings.position_controls.set(self.init_enable)

        if self.optimize != None and not self.optimize_cancelled:
            PositionalControls.optimize_locked = False
            shm.navigation_settings.optimize.set(self.init_optimize)


class MaxSpeed():
    def __init__(self, speed : float):
        self.speed = speed

    def __enter__(self):
        self.init_speed = shm.navigation_settings.max_speed.get()
        shm.navigation_settings.max_speed.set(self.speed)

    def __exit__(self, type, value, traceback):
        shm.navigation_settings.max_speed.set(self.initi_speed)


