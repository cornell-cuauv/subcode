
from math import exp
from time import time

class LowPassFilter:

    def __init__(self, rc):
        self._rc = rc
        self._x = 0.0

        self._last_time = time()

    def get(self, xn):
        t = time()
        dt = t - self._last_time
        self._last_time = t

        self._x += (1 - exp(-dt / self._rc)) * (xn - self._x)
        return self._x