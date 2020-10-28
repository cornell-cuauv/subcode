import numpy as np

from common import filt, mix

class Downconverter:
    def __init__(self, num_chs, L_x, L_b, h, D=1, ph=0, w=0, xp=np):
        self._mixr = mix.Mixer(L_x, ph=ph, w=w, xp=xp)
        self._filtr = filt.FIR(num_chs, L_b, h, D=D, xp=xp)

    def push(self, x):
        return self._filtr.push(self._mixr.push(x))

    def set_freq(self, f):
        self._mixr.set_freq(f)