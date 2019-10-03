#!/usr/bin/env python3
import time
import shm
import ctypes

from conf.vehicle import cameras

from vision.modules.base import ModuleBase, _PsuedoOptionsDict
from vision import options

directions = cameras.keys()

# o = [
#         ("double", "{}_blue_gain", 0.0, 50.0),
#         ("double", "{}_exposure", 0.0, 50.0),
#         ("double", "{}_green_gain", 0.0, 50.0),
#         ("double", "{}_red_gain", 0.0, 50.0),
#         ]

opts = []

DEFAULT_DOUBLE_MAX = 100.0
DEFAULT_DOUBLE_MIN = 0.0
DEFAULT_INT_MAX = 50
DEFAULT_INT_MIN = 0

for o, t in shm.camera_calibration._fields:
    print(o)
    if t == ctypes.c_double:
        opts.append(options.DoubleOption(o, getattr(shm.camera_calibration, o).get(), DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX))
    elif t == ctypes.c_int:
        opts.append(options.IntOption(o, getattr(shm.camera_calibration, o).get(), DEFAULT_INT_MIN, DEFAULT_INT_MAX))


class Calibrate(ModuleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process(self, *mats):
        for o, t in shm.camera_calibration._fields:
            getattr(shm.camera_calibration, o).set(self.options[o])

        for d, m in zip(directions, mats):
            self.post(d, m)


if __name__ == '__main__':
    Calibrate(directions, opts)()
