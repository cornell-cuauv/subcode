from mission.framework.combinators import Sequential
from mission.framework.primitive import FunctionTask

from hydrocode.scripts.udp_set_gain import set_gain

import shm

Configure = Sequential(
    FunctionTask(set_gain),
    FunctionTask(lambda: shm.hydrophones_settings.track_frequency_target.set(39500)),
    FunctionTask(lambda: shm.hydrophones_settings.track_magnitude_threshold.set(20000)),
)
