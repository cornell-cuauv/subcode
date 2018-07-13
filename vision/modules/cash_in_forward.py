#!/usr/bin/env python3
from vision.modules.base import ModuleBase
from vision import options
from vision.stdlib import *
import shm
import math
import cv2 as cv2
import numpy as np
from collections import namedtuple

from cash_in_shared import *


module_options = [
    options.IntOption('min_area', 2000, 1, 2000),
    options.DoubleOption('min_circularity', .10, 0, 1),
    options.DoubleOption('max_rectangularity', .75, 0, 1),
    options.DoubleOption('max_joining_dist', 200, 0, 500),
]



def get_kernel(size):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size * 2 + 1, size * 2 + 1), (size, size))


class CashInForward(ModuleBase):
    def process(self, img):
        print("asdf")
        self.img = img

        h, w, _ = img.shape

        shm.camera.forward_height.set(h)
        shm.camera.forward_width.set(w)

        self.post("Original", img)

        set_shared_globals(is_forward=True, options=self.options, post=self.post)

        preprocessed_image = preprocess(self.img, options=self.options, post=self.post)
        threshed = threshold(preprocessed_image, options=self.options, post=self.post)
        contours = find_contours(threshed, options=self.options, post=self.post)
        bins = find_bins(contours, options=self.options, post=self.post)

        final = img.copy()

        for name, binn in bins.items():
            shm_group = shm._eval("recovery_vision_forward_{}".format(name))
            output = shm_group.get()

            output.area = binn.area
            output.center_x = binn.x
            output.center_y = binn.y
            output.probability = binn.probability

            shm_group.set(output)

            cv2.circle(final, (int(binn.x), int(binn.y)), int(math.sqrt(binn.area)), BLUE, 5)
            cv2.putText(final, name, (int(binn.x), int(binn.y) - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, BLUE, 2)

        self.post("Final", final)


if __name__ == '__main__':
    CashInForward("forward", module_options)()
