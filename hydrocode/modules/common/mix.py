import cmath

import numpy as np

class Mixer:
    def __init__(self, L_x, ph=0, w=0, xp=np):
        assert L_x >= 1, 'Input block length must be at least 1'

        self._L_x = L_x
        self._ph = ph
        self._xp = xp

        self.set_freq(w)

    def push(self, x):
        nco = cmath.exp(1j * self._ph) * self._offsets
        self._ph += self._step

        y = x * nco

        return y

    def set_freq(self, w):
        self._offsets = self._xp.exp(1j * w * self._xp.arange(self._L_x))
        self._step = w * self._L_x