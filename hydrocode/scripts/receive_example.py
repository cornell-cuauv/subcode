#!/usr/bin/env python3

from multiprocessing import Queue
import sys

sys.path.insert(0, '../')
import hydrocomms

if __name__ == '__main__':
    q = Queue(maxsize=1)
    r = hydrocomms.Receive(
        q,
        gain_plot=('-gain_plot' in sys.argv),
        correlation_plot=('-correlation_plot' in sys.argv),
        dump=('-dump' in sys.argv)
    )

    while True:
        print('Got message: ' + str(q.get()))