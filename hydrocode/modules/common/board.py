from enum import auto, Enum
from multiprocessing import Process, Queue
import queue
import socket

import numpy as np

import common.const
from common.retry import retry
import pinger.const
try:
    import shm
except ImportError:
    from common import shm

class Section(Enum):
    PINGER = auto()
    COMMS = auto()

class Board:
    def __init__(self, section, pkts_per_recv, dump=False, xp=np):
        assert pkts_per_recv >= 1, (
            'Must get at least one packet per reception')

        self._pkts_per_recv = pkts_per_recv
        self._xp = xp

        if section is Section.PINGER:
            section_const = pinger.const
            self._shm_status = shm.hydrophones_pinger_status
        else:
            assert section is Section.COMMS, (
                'Board has two sections, PINGER and COMMS')
            section_const = common.const
            self._shm_status = shm.hydrophones_comms_status

        self._dump_file = open("dump.dat", "wb") if dump else None

        self._gain_values_array = xp.array(common.const.GAIN_VALUES)

        recv_addr = ('', section_const.RECV_PORT)
        self._recv_q = Queue(maxsize=10)
        self._recv_process = Process(target=self._receive_worker, args=(
            self._recv_q, recv_addr, pkts_per_recv))
        self._recv_process.daemon = True

        send_addr = (common.const.BOARD_ADDR, section_const.SEND_PORT)
        self._send_q = Queue(maxsize=10)
        self._send_process = Process(target=self._send_worker, args=(
            self._send_q, send_addr))
        self._send_process.daemon = True

        self._recv_process.start()
        self._send_process.start()

        self.config()

        (recv_buff, _) = retry(self._recv_q.get, queue.Empty)(timeout=0.1)
        (pkt_num, _, _) = self._unpack_recv_buff(recv_buff)
        self._shm_status.packet_number.set(pkt_num)

    def receive(self):
        (buff, sub_hdgs) = retry(self._recv_q.get, queue.Empty)(timeout=0.1)
        if self._dump_file is not None:
            self._dump_file.write(buff)

        (pkt_num, gains, sig) = self._unpack_recv_buff(buff)
        sub_hdgs = self._xp.asarray(sub_hdgs).reshape(
            1, -1).repeat(common.const.L_PKT, axis=1)

        self._check_pkt_num(pkt_num, self._shm_status.packet_number.get())
        self._shm_status.packet_number.set(pkt_num)

        return (sig, gains, sub_hdgs)

    def config(self, reset=False, autogain=False, man_gain_lvl=0):
        assert 0 <= man_gain_lvl < 14, 'Gain level must be within [0, 13]'

        buff = self._xp.array((reset, autogain, man_gain_lvl),
            dtype=common.const.CONFIG_PKT_DTYPE).tobytes()

        retry(self._send_q.put, queue.Full)(buff, timeout=0.1)

    def _unpack_recv_buff(self, buff):
        pkts = self._xp.frombuffer(buff, dtype=common.const.RECV_PKT_DTYPE)

        pkt_num = pkts['pkt_num'][-1]
        gains = self._gain_values_array[pkts['gain_lvl']].reshape(
            (1, -1)).repeat(common.const.L_PKT, axis=1)
        samples = self._xp.concatenate(
            pkts['samples'], axis=1)[: 4 if common.const.USE_4CHS else 3]

        return (pkt_num, gains, samples)

    def _check_pkt_num(self, curr, last):
        if curr < self._pkts_per_recv:
            print('\nHydrophones board has resetted\n')

        lost = curr - last - self._pkts_per_recv
        if lost > 0:
            print('\nLost ' + str(lost) + ' packets\n')

    @staticmethod
    def _receive_worker(q, addr, pkts_per_recv):
        pkt_size = common.const.RECV_PKT_DTYPE.itemsize

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)
        sock.bind(addr)

        while True:
            buff = bytearray(pkts_per_recv * pkt_size)
            view = memoryview(buff)
            sub_hdgs = list()
            for pkt_num in range(pkts_per_recv):
                retry(sock.recv_into, socket.timeout)(view, nbytes=pkt_size)
                view = (view[pkt_size :])
                sub_hdgs.append(shm.gx4.heading.get())

            retry(q.put, queue.Full)((buff, sub_hdgs), timeout=0.1)

    @staticmethod
    def _send_worker(q, addr):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.1)

        while True:
            buff = retry(q.get, queue.Empty)(timeout=0.1)

            retry(sock.sendto, socket.timeout)(buff, addr)
