from hydrocode.modules.common import filt, mix, pack

class Downconverter:
    """IQ Downconverter with optional decimation.

    Mixes input signal with a complex local oscillator of specified
    frequency and phase, and filters the result with a specified impulse
    response.
    """

    def __init__(self, num_chs, L_b, h, D=1, ph=0, w=0):
        """Constructor.

        :param num_chs: number of channels in the signal
        :param L_b: block length, the amount of samples to accumulate
            before peforming an operation and returning a result, must
            be an integer multiple of the decimation factor
        :param h: impulse response of the applied filter, order must be
            an integer multiple the decimation factor
        :param D: decimation factor, defaults to 1
        :param ph: local oscillator phase, defaults to 0
        :param w: downconversion frequency, positive value results in
            negative frequency shift, defaults to 0
        """

        self._mixr = mix.Mixer(L_b, ph=ph, w=-w) # -w for DOWN conversion
        self._filtr = filt.FIR(num_chs, L_b, h, D=D)

        self._pkr = pack.Packer(L_b)

    def push(self, x):
        """Push a block of samples.

        :param x: input signal, must be an array of shape (num_chs, L)
            where L <= L_b
        :return: None if accumulated less than L_b samples
                 (num_chs, L_b / D) shaped output signal array otherwise
        """

        packed = self._pkr.push(x)
        if packed is not None:
            return self._filtr.push(self._mixr.push(packed))

        return None

    def set_freq(self, w):
        """Set a new downconversion frequency.

        :param w: new normalized frequency
        """

        self._mixr.set_freq(-w) # -w for DOWN conversion

    def get_freq(self):
        """Get the downconversion frequency.

        :return: normalized downconversion frequency
        """

        return -self._mixr.get_freq()