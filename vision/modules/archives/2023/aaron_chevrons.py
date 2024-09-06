#!/usr/bin/env python3

import cv2
import numpy as np
from math import cos, sin, radians, degrees
from shm import chevrons_results_0
from vision.modules.base import ModuleBase
from vision.options import IntOption
from vision.framework.transform import elliptic_kernel, morph_remove_noise
from vision.framework.helpers import to_odd
from vision.framework.feature import outer_contours, contour_centroid, contour_approx, contour_perimeter, min_enclosing_rect
from vision.framework.draw import draw_contours, draw_circle, draw_line
from mission.framework.ssc256_consistency import ConsistentTargeting

module_options = [
    IntOption('tolerance', 30, 0, 100),
    IntOption('min lightness', 0, 0, 255),
    IntOption('noise kernel', 15, 0, 35),
    
]

class AaronChevrons(ModuleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conistency = ConsistentTargeting(20, 'pos', num_detections=4)

    def process(self, img):
        img_copy = img.copy()
        b, g, r = cv2.split(img)
        red = np.zeros_like(r, dtype=np.uint8)
        red[r > np.maximum(np.maximum(b, g), self.options['tolerance']) - self.options['tolerance']] = 255
        red[(b + g + r) / 3 < self.options['min lightness']] = 0
        self.post('red', red)
        red = morph_remove_noise(red, elliptic_kernel(to_odd(self.options['noise kernel'])))
        self.post('morphed', red)
        contours = outer_contours(red)
        # contours = [contour_approx(contour, epsilon=0.07 * contour_perimeter(contour)) for contour in outer_contours(red)]
        draw_contours(img_copy, contours, color=(0, 255, 0), thickness=2)
        self.post('chevrons', img_copy)

        img_copy = img.copy()
        # contours = [contour for contour in contours if len(contour) == 3 or len(contour == 4)]
        centers = [contour_centroid(contour) for contour in contours]
        centers += [None] * (4 - len(centers))
        valid_lst = [True] * len(contours) + [False] * (4 - len(contours))
        self.conistency.update(centers, valid_lst=valid_lst)
        consistent_centers = self.conistency.value()
        colors = [(0, 0, 255), (0, 255, 255), (0, 255, 0), (255, 0, 0)]
        written_to_shm = False
        for i, center in enumerate(consistent_centers):
            within_contour = None
            center_x, center_y = center
            for contour in contours:
                rect_x, rect_y, rect_w, rect_h = cv2.boundingRect(contour)
                if rect_x < center_x < rect_x + rect_w and rect_y < center_y < rect_y + rect_h:
                    within_contour = contour
                    break
            if within_contour is not None:
                draw_circle(img_copy, center, 5, colors[i], 3)
                (x, y), (w, h), angle = min_enclosing_rect(within_contour)
                box = cv2.boxPoints(((x, y), (w, h), angle))
                box = np.int0(box)
                cv2.drawContours(img_copy, [box], 0, (255, 255, 255), 2)
                if not written_to_shm:
                    chevron = chevrons_results_0.get()
                    chevron.angle = angle if w > h else 90 - angle
                    chevron.center_x, chevron.center_y = self.normalized((x, y))
                    chevron.width, chevron.height = self.normalized_size((w, h))
                    chevron.visible = True
                    chevrons_results_0.set(chevron)
                    written_to_shm = True
            else:
                pass
                draw_circle(img_copy, center, 5, (0, 0, 0), 3)
        if not written_to_shm:
            chevrons_results_0.visible.set(False)
        self.post('consistency', img_copy)


if __name__ == '__main__':
    AaronChevrons('downward', module_options)()