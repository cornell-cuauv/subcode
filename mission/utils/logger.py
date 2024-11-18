import os
import shm

from auvlog.client import Logger

class MissionLogger(Logger):
    def __init__(self, tree):
        super().__init__(tree)

    def __call__(self, message):
        if shm.active_mission.active.get():
            mission_log_path = os.path.join(
                shm.active_mission.log_path.get(),
                "mission.log" 
            )
        else:
            mission_log_path = None
        super().__call__(message, copy_to_stdout=True, copy_to_file=mission_log_path)

    def __getattr__(self, key):
        return MissionLogger(self.tree + [key])

mission_logger = MissionLogger([])

