#!/usr/bin/env python3
from vision.modules.ODJ_Vision.base import VisionProcessBase
from vision import options
from vision.framework.feature import contour_area, min_enclosing_circle, min_enclosing_rect, contour_centroid
import shm

import cv2
import numpy as np

module_options = [
    options.IntOption('a', 170, 0, 255), # 160
    options.IntOption('b', 160, 0, 255), # 150
    options.IntOption('dist', 20, 0, 50), # 15
    options.IntOption('thresh', 3, 0, 10), # 3
]


def find_vertical_rect(contour):
    rect = min_enclosing_rect(contour)

    # If rotation is between 45 and 135 degrees, then it's a vertical rectangle
    if (rect[2] > 45 and rect[2] < 135) or (rect[2] < -45 and rect[2] > -135):
        return rect[1][0] / rect[1][1]
    else:
        return rect[1][1] / rect[1][0]

def area_circle(contour):
    return 3.1415926 * min_enclosing_circle(contour)[1]**2 / (contour_area(contour))

filters_list = [
    (lambda x: contour_area(x) >= 150),
    (lambda x: False if contour_area(x) == 0 else 3.1415926 * min_enclosing_circle(x)[1]**2 / (contour_area(x)) > 3),
    (lambda x: find_vertical_rect(x) > 3)
]


class CompGateVision(VisionProcessBase):
    """
    A structured model for finding a buoy.
    """
    status = 0
    # status : int - determines the status of the gate. Used instead of self.is_visible
    # because there are multiple visibility components.

    # 0 - not visible
    # 1 - left and middle
    # 2 - middle and right
    # 3 - left, middle, and right

    def higher_process(self):
        """
        Requires two three long contours, both standing upright.
        Ordered by x-coordinate.

        Requires: clist is updated

        Effect: updates clist_final. Updates clist_draw.
        """
        # 1 or 0 is considered not visible.
        if len(self.clist) < 2:
            self.status = 0
        # 2 could be considered partially visible.
        elif len(self.clist) < 3:
            self.clist = sorted(self.clist, key=lambda x: contour_centroid(x)[0])
            if abs(min_enclosing_rect(self.clist[0])[2] % 90 - min_enclosing_rect(self.clist[1])[2] % 90) < 100:
                self.clist_final = self.clist[:2]
                if contour_centroid(self.clist[0])[1] - contour_centroid(self.clist[1])[1] > 150: # L/M
                    self.status = 1
                else: # M/R
                    self.status = 2
            else:
                self.status = 0
        # 3 could be considered completely visible.
        else:
            self.clist = sorted(self.clist, key=lambda x: contour_centroid(x)[0])
            if abs(min_enclosing_rect(self.clist[0])[2] % 90 - min_enclosing_rect(self.clist[1])[2] % 90) < 100 and abs(min_enclosing_rect(self.clist[2])[2] % 90 - min_enclosing_rect(self.clist[1])[2] % 90) < 40:
                self.clist_final = self.clist[:3]
                self.status = 3
            else:
                self.status = 0
        self.draw_param()
        pass

    def draw_param(self):
        # LMR
        def right_adjust(contour):
            right = contour
            right_len = max(min_enclosing_rect(right)[1][0], min_enclosing_rect(right)[1][1])
            right_adj = contour_centroid(right)
            right_adj = (int(right_adj[0]), int(right_adj[1] + right_len))
            return right_adj
        
        if self.status == 3:
            self.clist_draw["L"] = contour_centroid(self.clist_final[0])
            self.clist_draw["M"] = contour_centroid(self.clist_final[1])
            self.clist_draw["R"] = right_adjust(self.clist_final[2])
            self.clist_draw["left"] = ((self.clist_draw["L"][0] + self.clist_draw["M"][0])//2, self.clist_draw["L"][1])
            self.clist_draw["right"] = ((self.clist_draw["R"][0] + self.clist_draw["M"][0])//2, self.clist_draw["R"][1])
            pass
        # MR
        elif self.status == 2:
            self.clist_draw["M"] = contour_centroid(self.clist_final[0])
            self.clist_draw["R"] = right_adjust(self.clist_final[1])
            self.clist_draw["right"] = ((self.clist_draw["R"][0] + self.clist_draw["M"][0])//2, self.clist_draw["R"][1])
            pass
        # LM
        elif self.status == 1:
            self.clist_draw["L"] = contour_centroid(self.clist_final[0])
            self.clist_draw["M"] = contour_centroid(self.clist_final[1])
            self.clist_draw["left"] = ((self.clist_draw["L"][0] + self.clist_draw["M"][0])//2, self.clist_draw["L"][1])
            pass
        else:
            pass
    
    def shm(self):
        results = shm.gate_vision.get()

        left = None
        middle = None
        right = None

        if self.status == 3:
            left = self.clist_final[0]
            middle = self.clist_final[1]
            right = self.clist_final[2]

        elif self.status == 2:
            middle = self.clist_final[0]
            right = self.clist_final[1]

        elif self.status == 1:
            left = self.clist_final[0]
            middle = self.clist_final[1]

        elif self.status == 0:
            results.leftmost_visible = 0
            results.middle_visible = 0
            results.rightmost_visible = 0
        
        if left is not None:
            results.leftmost_x, results.leftmost_y = self.normalized(contour_centroid(left))
            results.leftmost_len = max(min_enclosing_rect(left)[1][1], min_enclosing_rect(left)[1][0])
            results.leftmost_visible = 1
        else:
            results.leftmost_visible = 0
        
        if middle is not None:
            results.middle_x, results.middle_y = self.normalized(contour_centroid(middle))
            results.middle_len = max(min_enclosing_rect(middle)[1][1], min_enclosing_rect(middle)[1][0])
            results.middle_visible = 1
        else:
            results.middle_visible = 0
               
        if right is not None:
            right_len = max(min_enclosing_rect(right)[1][1], min_enclosing_rect(right)[1][0])
            right_coord = contour_centroid(right)
            right_coord = (right_coord[0], right_coord[1] + right_len)
            right_coord = self.normalized(right_coord)

            results.rightmost_x = right_coord[0]
            results.rightmost_y = right_coord[1]
            results.rightmost_len = right_len
            results.rightmost_visible = 1
        else:
            results.rightmost_visible = 0

        results.img_height = self.status
        shm.gate_vision.set(results)
        pass


if __name__ == '__main__':
    CompGateVision("forward", options=module_options,
                   filters=filters_list)()
