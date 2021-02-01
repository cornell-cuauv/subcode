import numpy as np

from common import filt, pack
from comms import const, corrplot

class Synchronizer:
    def __init__(self, L_x, L_msg, samples_per_sym, pn_seq, orth_seq,
        plot=False, xp=np):
        assert L_x >= 1, 'Input block length must be at least 1'
        assert L_x < L_msg * samples_per_sym, (
            'Input block must be shorter than message length in samples')

        assert samples_per_sym >= 1, (
            'There must be at least one sample per symbol')

        assert len(pn_seq) >= 1, (
            'The PN sequence must have at least one symbol')
        assert len(pn_seq) == len(orth_seq), (
            'The PN/orthogonal sequence lengths must be equal')

        assert L_msg >= len(pn_seq), (
            'The transmission must be at least as long as the PN sequence')

        self._xp = xp

        self._L_pn_samples = len(pn_seq) * samples_per_sym
        self._L_msg_samples = L_msg * samples_per_sym
        L_transmission_samples = self._L_pn_samples + self._L_msg_samples

        h = xp.flip(xp.asarray(pn_seq, dtype=float).repeat(samples_per_sym))
        h /= len(h)
        self._pn_correlator = filt.FIR(1, L_x, h, xp=xp)

        h = xp.flip(xp.asarray(orth_seq, dtype=float).repeat(samples_per_sym))
        h /= len(h)
        self._orth_correlator = filt.FIR(1, L_x, h, xp=xp)

        h = xp.ones(const.L_THRESH_CALC) * const.THRESHOLD_FACTOR ** 2
        h /= len(h)
        self._thresh_accum = filt.FIR(1, L_x, h, xp=xp)

        self._plot = corrplot.CorrelationPlot(xp=xp) if plot else None

        self._transmission_pkr = pack.Packer(L_transmission_samples, xp=xp)

        self._triggered = False

    def push(self, sigs):
        msg = None

        corr_in = (sigs[-1] - sigs[0]).reshape(1, -1)
        corr_pn = self._pn_correlator.push(corr_in).real
        corr_orth = self._orth_correlator.push(corr_in).real
        thresh = self._xp.sqrt(self._thresh_accum.push(corr_orth ** 2).real)
        stacked = self._xp.concatenate(
            (corr_in, corr_pn, corr_orth, thresh, sigs))

        if self._triggered:
            transmission = self._transmission_pkr.push(stacked)
            if transmission is not None:
                (msg, stacked1) = self._extract_msg(transmission)
                stacked2 = self._transmission_pkr.get()
                stacked = self._xp.concatenate((stacked1, stacked2), axis=1)
                self._transmission_pkr.reset()
                self._triggered = False

                if self._plot is not None:
                    self._plot.plot(transmission[0].reshape(1, -1),
                                    transmission[1].reshape(1, -1),
                                    transmission[2].reshape(1, -1),
                                    transmission[3].reshape(1, -1))

        if not self._triggered:
            trig = self._xp.logical_and(stacked[1] >= const.SQUELCH_THRESH,
                                        stacked[1] >= stacked[3])
            if trig.any():
                self._transmission_pkr.push(stacked[:, trig.argmax() :])
                self._triggered = True

        return msg

    def _extract_msg(self, transmission):
        msg_start = transmission[1, : self._L_pn_samples].argmax() + 1
        msg_start = int(msg_start)
        msg_end = msg_start + self._L_msg_samples

        msg = transmission[4 :, msg_start : msg_end]
        remainder = transmission[:, msg_end :]

        return (msg, remainder)