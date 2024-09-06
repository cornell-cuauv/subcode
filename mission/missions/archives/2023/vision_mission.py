#!/usr/bin/env python3
from vision.modules.base import ModuleBase
from vision import options
from vision.framework.draw import draw_text
from vision.framework.color import *
from vision.framework.feature import *
from vision.framework.draw import *
from vision.framework.transform import *

from auv_math.camera import calc_forward_angles
from conf.vehicle import cameras

from math import degrees

import cv2
import shm

module_options = [
    options.BoolOption('Hue Inversion', False),
    options.IntOption('Hue Min',   5, 0, 179),
    options.IntOption('Hue Max',  15, 0, 179),
    options.IntOption('Sat Min', 100, 0, 255),
    options.IntOption('Sat Max', 255, 0, 255),
    options.IntOption('Val Min', 190, 0, 255),
    options.IntOption('Val Max', 255, 0, 255),
    options.IntOption('Dilation', 6, 1, 20),
    options.IntOption('Erosion', 1, 1, 20)
]

class HSVBuoyDetector(ModuleBase):
    def process(self, img):
        hsv, hsv_split = bgr_to_hsv(img)
        hsv_h, hsv_s, hsv_v = hsv_split

        self.post('HSV', hsv)
        self.post('HSV H', hsv_h)
        self.post('HSV S', hsv_s)
        self.post('HSV V', hsv_v)

        hsv_s_thresh = range_threshold(hsv_s, self.options["Sat Min"]-1, self.options["Sat Max"]+1)
        hsv_h_thresh = range_threshold(hsv_h, self.options["Hue Min"]-1, self.options["Hue Max"]+1)
        hsv_v_thresh = range_threshold(hsv_v, self.options["Val Min"]-1, self.options["Val Max"]+1)

        if self.options['Hue Inversion']:
            hsv_h_thresh = ~hsv_h_thresh


        self.post('Hue Threshold', hsv_h_thresh)
        self.post('Sat Threshold', hsv_s_thresh)
        self.post('Val Threshold', hsv_v_thresh)

        threshold = hsv_h_thresh & hsv_s_thresh & hsv_v_thresh

        threshold = dilate(threshold, elliptic_kernel(self.options['Dilation']))
        threshold = erode(threshold, elliptic_kernel(self.options['Erosion']))

        self.post('Threshold', threshold)

        contours = outer_contours(threshold)
        draw_contours(img, contours, thickness=5)
        coords = [(contour, contour_centroid(contour)) for contour in contours]
        coords = [(coord[0], coord[1], self.normalized(coord[1])) for coord in coords]
        coords = sorted(coords, key=lambda x: (-contour_area(x[0]) / (min_enclosing_circle(x[0])[1]**2)))
        
        buoy_visible = 0 < len(coords)

        results = shm.red_buoy_results.get()

        if buoy_visible:
            buoy = coords[0]
            draw_contours(img, [buoy[0]], thickness=10, color=(0, 255, 0))

            heading, yaw = calc_forward_angles(cameras["forward"], buoy[1])

            results.center_x = degrees(heading)
            results.center_y = degrees(yaw)
            results.area = contour_area(buoy[0])
            results.heuristic_score = 1
        else:
            results.heuristic_score = 0        

        shm.red_buoy_results.set(results)


        self.post('contours', img)

if __name__ == '__main__':
    HSVBuoyDetector("forward", module_options)()
