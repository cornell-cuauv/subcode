#!/usr/bin/env python3
import shm
import cv2
import numpy as np
from collections import namedtuple

from conf.vehicle import VEHICLE
from vision import options
from vision.modules.base import ModuleBase
from vision.framework.feature import outer_contours, contour_area, contour_centroid, min_enclosing_circle, min_enclosing_rect
from vision.framework.transform import resize, simple_gaussian_blur, morph_remove_noise, dilate, rect_kernel
from vision.framework.helpers import to_umat, to_odd
from vision.framework.color import bgr_to_lab, gray_to_bgr, range_threshold
from vision.framework.draw import draw_contours

OPTS_ODYSSEUS = [
    options.IntOption('lab_l_ref', 180, 0, 255),
    options.IntOption('lab_a_ref', 196, 0, 255),
    options.IntOption('lab_b_ref', 139, 0, 255),
    options.IntOption('color_dist_thresh', 50, 0, 255),
    options.IntOption('blur_kernel', 3, 0, 255),
    options.IntOption('blur_std', 10, 0, 500),
    options.DoubleOption('resize_width_scale', 0.5, 0, 1),
    options.DoubleOption('resize_height_scale', 0.5, 0, 1),
    options.IntOption('dilate_kernel', 7, 0, 255),
    options.IntOption('min_contour_area', 20, 0, 500),
    options.DoubleOption('min_contour_rect', 0.75, 0, 1),
    options.DoubleOption('max_angle_from_vertical', 15, 0, 90),
    options.DoubleOption('min_length', 30, 0, 500),
]

OPTS_AJAX = [
    options.IntOption('lab_l_ref', 175, 0, 255),
    options.IntOption('lab_a_ref', 185, 0, 255),
    options.IntOption('lab_b_ref', 119, 0, 255),
    options.IntOption('color_dist_thresh', 45, 0, 255),
    options.IntOption('blur_kernel', 3, 0, 255),
    options.IntOption('blur_std', 10, 0, 500),
    options.DoubleOption('resize_width_scale', 0.25, 0, 1),
    options.DoubleOption('resize_height_scale', 0.25, 0, 1),
    options.IntOption('dilate_kernel', 7, 0, 255),
    options.IntOption('min_contour_area', 20, 0, 500),
    options.DoubleOption('min_contour_rect', 0.75, 0, 1),
    options.DoubleOption('max_angle_from_vertical', 15, 0, 90),
    options.DoubleOption('min_length', 30, 0, 500),
]


ContourFeats = namedtuple('ContourFeats', ['contour', 'area', 'x', 'y', 'rect', 'angle', 'length'])


def try_index(arr, idx):
    if idx < len(arr):
        return arr[idx]
    return None


def thresh_color_distance(split, color, distance, ignore_channels=[], weights=[1, 1, 1]):
    for idx in ignore_channels:
        weights[idx] = 0
    weights /= np.linalg.norm(weights)
    dists = np.zeros(split[0].shape, dtype=np.float32)
    for i in range(3):
        if i in ignore_channels:
            continue
        dists += weights[i] * (np.float32(split[i]) - color[i])**2
    return range_threshold(dists, 0, distance**2), np.uint8(np.sqrt(dists))


class Gate(ModuleBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def process(self, *mats):
        h, w, _ = mats[0].shape
        h = int(h * self.options['resize_height_scale'])
        w = int(w * self.options['resize_width_scale'])
        mat = resize(mats[0], w, h)
        # Tuned for a 320x256 image
        reflection_cutoff = min(h, int(max(0, 3 - shm.kalman.depth.get())**2 * 18))
        mat[:reflection_cutoff] *= 0
        self.post('mat', mat)
        mat = to_umat(mat)
        mat = simple_gaussian_blur(mat, to_odd(self.options['blur_kernel']),
                                   self.options['blur_std'])
        lab, lab_split = bgr_to_lab(mat)
        threshed, dists = thresh_color_distance(lab_split, [self.options['lab_l_ref'], self.options['lab_a_ref'],
                                                     self.options['lab_b_ref']],
                                         self.options['color_dist_thresh'], ignore_channels=[], weights=[1, 20, 5])
        self.post('threshed', threshed)
        self.post('dists', dists)
        dilated = dilate(threshed, rect_kernel(self.options['dilate_kernel']))
        self.post('dilated', dilated)
        contours = outer_contours(dilated)
        areas = [*map(contour_area, contours)]
        centroids = [*map(contour_centroid, contours)]
        xs = [c[0] for c in centroids]
        ys = [c[1] for c in centroids]
        rects = [*map(min_enclosing_rect, contours)]
        lengths = [max(r[1]) for r in rects]
        vehicle_roll = shm.kalman.roll.get()
        lines = [cv2.fitLine(c, cv2.DIST_L2, 0, 0.01, 0.01) for c in contours]
        angles = [np.degrees(np.arctan2(line[1], line[0]))[0] for line in lines]
        angles = [min(abs(90 - a - vehicle_roll), abs(-90 - a - vehicle_roll)) for a in angles]
        rectangularities = [a / (1e-30 + rect[1][0] * rect[1][1]) for (c, a, rect) in zip(contours, areas, rects)]
        contours = [ContourFeats(*feats) for feats in zip(contours, areas, xs, ys, rectangularities, angles, lengths)]
        contours = filter(lambda c: c.angle < self.options['max_angle_from_vertical'], contours)
        contours = filter(lambda c: c.length > self.options['min_length'], contours)
        contours = filter(lambda c: c.area > self.options['min_contour_area'], contours)
        contours = filter(lambda c: c.rect > self.options['min_contour_rect'], contours)
        contours = sorted(contours, key=lambda c: c.area)[:3]
        contours_by_x = sorted(contours, key=lambda c: c.x)
        leftmost = try_index(contours_by_x, 0)
        middle = try_index(contours_by_x, 1)
        rightmost = try_index(contours_by_x, 2)
        tmp = np.zeros((h, w, 3))
        results = shm.gate_vision.get()
        results.leftmost_visible = leftmost is not None
        results.middle_visible = middle is not None
        results.rightmost_visible = rightmost is not None
        if leftmost is not None:
            draw_contours(tmp, [leftmost.contour], color=(255, 0, 0), thickness=-1)
            results.leftmost_x = leftmost.x
            results.leftmost_y = leftmost.y
            results.leftmost_len = leftmost.length
        if middle is not None:
            draw_contours(tmp, [middle.contour], color=(0, 255, 0), thickness=-1)
            results.middle_x = middle.x
            results.middle_y = middle.y
            results.middle_len = middle.length
        if rightmost is not None:
            draw_contours(tmp, [rightmost.contour], color=(0, 0, 255), thickness=-1)
            results.rightmost_x = rightmost.x
            results.rightmost_y = rightmost.y
            results.rightmost_len = rightmost.length
        shm.gate_vision.set(results)
        self.post('contours', tmp)


if __name__ == '__main__':
    Gate('forward', OPTS_ODYSSEUS if VEHICLE == 'odysseus' else OPTS_AJAX)()
