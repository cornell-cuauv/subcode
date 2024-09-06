#!/usr/bin/env python3
from mission.framework.ssc256_consistency import ConsistentTargeting
from vision.modules.ODJ_Vision.base import VisionProcessBase
from vision import options
from vision.framework.feature import contour_area, contour_perimeter, min_enclosing_circle, contour_centroid, contour_approx
import shm
from vision.framework.color import otsu_threshold, thresh_color_distance, bgr_to_lab
from vision.framework.feature import outer_contours, contour_area, min_enclosing_rect
from vision.framework.transform import elliptic_kernel, morph_remove_noise, morph_close_holes
from vision.framework.color import range_threshold, thresh_color_distance, bgr_to_lab, bgr_to_gray
from vision import options
from vision.modules.base import ModuleBase
from vision.framework.draw import draw_contours, draw_text, draw_circle, draw_rot_rect, draw_arrow
import math

import cv2
import numpy as np

module_options = [
    options.IntOption('min_thresh', 100, 0, 200),
    options.IntOption('a', 146, 0, 255),
    options.IntOption('b', 157, 0, 255),
    options.IntOption('c', 150, 0, 255),
    options.IntOption('dist', 25, 0, 50),
    options.IntOption('thresh', 1, 0, 10),
    options.IntOption('erode', 5, 1, 100),
    options.IntOption('erode_iter', 1, 1, 20),
]


colors = [(230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180), (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255), (170, 110, 40), (255, 250, 200), (128, 0, 0), (170, 255, 195), (128, 128, 0), (255, 215, 180), (0, 0, 128), (128, 128, 128), (255, 255, 255), (0, 0, 0)]

class OctagonChevronsVision(ModuleBase):

    def octagon_color_filter(self, img):
        """
        Creates contours for a certain color range.

        Effect: contour list now has contour values.
        """
        lab, lab_split = bgr_to_lab(img)
        gray, _ = bgr_to_gray(img)

        def option(str):
            return self.options[str]

        # thresh_color_distance
        # threshed, _ = thresh_color_distance(lab_split, (0, option('a'), option('b')), option('dist'), ignore_channels=[0])

        num_threshed, threshed = otsu_threshold(gray)

        if num_threshed < self.options['min_thresh']:
            threshed = threshed * 0

        # removes noise, then closes holes
        threshed = morph_remove_noise(threshed, elliptic_kernel(option('erode')), iterations=option('erode_iter'))
        threshed = morph_close_holes(threshed, elliptic_kernel(option('erode')), iterations=option('erode_iter'))

        return threshed

    def octagon_shape_filter(self, clist):
        """
        Filters contours based on certain filter functions.

        Effect: clist may be filtered.
        """
        if len(clist) == 0:
            return None, None, None

        # find largest contour
        clist = sorted(clist, key=contour_area, reverse=True)
        clist = clist[0]

        # Determining shape
        peri = contour_perimeter(clist)
        approx = contour_approx(clist, epsilon=0.04 * peri)
        lengths = len(approx)

        # Finding min enclosing circle
        (circle_x, circle_y), radius = min_enclosing_circle(clist)

        # Finding centroid
        centroid = contour_centroid(clist)

        # Finding min enclosing rect
        (rect_x, rect_y), (width, height), angle = min_enclosing_rect(clist)

        # Determing if shape is more octagon (circle) or bin (rect)
        circle_area = math.pi * radius**2
        rect_area = width * height
        real_area = contour_area(clist)

        print(f"point {lengths} : circle {circle_area / real_area} {circle_area} : rect_ratio {rect_area / real_area} {rect_area}")

        # As long as rect ratio is not between 0.9 and 1.2, proceed with octagon
        if rect_area / real_area < 0.9 or rect_area / real_area > 1.15:
            return [clist], (int(circle_x), int(circle_y)), int(radius) 
        else:
            return None, None, None

    def chevron_color_filter(self, img):
        """
        Creates contours for a certain color range.

        Effect: contour list now has contour values.
        """
        lab, lab_split = bgr_to_lab(img)
        self.post("lab", lab)

        def option(str):
            return self.options[str]

        # thresh_color_distance
        threshed, _ = thresh_color_distance(lab_split, (0, option(
            'a'), option('b')), option('dist'), ignore_channels=[0])

        # removes noise, then closes holes
        threshed = morph_close_holes(morph_remove_noise(threshed,
                                                        elliptic_kernel(option('thresh'))), elliptic_kernel(option('thresh')))

        threshed = morph_remove_noise(threshed, elliptic_kernel(option('erode')), iterations=option('erode_iter'))
        threshed = morph_close_holes(threshed, elliptic_kernel(option('erode')), iterations=option('erode_iter'))

        return threshed

    def chevron_shape_filter(self, clist):
        """
        Filters contours based on certain filter functions.

        Effect: clist may be filtered.
        """
        if len(clist) == 0:
            return None, None, None

        # find largest contour
        clist = sorted(clist, key=contour_area, reverse=True)

        centers = []
        areas = []

        for c in clist:
            (rect_x, rect_y), (width, height), angle = min_enclosing_rect(c)
            areas.append(width * height)
            centers.append(contour_centroid(c))

        return clist, centers, areas

    def process(self, img):
        # TODO: Filter out only the white objects that look like a octagon
        self.post('original', img)
        threshed = self.octagon_color_filter(img)
        self.post("threshed_octagon", threshed)

        octagon_clist, center, radius = self.octagon_shape_filter(outer_contours(threshed))
        if octagon_clist is None or center is None or radius is None:
            getattr(shm, f"yolo_octagon").visible.set(0)
        else:
            octagon_norm_center = self.normalized(center)

            # !!!!!!! Later add to shm if chevrons found
            
            try:
                getattr(shm, f"yolo_octagon").area.set(math.pi * radius**2)
                getattr(shm, f"yolo_octagon").center_x.set(octagon_norm_center[0])
                getattr(shm, f"yolo_octagon").center_y.set(octagon_norm_center[1])
                getattr(shm, f"yolo_octagon").visible.set(1)
            except AttributeError as e:
                print(e)

        # TODO: check if the chevron is in the octagon
        # remove everything outside of the octagon_circle
        mask = np.zeros_like(img)
        mask = cv2.circle(mask, center, radius, (255,255,255), -1)

        octagon_img = cv2.bitwise_and(img, mask)

        threshed = self.chevron_color_filter(octagon_img)
        self.post("threshed_chevron", threshed)

        chevron_clist, centers, areas = self.chevron_shape_filter(outer_contours(threshed))
        if chevron_clist is None or centers is None or areas is None:
            # getattr(shm, f"yolo_octagon").visible.set(0)
            for i in range(1, 4, 1):
                getattr(shm, f"yolo_chevron_{i}").visible.set(0)
        else:
            chevron_norm_centers = [self.normalized(c) for c in centers]

            for i in range(len(chevron_clist)):
                try:
                    getattr(shm, f"yolo_chevron_{i+1}").area.set(areas[i])
                    getattr(shm, f"yolo_chevron_{i+1}").center_x.set(chevron_norm_centers[i][0])
                    getattr(shm, f"yolo_chevron_{i+1}").center_y.set(chevron_norm_centers[i][1])
                    getattr(shm, f"yolo_chevron_{i+1}").visible.set(1)
                except AttributeError as e:
                    print(e)

            for i in range(i, 4):
                getattr(shm, f"yolo_chevron_{i+1}").visible.set(0)

        draw_contours(img, chevron_clist, (0, 255, 0), 5)
        print(center, radius)
        draw_circle(img, center, radius, (0, 255, 255), 5)
        self.post("octagon", img)    

if __name__ == '__main__':
    OctagonChevronsVision("downward", options=module_options)()
