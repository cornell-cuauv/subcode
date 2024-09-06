#!/usr/bin/env python3


import shm
import cv2
import numpy as np

from vision import options
from vision.framework.color import bgr_to_gray, bgr_to_lab, thresh_color_distance, range_threshold
from vision.framework.helpers import to_odd
from vision.framework.transform import resize, rect_kernel, morph_remove_noise, morph_close_holes
from vision.framework.feature import outer_contours, contour_centroid, contour_area, min_enclosing_rect
from vision.framework.draw import draw_contours, draw_rect, draw_circle

from vision.modules.base import ModuleBase


module_options = [
    options.IntOption('min_l', 200, 0, 255),
    options.IntOption('noise_kernel', 4, 0, 20),
    options.IntOption('close_kernel', 4, 0, 50),
    options.IntOption('min_orange_area', 300, 0, 1000),
    options.IntOption('delta', 100, 0, 500),
    options.BoolOption('debug', True)
]

class BinsFrame(ModuleBase):
    def process(self, img):
        self.post("original", img)
        _, (l, _, _) = bgr_to_lab(img)
        thresh = range_threshold(l, self.options['min_l'], 255)
        self.post('thresh', thresh)
        #morphed = morph_remove_noise(thresh, rect_kernel(to_odd(self.options['noise_kernel'])))
        #morphed = morph_close_holes(thresh, rect_kernel(to_odd(self.options['close_kernel'])))
        #self.post('morphed', morphed)
        contours = outer_contours(thresh)
        #contours = list(filter(lambda c : len(c) == 4, contours))
        #contours = sorted(contours, contour_area)


        cont1 = None
        area1 = 0
        cont2 = None
        area2 = 0
        for cont in contours:
            if contour_area(cont) > area1:
                cont2 = cont1
                area2 = area1
                cont1 = cont
                area1 = contour_area(cont)
            elif contour_area(cont) > area2:
                cont2 = cont
                area2 = contour_area(cont)
        if cont1 is not None:
            print(area1)
        if (cont1 is not None) & (cont2 is not None):
            draw_contours(img, [cont1, cont2], color=(0,255,0), thickness = 10)
            self.post("contours", img)

            (x1, y1), _, _ = min_enclosing_rect(cont1)
            (x2, y2), _, _ = min_enclosing_rect(cont2)
            grp1 = shm.bin1_frame_results
            grp2 = shm.bin2_frame_results
            if abs(x1 - x2) > abs(y1 - y2):
                if x1 < x2:
                    grp1.x.set(x1)
                    grp2.x.set(x2)
                    grp1.y.set(y1)
                    grp2.y.set(y2)
                else:
                    grp1.x.set(x2)
                    grp2.x.set(x1)
                    grp1.y.set(y2)
                    grp2.y.set(y1)
                    
            else:
                if y1 < y2:
                    grp1.x.set(x1)
                    grp2.x.set(x2)
                    grp1.y.set(y1)
                    grp2.y.set(y2)
                else:
                    grp1.x.set(x2)
                    grp2.x.set(x1)
                    grp1.y.set(y2)
                    grp2.y.set(y1)



if __name__ == '__main__':
    BinsFrame('downward', module_options)()
