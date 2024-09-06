#!/usr/bin/env python3
from vision.modules.ODJ_Vision.base import VisionProcessBase
from vision import options
from vision.framework.feature import contour_area, min_enclosing_ellipse, contour_centroid
import shm

module_options = [
    options.IntOption('a', 188, 0, 255),  # 179
    options.IntOption('b', 191, 0, 255),  # 175
    options.IntOption('dist', 25, 0, 50),
    options.IntOption('thresh', 5, 0, 10),  # 149
]

filters_list = [
    (lambda x: contour_area(x) >= 1000)
]


class PathVision(VisionProcessBase):
    """
    A structured model for finding a buoy.
    """

    def higher_process(self, img):

        """
        Reflection detection. Determines if two similar contours are reflections
        of each other, then rejects the reflection.

        Requires: clist is updated

        Effect: updates clist_final. Updates clist_draw.
        """
        self.clist = sorted(self.clist, key=lambda x: contour_area(x))
        if len(self.clist) == 0:
            self.is_visible = False
        else:
            self.is_visible = True
            self.clist_final = [self.clist[0]]

    def shm(self):
        results = shm.path_results.get()
        if self.is_visible:
            path = self.clist_final[0]
            results.center_x, results.center_y = self.normalized(contour_centroid(path))
            results.area = contour_area(path)
            results.angle = min_enclosing_ellipse(path)[2]
            results.visible = 1
        else:
            results.visible = 0
        shm.path_results.set(results)


if __name__ == '__main__':
    PathVision("downward", options=module_options,
               filters=filters_list)()
