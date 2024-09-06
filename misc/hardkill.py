#!/usr/bin/env python3

import shm
import time

if __name__ == "__main__":
    while True:
        if shm.switches.hard_kill.get():
            shm.switches.soft_kill.set(1)
            time.sleep(0.05)
        else:
            time.sleep(0.1)
