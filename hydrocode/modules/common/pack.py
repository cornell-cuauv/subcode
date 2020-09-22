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
        self._x = xp.zeros((num_chs, 0), dtype=dtype)
        self._y = xp.zeros((num_chs, L_y), dtype=dtype)
        self._y_index = 0

    def push(self, x):
        if self._y_index == 0:
            remainder_len = self._x.shape[1]
            self._y[:, : remainder_len] = self._x
            self._y_index = remainder_len

        free_space = self._L_y - self._y_index
        if free_space > self._L_x:
            self._y[:, self._y_index : self._y_index + self._L_x] = x
            self._y_index += self._L_x

            return None
        else:
            self._y[:, self._y_index :] = x[:, : free_space]
            self._y_index = 0
            self._x = x[:, free_space :]

            return self._y

class ArrayBuilder:
    def __init__(self, array_size, xp=np):
        assert array_size >= 1, 'Array size in packets must be at least 1'

        self._array_size = array_size
        self._xp = xp

        self._reset_block()

    def push(self, samples, gain, gx4_heading):
        self._block.append(samples)
        self._gains.append(gain)
        self._gx4_headings.append(gx4_heading)
        self._pkt_num += 1

        if self._pkt_num < self._array_size:
            return (None, None, None)
        else:
            sample_array = self._xp.array(self._block)
            y = self._xp.stack(self._xp.split(sample_array, const.NUM_CHS,
                axis=1)).reshape((const.NUM_CHS, -1))

            gain_array = self._xp.expand_dims(
                self._xp.array(self._gains).repeat(const.PKT_LEN), 0)

            gx4_heading_array = self._xp.expand_dims(
                self._xp.array(self._gx4_headings).repeat(const.PKT_LEN), 0)

            self._reset_block()

            return (y, gain_array, gx4_heading_array)

    def _reset_block(self):
        self._block = list()
        self._gains = list()
        self._gx4_headings = list()
        self._pkt_num = 0