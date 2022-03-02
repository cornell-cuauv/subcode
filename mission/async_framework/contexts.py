import shm


class PositionalControls():
    def __init__(self, enable : bool = True, optimize : bool = False):
        self.enable = enable
        self.optimize = optimize

    def __enter__(self):
        self.init_enable = shm.navigation_settings.position_controls.get()
        self.init_optimize = shm.navigation_settings.optimize.get()
        if self.enable != None:
            shm.navigation_settings.position_controls.set(self.enable)
        if self.optimize != None:
            shm.navigation_settings.optimize.set(self.optimize)

    def __exit__(self):
        if self.enable != None:
            shm.navigation_settings.position_controls.set(self.init_enable)
        if self.optimize != None:
            shm.navigation_settings.optimize.set(self.init_optimize)


class MaxSpeed():
    def __init__(self, speed : float):
        self.speed = speed

    def __enter__(self):
        self.init_speed = shm.navigation_settings.max_speed.get()
        shm.navigation_settings.max_speed.set(self.speed)

    def __exit__(self):
        shm.navigation_settings.max_speed.set(self.initi_speed)


