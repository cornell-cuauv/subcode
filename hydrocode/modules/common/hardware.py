import itertools
from enum import auto, Enum
import queue
import socket
from threading import Thread
import time

try:
    import cupy as xp
except ImportError:
    import numpy as xp
import numpy as np

import common.const 
from hydrocode.modules.common.retry import retry 
import comms.const
import pinger.const
try:
    import shm
except ImportError:
    from hydrocode.modules.common import shm

class HydrophonesSection(Enum):
    PINGER = auto()
    COMMS = auto()

class HydrophonesBoard:
    """Driver for hydrophones board.

    Receives samples and transmits configuration settings via UDP.
    """

    def __init__(self, section, pkts_per_recv, dump=False):
        """Constructor.

        :param section: section of the board to address, PINGER or COMMS
        :param pkts_per_recv: number of packets to receive in driver for
            one call (batch size)
        :param dump: True to dump raw data to disk, defaults to False
        """

        assert pkts_per_recv >= 1, (
            'Must get at least one packet per reception')

        self._pkts_per_recv = pkts_per_recv

        if section is HydrophonesSection.PINGER:
            section_const = pinger.const
            self._shm_status = shm.hydrophones_pinger_status
            # switch channels [0, 1] -> [1, 0], [2, 3] -> [3, 2]
            # (minor screw-up on the hydrophones board)
            self._switch_ch_order = True
        else:
            assert section is HydrophonesSection.COMMS, (
                'Hydrophones board has two sections, PINGER and COMMS')
            section_const = comms.const
            self._shm_status = shm.hydrophones_comms_status
            self._switch_ch_order = False

        self._dump_file = open('dump.dat', 'wb') if dump else None

        self._gain_val_array = np.array(common.const.GAIN_VALUES)

        recv_addr = ('', section_const.RECV_PORT)
        self._recv_q = queue.Queue(maxsize=1000)
        self._recv_thread = Thread(target=self._receive_daemon,
            args=(self._recv_q, recv_addr, pkts_per_recv), daemon=True)

        send_addr = (common.const.BOARD_ADDR, section_const.SEND_PORT)
        self._send_q = queue.Queue(maxsize=10)
        self._send_thread = Thread(target=self._send_daemon,
            args=(self._send_q, send_addr), daemon=True)

        self._recv_thread.start()
        self._send_thread.start()

        self.config()

        # do one reception without validating packet number, since board sends
        # packets before script starts
        (recv_buff, _) = retry(self._recv_q.get, queue.Empty)(timeout=0.1)
        (pkt_num, _, _) = self._unpack_recv_buff(recv_buff)
        self._shm_status.packet_number.set(pkt_num)

    def receive(self):
        """Receive one block of samples.

        The hydrophones board also includes the gain level at which each
        sample packet was taken. These levels are translated to gain
        values using a lookup array and returned together with the
        samples, one value for each sample. The method also returns a
        Kalman-reported heading of the sub for each sample, but all of
        the samples in a packet actually share the same reading.

        Note: Blocking method.

        :return: hydrophones board output and corresponding sub headings
        """

        (buff, sub_hdgs) = retry(self._recv_q.get, queue.Empty)(timeout=0.1)
        if self._dump_file is not None:
            self._dump_file.write(buff)

        (pkt_num, gains, sig) = self._unpack_recv_buff(buff)

        # repeat sub headings to get one for each sample
        sub_hdgs = np.asarray(sub_hdgs).reshape(1, -1).repeat(
            common.const.L_PKT, axis=1)

        self._check_pkt_num(pkt_num, self._shm_status.packet_number.get())
        self._shm_status.packet_number.set(pkt_num)

        # 012, 102, 021, 201, 210*, 120
        #sig = np.array(list(itertools.permutations(sig))[12][:-1])
        #print(list(itertools.permutations([0, 1, 2, 3]))[12][:-1])

        return (xp.asarray(sig), xp.asarray(gains), xp.asarray(sub_hdgs))

    def config(self, reset=False, autogain=False, man_gain_lvl=0):
        """Send a configuration packet to the hydrophones board.

        :param reset: True to reset the MCU, defaults to False
        :param autogain: True to enable board-level autogain, defaults
            to False
        :param man_gain_lvl: gain level setting in case autogain is
            False, defaults to 0
        """

        assert 0 <= man_gain_lvl < 14, 'Gain level must be within [0, 13]'

        buff = np.array((reset, autogain, man_gain_lvl),
            dtype=common.const.CONF_PKT_DTYPE).tobytes()
        try:
            self._send_q.put_nowait(buff)
        except queue.Full:
            pass

    def _unpack_recv_buff(self, buff):
        # Unpack received bytes to metadata and samples.
        # CuPy doesn't support frombuffer, so use NumPy and convert
        # later.

        pkts = np.frombuffer(buff, dtype=common.const.SAMPLE_PKT_DTYPE)

        pkt_num = pkts['pkt_num'][-1]

        # repeat gain level to get one for each sample and apply the
        # gain level -> gain value lookup array
        gains = self._gain_val_array[pkts['gain_lvl']].reshape(1, -1).repeat(
            common.const.L_PKT, axis=1)

        samples = np.concatenate(pkts['samples'], axis=1)
        if self._switch_ch_order:
            samples[[0, 1]] = samples[[1, 0]]
            samples[[2, 3]] = samples[[3, 2]]
        samples = samples[: 4 if common.const.USE_4CHS else 3]

        return (pkt_num, gains, samples)

    def _check_pkt_num(self, curr, last):
        # Validate packet number and print if any packets got lost.

        # this prints if the last received batch of packets contains
        # packets numbered 0 through N where N is smaller than the batch
        # size, which can only happen if the board boots after the
        # script has been started
        if curr < self._pkts_per_recv:
            print('\nHydrophones board resetted\n')

        # if the current packet number is greater than the last by more
        # than the batch size, packets got lost
        lost = curr - last - self._pkts_per_recv
        if lost > 0:
            print('\nLost ' + str(lost) + ' packets\n')

    @staticmethod
    def _receive_daemon(q, addr, pkts_per_recv):
        # Receive thread. Communicates with the main thread via a shared
        # safe queue. This is needed to ensure a buffer, so that no
        # packets are lost if the DSP code momentarily can't process
        # them fast enough.

        pkt_size = common.const.SAMPLE_PKT_DTYPE.itemsize

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(addr)

        while True:
            buff = bytearray(pkts_per_recv * pkt_size)
            view = memoryview(buff)
            sub_hdgs = []

            # this has to be super tight because it runs for every packet
            # received from the hydrophones board
            for pkt_num in range(pkts_per_recv):
                # receiving directly into memoryview, zero copy
                sock.recv_into(view, nbytes=pkt_size)
                view = (view[pkt_size :])
                sub_hdgs.append(shm.kalman.heading.get())
            try:
                q.put_nowait((buff, sub_hdgs))
            except queue.Full:
                pass

    @staticmethod
    def _send_daemon(q, addr):
        # Send thread. Communicates with the main thread via a shared
        # safe queue.

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while True:
            buff = q.get()

            sock.sendto(buff, addr)

class TransmitBoard:
    """Driver for transmit board.

    Sends data and modulation settings via Serial.
    """

    def __init__(self):
        """Constructor."""

        shm.transmit_settings.symbol_size.set(comms.const.SYMBOL_SIZE)
        shm.transmit_settings.symbol_rate.set(common.const.SAMPLE_RATE /
            comms.const.DECIM_FACTOR / comms.const.L_SYM)
        shm.transmit_settings.freq.set(comms.const.TX_FREQ)
        shm.transmit_settings.bandwidth.set(comms.const.BANDWIDTH)

        shm.transmit_streaming.word.set(0)
        shm.transmit_streaming.new_data.set(False)

    def send(self, data):
        """Send one message.

        :param data: bytes to send
        """

        # four phase handshake for each byte
        for byte in data:
            shm.transmit_streaming.word.set(byte)

            shm.transmit_streaming.new_data.set(True)
            while not shm.transmit_streaming.ack.get():
                time.sleep(comms.const.SERIAL_UPDATE_TIME)

            shm.transmit_streaming.new_data.set(False)
            while shm.transmit_streaming.ack.get():
                time.sleep(comms.const.SERIAL_UPDATE_TIME)
