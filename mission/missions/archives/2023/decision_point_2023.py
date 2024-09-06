#!/usr/bin/env python3

from math import pi
import asyncio
from shm import hydrophones_pinger_results as hydrophones
from auv_python_helpers.angles import abs_heading_sub_degrees
from mission.framework.base import AsyncBase
from mission.framework.consistency import SHMConsistencyTracker
from mission.framework.dead_reckoning import heading_to_element
from mission.framework.movement import depth

class DecisionPoint2023(AsyncBase):
    def __init__(self):
        self.first_task = self.listen()

    def closer_to_torpedoes(self, hydrophones):
        reading = hydrophones.heading * 180 / pi
        diff_from_torpedoes = abs_heading_sub_degrees(reading,
                heading_to_element('torpedoes'))
        diff_from_octagon = abs_heading_sub_degrees(reading,
                heading_to_element('octagon'))
        return diff_from_torpedoes < diff_from_octagon

    def closer_to_octagon(self, hydrophones):
        return not self.closer_to_torpedoes(hydrophones)
    
    async def listen(self):
        await depth(1)
        torpedoes = SHMConsistencyTracker(hydrophones,
                self.closer_to_torpedoes, (9, 10))
        octagon = SHMConsistencyTracker(hydrophones,
                self.closer_to_octagon, (9, 10))
        while not torpedoes.consistent and not octagon.consistent:
            await asyncio.sleep(0.1)
        if torpedoes.consistent:
            return 'torpedoes'
        return 'octagon'

if __name__ == '__main__':
    DecisionPoint2023().run(debug=True)