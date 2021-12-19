"""Code for transmitting and receiving comms

The Transmit and Receive classes are meant to be instantiated only once
each (though possibly by different scripts). They have a simple
interface, where the client creates and shares a thread-safe data queue
during instantiation. Byte messages of the correct size can be put into
the transmit queue of one sub, and they will show up in the receive
queue of the other. Messages are not retransmitted if lost, and there is
no error detection.
"""

from os import path
import queue
import sys
from threading import Thread

try:
    import cupy as xp
except ImportError:
    import numpy as xp

sys.path.insert(0, path.join(path.dirname(path.realpath(__file__)), 'modules'))
from common import convert, downconv, filt, gain, hardware
import common.const
from comms import demodulate, synchronize
import comms.const

class Receive:
    """Implements comms reception."""

    def __init__(self, q, gain_plot=False, correlation_plot=False, dump=False):
        """Constructor.

        :param q: receive queue to put messages in, must be thread-safe
        :param gain_plot: True to produce gain plot, defaults to False
        :param correlation_plot: True to produce correlation plot,
            defaults to False
        :param dump: True to dump raw data to disk, defaults to False
        """

        self._daemon_thread = Thread(target=self._daemon,
            args=(q, gain_plot, correlation_plot, dump), daemon=True)
        self._daemon_thread.start()

    @staticmethod
    def _daemon(q, gain_plot, correlation_plot, dump):
        # gain controller, normally used by hydrocomms in board autogain mode
        gainctrl = gain.Controller(
            hardware.HydrophonesSection.COMMS,
            int(comms.const.DUR_GAIN_INTERVAL * common.const.SAMPLE_RATE),
            plot=gain_plot,
        )

        # signal is split into channels, one for every symbol
        # each channel has its own downconverter tuned to the frequency
        # corresponding to the symbol
        # at a high level, the transmitted symbol can be decided by checking
        # which channel has the greatest amplitude
        num_symbols = 2 ** comms.const.SYMBOL_SIZE
        symbol_spacing = comms.const.BANDWIDTH / (num_symbols - 1)
        symbol_stopband = comms.const.SYMBOL_STOPBAND_FRAC * 2 * symbol_spacing
        h = filt.firgauss(
            convert.omega_hat(symbol_stopband),
            comms.const.FIR_ORDER,
        )
        symbols = (comms.const.RX_FREQ - comms.const.BANDWIDTH / 2 +
            xp.arange(num_symbols) * symbol_spacing)
        dwncnvs = []
        for symbol in symbols:
            dwncnvs.append(
                downconv.Downconverter(
                    4 if common.const.USE_4CHS else 3,
                    comms.const.L_FIR_BLOCK,
                    h,
                    D=comms.const.DECIM_FACTOR,
                    w=(convert.omega_hat(symbol)),
                )
            )

        # synchronizer finds the beginning of transmissions and returns the
        # section in the downconverted signals that corresponds to the message
        sync = synchronize.Synchronizer(
            comms.const.MSG_BYTES * 8 // comms.const.SYMBOL_SIZE + 1,
            comms.const.L_SYM,
            comms.const.PN_SEQ,
            comms.const.ORTH_SEQ,
            plot=correlation_plot,
        )

        # hydrophones driver obtains sample packets from the hydrophones board
        # and sends configuration packets
        hydrobrd = hardware.HydrophonesBoard(
            hardware.HydrophonesSection.COMMS,
            common.const.PKTS_PER_RECV,
            dump=dump,
        )

        # this superloop executes once each time the board driver delivers a
        # new batch of packets
        while True:
            (sig, gains, _) = hydrobrd.receive()

            gainctrl_result = gainctrl.push(sig, gains)
            if gainctrl_result is not None:
                (brd_ag, gain_lvl_desire) = gainctrl_result
                hydrobrd.config(autogain=brd_ag, man_gain_lvl=gain_lvl_desire)

            # normalize signal by dividing each sample to the gain it was taken
            # at in order to prevent sudden jumps in the signal
            sig = sig / gains

            symbol_sigs = []
            for symbol_num in range(num_symbols):
                symbol_sig = dwncnvs[symbol_num].push(sig)
                if symbol_sig is not None:

                    # all three/four hydrophones channels have their amplitudes
                    # summed up after downconversion, phase doesn't matter
                    symbol_sigs.append(xp.abs(symbol_sig).sum(axis=0))
            if len(symbol_sigs) == num_symbols:
                symbol_sigs = sync.push(xp.stack(symbol_sigs))
                if symbol_sigs is not None:
                    syms = demodulate.decide(symbol_sigs, comms.const.L_SYM)
                    msg = demodulate.decode(syms[1 :], comms.const.SYMBOL_SIZE)
                    try:
                        q.put_nowait(msg)
                    except queue.Full:
                        print('\nComms Rx queue full. Lost transmission.\n')

class Transmit:
    """Implements comms transmission."""

    def __init__(self, q):
        """Constructor.

        :param q: transmit queue to put messages in, must be thread-safe
        """

        self._daemon_thread = Thread(target=self._daemon,
            args=(q,), daemon=True)
        self._daemon_thread.start()

    @staticmethod
    def _daemon(q):
        # PN code header is created here, will be added automatically to each
        # message
        num_symbols = 2 ** comms.const.SYMBOL_SIZE
        head = comms.const.PN_SEQ + [-1]
        head_symbols = (xp.asarray(head) == 1) * (num_symbols - 1)
        head_bytes = demodulate.decode(head_symbols, comms.const.SYMBOL_SIZE)

        # transmit board driver sends messages and transmission configurations
        # to the board via Serial
        transbrd = hardware.TransmitBoard()

        # this superloop executes once for each message sent by the client
        while True:
            msg = q.get()
            if type(msg) is not bytes:
                raise TypeError('Expected bytes object, got ' + str(type(msg)))
            if len(msg) != comms.const.MSG_BYTES:
                raise ValueError('Message size must be ' +
                    str(comms.const.MSG_BYTES) + ' bytes')

            transbrd.send(head_bytes + msg)