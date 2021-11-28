#!/usr/bin/env python3

"""Hydrophone data dump replayer

Replays dumps over UDP. The packets look to pingerd or hydrocomms as if
they're coming from the actual board, except the gain cannot be
adjusted. Still, the real gain settings the data was taken at are
recorded within the packets. The dumps also contain information
specifying whether the packets must be sent to the pingerd or the
hydrocomms port.

Must be called with the dump file name as an argument.
"""

from os import path
import socket
import sys
import time

import numpy as np

sys.path.insert(0, path.join(
    path.dirname(path.dirname(path.realpath(__file__))), 'modules'))
import common.const
import comms.const
import pinger.const

def getSize(file):
    file.seek(0, 2)
    size = file.tell()
    return size

try:
    dump_filename = sys.argv[1]
except IndexError:
    raise Exception('Dump filename not specified')

dump_file = open(dump_filename, 'rb')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
pkt_size = common.const.SAMPLE_PKT_DTYPE.itemsize

print('Replaying ' + dump_filename + '...')

for pkt_num in range(getSize(dump_file) // pkt_size):
    # seek to the correct place in the binary file and load packet
    dump_file.seek(pkt_num * pkt_size)
    pkt_bytes = dump_file.read(pkt_size)
    pkt = np.frombuffer(pkt_bytes, dtype=common.const.SAMPLE_PKT_DTYPE)[0]

    # send packet to the correct port depending on its type
    if pkt['pkt_type'] == 0:
        sock.sendto(pkt_bytes, ('127.0.0.1', pinger.const.RECV_PORT))
    elif pkt['pkt_type'] == 1:
        sock.sendto(pkt_bytes, ('127.0.0.1', comms.const.RECV_PORT))
    else:
        raise ValueError('Valid packet types are 0 (pinger) and 1 (comms)')

    # wait for the amount of time the hydrophones board would take
    # to send another packet
    time.sleep(common.const.L_PKT / common.const.SAMPLE_RATE)