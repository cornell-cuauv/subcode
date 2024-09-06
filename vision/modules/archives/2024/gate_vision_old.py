#!/usr/bin/env python3
from vision.modules.base import ModuleBase
from vision import options
from vision.framework.color import bgr_to_lab
from vision.framework.color import bgr_to_hsv
from vision.framework.color import range_threshold
from vision.framework.color import *
from vision.framework.feature import *
from vision.framework.draw import *
from vision.framework.transform import *
import cv2
import numpy as np
import shm

module_options = [options.BoolOption('Hue Inversion', False), options.IntOption('Hue Min', 160, 0, 179), options.IntOption('Hue Max', 179, 0, 179), options.IntOption('Sat Min', 200, 0, 255), options.IntOption('Sat Max', 255, 0, 255), options.IntOption('Val Min', 80, 0, 255), options.IntOption('Val Max', 175, 0, 255), options.IntOption('Erode', 5, 1, 20), options.IntOption('Dilate', 5, 1, 20)]
#module_options = [options.BoolOption('Hue Inversion', True), options.IntOption('Hue Min', 17, 0, 179), options.IntOption('Hue Max', 80, 0, 179), options.IntOption('Sat Min', 80, 0, 255), options.IntOption('Sat Max', 255, 0, 255), options.IntOption('Val Min', 140, 0, 255), options.IntOption('Val Max', 255, 0, 255), options.IntOption('Erode', 5, 1, 20), options.IntOption('Dilate', 5, 1, 20)]

class Gate(ModuleBase):
    def process(self, img):
        hsv, hsv_split = bgr_to_hsv(img)
        hsv_h, hsv_s, hsv_v = hsv_split
        self.post('original', img)
        hsv_h_threshed = range_threshold(hsv_h, self.options['Hue Min'], self.options['Hue Max'])
        if self.options['Hue Inversion']:
            hsv_h_threshed = ~hsv_h_threshed
        hsv_s_threshed = range_threshold(hsv_s, self.options['Sat Min'], self.options['Sat Max'])
        hsv_v_threshed = range_threshold(hsv_v, self.options['Val Min'], self.options['Val Max'])
        self.post('threshed Hue', hsv_h_threshed)
        self.post('threshed Sat', hsv_s_threshed)
        self.post('threshed Val', hsv_v_threshed)
        combination = hsv_h_threshed & hsv_s_threshed & hsv_v_threshed
        combination = erode(combination, rect_kernel(self.options['Erode']))
        combination = dilate(combination, rect_kernel(self.options['Dilate']))
        self.post('combination', combination)

        # find gate
        gate_results = shm.gate_vision.get()
        gate_contours = outer_contours(combination)
        if (len(gate_contours) > 0):
            (x,y),(w,h),t = min_enclosing_rect(gate_contours[0])
            print(w*h)
            ratio = 2
            max1_contour = gate_contours[0]
            max1_area = 0
            max1_ratio = 0
            max2_contour = gate_contours[0]
            max2_area = 0
            max2_ratio = 0
            max3_contour = gate_contours[0]
            max3_area = 0
            max3_ratio = 0
            for contour in gate_contours:
                (x,y),(w,h),t = min_enclosing_rect(contour)
                rect = min_enclosing_rect(contour)
                #print(cv2.boxPoints(rect))
                box = np.int0(cv2.boxPoints(rect))
                #print("box", box)
                cv2.drawContours(img, [box], 0, (255, 200, 0), 5)
                #print(h/w, w/h)
                if (h>0 and w>0):
                    if (h/w>ratio or w/h>ratio) and w*h>=max1_area:
                        max3_ratio = max2_ratio
                        max3_contour = max2_contour
                        max3_area = max2_area
                        max2_ratio = max1_ratio
                        max2_contour = max1_contour
                        max2_area = max1_area
                        max1_ratio = max(h/w, w/h)
                        max1_contour = contour
                        max1_area = w*h
                    elif (h/w>ratio or w/h>ratio) and w*h>=max2_area:
                        max3_ratio = max2_ratio
                        max3_contour = max2_contour
                        max3_area = max2_area
                        max2_ratio = max(h/w, w/h)
                        max2_contour = contour
                        max2_area = w*h
                    elif (h/w>ratio or w/h>ratio) and w*h>=max3_area:
                        print(w*h)
                        max3_ratio = max(h/w, w/h)
                        max3_contour = contour
                        max3_area = w*h
            draw_contours(img, [max1_contour, max2_contour, max3_contour], color=(255, 0, 0), thickness=10)
            self.post("largest contours", img)

            # update shm
            print(contour_centroid(max1_contour))
            print(contour_centroid(max2_contour))
            print(contour_centroid(max3_contour))
            found = False
            print(max3_ratio)
            print(max3_area)
            if max1_area==0 and max2_area==0 and max3_area==0:    # none detected
                print("none")
                found = True
                self.clear_shm(gate_results, True, True, True)
            elif max1_area>0 and max2_area>0 and max3_area>0:    # all 3 detected
                center1_x, center1_y = contour_centroid(max1_contour)
                center2_x, center2_y = contour_centroid(max2_contour)
                center3_x, center3_y = contour_centroid(max3_contour)
                if center1_x<center2_x<center3_x:
                    found = self.valid_gate_3(gate_results, center1_x, center1_y, center2_x, center2_y, center3_x, center3_y)
                elif center1_x<center3_x<center2_x:
                    found = self.valid_gate_3(gate_results, center1_x, center1_y, center3_x, center3_y, center2_x, center2_y)
                elif center2_x<center1_x<center3_x:
                    found = self.valid_gate_3(gate_results, center2_x, center2_y, center1_x, center1_y, center3_x, center3_y)
                elif center2_x<center3_x<center1_x:
                        found = self.valid_gate_3(gate_results, center2_x, center2_y, center3_x, center3_y, center1_x, center1_y)
                elif center3_x<center2_x<center1_x:
                    found = self.valid_gate_3(gate_results, center3_x, center3_y, center2_x, center2_y, center1_x, center1_y)
                else:
                    found = self.valid_gate_3(gate_results, center3_x, center3_y, center1_x, center1_y, center2_x, center2_y)
                if found:
                    draw_contours(img, [max1_contour, max2_contour, max3_contour], thickness=10)
            if not found and max1_area>0 and max2_area>0:     # 2 detected
                max1_x, max1_y = contour_centroid(max1_contour)
                max2_x, max2_y = contour_centroid(max2_contour)
                difference_x = abs(max2_x - max1_x)
                difference_y = abs(max2_y - max1_y)
                center1_x, center1_y = max1_x, max1_y
                center2_x, center2_y = max2_x, max2_y
                if (max1_x>max2_x):
                    center1_x, center1_y = max2_x, max2_y
                    center2_x, center2_y = max1_x, max1_y
                found = self.valid_gate_2(gate_results, center1_x, center1_y, center2_x, center2_y)
                if found:
                    draw_contours(img, [max1_contour, max2_contour], thickness=10)
            if not found and max1_area>0:     # 1 detected
                print("left")
                draw_contours(img, [max1_contour], thickness=10)
                center1_x, center1_y = contour_centroid(max1_contour)
                gate_results.leftmost_visible = 1
                gate_results.leftmost_x, gate_results.leftmost_y = self.normalized((center1_x, center1_y))
                self.clear_shm(gate_results, False, True, True)
            self.post("gate", img)
        else:
            self.clear_shm(gate_results, True, True, True)
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
        x_ratio = 0.3
        print(left_x, middle_x, right_x)
        print("x", x_error, x_ratio*(right_x-middle_x), x_ratio*(middle_x-left_x))
        if x_error>(x_ratio*(right_x-middle_x)) and x_error>(x_ratio*(middle_x-left_x)):
            return False
        y_ratio = 0.2
        print("y", (right_y-middle_y), y_ratio*(left_y-middle_y))
        if abs(right_y-middle_y)>(y_ratio*(left_y-middle_y)):
            return False
        print("left middle right")
        gate_results.leftmost_visible = 1
        gate_results.middle_visible = 1
        gate_results.rightmost_visible = 1
        gate_results.leftmost_x, gate_results.leftmost_y = self.normalized((left_x, left_y))
        gate_results.middle_x, gate_results.middle_y = self.normalized((middle_x, middle_y))
        gate_results.rightmost_x, gate_results.rightmost_y = self.normalized((right_x, right_y))
        return True

    def valid_gate_2(self, gate_results, center1_x, center1_y, center2_x, center2_y):
        x_diff = center2_x - center1_x
        y_diff = abs(center2_y - center1_y)
        #print("y_diff/x_diff", y_diff/x_diff)
        if (x_diff>0 and y_diff/x_diff<0.15):
            print("middle right")
            gate_results.middle_visible = 1
            gate_results.rightmost_visible = 1
            gate_results.middle_x, gate_results.middle_y = self.normalized((center1_x, center1_y))
            gate_results.rightmost_x, gate_results.rightmost_y = self.normalized((center2_x, center2_y))
            self.clear_shm(gate_results, True, False, False)
            return True
        if (x_diff>0 and y_diff/x_diff<0.4):
            print("left right")
            gate_results.leftmost_visible = 1
            gate_results.rightmost_visible = 1
            gate_results.leftmost_x, gate_results.leftmost_y = self.normalized((center1_x, center1_y))
            gate_results.rightmost_x, gate_results.rightmost_y = self.normalized((center2_x, center2_y))
            self.clear_shm(gate_results, False, True, False)
            return True
        if (x_diff>0 and y_diff/x_diff<0.7):
            print("left middle")
            gate_results.leftmost_visible = 1
            gate_results.middle_visible = 1
            gate_results.leftmost_x, gate_results.leftmost_y = self.normalized((center1_x, center1_y))
            gate_results.middle_x, gate_results.middle_y = self.normalized((center2_x, center2_y))
            self.clear_shm(gate_results, False, False, True)
            return True
        return False


if __name__ == '__main__':
    Gate("forward", module_options)()
