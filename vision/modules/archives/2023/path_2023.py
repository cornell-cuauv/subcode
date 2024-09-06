#!/usr/bin/env python3

"""
Path Vision Module

OUTPUTS:
    * shm.path_results.visible -- Whether or not the path is detected.
    * shm.path_results.angle   -- The angle of the path relative to the sub.
            This is negative when the path is facing left and positive when the
            path is facing right. A higher absolute value means a more
            significant turn is necessary. 0 means the sub is facing in the
            same direction as the path.

STATUS:
    * Working in the simulator as of Jun 29.
    * Working in the pool when specifically tuned as of Jun 29.
"""


pool_lab_a_min: int = 136
pool_lab_a_max: int = 175
pool_lab_b_min: int = 119
pool_lab_b_max: int = 200

simulator_lab_a_min: int = 164
simulator_lab_a_max: int = 219
simulator_lab_b_min: int = 137
simulator_lab_b_max: int = 249

pool_min_area: int = 500
simulator_min_area: int = 500
max_rectangularity_error: float = 1.2 # area / area of min enclosing rect
max_sidelength_ratio_error: int = 4 # long side / short side


import os
import shm
import cv2
from vision.modules.base import ModuleBase
from vision.options import IntOption, DoubleOption
from vision.framework.color import range_threshold, bgr_to_lab
from vision.framework.feature import (outer_contours, contour_area,
        min_enclosing_rect)
from vision.framework.draw import draw_contours, draw_text

is_simulator = os.getenv('CUAUV_LOCALE') == 'simulator'
module_options = [
    IntOption('lab a min', simulator_lab_a_min if is_simulator
            else pool_lab_a_min, 0, 255),
    IntOption('lab a max', simulator_lab_a_max if is_simulator
            else pool_lab_a_max, 0, 255),
    IntOption('lab b min', simulator_lab_b_min if is_simulator
            else pool_lab_b_min, 0, 255),
    IntOption('lab b max', simulator_lab_b_max if is_simulator
            else pool_lab_b_max, 0, 255),
    IntOption('min area', simulator_min_area if is_simulator
            else pool_min_area, 0, 20000),
    DoubleOption('max rectangularity error', max_rectangularity_error, 0,
            0.895),
    IntOption('max sidelength ratio error', max_sidelength_ratio_error, 0, 100)
]

class AaronPath(ModuleBase):
    
    def satisfactory_area(self, contour):
        return contour_area(contour) > self.options['min area']

    def satisfactory_rectangularity(self, contour):
        _, (rect_width, rect_height), _ = min_enclosing_rect(contour)
        rectangularity = contour_area(contour) / (rect_width * rect_height)
        ideal_rectangularity = 0.946
        rectangularity_error = (rectangularity - ideal_rectangularity) ** 2
        return rectangularity_error < self.options['max rectangularity error']

    def satisfactory_sidelength_ratio(self, contour):
        _, (rect_width, rect_height), _ = min_enclosing_rect(contour)
        sidelength_ratio = (max(rect_width, rect_height)
                / min(rect_width, rect_height))
        ideal_sidelength_ratio = 4.000
        sidelength_ratio_error = ((sidelength_ratio - ideal_sidelength_ratio)
                ** 2)
        return (sidelength_ratio_error
                < self.options['max sidelength ratio error'])

    def process(self, img):

        # Thresholds
        _, (_, lab_a, lab_b) = bgr_to_lab(img)
        a_threshed = range_threshold(lab_a, self.options['lab a min'],
                self.options['lab a max'])
        b_threshed = range_threshold(lab_b, self.options['lab b min'],
                self.options['lab b max'])
        threshed = a_threshed & b_threshed

        # Post thresholds
        self.post('original', img)
        self.post('lab a threshed', a_threshed)
        self.post('lab b threshed', b_threshed)
        self.post('threshed', threshed)

        # Filter contours
        contours = outer_contours(threshed)
        contours = filter(self.satisfactory_area, contours)
        contours = filter(self.satisfactory_rectangularity, contours)
        contours = filter(self.satisfactory_sidelength_ratio, contours)
        contours = list(contours)

        if len(contours) > 0:
            best_contour = max(contours, key=contour_area)
            draw_contours(img, [best_contour], color=(0, 255, 0), thickness=5)

            # Angle
            (x, y), (w, h), angle = min_enclosing_rect(best_contour)
            if w < h:
                shm.path_results.angle.set(angle)
            else:
                shm.path_results.angle.set(angle - 90)
            draw_text(img, f"Angle: {round(shm.path_results.angle.get())}",
                    (10, img.shape[0] - 30), 2, thickness=3)

            shm.path_results.visible.set(1)
            shm.path_results.center_x.set(self.normalized(x, axis=0))
            shm.path_results.center_y.set(self.normalized(y, axis=1))
        else:
            shm.path_results.visible.set(0)

        self.post('best contour', img)


if __name__ == '__main__':
    AaronPath('downward', module_options)()
