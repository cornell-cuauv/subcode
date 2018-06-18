#!/usr/bin/env python3
from vision.modules.base import ModuleBase
from vision import options
import shm
import math
from enum import Enum
import cv2 as cv2
import numpy as np
from scipy.spatial.distance import pdist, squareform

gate = shm.bicolor_gate_vision

# SHM:
#  - general, black, and red centers
#  - confidence

module_options = [
    options.BoolOption('debug', True),
    options.IntOption('erode_size', 3, 1, 40),
    options.IntOption('gaussian_kernel', 4, 1, 40),
    options.IntOption('gaussian_stdev', 4, 0, 40),
    options.IntOption('thresh_size', 70, 1, 100),
    options.IntOption('min_area', 700, 1, 2000),
    options.IntOption('center_dist', 100, 1, 2000),
    options.IntOption('luv_l_thresh_min', 1, 1, 254),
    options.IntOption('luv_l_thresh_max', 76, 1, 254),
    options.IntOption('hough_votes', 1000, 100, 1000000),
    options.IntOption('rho', 7, 1, 100),
    options.IntOption('bin_dist_threshold', 50, 0, 1000),
    options.IntOption('min_length', 50, 1, 100000),
    options.IntOption('max_gap', 50, 1, 100000),
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

    #dilate = cv2.dilate(img, kernel)
    #erode = cv2.erode(dilate, kernel)

    erode2 = cv2.erode(img, kernel)
    dilate2 = cv2.dilate(erode2, kernel)

    return dilate2

def thresh(img, kernel, stdev, size, thresh_type, c):
    return cv2.adaptiveThreshold(cv2.GaussianBlur(img, (kernel * 2 + 1, kernel * 2 + 1), stdev, stdev), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, thresh_type, size * 2 + 1, c)

def draw_vert_line(img, x, color=WHITE):
    cv2.rectangle(img, (x, 0), (x, img.shape[0]), color, 4)

class BicolorGate(ModuleBase):
    def process(self, img):
        debug = self.options['debug']


        if debug:
            self.post('raw', img)

        # TODO does this rotation work?
        #img = rotate_img(img, shm.kalman.roll.get())

        if debug:
            self.post('rotated', img)

        # We use the L from LUV and the S from HLS
        (luv_l, luv_u, luv_v) = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2LUV))
        (hls_h, hls_l, hls_s) = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2HLS))
        (ycrcb_y, ycrcb_cr, ycrcb_cb) = cv2.split(cv2.cvtColor(img, cv2.COLOR_BGR2YCR_CB))

        g_b_k = self.options['gaussian_kernel']
        g_b_sd = self.options['gaussian_stdev']
        a_t_s = self.options['thresh_size']

        erode_size = self.options['erode_size']

        # Thresholds
        luv_u_thresh = clean(thresh(luv_u, g_b_k, g_b_sd, a_t_s, cv2.THRESH_BINARY, -1), erode_size)
        hls_h_thresh = clean(thresh(hls_h + 180, g_b_k, g_b_sd, a_t_s, cv2.THRESH_BINARY_INV, 2), erode_size)
        ycrcb_cr_thresh = clean(thresh(ycrcb_cr, g_b_k, g_b_sd, a_t_s, cv2.THRESH_BINARY, -1), erode_size)

        #luv_l_thresh = clean(cv2.inRange(luv_l, self.options['luv_l_thresh_min'], self.options['luv_l_thresh_max']), erode_size)

        if debug:
            self.post('luv_u_thresh', luv_u_thresh)
            self.post('hls_h_thresh', hls_h_thresh)
            self.post('ycrcb_cr_thresh', ycrcb_cr_thresh)

        # Combine them
        norm = (luv_u_thresh / 255) + (hls_h_thresh / 255) + (ycrcb_cr_thresh / 255)
        comp = (norm >= 2) * 255
        comp = comp.astype("uint8")

        if debug:
            self.post('comp', comp)

        # Clean up
        comp_clean = comp #cv2.erode(clean(comp, self.options['erode_size']), get_kernel(3))

        if debug:
            self.post('comp_clean', comp_clean)

        #edge_img = comp_clean.copy()
        #edges = cv2.Canny(edge_img, 50, 150, apertureSize = 3)

        lines = cv2.HoughLinesP(comp_clean, self.options["rho"], np.pi / 30, self.options["hough_votes"], minLineLength=self.options["min_length"], maxLineGap=self.options["max_gap"])

        horiz_lines = []
        vert_lines = []

        if debug and lines is not None:
            lines_img = img.copy()
            for line in lines:
                # rho, theta = line[0]
                # delta = np.pi / 6
                # valid_angles = np.array([0, np.pi/2, np.pi, np.pi*3/2, np.pi*2])
                # angle_difs = np.abs(valid_angles - theta)
                # if np.min(angle_difs) > delta:
                #     continue
                # a = np.cos(theta)
                # b = np.sin(theta)
                # x0 = a*rho
                # y0 = b*rho
                # x1 = int(x0 + 1000*(-b))
                # y1 = int(y0 + 1000*(a))
                # x2 = int(x0 - 1000*(-b))
                # y2 = int(y0 - 1000*(a))

                # cv2.line(lines_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                # cv2.circle(lines_img, (x0, y0), 10, (0, 255, 0), 10)
                # good_lines.append((rho, a, b))

                (x1, y1, x2, y2) = line[0]
                
                delta = np.pi / 12
#                valid_angles = np.array([0])

                theta = math.atan2(y2 - y1, x2 - x1) % np.pi
                #angle_dif = theta % (np.pi / 2)
                #if delta < angle_dif < np.pi / 2 - delta:
                #    continue

                vert_angles = np.array([np.pi / 2])
                horiz_angles = np.array([0, np.pi])

                vert_difs = np.abs(vert_angles - theta)
                horiz_difs = np.abs(horiz_angles - theta)

                if np.min(vert_difs) < delta:
                    vert_lines.append((x1, y1, x2, y2))
                elif np.min(horiz_difs) < delta:
                    horiz_lines.append((x1, y1, x2, y2))
                else:
                    continue

                cv2.line(lines_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
                #cv2.circle(lines_img, (x0, y0), 10, (0, 255, 0), 10)
                #good_lines.append((x1, y1, x2, y2))

            self.post("lines", lines_img)

            dist_thresh = self.options['bin_dist_threshold']

            vert_bins = make_bins(vert_lines, 1, dist_thresh)
            horiz_bins = make_bins(horiz_lines, 0, dist_thresh)

            binned = img.copy()

            for line in vert_bins:
                cv2.line(binned, (line[0], line[1]), (line[2], line[3]), BLUE, 2)
            for line in horiz_bins:
                cv2.line(binned, (line[0], line[1]), (line[2], line[3]), RED, 2)

            self.post('binned', binned)

            # vert_dists = squareform(pdist(vert_lines))
            # horiz_dists = squareform(pdist(horiz_lines))
            # dist_thresh = self.options['bin_dist_threshold']

            # vert_out = []
            # horiz_out = []

            # i = 0
            # while i < len(

            # good_lines_np = np.array(good_lines)

            # good_lines_np[:] *= [1 / img.shape[0], 1, 1]
            # dists = squareform(pdist(good_lines_np))

            # bins = []
            # dist_thresh = self.options["bin_dist_threashold"]

            # i = 0
            # while i < len(good_lines) - 1:
            #     j = i + 1
            #     while j < len(good_lines):
            #         if dists[i, j] < dist_thresh:
            #             del good_lines[j]
            #         else:
            #             j += 1


            #     bins.append(good_lines[i])
            #     i += 1


            # bins.append(good_lines[-1])

            # good_lines_img = img.copy()

            # for line in good_lines:
            #     x1, y1, x2, y2 = line

            #     cv2.line(good_lines_img, (x1, y1), (x2, y2), (0, 0, 255), 2)
            #     #cv2.circle(good_lines_img, (x0, y0), 10, (0, 255, 0), 10)

            # self.post("good lines", good_lines_img)

        ## Find all contours
        #(x, contours, x) = cv2.findContours(comp_clean, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        #draw = comp_clean.copy()

        #tall = []
        #wide = []

        #for contour in contours:
        #    area = cv2.contourArea(contour)
        #    if area > self.options['min_area']:
        #        x, y, w, h = cv2.boundingRect(contour)

        #        # Find contours that are "tall"
        #        if w != 0 and h / w > 8:
        #            tall.append((int(x + w / 2), int(y + h / 2)))
        #            cv2.rectangle(draw, (x, y), (x + w, y + h), (255, 0, 0), 4)
        #        elif h != 0 and w / h > 8:
        #            wide.append((int(x + w / 2), int(y + h / 2)))
        #            cv2.rectangle(draw, (x, y), (x + w, y + h), (255, 0, 0), 2)

        ## Find center x of all tall contours
        #avg_tall_x = 0
        #for (x, y) in tall:
        #    avg_tall_x += x
        #if len(tall) > 0:
        #    avg_tall_x /= len(tall)

        #right = None
        #left = None

        ## Left is to the left of center, right is to the right
        ## Pick the lowest (greatest y) of all possible lefts and rights
        #for side in tall:
        #    if side[0] > avg_tall_x + self.options['center_dist']:
        #        if right == None or side[1] > right[1] or side[0] > right[0]:
        #            right = side
        #    if side[0] < avg_tall_x - self.options['center_dist']:
        #        if left == None or side[1] > left[1] or side[0] < left[0]:
        #            left = side

        #top = None
        #orientation = 0 # +1 is B_R, -1 is R_B

        #if left != None and right != None:
            # Figure out which side is which
            # Find the highest horizontal piece (reflections seem to be more reliable)
            #for side in wide:
            #    # (left[0] < side[0] < right[0])
            #    if top == None or side[1] < top[1]:
            #        top = side

            #if top != None:
            #    fraction = (top[0] - left[0]) / (right[0] - left[0])
            #    if fraction > 0.6:
            #        orientation = 1
            #    elif fraction < 0.4:
            #        orientation = -1

        #for side in wide:
        #    # (left[0] < side[0] < right[0])
        #    if top == None or side[1] < top[1]:
        #        top = side

        #orientation = 1

        #if left != None and right != None:
        #    pass
            #if top != None:
            #    fraction = (top[0] - left[0]) / (right[0] - left[0])
            #    if fraction > 0.6:
            #        orientation = 1
            #    elif fraction < 0.4:
            #        orientation = -1
        #elif left == None and right == None and top != None:
        #    for side in tall:
        #        if side[0] > top[0] + self.options['center_dist']:
        #            if right == None or side[1] > right[1] or side[0] > right[0]:
        #                right = side
        #        if side[0] < top[0] - self.options['center_dist']:
        #            if left == None or side[1] > left[1] or side[0] < left[0]:
        #                left = side

        #final = img.copy()

        #if left != None:
        #    draw_vert_line(draw, left[0])
        #    draw_vert_line(final, left[0], RED)
        #if right != None:
        #    draw_vert_line(draw, right[0])
        #    draw_vert_line(final, right[0], RED)
        #if top != None:
        #    draw_vert_line(draw, top[0])
        #    if orientation == 1:
        #        top_color = BLUE
        #    elif orientation == -1:
        #        top_color = GREEN
        #    else:
        #        top_color = BLACK
        #    draw_vert_line(final, top[0], top_color)

        #self.post('draw', draw)

        ## We only detect if we see both left and right
        #if left != None and right != None:
        #    gate_center_x = (left[0] + right[0]) / 2
        #    gate_center_y = (left[1] + right[1]) / 2

        #    gate.gate_center_prob.set(1)
        #    gate.gate_center_x.set(self.normalized(gate_center_x, 0))
        #    gate.gate_center_y.set(self.normalized(gate_center_y, 1))

        #    if top != None and orientation != 0:
        #        left_center_x = 0.75 * left[0] + 0.25 * right[0]
        #        right_center_x = 0.25 * left[0] + 0.75 * right[0]

        #        if orientation == 1:
        #            gate.red_center_x.set(self.normalized(right_center_x, 0))
        #            gate.black_center_x.set(self.normalized(left_center_x, 1))
        #        elif orientation == -1:
        #            gate.red_center_x.set(self.normalized(left_center_x, 0))
        #            gate.black_center_x.set(self.normalized(right_center_x, 1))

        #        # Just use the same vertical center
        #        gate.red_center_y.set(self.normalized(gate_center_y, 0))
        #        gate.black_center_y.set(self.normalized(gate_center_y, 1))
        #else:
        #    gate.gate_center_prob.set(0)

        #    if top != None:
        #        gate.red_center_x.set(self.normalized(top[0], 0))

        #    if orientation == 1:
        #        pass
        #    elif orientation == -1:
        #        pass

        #self.post('final', final)

# axis: 0 for horiz, 1 for vert
def make_bins(lines, axis, thresh):
    def avg_val_for_axis(line, axis):
        if axis == 0:
            return (line[0] + line[2]) / 2
        elif axis == 1:
            return (line[1] + line[3]) / 2

    bins = []
    for line in lines:
        for line2 in lines:
            if line != line2 and abs(avg_val_for_axis(line, axis) - avg_val_for_axis(line2, axis)) < thresh:
                # Bin them
                found_bin = False
                for bin in bins:
                    if line in bin or line2 in bin:
                        bin.add(line)
                        bin.add(line2)
                        found_bin = True
                if not found_bin:
                    bins.append(set([line, line2]))

    out = []

    for bin in bins:
        x1 = 0
        x2 = 0
        y1 = 0
        y2 = 0

        for line in bin:
            x1 += line[0]
            x2 += line[2]
            y1 += line[1]
            y2 += line[3]

        x1 = int(x1 / len(bin))
        x2 = int(x2 / len(bin))
        y1 = int(y1 / len(bin))
        y2 = int(y2 / len(bin))

        out.append((x1, y1, x2, y2))

    return out

if __name__ == '__main__':
    BicolorGate(None, module_options)()
