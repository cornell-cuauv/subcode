import math

import numpy as np
from scipy.signal import windows

class FIR:
    def __init__(self, init, h, L, D=1, xp=np):
        assert init.ndim == 2, 'FIR must be initialized with a 2D array'
        assert init.shape[0] >= 1, 'FIR must have at least one input channel'

        assert h.ndim == 1, 'Impulse response must be a 1D array'
        assert len(h) >= 1, 'Impulse response length must be at least 1'

        assert L >= 1, 'Data block length must be at least 1'

        assert D >= 1, 'Decimation factor must be at least 1'

        assert init.shape[1] == len(h) - 1, (
            'Initialization array must have a width equal to the FIR order')
        assert (len(h) - 1) % D == 0, (
            'FIR order must be a multiple of the decimation factor')
        assert L % D == 0, (
            'Data block length must be a multiple of the decimation factor')

        self._overlap_samples = init
        self._num_chs = init.shape[0]

        self._ifft_len = (L + len(h) - 1) // D
        self._transient_len = (len(h) - 1) // D
        self._H = xp.fft.fft(h, n=(L + len(h) - 1))

        self._L = L

        self._D = D

        self._xp = xp

    def push(self, x):
        x = self._xp.concatenate((self._overlap_samples, x), axis=1)
        X = self._xp.fft.fft(x)

        Y = X * self._H
        Y = Y.reshape((self._num_chs, -1, self._ifft_len)
            ).sum(axis=1) / self._D
        y = self._xp.fft.ifft(Y)
        y = y[:, self._transient_len :]

        self._overlap_samples = x[:, self._L :]

        return y

def firgauss(stopband, atten=60, truncate=10, xp=np):
    assert stopband > 0, 'Stopband must be greater than 0'
    assert atten > 0, 'Attenuation at stopband must be greater than 0'
    assert truncate > 0, 'Number of std devs captured must be greater than 0'

    std = 2 * math.sqrt(atten / 10 * math.log(10)) / stopband
    h = windows.gaussian(math.ceil(truncate * std), std)
    h = xp.array(h)
    h /= h.sum()

    return h