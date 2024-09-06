#!/usr/bin/env python3

"""
Vision module for recognizing the torpedoes board.

Strategy:
* Threshold the image by lightness, keeping only dark pixels.
* Select the treshholds with areas at least a sufficient portion of their min
      enclosing rects.
* Choose the biggest such contour.

Status:
* Works well at Teagle when the sub is already aligned with the board or when
      it is off-axis.

Author(s):
* Written by Aaron.
"""


"""
Some possible tunings:

At Teagle:
* max_l: 70
* kernel_size: 25
* min_rectangularity: 0.5

On normal (brighter) calibration in Transdec: (in D)
* max_l: 150
* kernel_size: 4
* min_rectangularity: 0.3

On normal (brighter) calibration in Transdec: (in C)
* max_l: 120
* kernel_size: 4
* min_rectangularity: 0.3


"""

from math import pi, atan2, sin, cos, radians, degrees
from vision.modules.base import ModuleBase
from vision.options import IntOption, BoolOption, DoubleOption
import cv2
import numpy as np

from shm import torpedoes_board_vision
from vision.framework.color import bgr_to_lab, bgr_to_gray, range_threshold, otsu_threshold
from vision.framework.feature import canny, simple_canny, find_circles, find_corners, find_lines, outer_contours, contour_area, contour_approx, contour_perimeter
from vision.framework.draw import draw_circle, draw_line, draw_contours, draw_text
from vision.framework.transform import elliptic_kernel, morph_remove_noise, morph_close_holes
from vision.framework.helpers import to_odd


module_options = [
    # IntOption('max l', 120, 0, 255),
    # IntOption('kernel size', 4, 1, 35),
    # DoubleOption('min rectangularity', 0.3, 0.2, 1.0),
    # BoolOption('accept right triangles', True),
    # IntOption('angle tolerance', 10, 0, 30)
    IntOption('canny min', 39, 0, 255),
    IntOption('canny max', 255, 0, 255),
    DoubleOption('rho', 3, 0, 5),
    DoubleOption('theta', pi / 180, 0, pi / 10),
    DoubleOption('threshold', 150, 0, 500),
    DoubleOption('vertical angle allowance', 15, 0, 45),
    DoubleOption('horizontal angle allowance', 15, 0, 45)
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

def wrap_angle(angle):
    """make between (-pi, pi]"""
    if angle <= -pi:
        return angle + 2 * pi
    elif angle > pi:
        return angle - 2 * pi
    return angle

# True if at least two vertices are on the image's edges
def not_on_edge(img, contour):
    edge_count = 0
    for vertex in contour:
        x, y = vertex[0]
        if x < 5 or x > img.shape[1] - 5 or y < 5 or y > img.shape[0] - 5:
            edge_count += 1
    return edge_count < 2


class TorpedoesBoard2023(ModuleBase):
    def process(self, img):
        
        self.post('original', img)

        # # Thresh and morph
        # lab, (l, a, b) = bgr_to_lab(img)
        # thresh = range_threshold(l, 0, self.options['max l'])
        # self.post('thresh', thresh)
        # morphed = morph_remove_noise(thresh, elliptic_kernel(to_odd(self.options['kernel size'])))
        # morphed = morph_close_holes(thresh, elliptic_kernel(to_odd(self.options['kernel size'])))
        # self.post('morphed', morphed)

        # # Find and approximate contours
        # contours = outer_contours(morphed)
        # contours = list(map(lambda c: contour_approx(c, epsilon=0.1 * contour_perimeter(c, True)), contours))
        # contours = list(filter(lambda c: not_on_edge(img, c), contours))
        # draw_contours(img, contours, color=(0, 0, 255), thickness=3)
        # self.post('contours', img)

        # # Keep contours with 4 vertices, that are large,
        # # and that are a large portion of their bounding rect
        # good_contours = []
        # for contour in contours:
        #     if len(contour) == 4:
        #         x, y, w, h = cv2.boundingRect(contour)
        #         if w > 100 and h > 100 and contour_area(contour) / (w * h) > self.options['min rectangularity']:
        #             good_contours.append(contour)
        #     if self.options['accept right triangles']:
        #         if len(contour) == 3:
        #             x, y, w, h = cv2.boundingRect(contour)
        #             if w > 100 and h > 100 and 2 * contour_area(contour) / (w * h) > self.options['min rectangularity']:
        #                 angles = []
        #                 for i in range(3):
        #                     A = contour[i - 1]
        #                     B = contour[i]
        #                     C = contour[(i + 1) % 3]
        #                     old_x, old_y = A[0]  
        #                     curr_x, curr_y = B[0]  
        #                     new_x, new_y = C[0]
        #                     angle1 = atan2(curr_y - old_y, curr_x - old_x)
        #                     angle2 = atan2(new_y - curr_y, new_x - curr_x)
        #                     diff = wrap_angle(angle2 - angle1)
        #                     angles.append((degrees(diff), contour[i][0]))
        #                 right_angle = None
        #                 acute_angles = []
        #                 for angle in angles:
        #                     if abs(abs(angle[0]) - 90) < self.options['angle tolerance']:
        #                         right_angle = angle
        #                     else:
        #                         acute_angles.append(angle)
        #                 right_isosceles = (right_angle is not None) and (len(acute_angles) == 2) and (abs(acute_angles[0][0] - acute_angles[1][0]) < self.options['angle tolerance'])
        #                 if right_isosceles:
        #                     line_vector = acute_angles[1][1] - acute_angles[0][1]
        #                     unit_line_vector = line_vector / np.linalg.norm(line_vector)
        #                     a_to_line = acute_angles[0][1] - right_angle[1]
        #                     projection = np.dot(a_to_line, unit_line_vector) * unit_line_vector
        #                     reflected_vector = a_to_line - 2 * projection
        #                     reflected_point = acute_angles[0][1] + reflected_vector
        #                     new_contour = np.array([
        #                         np.array([np.array(right_angle[1])]),
        #                         np.array([np.array(acute_angles[0][1])]),
        #                         np.array([np.array(reflected_point)]),
        #                         np.array([np.array(acute_angles[1][1])])
        #                     ])
        #                     good_contours.append(new_contour.astype(int))

        # # Choose the biggest such contour
        # best_contour = None
        # if len(good_contours) > 0:
        #     best_contour = max(good_contours, key=lambda c: contour_area(c) if len(c) == 4 else 2 * contour_area(c))
        
        # # Draw and post
        # if best_contour is not None:
        #     draw_contours(img, [best_contour], color=(0, 255, 0), thickness=10)
        # self.post('ht-contours', img)

        # # Write to SHM
        # results = torpedoes_board_vision.get()
        # if best_contour is None:
        #     results.visible = False
        # else:
        #     results.visible = True
        #     x, y, w, h = cv2.boundingRect(best_contour)
        #     results.center_x, results.center_y = self.normalized((x + w / 2, y + h / 2))
        #     results.width, results.height = w / img.shape[1], h / img.shape[1]

        #     (x1, y1), (x2, y2), (x3, y3), (x4, y4) = [best_contour[i][0] for i in range(4)]
        #     if abs(x1 - x2) < abs(x1 - x3) and abs(x1 - x2) < abs(x1 - x4):
        #         if x1 < x3:
        #             results.left_sidelength = abs(y1 - y2)
        #             results.right_sidelength = abs(y3 - y4)
        #         else:
        #             results.left_sidelength = abs(y3 - y4)
        #             results.right_sidelength = abs(y1 - y2)
        #     elif abs(x1 - x3) < abs(x1 - x2) and abs(x1 - x3) < abs(x1 - x4):
        #         if x1 < x2:
        #             results.left_sidelength = abs(y1 - y3)
        #             results.right_sidelength = abs(y2 - y4)
        #         else:
        #             results.left_sidelength = abs(y2 - y4)
        #             results.right_sidelength = abs(y1 - y3)
        #     else:
        #         if x1 < x2:
        #             results.left_sidelength = abs(y1 - y4)
        #             results.right_sidelength = abs(y2 - y3)
        #         else:
        #             results.left_sidelength = abs(y2 - y3)
        #             results.right_sidelength = abs(y1 - y4)

        # torpedoes_board_vision.set(results)


        # Canny edge detection
        gray_img, _ = bgr_to_gray(img)
        canny_img = canny(gray_img, self.options['canny min'],
                self.options['canny max'])
        self.post('ht-canny', canny_img)

        # Hough lines
        lines = find_lines(canny_img, int(self.options['rho']), self.options['theta'], self.options['threshold'])
        lines_img = img.copy()
        for line in lines[0]:
            x1, y1, x2, y2 = line
            draw_line(lines_img, (x1, y1), (x2, y2), color=(0, 0, 0),
                    thickness=2)

        # Find horizontal and vertical lines
        horizontal_lines = []
        vertical_lines = []
        for i, line in enumerate(lines[1]):
            horizontal_allowance = radians(self.options['horizontal angle allowance'])
            vertical_allowance = radians(self.options['vertical angle allowance'])
            if (angle_diff(line[1], pi / 2) < horizontal_allowance
                    or angle_diff(line[1], -pi / 2) < horizontal_allowance):
                horizontal_lines.append((lines[0][i], lines[1][i]))
            if (angle_diff(line[1], 0) < vertical_allowance
                    or angle_diff(line[1], pi) < vertical_allowance):
                vertical_lines.append((lines[0][i], lines[1][i]))

        # Draw the horizontal and vertical lines
        for line in horizontal_lines:
            x1, y1, x2, y2 = line[0]
            draw_line(lines_img, (x1, y1), (x2, y2), color=(0, 0, 255),
                    thickness=2)
        for line in vertical_lines:
            x1, y1, x2, y2 = line[0]
            draw_line(lines_img, (x1, y1), (x2, y2), color=(0, 255, 0),
                thickness=2)

        # Choose two vertical lines which are sufficiently far apart
        chosen_vertical_lines = None
        for a in vertical_lines:
            for b in vertical_lines:
                if a[1][0] - b[1][0] > 100:
                    chosen_vertical_lines = [a, b]
                    break

        # Choose two horizontal lines which are sufficiently far apart
        chosen_horizontal_lines = None
        for a in horizontal_lines:
            for b in horizontal_lines:
                if a[1][0] - b[1][0] > 100 :
                    chosen_horizontal_lines = [a, b]
                    break

        # Draw the chosen horizontal and vertical lines
        if chosen_vertical_lines is not None:
            a, b = chosen_vertical_lines
            draw_line(lines_img, (a[0][0], a[0][1]), (a[0][2], a[0][3]),
                    color=(255, 255, 255), thickness=5)
            draw_line(lines_img, (b[0][0], b[0][1]), (b[0][2], b[0][3]),
                    color=(255, 255, 255), thickness=5)
        if chosen_horizontal_lines is not None:
            a, b = chosen_horizontal_lines
            draw_line(lines_img, (a[0][0], a[0][1]), (a[0][2], a[0][3]),
                    color=(255, 255, 255), thickness=5)
            draw_line(lines_img, (b[0][0], b[0][1]), (b[0][2], b[0][3]),
                    color=(255, 255, 255), thickness=5)
        self.post('ht-lines', lines_img)

        # Find the corner points of the rectangle at the intersections of the
        # chosen lines
        rect_img = img.copy()
        consistent_rect_img = img.copy()
        if (chosen_horizontal_lines is not None
                and chosen_vertical_lines is not None):
            bottom_left_corner = line_intersection(
                    chosen_horizontal_lines[0][0], chosen_vertical_lines[0][0])
            bottom_right_corner = line_intersection(
                    chosen_horizontal_lines[0][0], chosen_vertical_lines[1][0])
            top_left_corner = line_intersection(
                    chosen_horizontal_lines[1][0], chosen_vertical_lines[0][0])
            top_right_corner = line_intersection(
                    chosen_horizontal_lines[1][0], chosen_vertical_lines[1][0])
            draw_line(rect_img, bottom_left_corner, bottom_right_corner,
                    color=(0, 0, 255), thickness=10)
            draw_line(rect_img, bottom_right_corner, top_right_corner,
                    color=(0, 0, 255), thickness=10)
            draw_line(rect_img, top_right_corner, top_left_corner,
                    color=(0, 0, 255), thickness=10)
            draw_line(rect_img, top_left_corner, bottom_left_corner,
                    color=(0, 0, 255), thickness=10)
        self.post('ht-final', rect_img)

if __name__ == '__main__':
    TorpedoesBoard2023('forward', module_options)()
