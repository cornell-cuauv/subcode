#!/usr/bin/env python3

import sys
import time
import math
import threading
import random
import shm

SECS_BETWEEN_PINGS = 2
MAX_ERROR = 2

pingers = []
with open(sys.path[0] + '/world.cfg', 'r') as f:
    curr_obj = None
    while True:
        line = f.readline()
        if len(line.strip()) == 0:
            continue
        if line.strip()[0] == '{':
            curr_obj = {}
        if len(line.strip()) == 1:
            continue
        if line.strip()[-2:] == '},':
            if 'pinger_name' in curr_obj:
                name = curr_obj['pinger_name'][1:-1]
                north, east, _ = curr_obj['position'][1:-1].split(',')
                pingers.append({
                    'name': name,
                    'north': float(north),
                    'east': float(east)
                })
            curr_obj = None
        if curr_obj != None:
            if '=' in line:
                var, _, val = line.partition('=')
                curr_obj[var.strip()] = val.strip()
        if line.strip()[-1] == ')':
            break

if len(pingers) == 0:
    print('No pingers found in world.cfg. Aborting.')
    sys.exit(0)

print(f'\nFound {len(pingers)} pinger(s):')
for pinger in pingers:
    print(f'> Pinger with name "{pinger["name"]}" at ({pinger["north"]}, {pinger["east"]})')

enabled_pinger = None
def pinger_thread():
    while True:
        if enabled_pinger == None:
            time.sleep(0.1)
        else:
            dn = enabled_pinger['north'] - shm.kalman.north.get()
            de = enabled_pinger['east'] - shm.kalman.east.get()
            heading = math.atan2(de, dn)
            heading += (2 * random.random() * MAX_ERROR - MAX_ERROR / 2) * math.pi / 180
            shm.hydrophones_pinger_results.heading.set(heading)
            time.sleep(SECS_BETWEEN_PINGS)

print()
thread = threading.Thread(target=pinger_thread)
thread.start()
while True:
    enabled_pinger = None
    input(f'All pingers are off. Press enter to turn on the {pingers[0]["name"]} pinger.')
    for i in range(len(pingers) - 1):
        enabled_pinger = pingers[i]
        input(f'The {pingers[i]["name"]} pinger is on. Press enter to switch to the {pingers[i + 1]["name"]} pinger.')
    enabled_pinger = pingers[-1]
    input(f'The {pingers[-1]["name"]} pinger is on. Press enter to turn off all pingers.')
    print()
