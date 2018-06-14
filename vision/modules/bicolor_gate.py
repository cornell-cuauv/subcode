#!/usr/bin/env python3
from vision.modules.base import ModuleBase
from vision import options
import shm
import math
from enum import Enum
import cv2 as cv2
import numpy as np

gate = shm.bicolor_gate_vision

# SHM:
#  - general, black, and red centers
#  - confidence

module_options = [
    options.BoolOption('debug', False),
    options.IntOption('erode_size', 4, 1, 20),
    options.IntOption('gaussian_kernel', 12, 1, 20),
    options.IntOption('gaussian_stdev', 12, 0, 20),
    options.IntOption('thresh_size', 20, 1, 50),
    options.IntOption('min_area', 700, 1, 2000),
    options.IntOption('center_dist', 100, 1, 2000),
]

WHITE = (255, 255, 255)
RED = (0, 0, 255)
BLUE = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)

def rotate_img(img, theta):
    rows, cols, x = img.shape
    M = cv2.getRotationMatrix2D((cols / 2, rows / 2), theta, 1)
    return cv2.warpAffine(img, M, (cols, rows))

def get_kernel(size):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size * 2 + 1, size * 2 + 1), (size, size))

def clean(img, erode_size):
    kernel = get_kernel(erode_size)
    
    dilate = cv2.dilate(img, kernel)
    erode = cv2.erode(dilate, kernel)
    
    erode2 = cv2.erode(erode, kernel)
    dilate2 = cv2.dilate(erode2, kernel)
    
    return dilate2

def thresh(img, kernel, stdev, size):
    return cv2.adaptiveThreshold(cv2.GaussianBlur(img, (kernel * 2 + 1, kernel * 2 + 1), stdev, stdev), 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, size * 2 + 1, 0)

def draw_vert_line(img, x, color=WHITE):
    cv2.rectangle(img, (x, 0), (x, img.shape[0]), color, 4)

class BicolorGate(ModuleBase):
    def process(self, img):
        debug = self.options['debug']

        if debug:
            self.post('raw', img)

        # TODO does this rotation work?
        img = rotate_img(img, shm.kalman.roll.get())

        if debug:
            self.post('rotated', img)

        # We use the L from LUV and the S from HLS
        (luv_l, luv_u, luv_v) = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2LUV))
        (hls_h, hls_l, hls_s) = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2HLS))

        g_b_k = self.options['gaussian_kernel']
        g_b_sd = self.options['gaussian_stdev']
        a_t_s = self.options['thresh_size']

        # Thresholds
        luv_u_thresh = thresh(luv_u, g_b_k, g_b_sd, a_t_s)
        hls_s_thresh = thresh(hls_s, g_b_k, g_b_sd, a_t_s)

        if debug:
            self.post('luv_u_thresh', luv_u_thresh)
            self.post('hls_s_thresh', hls_s_thresh)

        # Combine them
        comp = luv_u_thresh & hls_s_thresh

        if debug:
            self.post('comp', comp)

        # Clean up
        comp_clean = cv2.erode(clean(comp, self.options['erode_size']), get_kernel(3))

        if debug:
            self.post('comp_clean', comp_clean)

        # Find all contours
        (x, contours, x) = cv2.findContours(comp_clean, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        draw = comp_clean.copy()

        tall = []
        wide = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.options['min_area']:
                x, y, w, h = cv2.boundingRect(contour)

                # Find contours that are "tall"
                if w != 0 and h / w > 4:
                    tall.append((int(x + w / 2), int(y + h / 2)))
                    cv2.rectangle(draw, (x, y), (x + w, y + h), (255, 0, 0), 4)
                elif h != 0 and w / h > 4:
                    wide.append((int(x + w / 2), int(y + h / 2)))
                    cv2.rectangle(draw, (x, y), (x + w, y + h), (255, 0, 0), 2)

        # Find center x of all tall contours
        avg_tall_x = 0
        for (x, y) in tall:
            avg_tall_x += x
        if len(tall) > 0:
            avg_tall_x /= len(tall)

        right = None
        left = None

        # Left is to the left of center, right is to the right
        # Pick the lowest (greatest y) of all possible lefts and rights
        for side in tall:
            if side[0] > avg_tall_x + self.options['center_dist']:
                if right == None or side[1] > right[1] or side[0] > right[0]:
                    right = side
            if side[0] < avg_tall_x - self.options['center_dist']:
                if left == None or side[1] > left[1] or side[0] < left[0]:
                    left = side

        top = None
        orientation = 0 # +1 is B_R, -1 is R_B

        if left != None and right != None:
            # Figure out which side is which
            # Find the lowest horizontal piece (higher ones might be reflections)
            for side in wide:
                if (left[0] < side[0] < right[0]) and (top == None or side[1] > top[1]):
                    top = side

            if top != None:
                fraction = (top[0] - left[0]) / (right[0] - left[0])
                if fraction > 0.6:
                    orientation = 1
                elif fraction < 0.4:
                    orientation = -1

        final = img.copy()

        if left != None:
            draw_vert_line(draw, left[0])
            draw_vert_line(final, left[0], RED)
        if right != None:
            draw_vert_line(draw, right[0])
            draw_vert_line(final, right[0], RED)
        if top != None:
            draw_vert_line(draw, top[0])
            if orientation == 1:
                top_color = BLUE
            elif orientation == -1:
                top_color = GREEN
            else:
                top_color = BLACK
            draw_vert_line(final, top[0], top_color)

        self.post('draw', draw)

        # We only detect if we see both left and right
        if left != None and right != None:
            gate_center_x = (left[0] + right[0]) / 2
            gate_center_y = (left[1] + right[1]) / 2

            gate.gate_center_prob.set(1)
            gate.gate_center_x.set(self.normalized(gate_center_x, 0))
            gate.gate_center_y.set(self.normalized(gate_center_y, 1))

            if top != None and orientation != 0:
                left_center_x = 0.75 * left[0] + 0.25 * right[0]
                right_center_x = 0.25 * left[0] + 0.75 * right[0]

                if orientation == 1:
                    gate.red_center_x.set(self.normalized(right_center_x, 0))
                    gate.black_center_x.set(self.normalized(left_center_x, 1))
                elif orientation == -1:
                    gate.red_center_x.set(self.normalized(left_center_x, 0))
                    gate.black_center_x.set(self.normalized(right_center_x, 1))

                # Just use the same vertical center
                gate.red_center_y.set(self.normalized(gate_center_y, 0))
                gate.black_center_y.set(self.normalized(gate_center_y, 1))
        else:
            gate.gate_center_prob.set(0)

        self.post('final', final)

if __name__ == '__main__':
    BicolorGate(None, module_options)()
