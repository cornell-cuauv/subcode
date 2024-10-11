#!/usr/bin/env python3
import time
import shm
import ctypes

from conf.vehicle import cameras, is_mainsub

from vision.modules.base import ModuleBase, _PsuedoOptionsDict
from vision import options

directions = list(cameras.keys())
print(directions)

opts = []

DEFAULT_DOUBLE_MAX = 100.0
DEFAULT_DOUBLE_MIN = 0.0
DEFAULT_INT_MAX = 50
DEFAULT_INT_MIN = 0

def build_opts():
    if is_mainsub:
        return [
            options.DoubleOption('downward_blue_gain',-1, DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX),  
            options.DoubleOption('downward_exposure', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX), 
            options.DoubleOption('downward_green_gain', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX), 
            options.DoubleOption('downward_red_gain', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX), 
            options.DoubleOption('forward_blue_gain', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX), 
            options.DoubleOption('forward_exposure', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX), 
            options.DoubleOption('forward_green_gain', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX),
            options.DoubleOption('forward_red_gain', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX),
            options.IntOption('zed_brightness'   ,  4, 0, 8),
            options.IntOption('zed_contrast'     ,   4, 0, 8),
            options.IntOption('zed_hue'          ,   0, 0, 11),
            options.IntOption('zed_saturation'   ,   4, 0, 8),
            options.IntOption('zed_gamma'        ,   4, 0, 8),
            options.IntOption('zed_sharpness'    ,   4, 0, 8),
            options.IntOption('zed_white_balance',5000, 2800, 6500),
            options.IntOption('zed_exposure'     ,  80, 0, 100),
            options.IntOption('zed_gain'         ,  100, 0, 100)
        ]

    else:
        for o, t in shm.camera_calibration._fields:
            print(o)
            if t == ctypes.c_double:
                opts.append(options.DoubleOption(o,
                                                 getattr(shm.camera_calibration, o).get(),
                                                 DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX))
            elif t == ctypes.c_int:
                opts.append(options.IntOption(o,
                                              getattr(shm.camera_calibration, o).get(),
                                              DEFAULT_INT_MIN, DEFAULT_INT_MAX))
        return opts


class Calibrate(ModuleBase):
    def __init__(self, directions):
        super().__init__(directions, build_opts())

        self.prev = {}

    def process(self, *mats):
        for o, t in shm.camera_calibration._fields:
            opt_val = self.options[o]
            if not o in self.prev or not opt_val == self.prev[o]:
                getattr(shm.camera_calibration, o).set(opt_val)
                self.prev[o] = opt_val

        for d, m in zip(directions, mats):
            self.post(d, m)


if __name__ == '__main__':
    Calibrate(directions)()
