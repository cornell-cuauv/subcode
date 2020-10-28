import numpy as np

from common import crop, pack
from pinger import triggerplot

class Trigger:
    def __init__(self, L_interval, L_search, fir_rise_time, plot=False, xp=np):
        assert fir_rise_time >= 1, 'Filter rise time must be at least 1'

        self._L_interval = L_interval
        self._L_search = L_search
        self._fir_rise_time = fir_rise_time
        self._xp = xp

        if plot:
            self._plot = triggerplot.TriggerPlot(xp=xp)
        else:
            self._plot = None

        self._pkr = pack.Packer(L_interval, xp=xp)

    def push(self, x):
        packed = self._pkr.push(x)
        if packed is not None:
            sep_ampl = self._xp.abs(packed)
            ampl = sep_ampl.sum(axis=0)
            ampl_delayed = self._xp.roll(ampl, self._fir_rise_time)
            mean_ampl = ampl.mean()

            trigger_function = (ampl + mean_ampl) / (ampl_delayed + mean_ampl)
            trigger_function[: self._fir_rise_time] = 0

            ampl_peak_pos = ampl.argmax()
            (search_start, search_end) = crop.find_bounds(
                self._L_interval, self._L_search, ampl_peak_pos)

            ping_pos = trigger_function.argmax()
            ping = packed[:, ping_pos]

            if self._plot is not None:
                self._plot.push(ampl, trigger_function, sep_ampl, ping_pos)

            return ping

        return None