from enum import Enum, auto
import socket

import numpy as np

import common.const
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

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(1)
        if section is Section.PINGER:
            self._sock.bind(('', pinger.const.RECV_PORT))
            self._send_port = pinger.const.SEND_PORT
            self._shm_status = shm.hydrophones_pinger_status
        else:
            assert section is Section.COMMS, (
                'Board has two sections, PINGER and COMMS')
            self._sock.bind(('', comms.const.RECV_PORT))
            self._send_port = comms.const.SEND_PORT
            self._shm_status = shm.hydrophones_comms_status

        self._recv_buff = bytearray(
            pkts_per_recv * common.const.RECV_PKT_DTYPE.itemsize)

        if dump:
            self._dump_file = open("dump.dat", "wb")
        else:
            self._dump_file = None

        self._gain_values_array = xp.array(common.const.GAIN_VALUES)

        self.config()

        self._receive_bytes()
        (pkt_num, _, _) = self._unpack_recv_buff()
        self._shm_status.packet_number.set(pkt_num)

    def receive(self):
        self._receive_bytes()
        (pkt_num, gains, sig) = self._unpack_recv_buff()

        self._check_pkt_num(pkt_num, self._shm_status.packet_number.get())
        self._shm_status.packet_number.set(pkt_num)

        return (gains, sig)

    def config(self, reset=False, autogain=False, man_gain_lvl=0):
        assert 0 <= man_gain_lvl < 14, 'Gain level must be within [0, 13]'

        config_buff = self._xp.array((reset, autogain, man_gain_lvl),
            dtype=common.const.CONFIG_PKT_DTYPE).tobytes()

        self._sock.sendto(config_buff,
            (common.const.BOARD_ADDR, self._send_port))

    def _receive_bytes(self):
        recv_buff_view = memoryview(self._recv_buff)
        recv_pkts = 0
        while recv_pkts < self._pkts_per_recv:
            try:
                self._sock.recv_into(recv_buff_view,
                    nbytes=common.const.RECV_PKT_DTYPE.itemsize)

                recv_buff_view = (
                    recv_buff_view[common.const.RECV_PKT_DTYPE.itemsize :])

                recv_pkts += 1
            except socket.timeout:
                pass

        if self._dump_file is not None:
            self._dump_file.write(self._recv_buff)

    def _unpack_recv_buff(self):
        pkts = self._xp.frombuffer(self._recv_buff,
            dtype=common.const.RECV_PKT_DTYPE)

        pkt_num = pkts['pkt_num'][-1]
        gains = self._gain_values_array[pkts['gain_lvl']].reshape(
            (1, -1)).repeat(common.const.L_PKT, axis=1)
        samples = self._xp.concatenate(pkts['samples'], axis=1)

        return (pkt_num, gains, samples)

    def _check_pkt_num(self, curr, last):
        if curr < self._pkts_per_recv:
            print('\nHydrophones board has resetted\n')

        lost = curr - last - self._pkts_per_recv
        if lost > 0:
            print('\nLost ' + str(lost) + ' packets\n')