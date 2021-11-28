#!/usr/bin/env python3

"""Example client for hydrocomms transmit

Allows user to specify ASCII messages of the correct size, and transmits
them using hydrocomms.
"""

import multiprocessing
from os import path
import queue
import sys

sys.path.insert(0, path.dirname(path.dirname(path.realpath(__file__))))
import hydrocomms

if __name__ == '__main__':
    # using the Linux default (fork) for starting processes introduces
    # concurency problems with multithreaded programs, and also requires a hack
    # to make Matplotlib work
    multiprocessing.set_start_method('spawn')

    q = queue.Queue(maxsize=1)
    t = hydrocomms.Transmit(q)

    while True:
        try:
            s = input('Enter ASCII string: ')
            msg = s.encode('ascii')
        except UnicodeEncodeError as e:
            print(e)
            continue

        while True:
            try:
                q.put(msg, timeout=0.1)
                break
            except queue.Full:
                pass