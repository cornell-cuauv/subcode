#!/usr/bin/env python3

import numpy as np
import sys
import cv2
import math
import pickle
from time import perf_counter

from vision.modules.base import ModuleBase
from vision.modules.ODJ_Vision.base import VisionProcessBase
from vision import options
from vision.framework.color import bgr_to_gray, range_threshold, otsu_threshold
from vision.framework.transform import (elliptic_kernel, morph_close_holes, dilate,
        rotate, translate, resize)
from vision.framework.feature import all_contours, outer_contours, contour_area, min_enclosing_circle, min_enclosing_rect, contour_centroid, simple_canny, canny
from vision.framework.draw import draw_contours, draw_circle, draw_text
import shm

module_options = [
    options.BoolOption('use otsu', False),
    options.BoolOption('use canny', True),
    options.IntOption('close', 2, 0, 21),
    options.IntOption('dilation', 1, 0, 21),
    options.IntOption('max', 65, 0, 255),
    options.IntOption('lower', 100, 0, 255),
    options.IntOption('upper', 255, 0, 255)
]

filters_list = [
    (lambda x: False if contour_area(x) == 0 else 3.1415926 * min_enclosing_circle(x)[1]**2 / (contour_area(x)) > 4), 
    (lambda x: contour_area(x) >= 1000),
]

glyph = "abydos"
file = glyph + '.pickle'

module_options.append(options.IntOption(glyph + "_error", 1000, 0, 1000))

class GlyphVision(VisionProcessBase):
    """
    A structured model for identifying a glyph. 
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with open('pickles/' + file, 'rb') as f:
            self.reference_contour = pickle.load(f)
            moments = cv2.moments(self.reference_contour)
            self.reference_hu_moments = cv2.HuMoments(moments)    
    
    def color_filter(self, img):
        self.post('original', img)
        gray, _ = bgr_to_gray(img)
        if self.options['use otsu']:
            _, threshed = otsu_threshold(gray)
            threshed = ~threshed
        elif self.options['use canny']:
            threshed = canny(gray, self.options['lower'], self.options['upper'])
        else:
            threshed = range_threshold(gray, 0, self.options['max'])
        threshed = morph_close_holes(threshed, elliptic_kernel(self.options['close']))
        threshed = dilate(threshed, elliptic_kernel(self.options['dilation']))
        self.post('threshed', threshed)
        self.clist = all_contours(threshed)

    def higher_process(self, img):
        def error(contour):
            result = 0
            moments = cv2.moments(contour)
            hu_moments = cv2.HuMoments(moments)
            for ref_moment, moment in zip(self.reference_hu_moments, hu_moments):
                result += (-1 * (moment / abs(moment)) * math.log10(abs(moment)) + 1 * (ref_moment / abs(ref_moment)) * math.log10(abs(ref_moment))) ** 2
                # result += abs(max(ref_moment, moment)) / abs(min(ref_moment, moment))
                # result += (ref_moment - moment) ** 2
            return result
        if len(self.clist) > 0:
            self.clist = list(sorted(self.clist, key=error))
            print(list(map(lambda x : error(x), self.clist)))
            best_contour = self.clist[0]
            if error(best_contour) < self.options[glyph + '_error']:
                self.is_visible = True
                self.clist_final = [best_contour]
                self.clist_draw[glyph] = contour_centroid(best_contour)
            else:
                self.is_visible = False
        else:
            self.is_visible = False
        pass

    def shm(self):
        results = shm.green_buoy_results.get()
        if self.is_visible:
            buoy = self.clist_final[0]
            results.center_x, results.center_y = self.normalized(contour_centroid(buoy))
            results.heuristic_score = 1
            results.area = contour_area(buoy)
        else:
            results.heuristic_score = 0
        shm.green_buoy_results.set(results)
        pass

    def draw(self, img):
        super().draw(img)
        return
        iter = 4 if len(self.clist) >= 4 else len(self.clist)
        for i in range(iter):
                draw_contours(img, self.clist[i], (255, 0, 0), 4)
                draw_text(img, str(i+1), contour_centroid(self.clist[i]), 3, (0, 0, 255), 3)


if __name__ == '__main__':
    GlyphVision("forward", options=module_options,
               filters=filters_list)()
