from common import pack

class Decimator:
    """Signal Decimator.

    Although Downconverter can be used for decimation without mixing and
    filtering, that would be inefficient because a convolution would
    still be perfomred.
    """

    def __init__(self, L_b, D=1):
        """Constructor.

        :param L_b: block length, the amount of samples to accumulate
            before peforming an operation and returning a result, must
            be an integer multiple of the decimation factor
        :param D: decimation factor, defaults to 1
        """

        assert L_b % D == 0, (
            'Decimation block length must be a multiple of the dec. factor')

        self._D = D

        self._pkr = pack.Packer(L_b)

    def push(self, x):
        """Push a block of samples.

        :param x: input signal, must be an array of shape (..., L) where
            L <= L_b
        :return: None if accumulated less than L_b samples
                 (..., L_b / D) shaped output signal array otherwise
        """

        packed = self._pkr.push(x)
        if packed is not None:
            return packed[:, : : self._D]

        return None