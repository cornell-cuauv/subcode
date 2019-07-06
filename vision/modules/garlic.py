#!/usr/bin/env python3
from math import pi, atan, sin, cos
from functools import reduce

import cv2
import numpy as np

from vision.modules.base import ModuleBase
from vision.framework.color import bgr_to_lab, range_threshold
from vision.framework.transform import elliptic_kernel, dilate, erode, rect_kernel
from vision.framework.feature import outer_contours, find_lines
from vision.framework.draw import draw_line
from vision.options import IntOption, DoubleOption

from auv_python_helpers.angles import abs_heading_sub_degrees, heading_sub_degrees
import shm

opts = [
        IntOption('yellow_l', 186, 0, 255),  # 224
        IntOption('yellow_a', 144, 0, 255),
        IntOption('yellow_b', 185, 0, 255),
        IntOption('red_l', 39, 0, 255),  # 224
        IntOption('red_a', 174, 0, 255),
        IntOption('red_b', 154, 0, 255),
        IntOption('lever_color_distance', 24, 0, 255),
        IntOption('contour_size_min', 50, 0, 1000),
        IntOption('intersection_size_min', 20, 0, 1000),
        IntOption('erode_kernel_size', 18, 0, 100),
        IntOption('dilate_kernel_size', 18, 0, 100),
        IntOption('dilate_iterations', 10, 0, 10),
        IntOption('line_thresh', 210, 0, 5000),
        IntOption('manipulator_angle', 25, -90, 90),
        DoubleOption('circularity_thresh', 0.8, 0, 1),
]

COLORSPACE = "lab"


def lines_to_angles(line):
    try:
        return atan((line[1]-line[3])/(line[0]-line[2]))
    except ZeroDivisionError:
        return pi/2
def vectors_to_degrees(vectors):
    degrees = atan(vectors[1]/vectors[0])*180/pi
    return degrees if degrees > 0 else 360+degrees
def angle_to_unit_circle(angle):
    return cos(angle), sin(angle)


class Color(ModuleBase):
    def process(self, mat):
        self.post('org', mat)
        # print(mat.shape)
        d = self.options['lever_color_distance']
        color = [self.options["yellow_%s" % c] for c in COLORSPACE]
        yellow = self.find_color(mat, color, d, iterations=self.options['dilate_iterations'])
        self.post('yellow', yellow)
        yellow_contours = self.contours_and_filter(yellow, self.options['contour_size_min'])
        yellow_contours = self.filter_circles(yellow_contours, self.options['circularity_thresh'])

        color = [self.options["red_%s" % c] for c in COLORSPACE]
        red = self.find_color(mat, color, d, use_first_channel=True, erode_mask=True, dilate_mask=True, iterations=6, rectangular=False)
        # red = dilate(red, elliptic_kernel(self.options['dilate_kernel_size']), iterations=1)
        red = erode(red, elliptic_kernel(self.options['dilate_kernel_size']), iterations=2)
        self.post('red', red)
        red_contours = outer_contours(red)

        platform, garlic = self.red_in_circle(mat, yellow_contours, red_contours)
        platform_center = None

        if platform is not None:
            platform_center = self.center(platform[0], post=True)
            garlic_mask = np.zeros((mat.shape[0], mat.shape[1]), dtype=np.uint8)
            garlic_mask = cv2.drawContours(garlic_mask, garlic, -1, (255, 0, 0), 10)
            self.post('garlic', garlic_mask)
            mat = cv2.circle(mat, platform_center, 4, (255, 255, 0), thickness=4)
            lines, garlic_vectors = self.find_garlic_angle(mat, garlic_mask)

            for l in lines:
                draw_line(mat, (l[0], l[1]), (l[2], l[3]), thickness=5)
            for v in garlic_vectors:
                draw_line(mat, platform_center, tuple([platform_center[i] + int(v[i] * 1000) for i in range(len(v))]), color=(0, 255, 0), thickness=5)
            manipulator_vector = angle_to_unit_circle(self.options['manipulator_angle']/180 * pi)
            draw_line(mat, platform_center, tuple([platform_center[i] + int(manipulator_vector[i]*1000) for i in range(len(platform_center))]), color=(255, 0, 0), thickness=4)
            closest = self.find_closest_angle(self.options['manipulator_angle'], *(vectors_to_degrees(v) for v in garlic_vectors), post=True)
            if closest is not None:
                closest_vector = angle_to_unit_circle(closest/180 * pi)
                draw_line(mat, platform_center, tuple([platform_center[i] + int(closest_vector[i] * 1000) for i in range(len(platform_center))]), color=(255, 255, 0), thickness=5)

        self.post('line', mat)

        mat = cv2.drawContours(mat, yellow_contours, -1, (0, 255, 0), 10)
        self.post('yellow_contours', mat)

    def find_color(self, mat, color, distance, use_first_channel=False, erode_mask=True, dilate_mask=True, iterations=1, rectangular=False):
        _, split = bgr_to_lab(mat)
        threshed = [range_threshold(split[i],
                    color[i] - distance, color[i] + distance)
                    for i in range(int(not use_first_channel), len(color))]
        combined = reduce(lambda x, y: cv2.bitwise_and(x, y), threshed)
        if dilate_mask or erode_mask:
            if erode_mask:
                kernel = elliptic_kernel(self.options['erode_kernel_size']) if not rectangular \
                        else rect_kernel(self.options['erode_kernel_size'])
                combined = erode(combined, kernel, iterations=1)
            if dilate_mask:
                kernel = elliptic_kernel(self.options['dilate_kernel_size']) if not rectangular \
                        else rect_kernel(self.options['dilate_kernel_size'])
                combined = dilate(combined, kernel, iterations=iterations)
        # _, contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # filtered = [i for i in contours if cv2.contourArea(i) > self.options['contour_size_min']]
        return combined

    def contours_and_filter(self, mat, size_thresh):
        _, contours, _ = cv2.findContours(mat, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filtered = [i for i in contours if cv2.contourArea(i) > size_thresh]
        return filtered

    def filter_circles(self, contours, circularity_thresh):
        def _check_circle(contour):
            circle_area = pi * cv2.minEnclosingCircle(contour)[1]**2
            area = cv2.contourArea(contour)
            return area/circle_area > circularity_thresh
        return [c for c in contours if _check_circle(c)]

    def red_in_circle(self, mat, yellow_contours, red_contours):
        mask = np.zeros((mat.shape[0], mat.shape[1]), dtype=np.uint8)
        for i in range(len(yellow_contours)):
            mask_y = mask.copy()
            mask_r = mask.copy()
            mask_y = cv2.fillPoly(mask_y, [yellow_contours[i]], 255)
            self.post('mask_y%d' % i, mask_y)
            mask_r = cv2.fillPoly(mask_r, red_contours, 255)
            self.post('mask_r%d' % i, mask_r)
            intersection = cv2.bitwise_and(mask_y, mask_r)
            self.post('intersection%d' % i, intersection)
            if any(map(lambda x: cv2.contourArea(x) > self.options['intersection_size_min'], outer_contours(intersection))):
                return [yellow_contours[i]], outer_contours(intersection)
        return None, None

    def center(self, contour, post=False):
        M = cv2.moments(contour)
        ret = (int(M['m10']/M['m00']), int(M['m01']/M['m00']))
        if post:
            shm.recovery_garlic.center_x.set(ret[0])
            shm.recovery_garlic.center_y.set(ret[1])
        return ret

    def find_garlic_angle(self, mat, garlic_mask):
        try:
            lines = find_lines(garlic_mask, 1, pi/180, self.options['line_thresh'])

            angles = np.array([angle_to_unit_circle(lines_to_angles(l)) for l in lines[0]], dtype=np.float32)
            if len(angles) < 2:
                return [], []

            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            compactness, label, centeroid = cv2.kmeans(angles, 2, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

            return lines[0], centeroid  # , [atan(c[1]/c[0]) for c in center]

        except cv2.error as e:
            print(e)
            return [], []

    def find_closest_angle(self, target, *angles, post=False):
        if len(angles) == 0: return
        closest = min(angles, key=lambda x: abs_heading_sub_degrees(target, x))
        if post:
            shm.recovery_garlic.angle_offset.set(heading_sub_degrees(target, closest))
        return closest

if __name__ == '__main__':
    Color('downward', opts)()
