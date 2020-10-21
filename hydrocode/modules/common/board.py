import socket

import numpy as np

import common.const
import pinger.const

class Board:
    def __init__(self, section, pkts_per_recv, xp=np):
        assert section == 'pinger', (
            'Board has two sections, "pinger" and "comms"')

        assert pkts_per_recv >= 1, (
            'Must get at least one packet per reception')

        self._xp = xp

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(1)

        self._pkts_per_recv = pkts_per_recv
        self._recv_buff = bytearray(
            pkts_per_recv * common.const.RECV_PKT_DTYPE.itemsize)

        self._gain_values_array = xp.array(common.const.GAIN_VALUES)

        if section == 'pinger':
            self._sock.bind(('', pinger.const.RECV_PORT))
            self._send_port = pinger.const.SEND_PORT

        self.config()

    def receive(self):
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

        return self._unpack_recv_buff()

    def config(self, reset=False, autogain=False, man_gain_lvl=0):
        assert 0 <= man_gain_lvl < 14, 'Gain level must be within [0, 13]'

        config_buff = self._xp.array((reset, autogain, man_gain_lvl),
            dtype=common.const.CONFIG_PKT_DTYPE).tobytes()

        self._sock.sendto(config_buff,
            (common.const.BOARD_ADDR, self._send_port))

    def check_pkt_num(self, curr, last):
        if curr < self._pkts_per_recv:
            print('\nHydrophones board has resetted\n')

        lost = curr - last - self._pkts_per_recv
        if lost > 0:
            print('\nLost ' + str(lost) + ' packets\n')

    def _unpack_recv_buff(self):
        pkts = self._xp.frombuffer(self._recv_buff,
            dtype=common.const.RECV_PKT_DTYPE)

        pkt_num = pkts['pkt_num'][-1]
        gains = self._gain_values_array[pkts['gain_lvl']].reshape(
            (1, -1)).repeat(common.const.L_PKT, axis=1)
        samples = self._xp.concatenate(pkts['samples'], axis=1)

        return (pkt_num, gains, samples)