import cmath

try:
    import cupy as xp
except ImportError:
    import numpy as xp

class Mixer:
    """Complex mixer (with two quadrature local oscillators)."""

    def __init__(self, L_x, ph=0, w=0):
        """Constructor.

        :param L_x: input block length, the amount of sample the mixer
            expects for an operation
        :param ph: local oscillator phase, defaults to 0
        :param w: local osciallator frequency, defaults to 0
        """

        assert L_x >= 1, 'Input block length must be at least 1'

        self._L_x = L_x
        self._ph = ph

        self.set_freq(w)

    def push(self, x):
        """Push a block of samples.

        :param x: input signal, must be L_x samples long
        :return: mixed signal
        """

        # update the samples of the local ocillator
        nco = cmath.exp(1j * self._ph) * self._offsets
        self._ph += self._w * self._L_x

        # mix
        y = x * nco

        return y

    def set_freq(self, w):
        """Set a new frequency for the local oscillator.

        :param w: new normalized frequency
        """

        self._offsets = xp.exp(1j * w * xp.arange(self._L_x))
        self._w = w

    def get_freq(self):
        """Get the frequency of the local oscillator.

        :return: normalized frequency of the local oscillator
        """

        return self._w