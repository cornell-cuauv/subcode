import numpy as np

from common import const, pack

class Controller:
    def __init__(self, num_sig_chs, L_x, L_interval, xp=np):
        self._gain_values_array = xp.array(const.GAIN_VALUES)

        self._sig_pkr = pack.Packer(num_sig_chs, L_x, L_interval, xp=xp)
        self._gain_pkr = pack.Packer(1, L_x, L_interval, xp=xp)

    def push(self, x, gains):
        packed_sig = self._sig_pkr.push(x)
        packed_gains = self._gain_pkr.push(gains)

        if packed_sig is not None:
            return self._best_gain(packed_sig, packed_gains)

    def _best_gain(self, sig, gains):
        peak = np.abs(sig).max()
        print("peak: " + str(peak))
        peak_pos = np.abs(sig).argmax() % sig.shape[1]
        print("peak pos: " + str(peak_pos))
        gain_at_peak = gains[:, peak_pos]
        print("gain_at_peak: " + str(gain_at_peak))

        peak_for_gains = peak / gain_at_peak * self._gain_values_array
        print("peak_for_gains: " + str(peak_for_gains))

        gain_lvl_desire = (peak_for_gains < const.CLIPPING_THRESHOLD).sum() - 1
        if gain_lvl_desire < 0:
            gain_lvl_desire = 0
        print("gain_lvl_desire: " + str(gain_lvl_desire))

        gain_desire = self._gain_values_array[gain_lvl_desire]
        print("gain_desire: " + str(gain_desire))

        return gain_lvl_desire



