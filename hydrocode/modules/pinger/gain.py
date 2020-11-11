import numpy as np

from common import const, gainplot, pack
try:
    import shm
except ImportError:
    from common import shm

class Controller:
    def __init__(self, L_interval, plot=False, xp=np):
        self._xp = xp

        if plot:
            self._plot = gainplot.GainPlot(xp=xp)
        else:
            self._plot = None

        self._gain_values_array = xp.array(const.GAIN_VALUES)

        self._sig_pkr = pack.Packer(L_interval, xp=xp)
        self._gains_pkr = pack.Packer(L_interval, xp=xp)

    def push(self, sig, gains):
        packed_sig = self._sig_pkr.push(sig)
        packed_gains = self._gains_pkr.push(gains)

        if packed_sig is not None:
            if self._plot is not None:
                self._plot.push(packed_sig, packed_gains)

            if shm.hydrophones_pinger_settings.user_gain_control.get():
                return shm.hydrophones_pinger_settings.user_gain_lvl.get()
            else:
                return self._best_gain_lvl(packed_sig, packed_gains)

        return None

    def _best_gain_lvl(self, sig, gains):
        peak = self._xp.abs(sig).max()
        peak_pos = self._xp.abs(sig).argmax() % sig.shape[1]
        gain_at_peak = gains[:, peak_pos]

        peak_for_gains = peak / gain_at_peak * self._gain_values_array

        gain_lvl_desire = (peak_for_gains < const.CLIPPING_THRESHOLD).sum() - 1
        gain_lvl_desire = int(gain_lvl_desire)
        if gain_lvl_desire < 0:
            gain_lvl_desire = 0

        return gain_lvl_desire