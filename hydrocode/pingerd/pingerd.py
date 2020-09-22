#!/usr/bin/env python3

import sys

import numpy as np
try:
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
from pinger import plot
import pinger.const

print('Pingerd starting...')

shm.hydrophones_pinger_results.heading.set(0)
shm.hydrophones_pinger_results.elevation.set(0)

L_init = common.const.INIT_ARRAY_SIZE * common.const.PKT_LEN
L_interval = int(pinger.const.INTERVAL_DUR * common.const.SAMPLE_RATE)

brd = board.Board('pinger')
arr = pack.ArrayBuilder(common.const.INIT_ARRAY_SIZE, xp=xp)
raw_plt = plot.RawPlot(common.const.NUM_CHS, L_init, L_interval, xp=xp)

print('Listening for packets...\n');
(_, _, pkt_num) = brd.receive()
shm.hydrophones_pinger_status.packet_number.set(pkt_num)

while True:
    expected_pkt_num = (
        shm.hydrophones_pinger_status.packet_number.get() + 1)
    (samples, gain_lvl, pkt_num) = brd.receive()
    board.validate_pkt_num(pkt_num, expected_pkt_num)
    shm.hydrophones_pinger_status.packet_number.set(pkt_num)

    gain = common.const.GAIN_VALUES[gain_lvl]
    gx4_heading = shm.gx4.heading.get()

    (x, gain_array, gx4_heading_array) = arr.push(samples, gain, gx4_heading)
    if x is None:
        continue

    raw_plt.push(x, gain_array)

    x = x / gain_array