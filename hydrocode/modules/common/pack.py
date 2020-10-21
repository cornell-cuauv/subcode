import numpy as np

from common import const

class Packer:
    def __init__(self, num_chs, L_x, L_y, dtype=np.float, xp=np):
        assert num_chs >= 1, 'Packer must have at least one input channel'
        assert L_x > 0, 'Input block length must be at least 1'
        assert L_y > 0, 'Output block length must be at least 1'
        assert L_y >= L_x, (
            'Output blocks must be at least as large as the input blocks')

        self._L_x = L_x
        self._L_y = L_y
        self._xp = xp

        self._remainder = xp.zeros((num_chs, 0), dtype=dtype)
        self._L_packed = 0

    def push(self, x):
        if self._L_packed == 0:
            self._packed = [self._remainder]
            self._L_packed = self._remainder.shape[1]

        free_space = self._L_y - self._L_packed
        if free_space > self._L_x:
            self._packed.append(x)
            self._L_packed += self._L_x

            return None
        else:
            self._packed.append(x[:, : free_space])
            self._remainder = x[:, free_space :]
            self._L_packed = 0

            return self._xp.concatenate(self._packed, axis=1)

    def reset(self):
        self._remainder = self._remainder[:, : 0]
        self._L_packed = 0