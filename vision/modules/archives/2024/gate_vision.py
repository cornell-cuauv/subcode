#!/usr/bin/env python3
from vision.modules.base import ModuleBase
from vision import options
from vision.framework.color import bgr_to_lab
from vision.framework.color import bgr_to_hsv
from vision.framework.color import white_balance_bgr, white_balance_bgr_blur
from vision.framework.color import range_threshold
from vision.framework.color import *
from vision.framework.feature import *
from vision.framework.draw import *
from vision.framework.transform import *
import copy
import cv2
import numpy as np
import shm

#module_options = [options.BoolOption('Hue Inversion', False), options.IntOption('Hue Min', 160, 0, 179), options.IntOption('Hue Max', 179, 0, 179), options.IntOption('Sat Min', 200, 0, 255), options.IntOption('Sat Max', 255, 0, 255), options.IntOption('Val Min', 80, 0, 255), options.IntOption('Val Max', 175, 0, 255), options.IntOption('Erode', 5, 1, 20), options.IntOption('Dilate', 5, 1, 20)]
#module_options = [options.BoolOption('Hue Inversion', True), options.IntOption('Hue Min', 17, 0, 179), options.IntOption('Hue Max', 80, 0, 179), options.IntOption('Sat Min', 80, 0, 255), options.IntOption('Sat Max', 255, 0, 255), options.IntOption('Val Min', 140, 0, 255), options.IntOption('Val Max', 255, 0, 255), options.IntOption('Erode', 5, 1, 20), options.IntOption('Dilate', 5, 1, 20)]
module_options = [
    options.BoolOption('Hue Inversion', True), 
    options.IntOption('Hue Min', 30, 0, 179), 
    options.IntOption('Hue Max', 150, 0, 179), 
    options.IntOption('Sat Min', 32, 0, 255), 
    options.IntOption('Sat Max', 255, 0, 255), 
    options.IntOption('Val Min', 70, 0, 255), 
    options.IntOption('Val Max', 255, 0, 255), 
    options.IntOption('Erode X', 8, 1, 40), 
    options.IntOption('Erode Y', 16, 1, 40), 
    options.IntOption('Dilate X', 6, 1, 40),
    options.IntOption('Dilate Y', 16, 1, 40),
    options.IntOption('White Balance Kernel', 100, 1, 200),
    options.IntOption('Water Surface Threshold', 50, 1, 255),
]

class GateVision(ModuleBase):
    def reset_debug_text(self):
        self.debug_text_pos = (25, 40)
    
    def draw_debug_text(self, text):
        text = text.replace("\n", " | ")
        average_color = np.mean(self.debug_image[self.debug_text_pos[1] + 16, :, :])
        if average_color < 127:
            text_color = (255, 255, 255)  # white
            text_outline = (0, 0, 0)  # black
        else:
            text_color = (0, 0, 0)  # black
            text_outline = (255, 255, 255)  # white
        
        draw_text(self.debug_image, text, self.debug_text_pos, 0.8, color=text_outline, thickness=8)
        draw_text(self.debug_image, text, self.debug_text_pos, 0.8, color=text_color, thickness=2)
        self.debug_text_pos = (self.debug_text_pos[0], self.debug_text_pos[1] + 32)
    
    
    def process(self, img):
        self.reset_debug_text()
        self.debug_image = img.copy()
        
        self.post('original', img)
        img = white_balance_bgr_blur(img, self.options['White Balance Kernel'])
        self.post('white balanced', img)
        
        hsv, hsv_split = bgr_to_hsv(img)
        hsv_h, hsv_s, hsv_v = hsv_split
        
        hsv_h_threshed = range_threshold(hsv_h, self.options['Hue Min'], self.options['Hue Max'])
        if self.options['Hue Inversion']:
            hsv_h_threshed = ~hsv_h_threshed
            
        hsv_s_threshed = range_threshold(hsv_s, self.options['Sat Min'], self.options['Sat Max'])
        hsv_v_threshed = range_threshold(hsv_v, self.options['Val Min'], self.options['Val Max'])
        
        self.post('threshed Hue', hsv_h_threshed)
        self.post('threshed Sat', hsv_s_threshed)
        self.post('threshed Val', hsv_v_threshed)
        
        combination = hsv_h_threshed & hsv_s_threshed & hsv_v_threshed
        
        combination = dilate(combination, rect_kernel(5, 1))
        combination = erode(combination, rect_kernel(self.options['Erode X'], self.options['Erode Y']))
        combination = dilate(combination, rect_kernel(self.options['Dilate X'], self.options['Dilate Y']))
        
        self.post('combination', combination)

        # find gate
        gate_results = shm.gate_vision.get()
        gate_contours = outer_contours(combination)
        ratio = 2

        def contour_ratio(contour):
            (x,y),(w,h),t = min_enclosing_rect(contour)
            w = max(1, w)
            h = max(1, h)
            return max(w/h, h/w)

        def contour_area(contour):
            (x,y),(w,h),t = min_enclosing_rect(contour)
            return w * h

        def valid_gate(contour):
            return ratio < contour_ratio(contour) and 1 < contour_area(contour)

        gate_contours = list(filter(valid_gate, list(gate_contours)))
        gate_contours.sort(key=lambda contour: contour_area(contour), reverse=True)

        draw_contours(img, gate_contours, color=(255, 0, 0), thickness=10)
        self.post("largest contours", img)
        
        min_x_dist = 20

        selected_contours_area = gate_contours[:3]

        while True:
            selected_contours = gate_contours[:3]
            selected_contours.sort(key=lambda contour: contour_centroid(contour)[0])
            
            changed = False
            for a, b in zip(selected_contours, selected_contours[1:]):
                x_a = contour_centroid(a)[0]
                x_b = contour_centroid(b)[0]
                if x_b - x_a < min_x_dist:
                    y_a = contour_centroid(a)[1]
                    y_b = contour_centroid(b)[1]
                    
                    
                    if y_b < y_a:
                        removal = b
                    else:
                        removal = a
                    gate_contours = list(filter(lambda contour: not np.array_equal(contour, removal), gate_contours))
                        
                    changed = True
                    
            if not changed:
                break

        selected_contours_area = gate_contours[:3]
        draw_contours(img, selected_contours_area, color=(0, 255, 0), thickness=10)
        self.post("largest contours without reflections", img)
        gate_xys = []

        self.draw_debug_text(f"Gates Detected: {len(selected_contours_area)}")
        
        found = False
        if len(selected_contours_area) == 3:
            gate_xys = []
            selected_contours = copy.deepcopy(selected_contours_area)
            selected_contours.sort(key=lambda contour: contour_centroid(contour)[0])
            for i, contour in enumerate(selected_contours):
                centroid = contour_centroid(contour)
                x, y = centroid
                gate_xys += [x, y]
            found = self.valid_gate_3(gate_results, *(gate_xys[:6]))
        if not found and len(selected_contours_area) >= 2:
            gate_xys = []
            selected_contours = sorted(selected_contours_area[:2], key=lambda contour: contour_centroid(contour)[0])
            for i, contour in enumerate(selected_contours):
                centroid = contour_centroid(contour)
                x, y = centroid
                gate_xys += [x, y]
            found = self.valid_gate_2(gate_results, *(gate_xys[:4]))
        if not found and len(selected_contours_area) >= 1:
            selected_contours = copy.deepcopy(selected_contours_area[:1])
            x, y = contour_centroid(selected_contours[0])
            x, y = self.normalized((x, y))
            self.draw_debug_text("left")
            gate_results.leftmost_visible = 1
            gate_results.leftmost_x, gate_results.leftmost_y = x, y
            self.clear_shm(gate_results, False, True, True)
            found = True

        if found:
            draw_contours(img, selected_contours, color=(0, 0, 255), thickness=10)
        else:
            self.draw_debug_text("none")
            self.clear_shm(gate_results, True, True, True)

        # update shm
        for i, contour in enumerate(selected_contours_area):
            centroid = contour_centroid(contour)
            x, y = centroid
            self.draw_debug_text(f"Gate {i + 1}: ({x}, {y})")

        self.post("gate", img)
        self.post("debug", self.debug_image)

        shm.gate_vision.set(gate_results)

    def clear_shm(self, gate_results, left, middle, right):
        if left:
            gate_results.leftmost_len = 0
            gate_results.leftmost_visible = 0
            gate_results.leftmost_x = 0
            gate_results.leftmost_y = 0
        if middle:
            gate_results.middle_len = 0
            gate_results.middle_visible = 0
            gate_results.middle_x = 0
            gate_results.middle_y = 0
        if right:
            gate_results.rightmost_len = 0
            gate_results.rightmost_visible = 0
            gate_results.rightmost_x = 0
            gate_results.rightmost_y = 0

    def valid_gate_3(self, gate_results, left_x, left_y, middle_x, middle_y, right_x, right_y):
        x_error = abs((right_x-middle_x)-(middle_x-left_x))
        x_ratio = 0.5
        # self.draw_debug_text(str(left_x) + str(middle_x) + str(right_x))
        # self.draw_debug_text("x" + str(x_error) + str(x_ratio*(right_x-middle_x)) + str(x_ratio*(middle_x-left_x)))
        if x_error>(x_ratio*(right_x-middle_x)) and x_error>(x_ratio*(middle_x-left_x)):
            return False
        y_ratio = 0.5
        # self.draw_debug_text("y" + str(right_y-middle_y) + str(y_ratio*(left_y-middle_y)))
        if abs(right_y-middle_y)>(y_ratio*(left_y-middle_y)):
            return False
        self.draw_debug_text("left middle right")
        gate_results.leftmost_visible = 1
        gate_results.middle_visible = 1
        gate_results.rightmost_visible = 1
        gate_results.leftmost_x, gate_results.leftmost_y = self.normalized((left_x, left_y))
        gate_results.middle_x, gate_results.middle_y = self.normalized((middle_x, middle_y))
        gate_results.rightmost_x, gate_results.rightmost_y = self.normalized((right_x, right_y))
        return True

    def valid_gate_2(self, gate_results, center1_x, center1_y, center2_x, center2_y):
        self.draw_debug_text(str(center1_x) + " " + str(center1_y))
        self.draw_debug_text(str(center2_x) + " " + str(center2_y))
        x_diff = center2_x - center1_x
        y_diff = abs(center2_y - center1_y)
        self.draw_debug_text("y_diff/x_diff " + str(y_diff/x_diff))
        if (x_diff>0 and y_diff/x_diff<0.15):
            self.draw_debug_text("middle right")
            gate_results.middle_visible = 1
            gate_results.rightmost_visible = 1
            gate_results.middle_x, gate_results.middle_y = self.normalized((center1_x, center1_y))
            gate_results.rightmost_x, gate_results.rightmost_y = self.normalized((center2_x, center2_y))
            self.clear_shm(gate_results, True, False, False)
            return True
        if (x_diff>0 and y_diff/x_diff<0.27):
            self.draw_debug_text("left right")
            gate_results.leftmost_visible = 1
            gate_results.rightmost_visible = 1
            gate_results.leftmost_x, gate_results.leftmost_y = self.normalized((center1_x, center1_y))
            gate_results.rightmost_x, gate_results.rightmost_y = self.normalized((center2_x, center2_y))
            self.clear_shm(gate_results, False, True, False)
            return True
        if (x_diff>0 and y_diff/x_diff<0.7):
            self.draw_debug_text("left middle")
            gate_results.leftmost_visible = 1
            gate_results.middle_visible = 1
            gate_results.leftmost_x, gate_results.leftmost_y = self.normalized((center1_x, center1_y))
            gate_results.middle_x, gate_results.middle_y = self.normalized((center2_x, center2_y))
            self.clear_shm(gate_results, False, False, True)
            return True
        return False


if __name__ == '__main__':
    GateVision("forward", module_options)()
