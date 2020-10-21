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
from pinger import gain, rawplot
import pinger.const

print('Pingerd starting...')

shm.hydrophones_pinger_results.heading.set(0)
shm.hydrophones_pinger_results.elevation.set(0)

L_recv = common.const.PKTS_PER_RECV * common.const.L_PKT
L_interval = int(pinger.const.INTERVAL_DUR * common.const.SAMPLE_RATE)

gainctrl = gain.Controller(common.const.NUM_CHS, L_recv, L_interval, xp=xp)

if '-raw_plot' in sys.argv:
    raw_plt = rawplot.RawPlot(common.const.NUM_CHS, L_recv, L_interval, xp=xp)

brd = board.Board('pinger', common.const.PKTS_PER_RECV, xp=np)
(pkt_num, _, _,) = brd.receive()
shm.hydrophones_pinger_status.packet_number.set(pkt_num)

while True:
    (pkt_num, gains, x) = brd.receive()
    gains = xp.asarray(gains)
    x = xp.asarray(x)

    brd.check_pkt_num(
        pkt_num, shm.hydrophones_pinger_status.packet_number.get())
    shm.hydrophones_pinger_status.packet_number.set(pkt_num)

    gx4_headings = shm.gx4.heading.get() * xp.ones((1, L_recv))

    gain_lvl_desire = gainctrl.push(x, gains)
    if gain_lvl_desire is not None:
        brd.config(man_gain_lvl=gain_lvl_desire)

    if 'raw_plt' in globals():
        raw_plt.push(x, gains)

    x = x / gains
