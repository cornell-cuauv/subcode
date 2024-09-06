#!/usr/bin/env python3
from vision.modules.ODJ_Vision.base import VisionProcessBase
from vision import options
from vision.framework.feature import contour_area, min_enclosing_circle, min_enclosing_rect, contour_centroid
import shm

module_options = [
    options.IntOption('a', 165, 0, 255),  # 179
    options.IntOption('b', 160, 0, 255),  # 175
    options.IntOption('dist', 20, 0, 50),
    options.IntOption('thresh', 3, 0, 10),  # 149
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
    (lambda x: contour_area(x) >= 20),
    (lambda x: False if contour_area(x) == 0 else 3.1415926 * min_enclosing_circle(x)[1]**2 / (contour_area(x)) > 6),
    (lambda x: find_vertical_rect > 2)
]


class QualGateVision(VisionProcessBase):
    """
    A structured model for finding a buoy.
    """

    def higher_process(self):
        """
        Requires two long contours, both standing upright.

        Requires: clist is updated

        Effect: updates clist_final. Updates clist_draw.
        """

        if len(self.clist) < 2:
            self.is_visible = False
        else:
            self.clist = sorted(self.clist, key=lambda x: (min_enclosing_rect(
                x)[1][0]*min_enclosing_rect(x)[1][1] / (contour_area(x))) * contour_area(x))
            self.clist = self.clist[-2:]

            if abs(min_enclosing_rect(self.clist[0])[2] % 90 - min_enclosing_rect(self.clist[1])[2] % 90) < 40:
                self.clist_final = sorted(
                    [self.clist[0], self.clist[1]], key=lambda x: contour_centroid(x)[0])
                self.is_visible = True
            else:
                self.is_visible = False

    def shm(self):
        results = shm.gate_vision.get()
        if self.is_visible:
            left = self.clist_final[0]
            right = self.clist_final[1]

            results.leftmost_x, results.leftmost_y = self.normalized(
                contour_centroid(left))
            results.leftmost_len = min_enclosing_rect(left)[1][1]
            results.rightmost_x, results.rightmost_y = self.normalized(
                contour_centroid(right))
            results.rightmost_len = min_enclosing_rect(right)[1][1]
            results.middle_visible = 1
            results.middle_x = (results.leftmost_x + results.rightmost_x) / 2
            results.middle_y = (results.leftmost_y + results.rightmost_y) / 2
        else:
            results.middle_visible = 0
        shm.gate_vision.set(results)
        pass


if __name__ == '__main__':
    QualGateVision("forward", options=module_options,
                   filters=filters_list)()
