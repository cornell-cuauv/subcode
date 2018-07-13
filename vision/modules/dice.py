#!/usr/bin/env python3

# Written by Will Smith.

import traceback
import sys
import math

import cv2
import numpy as np
import shm

from vision.modules.base import ModuleBase
from vision import options

import slam.slam_util as slam
from will_common import find_best_match

options = [
    options.BoolOption('debug', False),
    options.IntOption('hsv_thresh_c', 20, 0, 100),
]

FORWARD_CAM_WIDTH = shm.camera.forward_width.get()
FORWARD_CAM_HEIGHT = shm.camera.forward_height.get()

class Dice(ModuleBase):
    def post_umat(self, tag, img):
        self.post(tag, cv2.UMat.get(img))

    def kernel(self, size):
        return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size * 2 + 1, size * 2 + 1), (size, size))

    def dist(self, p1, p2):
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

    def process(self, mat):
        # for simulator
        shm.camera.forward_width.set(mat.shape[1])
        shm.camera.forward_height.set(mat.shape[0])
        global FORWARD_CAM_WIDTH
        FORWARD_CAM_WIDTH = mat.shape[0]

        try:
            debug = self.options['debug']

            if debug:
                self.post('raw', mat)

            hsv_h, hsv_s, hsv_v = cv2.split(cv2.cvtColor(mat, cv2.COLOR_BGR2HSV))
            #luv_l, luv_u, luv_v = cv2.split(cv2.cvtColor(mat, cv2.COLOR_BGR2LUV))
            #y_y, y_cr, y_cb = cv2.split(cv2.cvtColor(mat, cv2.COLOR_BGR2YCR_CB))

            if debug:
                self.post('hsv_v', hsv_v)
                #self.post('luv_u', luv_u)
                #self.post('luv_v', luv_v)
                #self.post('y_cr', y_cr)
                #self.post('y_cb', y_cb)

            hsv_v_thresh = cv2.adaptiveThreshold(hsv_v, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 99, self.options['hsv_thresh_c'])
            #luv_u_thresh = cv2.adaptiveThreshold(luv_u, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 99, 5)
            #luv_v_thresh = cv2.adaptiveThreshold(luv_v, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 199, 5)
            #y_cr_thresh = cv2.adaptiveThreshold(y_cr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 99, 5)
            #y_cb_thresh = cv2.adaptiveThreshold(y_cb, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 5)

            hsv_v_c = cv2.erode(hsv_v_thresh, self.kernel(0))
            #luv_u_c = cv2.erode(luv_u_thresh, self.kernel(0))
            #luv_v_c = cv2.erode(luv_v_thresh, self.kernel(0))
            #y_cr_c = cv2.erode(y_cr_thresh, self.kernel(0))
            #y_cb_c = cv2.erode(y_cb_thresh, self.kernel(0))

            if debug:
                self.post('hsv_v_c', hsv_v_c)
                #self.post('luv_u_c', luv_u_c)
                #self.post('luv_v_c', luv_v_c)
                #self.post('y_cr_c', y_cr_c)
                #self.post('y_cb_c', y_cb_c)

            # Find the dots in hsv_v

            x, contours, x = cv2.findContours(hsv_v_c, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            dots = []

            # Problem is that this depends on the distance
            # When the dice are really far away the dots are tiny
            min_area = 10

            for contour in contours:
                area = cv2.contourArea(contour)
                if area > min_area:
                    # Bound with circle
                    x, circ_r = cv2.minEnclosingCircle(contour)
                    circ_area = math.pi * circ_r**2

                    if circ_area / area < 2.5:
                        # problems if contour isn't big enough
                        try:
                            # Bound with ellipse
                            (ell_cx, ell_cy), (ell_w, ell_h), theta = cv2.fitEllipse(contour)
                            ell_area = math.pi * ell_w * ell_h / 4

                            if ell_area / area < 1.5:
                                dots.append((contour, (ell_cx, ell_cy), (ell_w + ell_h) / 2))
                        except cv2.error:
                            pass

            dotted = mat.copy()
            density_dots = np.zeros(mat.shape, np.uint8)

            for dot in dots:
                x, y, w, h = cv2.boundingRect(dot[0])
                cv2.rectangle(dotted, (x, y), (x+w, y+h), 0, thickness=2)

            cv2.drawContours(density_dots, [dot[0] for dot in dots], -1, (255, 255, 255), 3)
            if debug:
                self.post('density_dots', density_dots)
                self.post('dotted', dotted)

            # Group the dots into buckets

            # Each dot on the same die should be close together and have a similar area

            # Start out with all dots in separate groups and then combine them
            groups = [set([dot[1]]) for dot in dots]

            # This iteration avoids checking the same pair twice
            for i, dot1 in enumerate(dots):
                for dot2 in dots[i+1:]:
                    dist = self.dist(dot2[1], dot1[1])
                    radius_ratio = max(dot1[2], dot2[2]) / min(dot1[2], dot2[2])
                    avg_radius = (dot1[2] + dot2[2]) / 2

                    if dist < avg_radius * 5 and radius_ratio < 1.5:
                        # They should be in the same group

                        # Find the two groups
                        group1 = None
                        group2 = None
                        for group in groups:
                            if dot1[1] in group:
                                group1 = group
                            if dot2[1] in group:
                                group2 = group
                            if (group1 is not None) and (group2 is not None):
                                break

                        if group1 != group2:
                            # Combine the groups
                            group1 |= group2
                            groups.remove(group2)

            groups_out = dotted.copy()

            # Sort by size - most dots first
            groups = sorted(groups, key=lambda group: len(group), reverse=True)

            shm_values = []

            SHM_VARS = [shm.dice0, shm.dice1] #, shm.dice2, shm.dice3]

            #count = 0
            for group in groups:
                gcx = int(sum([dot[0] for dot in group]) / len(group))
                gcy = int(sum([dot[1] for dot in group]) / len(group))
                rad = max([self.dist(dot1, dot2) for dot1 in group for dot2 in group]) / 2
                dist = None if rad == 0 else 0.11 * FORWARD_CAM_WIDTH / rad # hella sketch, be ware or be dare

                shm_values.append((gcx, gcy, len(group), rad, dist))

                cv2.circle(groups_out, (gcx, gcy), len(group) * 10, (0, 0, 255) if len(group) >= 5 else (0, 0, 0), thickness=(2 * len(group)))

                #if dist is not None:
                #    x, y = slam.sub_to_vision(slam.slam_to_sub(slam.sub_to_slam(slam.vision_to_sub(gcx, gcy, dist, 0))), 0)
                #    count += 1
                #    print(count, x, y)
                #    cv2.circle(groups_out, (int(x), int(y)), 30, (0, 255, 255), thickness=10)

            # Want at least two values
            #shm_values += [None] * (len(SHM_VARS) - min(len(shm_values), len(SHM_VARS)))

            if debug:
                self.post('groups_out', groups_out)

            slam_keys = ['dice1', 'dice2']

            old_data = [slam.request(key, 'f') for key in slam_keys]
            new_data = shm_values[:2]

            data = find_best_match(old_data, new_data, lambda new, old: self.dist(new, (old[0], old[1])))

            slam_out = groups_out.copy()

            for (key, datum) in zip(slam_keys, data):
                (cx, cy, count, radius, dist) = datum
                if count >= 5:
                    slam.observe(key, cx, cy, dist, 'f')

            #roulette_coords = slam.sub_to_vision(slam.slam_to_sub(np.array([5 - shm.kalman.north.get(), -6 - shm.kalman.east.get(), 3.5 - shm.kalman.depth.get()])), 0)
            #cv2.circle(slam_out, (int(roulette_coords[0]), int(roulette_coords[1])), 100, (255, 255, 0), thickness=10)

            #self.post('slam_out', slam_out)

            for i, (val, var) in enumerate(zip(data, SHM_VARS)):
                new_var = var.get()

                if val is None:
                    new_var.visible = False
                else:
                    (cx, cy, count, radius, dist) = val

                    dx, dy, d = slam.request_pos_rel(slam_keys[i], 'f')

                    new_var.visible = True
                    new_var.center_x = 0 #self.normalized(slammed_coords[0], 1)
                    new_var.center_y = 0 #self.normalized(slammed_coords[1], 0)
                    new_var.count = count
                    new_var.radius = radius
                    new_var.radius_norm = radius / FORWARD_CAM_WIDTH if FORWARD_CAM_WIDTH != 0 else -1

                    new_var.theta = np.arctan2(dy, dx)
                    new_var.depth = d + shm.kalman.depth.get()
                    # Assuming depth is level already
                    new_var.dist = np.sqrt(dx**2 + dy**2)

                var.set(new_var)

            self.post('slam_out', slam_out)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)
if __name__ == '__main__':
    Dice('forward', options)()
