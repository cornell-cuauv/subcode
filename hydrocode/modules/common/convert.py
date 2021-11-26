import math

from common import const

def omega_hat(f):
    """Convert to angular frequency normalized to sampling rate.

    :param f: frequency (Hz)
    :return: normalized angular frequency (no units)
    """

    return 2 * math.pi * f / const.SAMPLE_RATE