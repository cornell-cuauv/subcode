import shm

from typing import Optional

class PositionalControls():
    init_enable = False
    enable_depth = 0
    init_optimize = True
    optimize_depth = 0
    
    def __init__(self, enable : Optional[bool] = True,
            optimize : Optional[bool] = False):
        self.enable = enable
        self.enable_var = shm.navigation_settings.position_controls
        self.optimize = optimize
        self.optimize_var = shm.navigation_settings.optimize

    def __enter__(self):
        if self.enable != None:
            if PositionalControls.enable_depth == 0:
                PositionalControls.init_enable = self.enable_var.get()
                self.enable_var.set(self.enable)
            elif self.enable == (not self.enable_var.get()):
                raise Exception("Attempted PositionalControls contradiction.")
            PositionalControls.enable_depth += 1
        if self.optimize != None:
            if PositionalControls.optimize_depth == 0:
                Positionalcontrols.init_optimize = self.optimize_var.get()
                self.optimize_var.set(self.optimize)
            elif self.optimize == (not self.optimize_var.get()):
                raise Exception("Attempted PositionalControls contradiction.")
            PositionalControls.optimize_depth += 1


    def __exit__(self):
        if self.enable != None:
            PositionalControls.enable_depth -= 1
            if PositionalControls.enable_depth == 0:
                self.enable_var.set(PositionalControls.init_enable)
        if self.optimize != None:
            PositionalControls.optimize_depth -= 1
            if PositionalControls.optimize_depth == 0:
                self.optimize_var.set(PositionalControls.init_optimize)
            

class MaxSpeed():
    def __init__(self, speed : float):
        self.speed = speed

    def __enter__(self):
        self.init_speed = shm.navigation_settings.max_speed.get()
        shm.navigation_settings.max_speed.set(self.speed)

    def __exit__(self, type, value, traceback):
        shm.navigation_settings.max_speed.set(self.initi_speed)


