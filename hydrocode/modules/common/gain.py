try:
    import cupy as xp
except ImportError:
    import numpy as xp

from hydrocode.modules.common import const, gainplot, pack
from hydrocode.modules.common.hardware import HydrophonesSection
try:
    import shm
except ImportError:
    from hydrocode.modules.common import shm

class Controller:
    """Gain controller specific to our hardware and tasks.

    Supports three modes specified from shm:
    0 - Manual gain from shm
    1 - Host autogain, high latency, can be synchronized with pinger DSP
    2 - Board-level autogain, fast attack & low latency, good for comms
    """

    def __init__(self, section, L_interval, plot=False):
        """Constructor.

        :param section: section of the board to control, PINGER or COMMS
        :param L_interval: gain change time interval (samples)
        :param plot: True to produce gain plot, defaults to False
        """

        if section is HydrophonesSection.PINGER:
            self._shm_settings = shm.hydrophones_pinger_settings
            self._shm_settings.gain_control_mode.set(1)
        else:
            assert section is HydrophonesSection.COMMS, (
                'Hydrophones board has two sections, PINGER and COMMS')
            self._shm_settings = shm.hydrophones_comms_settings
            self._shm_settings.gain_control_mode.set(2)
        self._shm_settings.user_gain_lvl.set(13)

        self._plot = gainplot.GainPlot() if plot else None

        self._gain_values_array = xp.array(const.GAIN_VALUES)

        self._sig_pkr = pack.Packer(L_interval)
        self._gains_pkr = pack.Packer(L_interval)

    def push(self, sig, gains):
        """Push a block of samples.

        Returned gain configurations have structure
        (board autogain enable, manual/host gain setting)

        The samples themselves are technically needed only for the host
        autogain mode, but this is how the controller keeps track of
        time.

        :param sig: input signal
        :param gains: the gain level at which each sample was taken,
            must have the same length as sig
        :return: None if gain change interval has not elapsed
                 new gain configuration otherwise
        """

        packed_sig = self._sig_pkr.push(sig)
        packed_gains = self._gains_pkr.push(gains)

        if packed_sig is not None:
            if self._plot is not None:
                self._plot.plot(packed_sig, packed_gains)

            gain_ctrl_mode = self._shm_settings.gain_control_mode.get()
            if gain_ctrl_mode == 0: # user controls gain
                return (False, self._shm_settings.user_gain_lvl.get())
            elif gain_ctrl_mode == 1: # host (Python code) controls gain
                return (False, self._best_gain_lvl(packed_sig, packed_gains))
            else: # hydrophones board controls gain
                return (True, 0)

        return None

    def _best_gain_lvl(self, sig, gains):
        # Host autogain algorithm:
        # Pick the gain level that would have brought the highest sample
        # in the last interval as close as possible, but not above the
        # clipping threshold. Pinger Tracking DSP document explains why
        # this is good for pinger.

        peak = xp.abs(sig).max()
        peak_pos = xp.abs(sig).argmax() % sig.shape[1]
        gain_at_peak = gains[:, peak_pos]

        # the hypothetical value of the highest sample for all gain settings
        peak_for_gains = peak / gain_at_peak * self._gain_values_array

        desire = int((peak_for_gains < const.CLIP_THRESH).sum() - 1)

        return desire if desire > 0 else 0
