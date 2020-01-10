#!/usr/bin/env python3
import shm

from vision.modules.base import ModuleBase
from vision.framework.sift import SIFT, draw_transformed_box, draw_keypoints

class SIFTDemo(ModuleBase):
    def __init__(self, *args, **kwargs):
        self.sift = SIFT()
        self.sift.add_source(#TODO)
        super().__init__(*args, **kwargs)

    def process(self, mat):
        # Since color doesn't usually affect features, convert to grayscale for
        # faster processing
        # This isn't really required, and I don't actually know how much
        # performance boost we get from this. It is, however, standard practice
        # when doing feature detection, so we're doing it.
        mat, _ = bgr_to_gray(mat)

        matched, kp, des, _ = self.sift.match(mat)
        kpmat = np.copy(mat)
        # TODO: Draw keypoints may not work atm
        kpmat = draw_keypoints(kpmat, kp)
        self.post("keypoints", kpmat)

        for name, good, dst, _ in matched:
            mat = draw_transformed_box(mat, dst)

        self.post("boxes", mat)



if __name__ == '__main__':
    SIFTDemo()()
