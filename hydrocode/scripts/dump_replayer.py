#!/usr/bin/env python3

# Script for replaying raw hydrophones data dumps.
# Read Hydrophones Code wiki entry for more details.

import socket
import struct
import sys
import time

sys.path.insert(0, '../modules')
import common.const
import pinger.const

# get binary file size
def getSize(file):
    file.seek(0, 2)
    size = file.tell()
    return size

# check whether dump filename was specified
try:
    dump_filename = sys.argv[1]
except IndexError:
    print('Dump filename not specified')
    raise

 # load binary file specified from terminal
dump_file = open(dump_filename, 'rb')

pkt_type = struct.unpack('<b', dump_file.read(1))[0]
if pkt_type == 0:
    port = pinger.const.RECV_PORT
elif pkt_type == 1:
    port = comms.const.RECV_PORT
else:
    raise ValueError('Valid packet types are 0 (pinger) and 1 (comms)')

# initialize UDP networking
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
pkt_size = (common.const.NUM_CHS * common.const.L_PKT * 2 +
    common.const.PKT_HEADER_SIZE)

print('Replaying ' + dump_filename + '...')

# send packets
for pkt_num in range(getSize(dump_file) // pkt_size):
    dump_file.seek(pkt_num * pkt_size)
    sock.sendto(dump_file.read(pkt_size), ('127.0.0.1', port))

    # wait for the amount of time the hydrophones board would take
    # to send another packet
    time.sleep(common.const.L_PKT / common.const.SAMPLE_RATE)