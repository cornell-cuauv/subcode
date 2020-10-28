import math

import numpy as np
from scipy.signal import windows

from common import pack

class FIR:
    def __init__(self, num_chs, L_b, h, D=1, xp=np):
        assert num_chs >= 1, 'Filter must have at least one input channel'

        assert h.ndim == 1, 'Impulse response must be a 1D array'
        assert len(h) - 1 >= 0, 'FIR Order must be at least 0'

        assert D >= 1, 'Decimation factor must be at least 1'

        assert (len(h) - 1) % D == 0, (
            'FIR order must be a multiple of the decimation factor')
        assert L_b % D == 0, (
            'FIR block length must be a multiple of the decimation factor')

        self._num_chs = num_chs
        self._L_b = L_b
        self._D = D
        self._xp = xp

        self._overlap_samples = xp.zeros((num_chs, len(h) - 1), dtype=complex)

        self._L_ifft = (L_b + len(h) - 1) // D
        self._L_transient = (len(h) - 1) // D
        self._H = xp.fft.fft(h, n=(L_b + len(h) - 1))

        self._pkr = pack.Packer(L_b, xp=xp)

    def push(self, x):
        packed = self._pkr.push(x)
        if packed is not None:
            return self._push_filt(packed)

        return None

    def _push_filt(self, x):
        x = self._xp.concatenate((self._overlap_samples, x), axis=1)
        X = self._xp.fft.fft(x)

        Y = X * self._H
        Y = Y.reshape((self._num_chs, -1, self._L_ifft)).sum(axis=1) / self._D
        y = self._xp.fft.ifft(Y)
        y = y[:, self._L_transient :]

        self._overlap_samples = x[:, self._L_b :]

        return y

def firgauss(stopband, order, atten=60, xp=np):
    assert stopband > 0, 'Stopband must be greater than 0'
    assert order >= 0, 'Order must be at least 0'
    assert atten > 0, 'Attenuation at stopband must be greater than 0'

    std = 2 * math.sqrt(atten / 10 * math.log(10)) / stopband

    h = windows.gaussian(order + 1, std)
    h = xp.asarray(h)
    h /= h.sum()

    return (h, std)

def gauss_rise_time(std, rise_factor):
    assert rise_factor > 0, 'Rise factor must be greater than 0'

    return int(std * math.sqrt(2 * math.log(rise_factor)))