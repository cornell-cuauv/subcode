import math

try:
    import cupy as xp
except ImportError:
    import numpy as xp
from scipy.signal import windows

class FIR:
    """Finite impulse response filter with optional decimation.

    Performs fast convolution in the frequency domain using the
    overlap-save algorithm:

    M. Borgerding, "Turning overlap-save into a multiband mixing,
    downsampling filter bank," in IEEE Signal Processing Magazine, vol.
    23, no. 2, pp. 158-161, March 2006, doi: 10.1109/MSP.2006.1598092.
    """

    def __init__(self, num_chs, L_x, h, D=1):
        """Constructor.

        :param num_chs: number of channels in the signal
        :param L_x: input block length, the amount of sample the filter
            expects for an operation
        :param h: impulse response, order must be an integer multiple of
            the decimation factor
        :param D: decimation factor, defaults to 1
        """

        assert num_chs >= 1, 'Filter must have at least one input channel'

        assert h.ndim == 1, 'Impulse response must be a 1D array'
        assert len(h) - 1 >= 0, 'FIR Order must be at least 0'

        assert D >= 1, 'Decimation factor must be at least 1'

        assert (len(h) - 1) % D == 0, (
            'FIR order must be a multiple of the decimation factor')
        assert L_x >= 1, 'Input block length must be at least 1'
        assert L_x % D == 0, (
            'Input block length must be a multiple of the decimation factor')

        self._num_chs = num_chs
        self._L_x = L_x # L in paper
        self._D = D # D in paper

        # initialize overlap region with zeros
        self._overlap_samples = xp.zeros((num_chs, len(h) - 1), dtype=complex)

        self._L_ifft = (L_x + len(h) - 1) // D # N / D in paper
        self._L_transient = (len(h) - 1) // D # (P - 1) / D in paper
        self._H = xp.fft.fft(h, n=(L_x + len(h) - 1)) # FIR transfer function

    def push(self, x):
        """Push a block of samples.

        :param x: input signal, must be an array of shape (num_chs, L_x)
        :return: (num_chs, L_x / D) shaped filtered signal array
        """

        # concatenate overlap region to input and convert to frequency domain
        x = xp.concatenate((self._overlap_samples, x), axis=1)
        X = xp.fft.fft(x)

        # convolve in frequency domain
        Y = X * self._H

        # decimate
        Y = Y.reshape(self._num_chs, -1, self._L_ifft).sum(axis=1) / self._D

        # bring back to time domain and discard wrap-around
        y = xp.fft.ifft(Y)
        y = y[:, self._L_transient :]

        # update overlap region
        self._overlap_samples = x[:, self._L_x :]

        return y

def firgauss(stopband, order, atten=60):
    """Generate lowpass sampled gaussian impulse response.

    :param stopband: twice the frequency at which the attenuation reaches atten
    :param order: (number of samples at which to truncate impulse response) - 1
    :param atten: attenuation at stopband (dB), defaults to 60
    :return: impulse response
    """

    assert stopband > 0, 'Stopband must be greater than 0'
    assert order >= 0, 'Order must be at least 0'
    assert atten > 0, 'Attenuation at stopband must be greater than 0'

    # standard deviation (samples) in the time domain, check Wikipedia
    std = 2 * math.sqrt(atten / 10 * math.log(10)) / stopband

    # generate impulse response and normalize to unity gain
    h = xp.asarray(windows.gaussian(order + 1, std))
    h /= h.sum()

    return h

def gauss_rise_time(h):
    """Compute the rise time of a gaussian impulse response.

    Rise time is defined here as the number of samples it takes for the
    step response to rise from 1% to 99% of its final value.

    :param h: impulse response
    :return: rise time (samples)
    """

    low = 0.01
    high = 0.99

    assert len(h) - 1 >= 0, 'FIR Order must be at least 0'

    step_resp = h.cumsum()
    step_resp /= step_resp[-1]

    rise_t = int(xp.abs(step_resp - high).argmin() -
        xp.abs(step_resp - low).argmin())

    return rise_t