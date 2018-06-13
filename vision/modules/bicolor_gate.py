#!/usr/bin/env python3
from vision.modules.base import ModuleBase
from vision import options
import shm.yellow_buoy_results as gate
import math
import cv2 as cv2
import numpy as np

# SHM:
#  - general, black, and red centers
#  - confidence

module_options = [
#    options.IntOption('luv_u_thresh_min', 102, 1, 254),
#    options.IntOption('luv_u_thresh_max', 254, 1, 254),
#    options.IntOption('hls_s_thresh_min', 40, 1, 254),
#    options.IntOption('hls_s_thresh_max', 254, 1, 254),
    options.IntOption('erode_size', 4, 1, 20),
    options.IntOption('gaussian_kernel', 12, 1, 20),
    options.IntOption('gaussian_stdev', 12, 0, 20),
    options.IntOption('thresh_size', 20, 1, 50),
    options.IntOption('min_area', 700, 1, 2000),
    options.IntOption('center_dist', 100, 1, 2000),
]

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

class BicolorGate(ModuleBase):
    def process(self, img):
        self.post('raw', img)

        # We use the L from LUV and the S from HLS
        (luv_l, luv_u, luv_v) = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2LUV))
        (hls_h, hls_l, hls_s) = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2HLS))

        g_b_k = self.options['gaussian_kernel']
        g_b_sd = self.options['gaussian_stdev']
        a_t_s = self.options['thresh_size']

        # Thresholds
        luv_u_thresh = thresh(luv_u, g_b_k, g_b_sd, a_t_s)
        hls_s_thresh = thresh(hls_s, g_b_k, g_b_sd, a_t_s)

        self.post('luv_u_thresh', luv_u_thresh)
        self.post('hls_s_thresh', hls_s_thresh)

        # Combine them
        comp = luv_u_thresh & hls_s_thresh

        self.post('comp', comp)

        # Clean up
        comp_clean = cv2.erode(clean(comp, self.options['erode_size']), get_kernel(3))

        self.post('comp_clean', comp_clean)

        # Find all contours
        (x, contours, x) = cv2.findContours(comp_clean, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        draw = comp_clean.copy()

        tall = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.options['min_area']:
                x, y, w, h = cv2.boundingRect(contour)

                # Find contours that are "tall"
                if (w != 0 and h / w > 4):
                    tall.append((x, y))
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
                if right == None or right[1] > side[1] or right[0] < side[0]:
                    right = side
            if side[0] < avg_tall_x - self.options['center_dist']:
                if left == None or left[1] > side[1] or left[0] > side[0]:
                    left = side

        if left != None:
            cv2.rectangle(draw, (left[0], 0), (left[0], len(draw)), (255, 255, 0), 4)
        if right != None:
            cv2.rectangle(draw, (right[0], 0), (right[0], len(draw)), (255, 255, 0), 4)

        self.post('draw', draw)

        # We only detect if we see both left and right
        if left != None and right != None:
            gate.heuristic_score = 1
            gate.center_x.set(self.normalized((left[0] + right[0]) / 2, 0))
            gate.center_y.set(self.normalized((left[1] + right[1]) / 2, 1))
        else:
            gate.heuristic_score = 0

if __name__ == '__main__':
    BicolorGate(None, module_options)()
