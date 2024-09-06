import shm

from mission.missions.master_missions.common import *

from mission.missions.prequal import goAroundBuoy

async def generator():
yield goAroundBuoy(), INFINITE_TIME
