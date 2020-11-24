import numpy as np

from common import pack

class Decimator:
    def __init__(self, L_b, D=1, xp=np):
        assert L_b % D == 0, ('Decimation block length must be a multiple ' +
            'of the decimation factor')

        self._D = D

        self._pkr = pack.Packer(L_b, xp=xp)

    def push(self, x):
        packed = self._pkr.push(x)
        if packed is not None:
            return packed[:, : : self._D]

        return None