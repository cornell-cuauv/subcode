#!/usr/bin/env python3

"""
Gate Vision Module

OUTPUTS: TODO
STATUS:
    * Untested in the simulator.
    * Working in the pool (but not that well) when specifically tuned as of Jul 5.
"""

simulator_red_lab_l_min = 0
simulator_red_lab_l_max = 0
simulator_red_lab_a_min = 0
simulator_red_lab_a_max = 0
simulator_red_lab_b_min = 0
simulator_red_lab_b_max = 0

simulator_black_lab_l_min = 0
simulator_black_lab_l_max = 0
simulator_black_lab_a_min = 0
simulator_black_lab_a_max = 0
simulator_black_lab_b_min = 0
simulator_black_lab_b_max = 0

pool_red_lab_l_min = 0
pool_red_lab_l_max = 46
pool_red_lab_a_min = 0
pool_red_lab_a_max = 43
pool_red_lab_b_min = 43
pool_red_lab_b_max = 136

pool_black_lab_l_min = 0
pool_black_lab_l_max = 24
pool_black_lab_a_min = 0
pool_black_lab_a_max = 27
pool_black_lab_b_min = 0
pool_black_lab_b_max = 30

import os
import cv2
import shm
from vision.modules.base import ModuleBase
from vision.options import IntOption, DoubleOption, BoolOption
from vision.framework.color import range_threshold, bgr_to_lab
from vision.framework.feature import (outer_contours, contour_area,
        min_enclosing_rect)
from vision.framework.draw import draw_contours, draw_text, draw_circle

is_simulator = False # os.getenv('CUAUV_LOCALE') == 'simulator'
module_options = [
    BoolOption('show intermediate thresholds', False),
    IntOption('red lab l min', simulator_red_lab_l_min if is_simulator
            else pool_red_lab_l_min, 0, 255),
    IntOption('red lab l max', simulator_red_lab_a_max if is_simulator
            else pool_red_lab_a_max, 0, 255),
    IntOption('red lab a min', simulator_red_lab_a_min if is_simulator
            else pool_red_lab_a_min, 0, 255),
    IntOption('red lab a max', simulator_red_lab_a_max if is_simulator
            else pool_red_lab_a_max, 0, 255),
    IntOption('red lab b min', simulator_red_lab_b_min if is_simulator
            else pool_red_lab_b_min, 0, 255),
    IntOption('red lab b max', simulator_red_lab_b_max if is_simulator
            else pool_red_lab_b_max, 0, 255),
    IntOption('black lab l min', simulator_black_lab_l_min if is_simulator
            else pool_black_lab_l_min, 0, 255),
    IntOption('black lab l max', simulator_black_lab_l_max if is_simulator
            else pool_black_lab_l_max, 0, 255),
    IntOption('black lab a min', simulator_black_lab_a_min if is_simulator
            else pool_black_lab_a_min, 0, 255),
    IntOption('black lab a max', simulator_black_lab_a_max if is_simulator
            else pool_black_lab_a_max, 0, 255),
    IntOption('black lab b min', simulator_black_lab_b_min if is_simulator
            else pool_black_lab_b_min, 0, 255),
    IntOption('black lab b max', simulator_black_lab_b_max if is_simulator
            else pool_black_lab_b_max, 0, 255),
]

class AaronGate(ModuleBase):

    def contour_satisfactory(self, contour):
        _, _, w, h = cv2.boundingRect(contour)
        if contour_area(contour) < w * h / 2:
            return False
        if w > h / 3:
            return False
        if contour_area(contour) < 300:
            return False
        return True

    def process(self, img):

        # Thresholds
        (lab_l, lab_a, lab_b) = cv2.split(img)
        red_l_threshed = range_threshold(lab_l, self.options['red lab l min'],
                self.options['red lab l max'])
        red_a_threshed = range_threshold(lab_a, self.options['red lab a min'],
                self.options['red lab a max'])
        red_b_threshed = range_threshold(lab_b, self.options['red lab b min'],
                self.options['red lab b max'])
        red_threshed = red_l_threshed & red_a_threshed & red_b_threshed
        black_l_threshed = range_threshold(lab_a, self.options['black lab l min'],
                self.options['black lab l max'])
        black_a_threshed = range_threshold(lab_a, self.options['black lab a min'],
                self.options['black lab a max'])
        black_b_threshed = range_threshold(lab_b, self.options['black lab b min'],
                self.options['black lab b max'])
        black_threshed = black_l_threshed & black_a_threshed & black_b_threshed

        # Post thresholds
        self.post('original', img)
        if self.options['show intermediate thresholds']:
            self.post('red l threshed', red_l_threshed)
            self.post('red a threshed', red_a_threshed)
            self.post('red b threshed', red_b_threshed)
            self.post('black l threshed', black_l_threshed)
            self.post('black a threshed', black_a_threshed)
            self.post('black b threshed', black_b_threshed)
        self.post('red threshed', red_threshed)
        self.post('black threshed', black_threshed)

        # Filter contours
        red_contours = outer_contours(red_threshed)
        red_contours = list(filter(self.contour_satisfactory, red_contours))
        black_contours = outer_contours(black_threshed)
        black_contours = list(filter(self.contour_satisfactory, black_contours))

        # Post contours
        img_copy = img.copy()
        draw_contours(img_copy, red_contours, color=(0, 0, 255), thickness=5)
        draw_contours(img_copy, black_contours, color=(0, 255, 0), thickness=5)
        self.post('contours', img_copy)

        # Find 2-part left and right verticals
        left_x, left_y, left_len, left_visible = None, None, None, False
        left_red, left_black = None, None
        right_x, right_y, right_len, right_visible = None, None, None, False
        right_red, right_black = None, None
        for red in red_contours:
            red_x, red_y, red_w, red_h = cv2.boundingRect(red)
            for black in black_contours:
                black_x, black_y, black_w, black_h = cv2.boundingRect(black)
                if abs((red_x + red_w / 2) - (black_x + black_w / 2)) < 50:
                    # print(self.normalized(abs(red_x + red_w / 2 - black_x + black_w / 2), axis=0), red_x, black_x)
                    if red_y > black_y:
                        left_x = (red_x + red_w / 2 + black_x + black_w / 2) / 2
                        left_y = (red_y + red_h / 2 + black_y + black_h / 2) / 2
                        left_len = 2 * max(red_h, black_h)
                        left_visible = True
                        left_red = red
                        left_black = black
                        break
                    if red_y < black_y:
                        right_x = (red_x + red_w / 2 + black_x + black_w / 2) / 2
                        right_y = (red_y + red_h / 2 + black_y + black_h / 2) / 2
                        right_len = 2 * max(red_h, black_h)
                        right_visible = True
                        right_red = red
                        right_black = black
                        break

        # Find a corroborated middle
        middle_x, middle_y, middle_len, middle_visible = None, None, None, False
        middle = None
        for red in red_contours:
            if red is not left_red and red is not right_red:
                if left_visible and not right_visible:
                    red_x, red_y, red_w, red_h = cv2.boundingRect(red)
                    if red_x > left_x and abs((red_y + red_h) - left_y) < 100:
                        middle_x = red_x + red_w / 2
                        middle_y = red_y + red_h / 2
                        middle_len = red_h
                        middle_visible = True
                        middle = red
                        break
                if right_visible and not left_visible:
                    red_x, red_y, red_w, red_h = cv2.boundingRect(red)
                    if red_x < right_x and abs((red_y + red_h) - right_y) < 100:
                        middle_x = red_x + red_w / 2
                        middle_y = red_y + red_h / 2
                        middle_len = red_h
                        middle_visible = True
                        middle = red
                        break
                if left_visible and right_visible:
                    red_x, red_y, red_w, red_h = cv2.boundingRect(red)
                    if red_x > left_x and red_x < right_x and abs((red_y + red_h) - left_y) < 100:
                        middle_x = red_x + red_w / 2
                        middle_y = red_y + red_h / 2
                        middle_len = red_h
                        middle_visible = True
                        middle = red
                        break
        
        # Draw 2-part verticals and corroborated middle
        img_copy = img.copy()
        if left_visible:
            draw_circle(img_copy, (round(left_x), round(left_y)), 10, color=(0, 255, 255), thickness=10)
        if right_visible:
            draw_circle(img_copy, (round(right_x), round(right_y)), 10, color=(255, 0, 255), thickness=10)
        if middle_visible:
            draw_circle(img_copy, (round(middle_x), round(middle_y)), 10, color=(255, 255, 0), thickness=10)
        self.post('2-part verticals', img_copy)


                


if __name__ == '__main__':
    AaronGate('forward', module_options)()