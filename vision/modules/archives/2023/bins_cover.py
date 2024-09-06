#!/usr/bin/env python3


import shm
import cv2
import numpy as np

from vision import options
from vision.framework.color import bgr_to_gray, bgr_to_lab, thresh_color_distance
from vision.framework.helpers import to_odd
from vision.framework.transform import resize, rect_kernel, morph_remove_noise, morph_close_holes
from vision.framework.feature import outer_contours, contour_centroid, contour_area, min_enclosing_rect
from vision.framework.draw import draw_contours, draw_rect, draw_circle

from vision.modules.base import ModuleBase


mod_options = [
    options.IntOption('lab_a_orange', 174, 0, 255),
    options.IntOption('lab_b_orange', 205, 0, 255),
    options.IntOption('dist_orange', 66, 0, 255),

    options.IntOption('lab_a_purple', 137, 0, 255),
    options.IntOption('lab_b_purple', 94, 0, 255),
    options.IntOption('dist_purple', 25, 0, 255),

    options.IntOption('noise_kernel', 4, 0, 20),
    options.IntOption('close_kernel', 4, 0, 50),
    options.IntOption('min_orange_area', 300, 0, 1000),
    options.IntOption('delta', 100, 0, 500),
    options.BoolOption('debug', True)
]


class BinsCover(ModuleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loc1 = (None, None)
        self.loc2 = (None, None)

    def wrap_angle(self, angle):
        dist1 = 180 - angle
        dist2 = -angle

        if abs(dist1) < abs(dist2):
            return dist1
        else:
            return dist2

    def get_bin_cover(self, orange_rect, purple_rect):
        # should be sorted from largest to smallest
        def get_coords(rect):
            center, dims, _ = rect
            length = max(*dims)
            width = min(*dims)
            x1 = center[0] - length/2
            x2 = center[0] + length/2
            y1 = center[1] - width/2
            y2 = center[1] + width/2

            return ((min(x1, x2), min(y1, y2)), (max(x1, x2), max(y1, y2)))

        # purple rectangle needs to be in the orange rectangle!!!!!
        rect1, rect2 = None, None
        certainty1, certainty2 = 0, 0
        handle1, handle2 = None, None

        rejected = []
        if len(purple_rect) == 0:
            rejected = orange_rect
        else:
            for o in orange_rect:
                flag = False
                for p in purple_rect:
                    pc = get_coords(p)
                    oc = get_coords(o)
                    if pc[0][0] > oc[0][0] and pc[0][1] > oc[0][1] and \
                            pc[1][0] < oc[1][0] and pc[1][1] < oc[1][1]:
                        if rect1 is None:
                            rect1 = o
                            certainty1 = 1
                            handle1 = p
                            flag = True
                            break
                        elif rect2 is None:
                            rect2 = o
                            certainty2 = 1
                            flag = True
                            handle2 = p
                            break
                        else:
                            return rect1, certainty1, handle1, rect2, certainty2, handle2
                if not flag:
                    rejected.append(o)

        if rect1 is None and len(rejected) > 0:
            rect1 = rejected[0]
            certainty1 = 0.5
            rejected.pop(0)
        if rect2 is None and len(rejected) > 0:
            rect2 = rejected[0]
            certainty2 = 0.5

        return rect1, certainty1, handle1, rect2, certainty2, handle2

    def dist(self, t1, t2):
        if t1[0] is None or t2[0] is None:
            return 0
        return ((t1[0] - t2[0])**2 + (t1[1]-t2[1])**2)**0.5

    def process(self, img): #, depth_img):
        total_area = img.shape[0] * img.shape[1]
        long_side = max(img.shape[0], img.shape[1])

        # convert
        lab, lab_split = bgr_to_lab(img)

        # mask
        orange_thresh, orange_dist = thresh_color_distance(
            lab_split,
            (0, self.options['lab_a_orange'], self.options['lab_b_orange']),
            self.options['dist_orange'],
            ignore_channels=[0]
        )

        purple_thresh, purple_dist = thresh_color_distance(
            lab_split,
            (0, self.options['lab_a_purple'], self.options['lab_b_purple']),
            self.options['dist_purple'],
            ignore_channels=[0]
        )

        orange_thresh = morph_remove_noise(
            orange_thresh,
            rect_kernel(to_odd(self.options['noise_kernel'])))
        orange_thresh = morph_close_holes(
            orange_thresh,
            rect_kernel(to_odd(self.options['close_kernel']))
        )
        purple_thresh = morph_remove_noise(
            purple_thresh,
            rect_kernel(to_odd(self.options['noise_kernel'])))

        # orange_thresh = orange_thresh | purple_thresh

        # rectagles on orange_thresh
        # only grab the top 5 matches
        orange_contours = sorted(outer_contours(
            orange_thresh), key=lambda x: -contour_area(x))[:5]
        orange_contours = list(filter(lambda x: contour_area(
            x) > self.options['min_orange_area'], orange_contours))
        cover_rect = [min_enclosing_rect(contour)
                      for contour in orange_contours]
        purple_contours = sorted(outer_contours(
            purple_thresh), key=lambda x: -contour_area(x))[:5]
        handle_rect = [min_enclosing_rect(contour)
                       for contour in purple_contours]

        r1, c1, h1, r2, c2, h2 = self.get_bin_cover(
            list(cover_rect), list(handle_rect))
        if r1 is not None and r2 is not None:
            """match detected bins to their last known locations"""
            if (self.dist(r1[0], self.loc1) > self.noise and
                    self.dist(r1[0], self.loc1) > self.dist(r2[0], self.loc1)):
                # swappy swap
                r1, c1, h1, r2, c2, h2 = r2, c2, h2, r1, c1, h1
            self.loc1 = r1[0]
            self.loc2 = r2[0]
        elif r1 is not None:
            if self.dist(r1[0], self.loc1) > self.noise:
                # swappy swap
                r1, c1, h1, r2, c2, h2 = r2, c2, h2, r1, c1, h1
                self.loc2 = r2[0]
                self.loc1 = (None, None)
            else:
                self.loc1 = r1[0]
                self.loc2 = (None, None)
        else:
            self.loc1 = (None, None)
            self.loc2 = (None, None)

        """ we want bin1 to be the most certain one"""
        if r1 is not None and r2 is not None and c2 > c1:
            r1, c1, h1, r2, c2, h2 = r2, c2, h2, r1, c1, h1
            self.loc1 = r1[0]
            self.loc2 = r2[0]

        # write to shm!

        grp = shm.bin1_lid_results.get()
        if r1 is None:
            grp.certainty = 0
            grp.area = 0
            grp.x = 0
            grp.y = 0
            grp.lid_length = 0
        else:
            grp.area = (r1[1][0] * r1[1][1]) / total_area
            grp.certainty = c1

            a = self.normalized((int(r1[0][0]), int(r1[0][1])))
            grp.x = a[0]
            grp.y = a[1]
            draw_circle(
                img, ((int(r1[0][0]), int(r1[0][1]))), 20, thickness=20)
            grp.lid_length = max(h1[1][0], h1[1][1]) if h1 is not None else 0
            grp.lid_length /= long_side

            best_fit_line = cv2.fitLine(
                np.int0(cv2.boxPoints(r1)), cv2.DIST_L2, 0, 0.01, 0.01)
            best_angle = np.degrees(np.arctan2(
                best_fit_line[0], best_fit_line[1]))[0]
            print(self.wrap_angle(best_angle))

            grp.angle = self.wrap_angle(best_angle)

        shm.bin1_lid_results.set(grp)
        
        grp = shm.bin2_lid_results.get()
        if r2 is None:
            grp.certainty = 0
            grp.area = 0
            grp.x = 0
            grp.y = 0
            grp.lid_length = 0
        else:
            grp.area = r2[1][0] * r2[1][1] / total_area
            grp.certainty = c2
            
            a = self.normalized((int(r2[0][0]), int(r2[0][1])))
            grp.x = a[0]
            grp.y = a[1]
            grp.lid_length = max(h2[1][0], h2[1][1]) if h2 is not None else 0
            grp.lid_length /= long_side


            best_fit_line = cv2.fitLine(np.int0(cv2.boxPoints(r2)), cv2.DIST_L2, 0, 0.01, 0.01)
            best_angle = np.degrees(np.arctan2(best_fit_line[0], best_fit_line[1]))[0]
            grp.angle = self.wrap_angle(best_angle)

        shm.bin2_lid_results.set(grp)
        

        if self.is_debug:
            self.post('Orange Mask', orange_thresh)
            self.post('Orange Dist', orange_dist)

            self.post('Purple Mask', purple_thresh)
            self.post('Purple Dist', purple_dist)

        for c in cover_rect:
            draw_contours(img, [np.int0(cv2.boxPoints(c))],
                          color=[0, 255, 0], thickness=4)

        for c in handle_rect:
            draw_contours(img, [np.int0(cv2.boxPoints(c))],
                          color=[0, 255, 255], thickness=4)

        if r1 is not None:
            cv2.putText(img, f'BIN 1 ({c1 * 100})%', tuple(map(int, r1[0])),
                        1, 3, (255, 0, 100), 4, 2)
        if r2 is not None:
            cv2.putText(img, f'BIN 2 ({c2 * 100})%', tuple(map(int, r2[0])),
                        1, 3, (255, 0, 100), 4, 2)

        self.post('Rectangles', img)
        #self.post('depth', depth_img)

    @property
    def noise(self):
        return self.options['delta']

    @property
    def is_debug(self):
        return self.options['debug']


if __name__ == '__main__':
    BinsCover('downward', mod_options)()
