#!/usr/bin/env python3

"""Example client for hydrocomms receive

Prints ASCII messages received over hydrocomms.

Options: --gain_plot        to produce gain plot
         --correlation_plot to produce correlation plot
         --dump             to dump raw hydrophones data to disk
"""

import multiprocessing
from os import path
import queue
import sys

sys.path.insert(0, path.dirname(path.dirname(path.realpath(__file__))))
import hydrocomms

if __name__ == '__main__':
    print('Listening for comms...')

    # using the Linux default (fork) for starting processes introduces
    # concurency problems with multithreaded programs, and also requires a hack
    # to make Matplotlib work
    multiprocessing.set_start_method('spawn')

    q = queue.Queue(maxsize=1)
    r = hydrocomms.Receive(
        q,
        gain_plot=('--gain_plot' in sys.argv),
        correlation_plot=('--correlation_plot' in sys.argv),
        dump=('--dump' in sys.argv)
    )

    while True:
        try:
            print('Got message: ' + str(q.get(timeout=0.1)))
        except queue.Empty:
            pass