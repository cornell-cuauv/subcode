import numpy as np

from common import const, gainplot, pack
from common.hardware import HydrophonesSection
try:
    import shm
except ImportError:
    from common import shm

class Controller:
    def __init__(self, section, L_interval, plot=False, xp=np):
        self._xp = xp

        if section is HydrophonesSection.PINGER:
            self._shm_settings = shm.hydrophones_pinger_settings
        else:
            assert section is HydrophonesSection.COMMS, (
                'Hydrophones board has two sections, PINGER and COMMS')
            self._shm_settings = shm.hydrophones_comms_settings

        self._plot = gainplot.GainPlot(xp=xp) if plot else None

        self._gain_values_array = xp.array(const.GAIN_VALUES)

        self._sig_pkr = pack.Packer(L_interval, xp=xp)
        self._gains_pkr = pack.Packer(L_interval, xp=xp)

    def push(self, sig, gains):
        packed_sig = self._sig_pkr.push(sig)
        packed_gains = self._gains_pkr.push(gains)

        if packed_sig is not None:
            if self._plot is not None:
                self._plot.plot(packed_sig, packed_gains)

            gain_ctrl_mode = self._shm_settings.gain_control_mode.get()
            if gain_ctrl_mode == 0:
                return (False, self._shm_settings.user_gain_lvl.get())
            elif gain_ctrl_mode == 1:
                return (False, self._best_gain_lvl(packed_sig, packed_gains))
            else:
                return (True, 0)

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