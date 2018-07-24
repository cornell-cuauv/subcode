from mission.framework.combinators import Sequential
from mission.framework.primitive import FunctionTask

from hydrocode.scripts.udp_set_gain import set_gain

import shm

from mission.constants.region import PINGER_FREQUENCY
from mission.constants.config import track

Configure = Sequential(
    FunctionTask(set_gain),
    FunctionTask(lambda: shm.hydrophones_settings.track_frequency_target.set(PINGER_FREQUENCY)),
    FunctionTask(lambda: shm.hydrophones_settings.track_magnitude_threshold.set(track.track_mag_thresh)),
)
