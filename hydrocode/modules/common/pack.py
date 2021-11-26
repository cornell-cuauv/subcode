try:
    import cupy as xp
except ImportError:
    import numpy as xp

class Packer:
    """Packs blocks of samples until a certain length is reached."""

    def __init__(self, L_y):
        """Constructor.

        :param L_y: length of the output block
        """

        assert L_y >= 1, 'Output block length must be at least 1'

        self._L_y = L_y

        self.reset()

    def push(self, x):
        """Push a block of samples.

        If the output block length is exceeded, the remaining samples
        are added to the next round.

        :param x: input signal, can't be longer than L_y
        :return: None if accumulated less than L_y samples
                 accumulated samples otherwise
        """

        L_x = x.shape[1]
        assert L_x <= self._L_y, (
            'Input block length must be at most equal to output block length')

        free_space = self._L_y - self._L_packed
        if free_space > L_x:
            self._packed.append(x)
            self._L_packed += L_x

            return None
        else:
            self._packed.append(x[:, : free_space])

            ret = self.get()

            self._packed = [x[:, free_space :]]
            self._L_packed = self._packed[0].shape[1]

            return ret

    def get(self):
        """Get the currently packed samples, regardless of how many.

        :return: currently packed samples
        """

        return xp.concatenate(self._packed, axis=1)

    def reset(self):
        """Delete the currently packed samples."""

        self._packed = []
        self._L_packed = 0