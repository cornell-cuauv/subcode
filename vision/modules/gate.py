#!/usr/bin/env python3
import shm
import cv2
import numpy as np

from vision import options
from vision.modules.base import ModuleBase
from vision.framework.transform import resize, simple_gaussian_blur
from vision.framework.helpers import to_umat  # , from_umat
from vision.framework.color import bgr_to_lab, range_threshold


OPTS = [
         options.DoubleOption('placeholder', 0.0, 0, 1),
       ]


class Gate(ModuleBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process(self, *mats):
        mat = to_umat(mats[0])
        self.post('mat', mat)


if __name__ == '__main__':
    Gate('forward', OPTS)()
