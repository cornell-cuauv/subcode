#!/usr/bin/env python3
from vision.modules.ODJ_Vision.base import VisionProcessBase
from vision import options
from vision.framework.feature import contour_area, min_enclosing_circle, contour_centroid
import shm

module_options = [
    options.IntOption('a', 175, 0, 255),  # 156
    options.IntOption('b', 175, 0, 255),  # 166
    options.IntOption('dist', 25, 0, 50), # 25
    options.IntOption('thresh', 5, 0, 10),  # 149
]

filters_list = [
    (lambda x: contour_area(x) >= 500),
    (lambda x: False if contour_area(x) == 0 else 3.1415926 *
     min_enclosing_circle(x)[1]**2 / (contour_area(x)) < 1.6)
]


class BuoyVision(VisionProcessBase):
    """
    A structured model for finding a buoy.
    """

    def higher_process(self):
        """
        Reflection detection. Determines if two similar contours are reflections
        of each other, then rejects the reflection.

        Requires: clist is updated

        Effect: updates clist_final. Updates clist_draw.
        """
        self.is_visible = True
        final = None
        if len(self.clist) >= 2:
            def heuristic(contour):
                if (contour_area(contour)) == 0:
                    return 100
                return (min_enclosing_circle(contour)[1]**2 / (contour_area(contour))) * contour_area(contour)

            self.clist = sorted(self.clist, key=lambda x: heuristic(x))

            first, second = self.clist[0], self.clist[1]
            first_x, first_y = self.normalized(contour_centroid(first))
            second_x, second_y = self.normalized(contour_centroid(second))

            # roundness, size are within 4:5 ratio, and x-coordinates within 0.05 apart
            if (0.8 < heuristic(first) / heuristic(second)
                    and contour_area(first) / contour_area(second) < 1.25
                    and 0.8 < contour_area(first) / contour_area(second)
                    and abs(first_x - second_x) < 0.05):
                if first_y < second_y:
                    final = second
                else:
                    final = first
            else:
                final = first
        elif len(self.clist) >= 1:
            final = self.clist[0]
        else:
            self.is_visible = False

        if self.is_visible:
            self.clist_final = [final]
            self.clist_draw["buoy"] = contour_centroid(final)

    def shm(self):
        results = shm.red_buoy_results.get()
        if self.is_visible:
            buoy = self.clist_final[0]
            results.center_x, results.center_y = self.normalized(
                contour_centroid(buoy))
            results.area = contour_area(buoy)
            results.heuristic_score = 1
        else:
            results.heuristic_score = 0
        shm.red_buoy_results.set(results)


if __name__ == '__main__':
    BuoyVision("forward", options=module_options,
               filters=filters_list)()
