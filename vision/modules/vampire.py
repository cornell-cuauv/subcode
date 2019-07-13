#!/usr/bin/env python3
from math import pi, atan, sin, cos
from functools import reduce

import cv2
import numpy as np

from vision.modules.base import ModuleBase
from vision.framework.color import bgr_to_lab, range_threshold
from vision.framework.transform import elliptic_kernel, dilate, erode, rect_kernel
from vision.framework.feature import outer_contours, find_lines, contour_centroid, contour_area
from vision.framework.draw import draw_line
from vision.options import IntOption, DoubleOption

from vision.modules.attilus_garbage import thresh_color_distance, filter_contour_size, filter_shapularity, angle_to_line, MANIPULATOR_ANGLE

opts = [
        IntOption('yellow_l', 186, 0, 255),  # 224
        IntOption('yellow_a', 144, 0, 255),
        IntOption('yellow_b', 185, 0, 255),
        IntOption('purple_l', 39, 0, 255),  # 224
        IntOption('purple_a', 160, 0, 255),
        IntOption('purple_b', 80, 0, 255),
        IntOption('vampire_color_distance', 30, 0, 255),
        IntOption('contour_size_min', 50, 0, 1000),
        IntOption('intersection_size_min', 20, 0, 1000),
        IntOption('erode_kernel_size', 5, 0, 100),
        IntOption('erode_iterations', 3, 0, 100),
        IntOption('dilate_kernel_size', 5, 0, 100),
        IntOption('dilate_iterations', 6, 0, 10),
        IntOption('line_thresh', 210, 0, 5000),
        IntOption('manipulator_angle', MANIPULATOR_ANGLE, 0, 359),
        DoubleOption('rectangle_padding', 0.4, -1, 1),
        DoubleOption('rectangularity_thresh', 0.8, 0, 1),
]

COLORSPACE = "lab"


class Vampire(ModuleBase):
    def process(self, mat):
        self.post('org', mat)
        # print(mat.shape)
        _, split = bgr_to_lab(mat)
        d = self.options['vampire_color_distance']
        color = [self.options["yellow_%s" % c] for c in COLORSPACE]
        self.rectangles = self.find_yellow_rectangle(split, color, d, self.options['erode_kernel_size'],
                                                self.options['erode_iterations'],
                                                self.options['dilate_kernel_size'],
                                                self.options['dilate_iterations'],
                                                self.options['contour_size_min'],
                                                self.options['rectangularity_thresh'],
                                                -self.options['rectangle_padding'])

        for y in self.rectangles:
            rectangle = cv2.boxPoints(y['rectangle'])
            mat = cv2.drawContours(mat, [np.int0(rectangle)], 0, (0, 0, 255), 10)

        color = [self.options["purple_%s" % c] for c in COLORSPACE]
        # purple = self.find_color(mat, color, d, use_first_channel=False, erode_mask=True, dilate_mask=True, iterations=3, rectangular=False)
        # self.post('purple', purple)
        # purple_contours = self.contours_and_filter(purple, self.options['contour_size_min'])
        self.find_vampire(mat, split, color, d)

        mat = cv2.drawContours(mat, [r['contour'] for r in self.rectangles], -1, (0, 255, 0), 10)
        # mat = cv2.drawContours(mat, purple_contours, -1, (0, 255, 0), 10)
        self.post('yellow_contours', mat)


    def find_yellow_rectangle(self, split, color, distance, erode_kernel, erode_iterations,
                              dilate_kernel, dilate_iterations, min_contour_size,
                              min_rectangularity, padding_offset):
        mask = thresh_color_distance(split, color, distance)
        mask = erode(mask, rect_kernel(erode_kernel), iterations=erode_iterations)
        mask = dilate(mask, rect_kernel(dilate_kernel), iterations=dilate_iterations)

        contours = outer_contours(mask)
        contours = filter_contour_size(contours, min_contour_size)

        def box_area(contour):
            r = cv2.minAreaRect(contour)
            return r[1][0] * r[1][1]

        contours = filter_shapularity(box_area, contours, min_rectangularity)

        def rectangle_with_offset(contour):
            r = cv2.minAreaRect(contour)
            return r[0], (max(r[1][0] * (1-padding_offset), 0), max(r[1][1] * (1-padding_offset), 0)), r[2]

        return [{'contour': c, 'rectangle': rectangle_with_offset(c)} for c in contours]


    def find_vampire(self, mat, split, color, distance):
        mask = thresh_color_distance(split, color, distance)
        self.post('purple', mask)
        i, mask_r = self.intersect_rectangles(self.rectangles, mask, self.options['intersection_size_min'])
        self.post('rectangle', mask_r)

        if i is not None:
            purple = cv2.bitwise_and(mask, mask_r)
            purple_contours = outer_contours(purple)

            purple_center = contour_centroid(max(purple_contours, key=contour_area))
            print(purple_center)

            align_angle = self.rectangles[i]['rectangle'][2] + 270 if self.rectangles[i]['rectangle'][1][1] > self.rectangles[i]['rectangle'][1][0] else self.rectangles[i]['rectangle'][2]

            cv2.circle(mat, purple_center, 20, color=(0, 0, 255), thickness=-1)
            draw_line(mat, *angle_to_line(self.options['manipulator_angle'], origin=purple_center), thickness=5)
            draw_line(mat, *angle_to_line(align_angle, origin=purple_center), color=(0, 255, 0), thickness=5)

        self.post('hmm', mat)


    def intersect_rectangles(self, rectangles, mask, min_size):
        for i in range(len(rectangles)):
            c = rectangles[i]['rectangle']
            mask_c = np.zeros(mask.shape, dtype=np.uint8)
            mask_c = cv2.fillPoly(mask_c, [np.int0(cv2.boxPoints(c))], color=255)
            # self.post('mask_%d'%i, mask_c)
            intersect = cv2.bitwise_and(mask, mask_c)
            # self.post('intersect_%d'%i, intersect)
            if any(map(lambda x: cv2.contourArea(x) > min_size, outer_contours(intersect))):
                return i, intersect
        return None, None



if __name__ == '__main__':
    Vampire('downward', opts)()
