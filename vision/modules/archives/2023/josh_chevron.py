#!/usr/bin/env python3

import os
import shm
import cv2
from vision.modules.base import ModuleBase
from vision.options import IntOption, DoubleOption
from vision.framework.color import range_threshold, bgr_to_lab
from vision.framework.feature import outer_contours, contour_area, min_enclosing_rect
from vision.framework.draw import draw_contours, draw_text
from vision.framework.transform import morph_remove_noise, morph_close_holes
from vision.framework.transform import rect_kernel


module_options = [
    IntOption('lab a min', 0, 0, 255),
    IntOption('lab a max', 0, 0, 255),
    IntOption('lab b min', 0, 0, 255),
    IntOption('lab b max', 0, 0, 255),
    IntOption('min area', 0, 0, 1000)
]

class Chevron(ModuleBase):
    def process(self, img):
        _, (_, lab_a, lab_b) = bgr_to_lab(img)
        a_threshed = range_threshold(lab_a, self.options['lab a min'], self.options['lab a max'])         
        b_threshed = range_threshold(lab_b, self.options['lab b min'], self.options['lab b max'])
        threshed = a_threshed & b_threshed

        self.post('original', img)
        self.post('lab a threshed', a_threshed)
        self.post('lab b threshed', b_threshed)
        self.post('threshed', threshed)

        morph_close_holes(img, rect_kernel(5))
        morph_remove_noise(img, rect_kernel(5))
        contours = outer_contours(threshed)
        if len(contours) > 0:
            best_contour = max(contours, key=contour_area)
            print(contour_area(best_contour))
            if contour_area(best_contour) > self.options['min area']:
                draw_contours(img, [best_contour], color = (0, 255, 0), thickness = 5)
                (x, y), _, _ = min_enclosing_rect(best_contour)
                shm.chev_results.visible.set(1)
                shm.chev_results.x.set(-self.normalized(x, axis=0))
                shm.chev_results.y.set(-self.normalized(y, axis=1))
            else:
                shm.chev_results.visible.set(0)
        else:
            shm.chev_results.visible.set(0)

        self.post('Chevron', img)

if __name__ == '__main__':
    Chevron('downward', module_options)()
