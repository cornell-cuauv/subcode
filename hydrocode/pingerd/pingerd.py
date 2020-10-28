#!/usr/bin/env python3

import math
import sys

import numpy as np
try:
    raise ImportError
    import cupy as xp
    print('Using CuPy\n')
except ImportError:
    xp = np

sys.path.insert(0, '../modules')

from common import board, convert, downconv, filt
import common.const
from pinger import gain, trigger
import pinger.const

try:
    import shm
except ImportError:
    from common import shm

print('Pingerd starting...')

L_recv = common.const.PKTS_PER_RECV * common.const.L_PKT
L_interval = int(pinger.const.DUR_INTERVAL * common.const.SAMPLE_RATE)

gainctrl = gain.Controller(L_interval, plot=('-gain_plot' in sys.argv), xp=xp)

(h, fir_std) = filt.firgauss(
    convert.omega_hat(pinger.const.STOPBAND), pinger.const.FIR_ORDER, xp=xp)
dwncnv = downconv.Downconverter(
    common.const.NUM_CHS,
    L_recv,
    pinger.const.L_BLOCK_FIR,
    h,
    D=pinger.const.DECIM_FACTOR,
    w=(convert.omega_hat(shm.hydrophones_pinger_settings.frequency.get())),
    xp=xp
)

fir_rise_time = filt.gauss_rise_time(fir_std, pinger.const.FIR_RISE_FACTOR)
trig = trigger.Trigger(
    L_interval // pinger.const.DECIM_FACTOR,
    pinger.const.L_SEARCH,
    fir_rise_time // pinger.const.DECIM_FACTOR,
    plot=('-trigger_plot' in sys.argv),
    xp=xp
)

brd = board.Board(board.Section.PINGER, common.const.PKTS_PER_RECV,
    dump=('-dump' in sys.argv), xp=np)

while True:
    (gains, sig) = brd.receive()
    gains = xp.asarray(gains)
    sig = xp.asarray(sig)

    sub_headings = shm.gx4.heading.get() * xp.ones((1, L_recv))

    gain_lvl_desire = gainctrl.push(sig, gains)
    if gain_lvl_desire is not None:
        brd.config(man_gain_lvl=gain_lvl_desire)

    sig = sig / gains

    sig = dwncnv.push(sig)
    if sig is not None:
        ping = trig.push(sig)
        if ping is not None:
            pass



