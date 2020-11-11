import numpy as np

from common import crop, pack
from pinger import pingplot, triggerplot

class Trigger:
    def __init__(self, L_interval, L_search, fir_rise_time,
        trigger_plot=False, ping_plot=False, xp=np):
        assert fir_rise_time >= 1, 'Filter rise time must be at least 1'

        self._L_interval = L_interval
        self._L_search = L_search
        self._fir_rise_time = fir_rise_time
        self._xp = xp

        if trigger_plot:
            self._trigger_plot = triggerplot.TriggerPlot(xp=xp)
        else:
            self._trigger_plot = None

        if ping_plot:
            self._ping_plot = pingplot.PingPlot(xp=xp)
        else:
            self._ping_plot = None

        self._pkr = pack.Packer(L_interval, xp=xp)

    def push(self, x):
        packed = self._pkr.push(x)
        if packed is not None:
            ampl = self._xp.abs(packed).sum(axis=0)
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
            ping = packed[:, ping_pos]

            if self._trigger_plot is not None:
                self._trigger_plot.push(ampl, trigger_f, ping_pos)

            if self._ping_plot is not None:
                self._ping_plot.push(packed, ping_pos)

            return ping

        return None