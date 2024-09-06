try:
    import cupy as xp
except ImportError:
    import numpy as xp

from hydrocode.modules.common import filt, pack
from comms import const, corrplot

class Synchronizer:
    """Transmission detector and clock symbol synchronizer.

    In the absence of a clock signal, the receiver must indentify
    the beginning of transmissions and synchronize a local clock to the
    sequence of symbols received from the transmitter. If the
    transmission header always contains a section known to the receiver,
    the peak of a free-running correlation can be used to identify
    the transmission and recover the symbol timing. See Section 7.3.3
    in:

    B. Benson et al., "Design of a low-cost, underwater acoustic modem
    for short-range sensor networks," OCEANS'10 IEEE SYDNEY, 2010, pp.
    1-9, doi: 10.1109/OCEANSSYD.2010.5603816.
    """

    def __init__(self, L_msg, L_sym, pn_seq, orth_seq, plot=False):
        """Constructor.

        :param L_msg: message size (bytes)
        :param L_sym: symbol length (samples after decimation)
        :param pn_seq: PN code transmitted before each message
        :param orth_seq: Any PN code orthogonal to the first
        :param plot: True to produce correlation plot, defaults to False
        """

        assert L_sym >= 1, 'There must be at least one sample per symbol'

        assert len(pn_seq) >= 1, (
            'The PN sequence must have at least one symbol')
        assert len(pn_seq) == len(orth_seq), (
            'The PN/orthogonal sequence lengths must be equal')

        assert L_msg >= len(pn_seq), (
            'The message must be at least as long as the PN sequence')

        self._L_pn_samples = len(pn_seq) * L_sym
        self._L_msg_samples = L_msg * L_sym
        L_transmission_samples = self._L_pn_samples + self._L_msg_samples

        # correlators are implemented using FIR filters
        # PN sequence is flipped because we want correlation, not convolution
        h = xp.flip(xp.asarray(pn_seq, dtype=float).repeat(L_sym), axis=0)
        h /= len(h)
        self._pn_correlator = filt.FIR(1, L_transmission_samples - 1, h)

        h = xp.flip(xp.asarray(orth_seq, dtype=float).repeat(L_sym), axis=0)
        h /= len(h)
        self._orth_correlator = filt.FIR(1, L_transmission_samples - 1, h)

        # dynamic threshold calculator needs a moving average
        h = xp.ones(const.L_THRESH_CALC) * const.THRESHOLD_FACTOR ** 2
        h /= len(h)
        self._thresh_accum = filt.FIR(1, L_transmission_samples - 1, h)

        self._plot = corrplot.CorrelationPlot() if plot else None

        self._input_pkr = pack.Packer(L_transmission_samples - 1)
        self._transmission_pkr = pack.Packer(L_transmission_samples)

        self._triggered = False

    def push(self, x):
        """Push a block of samples.

        If a transmission occured, the returned signal starts at the
        first sample of the message. It can be directly chpped into
        sections of L_sym length to separate the symbols in time.

        :param x: array where each row represents the samples in one
            downconversion channel (corresponding to one symbol type)
        :return: the samples of the message if a transmission occured,
                 None otherwise
        """

        # we only want to perform operations when enough samples have
        # accumulated, otherwise the correlation operation may be inefficient
        packed = self._input_pkr.push(x)
        if packed is not None:
            return self._sync(packed)

        return None

    def _sync(self, x):
        # Check for a transmission and synchronize if triggered.
        # Triggering happens when the output of the PN code correlator
        # exceeds both the static (squelch) and the dynamic threshold.
        # Triggering may happen prematurely, before the end of the PN
        # sequence, so the signal is recorded but not immediately
        # declared to represent a valid message. Once the grace period
        # after the initial triggering (L_transmission_samples) ends,
        # the message is extracted beginning from the point where
        # the PN code correlator attained its maximum value.

        msg = None

        # the correlator input is the amplitude on the highest frequency symbol
        # channel minus the amplitude on the lowest frequency symbol channel
        # because the symbols farthest spaced are the easiest to distinguish
        corr_in = (x[-1] - x[0]).reshape(1, -1)
        corr_pn = xp.abs(self._pn_correlator.push(corr_in))
        corr_orth = xp.abs(self._orth_correlator.push(corr_in))
        thresh = xp.sqrt(xp.abs(self._thresh_accum.push(corr_orth ** 2)))
        stacked = xp.concatenate((corr_in, corr_pn, corr_orth, thresh, x))

        # triggering had previously occured
        if self._triggered:
            transmission = self._transmission_pkr.push(stacked)

            # grace period over
            if transmission is not None:
                (msg, stacked_r1) = self._extract_msg(transmission)
                stacked_r2 = self._transmission_pkr.get()
                stacked = xp.concatenate((stacked_r1, stacked_r2), axis=1)
                self._transmission_pkr.reset()
                self._triggered = False

                if self._plot is not None:
                    self._plot.plot(transmission[0].reshape(1, -1),
                                    transmission[1].reshape(1, -1),
                                    transmission[2].reshape(1, -1),
                                    transmission[3].reshape(1, -1))

        # idle, awaiting triggering
        if not self._triggered:
            trig = xp.logical_and(stacked[1] >= const.SQUELCH_THRESH,
                                  stacked[1] >= stacked[3])
            if trig.any():
                self._transmission_pkr.push(stacked[:, trig.argmax() :])
                self._triggered = True

        return msg

    def _extract_msg(self, transmission):
        # Get message from a signal recording taken after triggering.

        msg_start = int(transmission[1, : self._L_pn_samples].argmax() + 1)
        msg_end = msg_start + self._L_msg_samples

        msg = transmission[4 :, msg_start : msg_end]
        remainder = transmission[:, msg_end :]

        return (msg, remainder)