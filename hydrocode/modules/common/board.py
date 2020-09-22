import socket
import struct

import common.const
import pinger.const

class Board:
    def __init__(self, section):
        assert section == 'pinger', (
            'Board has two sections, "pinger" and "comms"')

        self._recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self._recv_buff = bytearray(common.const.NUM_CHS *
            common.const.PKT_LEN * 2 + common.const.PKT_HEADER_SIZE)
        self._config_buff = bytearray(common.const.CONFIG_PKT_SIZE)

        self._unpack_string = ('<bibh' +
            str(common.const.NUM_CHS * common.const.PKT_LEN) + 'h')
        self._pack_string = '<??b'

        if section == 'pinger':
            self._recv_sock.bind(('', pinger.const.RECV_PORT))
            self._send_port = pinger.const.SEND_PORT

        self.config()

    def receive(self):
        self._recv_sock.recv_into(self._recv_buff)
        data = struct.unpack(self._unpack_string, self._recv_buff)

        pkt_type = data[0]
        pkt_num = data[1]
        gain_lvl = data[2]
        max_sample = data[3]
        samples = data[4:]

        return (samples, gain_lvl, pkt_num)

    def config(self, reset=False, autogain=False, man_gain_lvl=0):
        assert 0 <= man_gain_lvl < 14, 'Gain level must be within [0, 13]'

        struct.pack_into(self._pack_string, self._config_buff, 0,
            bool(reset), bool(autogain), man_gain_lvl)

        self._send_sock.sendto(self._config_buff,
            (common.const.BOARD_ADDR, self._send_port))

def validate_pkt_num(actual, expected):
    if actual == 0:
        print('\nHydrophones board has resetted\n')
    elif actual != expected:
        print('\nSample packet discontinuity detected. Got ' +
              str(actual) + ' when expecting ' +
              str(expected) + '\n')