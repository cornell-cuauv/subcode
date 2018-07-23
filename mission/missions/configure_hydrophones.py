from mission.framework.combinators import Sequential
from mission.framework.primitive import FunctionTask

import shm

Configure = Sequential(
    FunctionTask(lambda: shm.hydrophones_settings.track_frequency_target.set(39500)),
    FunctionTask(lambda: shm.hydrophones_settings.track_magnitude_threshold.set(11000)),
)
