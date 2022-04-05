import shm

class PositionalControls():
    locked = False

    def __init__(self, enable = True, optimize = False):
        self.enable = enable
        self.optimize = optimize

    def __enter__(self):
        self.init_enable = shm.navigation_settings.position_controls.get()
        self.init_optimize = shm.navigation_settings.optimize.get()

        self.cancelled = locked
        if locked and (self.enable != self.init_enable
                or self.optimize != self.init_optimize):
            raise Exception("Attempted PositionalControls contradiction.")
        if not locked:
            locked = True
            shm.navigation_settings.position_controls.set(self.enable)
            shm.navigation_settings.optimize.set(self.optimize)

    def __exit__(self, type, value, traceback):
        if not self.cancelled:
            locked = False
            shm.navigation_settings.position_controls.set(self.init_enable)
            shm.navigation_settings.optimize.set(self.init_optimize)


class MaxSpeed():
    def __init__(self, speed : float):
        self.speed = speed

    def __enter__(self):
        self.init_speed = shm.navigation_settings.max_speed.get()
        shm.navigation_settings.max_speed.set(self.speed)

    def __exit__(self, type, value, traceback):
        shm.navigation_settings.max_speed.set(self.initi_speed)


