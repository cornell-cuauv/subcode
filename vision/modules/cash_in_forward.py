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


module_options = get_shared_options(is_forward=True) + [
]


def get_kernel(size):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size * 2 + 1, size * 2 + 1), (size, size))


class CashInForward(ModuleBase):
    def process(self, img):
        print("asdf")
        self.img = img

        img = img[::2, ::2, :]
        h, w, _ = img.shape

        shm.camera.forward_height.set(h)
        shm.camera.forward_width.set(w)

        self.post("Original", img)

        set_shared_globals(is_forward=True, options=self.options, post=self.post, img=img)

        preprocessed_image = preprocess(img)
        threshed = threshold(preprocessed_image)
        contours = find_contours(threshed)
        funnels = find_funnels(contours)

        final = img.copy()

        # for name, binn in bins.items():
        #     shm_group = shm._eval("recovery_vision_forward_{}".format(name))
        #     output = shm_group.get()

        #     output.area = binn.area
        #     output.center_x = binn.x
        #     output.center_y = binn.y
        #     output.probability = binn.probability

        #     shm_group.set(output)

        #     cv2.circle(final, (int(binn.x), int(binn.y)), int(math.sqrt(binn.area)), BLUE, 5)
        #     cv2.putText(final, name, (int(binn.x), int(binn.y) - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, BLUE, 2)

        self.post("Final", final)


if __name__ == '__main__':
    CashInForward("forward", module_options)()
