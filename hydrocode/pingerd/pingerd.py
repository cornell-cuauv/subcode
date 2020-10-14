#!/usr/bin/env python3

import sys

import numpy as np
try:
    raise ImportError
    import cupy as xp
    print('Using CuPy\n')
except ImportError:
    xp = np

sys.path.insert(0, '../modules')

try:
    import shm
except ImportError:
    print('Warning: SHM not present. Using SHM spoofer\n')
    from common import shm

from common import board, filt, mix, pack
import common.const
from pinger import gain, plot
import pinger.const

print('Pingerd starting...')

shm.hydrophones_pinger_results.heading.set(0)
shm.hydrophones_pinger_results.elevation.set(0)

L_recv = common.const.PKTS_PER_RECV * common.const.L_PKT
L_interval = int(pinger.const.INTERVAL_DUR * common.const.SAMPLE_RATE)

gain_ctrl = gain.Controller()

if '-raw_plot' in sys.argv:
    raw_plt = plot.RawPlot(
        common.const.NUM_CHS, L_recv, L_interval, xp=xp)

brd = board.Board('pinger', common.const.PKTS_PER_RECV, xp=np)
(_, _, pkt_num) = brd.receive()
shm.hydrophones_pinger_status.packet_number.set(pkt_num)

while True:
    (x, gains, pkt_num) = brd.receive()
    x = xp.asarray(x)
    gains = xp.asarray(gains)
    
    brd.check_pkt_num(
        pkt_num, shm.hydrophones_pinger_status.packet_number.get())
    shm.hydrophones_pinger_status.packet_number.set(pkt_num)

    gx4_headings = shm.gx4.heading.get() * xp.ones((1, L_recv))

    if 'raw_plt' in globals():
        raw_plt.push(x, gains)

    x = x / gains
