import numpy as np

class Packer:
    def __init__(self, L_y, xp=np):
        assert L_y >= 1, 'Output block length must be at least 1'

        self._L_y = L_y
        self._xp = xp

        self.reset()

    def push(self, x):
        L_x = x.shape[1]
        assert L_x <= self._L_y, (
            'Input block length must be at most equal to output block length')

        if self._L_packed == 0:
            if self._remainder is not None:
                self._packed = [self._remainder]
                self._L_packed = self._remainder.shape[1]
            else:
                self._packed = []

        free_space = self._L_y - self._L_packed
        if free_space > L_x:
            self._packed.append(x)
            self._L_packed += L_x

            return None
        else:
            self._packed.append(x[:, : free_space])
            self._remainder = x[:, free_space :]
            self._L_packed = 0

            return self._xp.concatenate(self._packed, axis=1)

    def reset(self):
        self._remainder = None
        self._L_packed = 0