#!/usr/bin/env python3

from mission.runner import run
from mission.framework.position import move_x
from mission.framework.movement import relative_to_initial_heading

async def main():
    for i in range(4):
        await move_x(3, tolerance=0.3)
        await relative_to_initial_heading(90,tolerance=10)

run(main(), 'square')
