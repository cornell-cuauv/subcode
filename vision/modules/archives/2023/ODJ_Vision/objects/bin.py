#!/usr/bin/env python3
from vision.framework.sift import SIFT
from vision.modules.ODJ_Base import VisionProcessBase

import shm
import cv2
import numpy as np

from vision.modules.base import ModuleBase
from vision.framework.sift import SIFT, draw_transformed_box, draw_keypoints
from vision.framework.color import bgr_to_gray
from vision.framework.transform import resize


class BinVision(ModuleBase):
    def __init__(self, *args, **kwargs):
        self.sift = SIFT()
        # Because of relative path, this line only works when
        # manually executing the vision module from the vision
        # modules directory
        self.source = cv2.imread("../../buoy_images/real_badge.png")
        self.source, _ = bgr_to_gray(self.source)
        kp, des = self.sift.add_source("real_badge", self.source)
        self.source = draw_keypoints(self.source, kp)
        super().__init__(*args, **kwargs)

    def process(self, mat):
        # Since color doesn't usually affect features, convert to grayscale for
        # faster processing
        # This isn't really required, and I don't actually know how much
        # performance boost we get from this. It is, however, standard practice
        # when doing feature detection, so we're doing it.
        self.post("source", self.source)
        self.post("org", mat)
        gmat, _ = bgr_to_gray(mat)
        self.post("gray", gmat)

        matched, kp, des = self.sift.match(gmat, draw=True)
        kpmat = np.copy(mat)
        kpmat = draw_keypoints(kpmat, kp)
        self.post("keypoints", kpmat)

        for name, good, dst, _, drawim in matched:
            self.post(f"match: {name}", resize(drawim, int(
                drawim.shape[1]*0.5), int(drawim.shape[0]*0.5)))
            mat = draw_transformed_box(mat, dst)

        self.post("bin", mat)


if __name__ == '__main__':
    BinVision("downward")()
