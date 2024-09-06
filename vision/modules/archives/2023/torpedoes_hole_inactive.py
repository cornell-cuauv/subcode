#!/usr/bin/env python3

from math import pi, atan2, sin, cos
from vision.modules.base import ModuleBase
from vision.options import IntOption, BoolOption
import cv2
import numpy as np
from vision.framework.color import bgr_to_lab, bgr_to_gray, range_threshold
from vision.framework.feature import canny, simple_canny, find_circles, find_corners, find_lines, outer_contours
from vision.framework.draw import draw_circle, draw_line, draw_contours, draw_text
from vision.framework.transform import elliptic_kernel, morph_remove_noise, morph_close_holes


options = [
    IntOption('min a', 141, 0, 255),
    IntOption('max a', 234, 0, 255),
    IntOption('min b', 134, 0, 255),
    IntOption('max b', 229, 0, 255),
    BoolOption('lines debug', False),
    IntOption('canny min', 150, 0, 255),
    IntOption('canny max', 255, 0, 255)
]

def angle_diff(a, b):
    return abs(atan2(sin(a - b), cos(a - b)))

# Adapted from https://stackoverflow.com/questions/20677795/how-do-i-compute-the-intersection-point-of-two-lines
def line_intersection(line1, line2):
    line1 = ((line1[0], line1[1]), (line1[2], line1[3]))
    line2 = ((line2[0], line2[1]), (line2[2], line2[3]))

    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
       raise Exception('lines do not intersect')

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return round(x), round(y)

class Torpedoes2023(ModuleBase):
    def process(self, img):
        
        self.post('original', img)
        b, g, r = cv2.split(img)

        # gray_img, _ = bgr_to_gray(img)
        # canny_img = canny(gray_img, self.options['canny min'], self.options['canny max'])
        # if self.options['lines debug']:
        #     self.post('canny', canny_img)

        # lines = find_lines(canny_img, 1, pi / 180, 150)
        # lines_img = img.copy()
        # for line in lines[0]:
        #     x1, y1, x2, y2 = line
        #     draw_line(lines_img, (x1, y1), (x2, y2), color=(0, 0, 0), thickness=2)

        # horizontal_lines = []
        # vertical_lines = []
        # for i, line in enumerate(lines[1]):
        #     if angle_diff(line[1], pi / 2) < 0.1 or angle_diff(line[1], -pi / 2) < 0.1:
        #         horizontal_lines.append((lines[0][i], lines[1][i]))
        #     if angle_diff(line[1], pi) < 0.1 or angle_diff(line[1], pi) < 0.1:
        #         vertical_lines.append((lines[0][i], lines[1][i]))

        # for line in horizontal_lines:
        #     x1, y1, x2, y2 = line[0]
        #     draw_line(lines_img, (x1, y1), (x2, y2), color=(0, 0, 255), thickness=2)
        # for line in vertical_lines:
        #     x1, y1, x2, y2 = line[0]
        #     draw_line(lines_img, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=2)

        # chosen_vertical_lines = None
        # for a in vertical_lines:
        #     for b in vertical_lines:
        #         if a[1][0] - b[1][0] > 50:
        #             chosen_vertical_lines = [a, b]
        #             break

        # chosen_horizontal_lines = None
        # for a in horizontal_lines:
        #     for b in horizontal_lines:
        #         for c in horizontal_lines:
        #             if a[1][0] - b[1][0] > 50 and b[1][0] - c[1][0] > 50 and abs((a[1][0] - b[1][0]) - (b[1][0] - c[1][0])) < 30:
        #                 chosen_horizontal_lines = [a, b, c]

        # if chosen_vertical_lines is not None:
        #     a, b = chosen_vertical_lines
        #     draw_line(lines_img, (a[0][0], a[0][1]), (a[0][2], a[0][3]), color=(255, 255, 255), thickness=5)
        #     draw_line(lines_img, (b[0][0], b[0][1]), (b[0][2], b[0][3]), color=(255, 255, 255), thickness=5)
        # if chosen_horizontal_lines is not None:
        #     a, b, c = chosen_horizontal_lines
        #     draw_line(lines_img, (a[0][0], a[0][1]), (a[0][2], a[0][3]), color=(255, 255, 255), thickness=5)
        #     draw_line(lines_img, (b[0][0], b[0][1]), (b[0][2], b[0][3]), color=(255, 255, 255), thickness=5)
        #     draw_line(lines_img, (c[0][0], c[0][1]), (c[0][2], c[0][3]), color=(255, 255, 255), thickness=5)

        # if self.options['lines debug']:
        #     self.post('lines', lines_img)


        # rect_img = img.copy()
        # if chosen_horizontal_lines is not None and chosen_vertical_lines is not None:
        #     bottom_left_corner = line_intersection(chosen_horizontal_lines[0][0], chosen_vertical_lines[0][0])
        #     bottom_right_corner = line_intersection(chosen_horizontal_lines[0][0], chosen_vertical_lines[1][0])
        #     top_left_corner = line_intersection(chosen_horizontal_lines[2][0], chosen_vertical_lines[0][0])
        #     top_right_corner = line_intersection(chosen_horizontal_lines[2][0], chosen_vertical_lines[1][0])
        #     draw_line(rect_img, bottom_left_corner, bottom_right_corner, color=(0, 255, 0), thickness=5)
        #     draw_line(rect_img, bottom_right_corner, top_right_corner, color=(0, 255, 0), thickness=5)
        #     draw_line(rect_img, top_right_corner, top_left_corner, color=(0, 255, 0), thickness=5)
        #     draw_line(rect_img, top_left_corner, bottom_left_corner, color=(0, 255, 0), thickness=5)
        # # self.post('rect', rect_img)



        lab, (_, a, b) = bgr_to_lab(img)
        thresh_a = range_threshold(a, self.options['min a'], self.options['max a'])
        thresh_b = range_threshold(b, self.options['min b'], self.options['max b'])
        thresh = thresh_a & thresh_b
        thresh = morph_remove_noise(thresh, elliptic_kernel(5))
        thresh = morph_close_holes(thresh, elliptic_kernel(5))
        # self.post('thresh a', thresh_a)
        # self.post('thresh b', thresh_b)
        self.post('thresh', thresh)

        # circles = find_circles(thresh, 2, 100, circle_thresh=40, max_radius=100)
        # if circles is not None:
        #     for circle in circles[0]:
        #         mask = np.zeros(gray_img.shape, np.uint8)
        #         draw_circle(mask, (circle[0], circle[1]), circle[2], color=(255, 255, 255), thickness=1)
        #         boundary_fraction = np.sum(mask & thresh) / np.sum(mask)
        #         mask = np.zeros(gray_img.shape, np.uint8)
        #         draw_circle(mask, (circle[0], circle[1]), circle[2], color=(255, 255, 255), thickness=-1)
        #         draw_circle(mask, (circle[0], circle[1]), circle[2], color=(0, 0, 0), thickness=20)
        #         internal_fraction = np.sum(mask & thresh) / np.sum(mask)
        #         if boundary_fraction > 0.2 and internal_fraction < 0.2:
        #             draw_circle(rect_img, (circle[0], circle[1]), circle[2], color=(0, 255, 0), thickness=5)
        #             # if internal_fraction != float('nan'):
        #                 # draw_text(img, str(round(100 * internal_fraction) / 100), (circle[0], circle[1]), thickness=2, scale=3, color=(255, 255, 255))
        #         else:
        #             pass
        #             # draw_circle(img, (circle[0], circle[1]), circle[2], color=(0, 0, 255), thickness=5)
        #             # if internal_fraction != float('nan'):
        #                 # draw_text(img, str(round(100 * internal_fraction) / 100), (circle[0], circle[1]), thickness=2, scale=3, color=(255, 255, 255))
        # self.post('circles', rect_img)

        # circles = find_circles(canny_img, 2, 100, circle_thresh=100, max_radius=100)
        # if circles is not None:
        #     for circle in circles[0]:
        #         draw_circle(img, (circle[0], circle[1]), circle[2], color=(0, 255, 0), thickness=5)

        contours = outer_contours(thresh)
        draw_contours(img, contours, color=(0, 255, 0), thickness=3)
        self.post('contours', img)

if __name__ == '__main__':
    Torpedoes2023('forward', options)()