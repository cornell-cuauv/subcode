#!/usr/bin/env python3

"""Pinger tracking daemon

Meant to run in the background and update SHM variables with the heading
and elevation of the last detected ping, which are used by the pinger
tracking mission. The reported heading is a sum of the sub heading from
Kalman and the relative heading of the pinger to the sub, computed from
the hydrophone signals. Reporting relative headings is bad because the
sub may turn around before the results are posted to SHM.

Options: --gain_plot    to produce gain plot
         --trigger_plot to produce trigger plot
         --ping_plot    to produce ping plot
         --heading_plot to produce heading plot
         --scatter_plot to produce scatter plot
         --dump         to dump raw hydrophones data to disk
"""

import multiprocessing
from os import path
import sys

try:
    import cupy as xp
except ImportError:
    import numpy as xp

sys.path.insert(0, path.join(path.dirname(path.realpath(__file__)), 'modules'))
from hydrocode.modules.common import convert, downconv, filt, gain, hardware
import common.const
from hydrocode.modules.pinger import angles, decimate, trigger
import pinger.const
try:
    import shm
except ImportError:
    from hydrocode.modules.common import shm

if __name__ == '__main__':
    print('Pingerd starting...')

    # using the Linux default (fork) for starting processes introduces
    # concurency problems with multithreaded programs, and also requires a hack
    # to make Matplotlib work
    multiprocessing.set_start_method('spawn')

    L_INTERVAL = int(pinger.const.DUR_INTERVAL * common.const.SAMPLE_RATE)

    # gain controller, normally used by pingerd in host autogain mode
    gainctrl = gain.Controller(
        hardware.HydrophonesSection.PINGER,
        L_INTERVAL,
        plot=('--gain_plot' in sys.argv),
    )

    # downconverter brings tracked pinger signals to baseband and filters out
    # signals from other pingers
    h = filt.firgauss(
        convert.omega_hat(pinger.const.STOPBAND),
        pinger.const.FIR_ORDER,
    )
    freq = shm.hydrophones_pinger_settings.frequency.get()
    if freq not in pinger.const.USUAL_FREQS:
        print('Warning: Tracking unusual frequency ' + str(freq) + ' Hz')
        print('Track frequency must be set manually in shm')
    dwncnv = downconv.Downconverter(
        4 if common.const.USE_4CHS else 3,
        pinger.const.L_FIR_BLOCK,
        h,
        D=pinger.const.DECIM_FACTOR,
        w=(convert.omega_hat(freq)),
    )

    # recorded sub headings must be kept in sync with the hydrophones signals,
    # which get decimated during downconversion
    subhdgsdecim = decimate.Decimator(
        pinger.const.L_FIR_BLOCK,
        D=pinger.const.DECIM_FACTOR,
    )

    # trigger identifies the beginning of pings and extracts phases before
    # multipath propagation corrupts the signal
    fir_rise_time = filt.gauss_rise_time(h)
    trig = trigger.Trigger(
        L_INTERVAL // pinger.const.DECIM_FACTOR,
        pinger.const.L_SEARCH,
        fir_rise_time // pinger.const.DECIM_FACTOR,
        trigger_plot=('--trigger_plot' in sys.argv),
        ping_plot=('--ping_plot' in sys.argv),
    )

    # maximum likelihood estiator obtains heading and elevation angles from the
    # phase differences
    anglmle = angles.AnglesMLE(
        heading_plot=('--heading_plot' in sys.argv),
        scatter_plot=('--scatter_plot' in sys.argv)
    )

    # hydrophones driver obtains sample packets from the hydrophones board and
    # sends configuration packets
    hydrobrd = hardware.HydrophonesBoard(
        hardware.HydrophonesSection.PINGER,
        common.const.PKTS_PER_RECV,
        dump=('--dump' in sys.argv),
    )

    # this superloop executes once each time the board driver delivers a new
    # batch of packets
    while True:
        (sig, gains, sub_hdgs) = hydrobrd.receive()
        sub_hdgs = xp.radians(sub_hdgs)

        gainctrl_result = gainctrl.push(sig, gains)
        if gainctrl_result is not None:
            (brd_ag, gain_lvl_desire) = gainctrl_result
            hydrobrd.config(autogain=brd_ag, man_gain_lvl=gain_lvl_desire)

        # normalize signal by dividing each sample to the gain it was taken at
        # in order to prevent sudden jumps in the signal
        sig = sig / gains

        # the DSP modules instantiated earlier accumulate samples, and once
        # they reach enough to perform an operation, they return a result
        # instead of None
        sig = dwncnv.push(sig)
        sub_hdgs = subhdgsdecim.push(sub_hdgs)
        if sig is not None:
            trig_result = trig.push(sig, sub_hdgs)
            if trig_result is not None:
                (ping_phase, sub_hdg) = trig_result
                (hdg, elev) = anglmle.hdg_elev(ping_phase, dwncnv.get_freq())
                abs_hdg = angles.wrap_angle(sub_hdg + hdg)
                shm.hydrophones_pinger_results.heading.set(abs_hdg)
                shm.hydrophones_pinger_results.elevation.set(elev)
                print('Relative HDG: ' + '{:.2f}'.format(hdg) +
                    ' Relative ELEV: ' + '{:.2f}'.format(elev))

                dwncnv.set_freq(convert.omega_hat(
                    shm.hydrophones_pinger_settings.frequency.get()))