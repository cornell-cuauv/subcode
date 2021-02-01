import numpy as np

from common import crop, pack
from pinger import pingplot, trigplot

class Trigger:
    def __init__(self, L_interval, L_search, fir_rise_time,
        trigger_plot=False, ping_plot=False, xp=np):
        assert fir_rise_time >= 1, 'Filter rise time must be at least 1'

        self._L_interval = L_interval
        self._L_search = L_search
        self._fir_rise_time = fir_rise_time
        self._xp = xp

        self._trigger_plot = (
            trigplot.TriggerPlot(xp=xp) if trigger_plot else None)
        self._ping_plot = pingplot.PingPlot(xp=xp) if ping_plot else None

        self._sig_pkr = pack.Packer(L_interval, xp=xp)
        self._sub_hdgs_pkr = pack.Packer(L_interval, xp=xp)

    def push(self, sig, sub_hdgs):
        packed_sig = self._sig_pkr.push(sig)
        packed_sub_hdgs = self._sub_hdgs_pkr.push(sub_hdgs)
        if packed_sig is not None:
            ampl = self._xp.abs(packed_sig).sum(axis=0)
            ampl_delayed = self._xp.roll(ampl, self._fir_rise_time)
            mean_ampl = ampl.mean()

            trigger_f = (ampl + mean_ampl) / (ampl_delayed + mean_ampl)
            trigger_f[: self._fir_rise_time] = 0

            ampl_peak_pos = ampl.argmax()
            ampl_peak_pos = int(ampl_peak_pos)
            (search_start, search_end) = crop.find_bounds(
                self._L_interval, self._L_search, ampl_peak_pos)

            ping_pos = trigger_f.argmax()
            ping_pos = int(ping_pos)
            ping_phase = self._xp.angle(packed_sig[:, ping_pos])
            sub_hdg = packed_sub_hdgs[0, ping_pos]

            if self._trigger_plot is not None:
                self._trigger_plot.plot(ampl, trigger_f, ping_pos)

            if self._ping_plot is not None:
                self._ping_plot.plot(packed_sig, ping_pos)

            return (ping_phase, sub_hdg)

        return None