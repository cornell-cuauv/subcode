#!/usr/bin/env python3

import shm
from mission.runner import run

async def main():
    init = shm.vision_modules.Record.get()
    shm.vision_modules.Record.set(1)
    input("Press enter to end this mission.")
    shm.vision_modules.Record.set(init)

if __name__ == '__main__':
    run(main(), 'record')
