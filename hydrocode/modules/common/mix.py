import cmath

import numpy as np

class Mixer:
    def __init__(self, f, L, ph=0, xp=np):
        assert L >= 1, 'Data block length must be at least 1'

        self._offsets = xp.exp(1j * f * xp.arange(L))
        self._step = f * L
        self._ph = ph

    def push(self, x):
        nco = cmath.exp(1j * self._ph) * self._offsets
        self._ph += self._step

        y = x * nco

        return y