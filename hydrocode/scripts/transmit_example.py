#!/usr/bin/env python3

import multiprocessing
from os import path
import queue
import sys

sys.path.insert(0, path.dirname(path.dirname(path.realpath(__file__))))
import hydrocomms

if __name__ == '__main__':
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