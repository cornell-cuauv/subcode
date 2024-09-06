#!/usr/bin/env python3

"""
Vision module for recognizing the upper torpedo hole.

Strategy:
* Choose the upper of the largest two red contours which both have lots of
* vertices and are mostly convex.

Status:
* Works well at Teagle when the sub is close enough to the board for the board
      to take up almost the whole screen, or when the sub is even closer.
* Requires some manual tuning of the threshold parameters depending on lighting
      in different parts of Teagle.

Author(s):
* Written by Jeffrey (in 2022).
* Adapted by Aaron.
"""

#NOTE: https://stackoverflow.com/questions/45323590/do-contours-returned-by-cvfindcontours-have-a-consistent-orientation
# outer contour points are ordered CCW


import shm
import cv2
from math import pi, atan2

from shm import torpedoes_hole_vision
from vision.modules.base import ModuleBase
from vision.framework.sift import SIFT, draw_transformed_box, draw_keypoints
from vision.framework.color import bgr_to_gray, bgr_to_lab, thresh_color_distance
from vision.framework.transform import (
        resize, 
        morph_remove_noise, 
        morph_close_holes,
        elliptic_kernel,
        rect_kernel
)
from vision.framework.helpers import to_odd
from vision.framework.feature import (
    contour_centroid,
    contour_area,
    min_enclosing_rect,
    min_enclosing_circle,
    min_enclosing_ellipse,
    find_circles,
    outer_contours,
)
from vision.framework.draw import draw_contours, draw_circle, draw_ellipse
from vision import options

module_options = [
    options.IntOption('lab_a', 181, 0, 255),
    options.IntOption('lab_b', 143, 0, 255),
    options.IntOption('dist', 34, 0, 255),
    options.IntOption('noise_kernel', 3, 1, 23),
    options.DoubleOption('noise_area', 0.3, 0, 0.5),
    options.DoubleOption('arc_percentage', 0.009, 0, 0.2),
    options.IntOption('vertices', 7, 3, 15),
    options.IntOption('convexity tolerance', 13, 0, 15),

    options.BoolOption('debug', True),
]



class TorpedoesHole2023(ModuleBase):
    def is_convex_contour(self, outer_contour, tolerance=0):
        """ returns true if the contour is convex
        > since the contours are are in order, we start at outer_contour[0] and expect
          all subsequent line segments to curve in the same directoin
        > Let a negative direction denote a curve left and a positive direction
          denote a curve right
        > Tolerance: how many times it can be "concave"
        """
        def wrap_angle(angle):
            """make between (-pi, pi]"""
            if angle <= -pi:
                return angle + 2 * pi
            elif angle > pi:
                return angle - 2 * pi
            return angle

        if len(outer_contour) < 3:
            return False
        direction = 0
        angle_cumulation = 0
        length = len(outer_contour)
        for i in range(length):
            A = outer_contour[i - 1]
            B = outer_contour[i]
            C = outer_contour[(i + 1) % length]

            old_x, old_y    = A[0]  
            curr_x, curr_y  = B[0]  
            new_x, new_y    = C[0]  

            angle1 = atan2(curr_y - old_y, curr_x - old_x)
            angle2 = atan2(new_y - curr_y, new_x - curr_x)
            diff = wrap_angle(angle2 - angle1)
            angle_cumulation += diff
            # if no delta idk wtf
            if diff == 0:
                return False

            # init the first iteration
            # else check if consistent (-)*(-) and (+)*(+) = (+)
            if i == 0:
                direction = 1 if diff > 0 else -1
            elif direction * diff <= 0: 
                if tolerance > 0:
                    tolerance -= 1
                    direction *= -1
                else:
                    return False
        
        return True#abs(round(angle_cumulation / TWO_PI)) == 1


    def process(self, img):
        AREA = img.shape[0] * img.shape[1] / 100

        lab, lab_split = bgr_to_lab(img)
        red_thresh, red_dist = thresh_color_distance(lab_split,
            (0, self.options['lab_a'], self.options['lab_b']),
            self.options['dist'], ignore_channels = [0])
        red_thresh = morph_close_holes(red_thresh,
            rect_kernel(to_odd(self.options['noise_kernel'])))

        # Get contours (largest first)
        contours = outer_contours(red_thresh)
        contours = sorted(contours, key=contour_area, reverse=True)

        # Keep the contours of sufficient area that have at least 3 vertices
        contours = list(filter(lambda x: (contour_area(x) / AREA) >
                self.options['noise_area'] and len(x) >=  3, contours))

        circle_contour = None

        mat = img.copy()
        draw_contours(mat, contours, color = [255, 255 ,0], thickness=2)
        
        circles = []
        for contour in contours:
            polygon = cv2.approxPolyDP(contour, self.options['arc_percentage']
                    * cv2.arcLength(contour, True), True)
            draw_contours(mat, polygon, color = [0, 255, 255], thickness=5) 
            if (circle_contour is None and len(polygon) > self.options['vertices']
                    and self.is_convex_contour(polygon, tolerance=self.options['convexity tolerance'])):
                circles.append(contour)
        
        circles_mat = img.copy()
        for circle in circles:
            draw_contours(circles_mat, [circle], color=[0, 0, 0], thickness=10)
        
        # Choose the higher circle (of the smallest two) if there are options
        if len(circles) == 1:
            circle_contour = circles[0]
        elif len(circles) > 1:
            _, y1 = contour_centroid(circles[0])
            _, y2 = contour_centroid(circles[1])
            if y1 < y2:
                circle_contour = circles[0]
            else:
                circle_contour = circles[1]

        # Draw the chosen circle (if there is one)
        if circle_contour is not None:
            (x, y), (w, h), angle = min_enclosing_ellipse(circle_contour)
            center = (int(x), int(y))
            radii = (int(w / 2), int(h / 2))
            cv2.ellipse(img, center, radii, int(angle), 0, 360, (255, 0, 0),
                    thickness=20)

        results = torpedoes_hole_vision.get()
        if circle_contour is None:
            results.visible = False
        else:
            results.visible = True
            results.center_x, results.center_y = self.normalized((x, y))
            results.radius = abs(w / img.shape[1] + h / img.shape[1]) / 4
        torpedoes_hole_vision.set(results)


        # Post images
        self.post('red mask', red_thresh)
        self.post('distance', red_dist)
        self.post('contours', mat) 
        self.post('circles', circles_mat)
        self.post('final', img)

    @property
    def is_debug(self):
        return self.options['debug']

if __name__ == '__main__':
    TorpedoesHole2023('forward', module_options)()

