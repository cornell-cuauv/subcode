#!/usr/bin/env python3
import cv2
import time
import shm
import ctypes
import numpy as np

from conf.vehicle import cameras, is_mainsub

from vision.core.base import ModuleBase, VideoSource
from vision.core import tuners

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
            tuners.DoubleTuner('downward_blue_gain',-1, DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX),  
            tuners.DoubleTuner('downward_exposure', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX), 
            tuners.DoubleTuner('downward_green_gain', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX), 
            tuners.DoubleTuner('downward_red_gain', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX), 
            tuners.DoubleTuner('forward_blue_gain', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX), 
            tuners.DoubleTuner('forward_exposure', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX), 
            tuners.DoubleTuner('forward_green_gain', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX),
            tuners.DoubleTuner('forward_red_gain', -1,DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX),
            tuners.IntTuner('zed_brightness'   ,  4, 0, 8),
            tuners.IntTuner('zed_contrast'     ,   4, 0, 8),
            tuners.IntTuner('zed_hue'          ,   0, 0, 11),
            tuners.IntTuner('zed_saturation'   ,   4, 0, 8),
            tuners.IntTuner('zed_gamma'        ,   4, 0, 8),
            tuners.IntTuner('zed_sharpness'    ,   4, 0, 8),
            tuners.IntTuner('zed_white_balance',5000, 2800, 6500),
            tuners.IntTuner('zed_exposure'     ,  80, 0, 100),
            tuners.IntTuner('zed_gain'         ,  100, 0, 100)
        ]

    else:
        for o, t in shm.camera_calibration._fields:
            print(o)
            if t == ctypes.c_double:
                opts.append(tuners.DoubleTuner(o,
                                                getattr(
                                                    shm.camera_calibration, o).get(),
                                                DEFAULT_DOUBLE_MIN, DEFAULT_DOUBLE_MAX))
            elif t == ctypes.c_int:
                opts.append(tuners.IntTuner(o,
                                            getattr(
                                                shm.camera_calibration, o).get(),
                                            DEFAULT_INT_MIN, DEFAULT_INT_MAX))
        return opts


class Calibrate(ModuleBase):
    def __init__(self, directions):
        super().__init__(directions, build_opts())
        self.prev = {}

    def process(self, name, mat):
        for o, t in shm.camera_calibration._fields:
            opt_val = self.tuners[o]
            if not o in self.prev or not opt_val == self.prev[o]:
                getattr(shm.camera_calibration, o).set(opt_val)
                self.prev[o] = opt_val

        if name == 'depth':
            mat = cv2.normalize(mat, None, 255, 0, cv2.NORM_MINMAX, cv2.CV_8U)
            self.post(name, mat)
        elif name == 'normal':
            mat = np.clip((mat * 255), 0, 255.0).astype(np.uint8)
            self.post(name, mat)
        else:
            self.post(name, mat)


if __name__ == '__main__':
    Calibrate([VideoSource('forward'), VideoSource('forward2'), VideoSource('depth', short_type=np.float32), VideoSource('normal', short_type=np.float32)])()
