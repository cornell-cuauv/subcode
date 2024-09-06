try:
    import cupy as xp
except ImportError:
    import numpy as xp

from hydrocode.modules.common import crop, pack
from hydrocode.modules.pinger import pingplot, trigplot

class Trigger:
    """Ping rising edge detector.

    Finds the most likely position for the rising edge of the ping in a
    ping processing interval, and extracts phases just after it. AKA
    Vlad's only meaningful contribution to this project team. Algorithm
    is described in the Pinger Tracking DSP document.
    """

    def __init__(self, L_interval, L_search, fir_rise_time,
        trigger_plot=False, ping_plot=False):
        """Constructor.

        :param L_interval: ping processing interval length (samples
            after decimation)
        :param L_search: # length of the interval around the highest
            signal amplitude in which to look for the rising edge
            (samples after decimation)
        :param fir_rise_time: rise time of the gaussian filter used in
            downconversion (samples after decimation)
        :param trigger_plot: True to produce trigger plot, defaults to
            False
        :param ping_plot: True to produce ping plot, defaults to False
        """

        assert fir_rise_time >= 1, 'Filter rise time must be at least 1'

        self._L_interval = L_interval
        self._L_search = L_search
        self._fir_rise_time = fir_rise_time

        self._trigger_plot = (
            trigplot.TriggerPlot() if trigger_plot else None)
        self._ping_plot = pingplot.PingPlot() if ping_plot else None

        self._sig_pkr = pack.Packer(L_interval)
        self._sub_hdgs_pkr = pack.Packer(L_interval)

    def push(self, sig, sub_hdgs):
        """Push a block of samples.

        :param sig: the downconverted signal
        :param sub_hdgs: the decimated sub headings from Kalman,
            still synchronized to the signal
        :return: the extracted phases, along with the heading of the sub
            at the extraction point
        """

        packed_sig = self._sig_pkr.push(sig)
        packed_sub_hdgs = self._sub_hdgs_pkr.push(sub_hdgs)
        if packed_sig is not None:
            # find A[n], A[n - tau_r], and A_avg in the Pinger Tracking DSP
            # document
            ampl = xp.abs(packed_sig).sum(axis=0)
            ampl_delayed = xp.roll(ampl, self._fir_rise_time)
            mean_ampl = ampl.mean()

            # find f_trigger[n] in the document
            trigger_f = (ampl + mean_ampl) / (ampl_delayed + mean_ampl)
            trigger_f[: self._fir_rise_time] = 0

            # look for a rising edge only in a short interval centered on the
            # highest signal amplitude
            ampl_peak_pos = int(ampl.argmax())
            (search_start, search_end) = crop.find_bounds(
                self._L_interval, self._L_search, ampl_peak_pos)
            trigger_f[: search_start] = 0
            trigger_f[search_end :] = 0

            # extract phases
            ping_pos = int(trigger_f.argmax())
            ping_phase = xp.angle(packed_sig[:, ping_pos])
            sub_hdg = packed_sub_hdgs[0, ping_pos]

            if self._trigger_plot is not None:
                self._trigger_plot.plot(ampl, trigger_f, ping_pos)

            if self._ping_plot is not None:
                self._ping_plot.plot(packed_sig, ping_pos)

            return (ping_phase, sub_hdg)

        return None