#!/usr/bin/env python3

from multiprocessing import Queue
import sys

sys.path.insert(0, '../')
import hydrocomms

if __name__ == '__main__':
    q = Queue(maxsize=1)
    t = hydrocomms.Transmit(q)

    while True:
        try:
            s = input('Enter ASCII string: ')
            msg = s.encode('ascii')
        except UnicodeEncodeError as e:
            print(e)
            continue

        q.put(msg)