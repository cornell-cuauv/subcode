#!/usr/bin/env python3
from vision.modules.base import ModuleBase
from vision import options
import shm
import math
import cv2 as cv2
import numpy as np
from collections import namedtuple

black_left = False
gate_shm_group = shm.bicolor_gate_vision

# SHM:
#  - general, black, and red centers
#  - confidence

module_options = [
    options.BoolOption('thresh_debug', True),
    options.BoolOption('contour_debug', False),
    options.BoolOption('bins_debug', False),
    options.IntOption('erode_size', 2, 1, 40),
    options.IntOption('gaussian_kernel', 1, 1, 40),
    options.IntOption('gaussian_stdev', 2, 0, 40),
    options.IntOption('thresh_size', 90, 1, 100),
    options.IntOption('min_area', 200, 1, 2000),
]


WHITE = (255, 255, 255)
RED = (0, 0, 255)
BLUE = (255, 0, 0)
GREEN = (0, 255, 0)
ORANGE = (255, 165, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)

def get_kernel(size):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size * 2 + 1, size * 2 + 1), (size, size))


class CashInForward(ModuleBase):
    def threshold(self):
        threshes = {}
        debugs = {}

        k_size = self.options["gaussian_kernel"]
        k_std = self.options["gaussian_stdev"]
        blurred = debugs["blurred"] = cv2.GaussianBlur(self.img, (k_size * 2 + 1, k_size * 2 + 1), k_std, k_std)
        (luv_l, luv_u, luv_v) = cv2.split(cv2.cvtColor(blurred, cv2.COLOR_BGR2LUV))

        debugs["luv_u"] = luv_u

        threshes["red"] = cv2.adaptiveThreshold(
            luv_u,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            self.options["thresh_size"] * 2 + 1,
            -5
        )

        threshes["green"] = cv2.adaptiveThreshold(
            luv_u,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            self.options["thresh_size"] * 2 + 1,
            5
        )

        e_size = self.options["erode_size"]
        e_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (e_size * 2 + 1, e_size * 2 + 1), (e_size, e_size))

        cleaned = {
            name: cv2.dilate(cv2.erode(image, e_kernel), e_kernel)
            for name, image in threshes.items()
        }

        if self.options["thresh_debug"]:
            for name, image in debugs.items():
                self.post("thresh_debug_{}".format(name), image)

            for name, image in threshes.items():
                self.post("thresh_{}".format(name), image)

            for name, image in cleaned.items():
                self.post("thresh_cleaned_{}".format(name), image)

        return cleaned

    FeaturedContour = namedtuple("FeaturedContour", ["x", "y", "area", "contour"])

    def calc_contour_features(self, contour):
        moments = cv2.moments(contour)
        x = int(moments['m10']/moments['m00'])
        y = int(moments['m01']/moments['m00'])

        area = cv2.contourArea(contour)

        return self.FeaturedContour(x, y, area, contour)


    def find_contours(self, images):
        all_contours = {
            name: cv2.findContours(image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[1]
            for name, image in images.items()
        }

        contours = {}

        for name, all_cs in all_contours.items():
            cs = []

            for contour in all_cs:
                area = cv2.contourArea(contour)

                if area < self.options["min_area"]:
                    continue

                moments = cv2.moments(contour)
                x = int(moments['m10']/moments['m00'])
                y = int(moments['m01']/moments['m00'])

                cs.append(self.FeaturedContour(x, y, area, contour))

            contours[name] = cs

        if self.options["contour_debug"]:
            for name, fcs in contours.items():
                image = self.img.copy()
                cs = [fc.contour for fc in fcs]
                cv2.drawContours(image, cs, -1, BLUE, 2)
                self.post("contours_{}".format(name), image)

        return contours


    Bin = namedtuple("Bin", ["x", "y", "area", "probability"])

    def find_bins(self, contours):
        bins = {}

        for name, cs in contours.items():
            if len(cs) == 0:
                bins[name] = self.Bin(0, 0, 0, 0)
                continue

            total_area = sum(fc.area for fc in cs)
            x = sum(fc.x * fc.area for fc in cs) / total_area
            y = sum(fc.y * fc.area for fc in cs) / total_area

            bins[name] = self.Bin(x, y, total_area, 1)

        if self.options["bins_debug"]:
            for name, binn in bins.items():
                image = self.img.copy()
                cv2.circle(image, (int(binn.x), int(binn.y)), int(math.sqrt(binn.area)), BLUE, 5)
                self.post("bin_{}".format(name), image)

        return bins


    def process(self, img):
        print("asdf")
        self.img = img

        self.post("Original", img)

        threshed = self.threshold()
        contours = self.find_contours(threshed)
        bins = self.find_bins(contours)

        final = img.copy()

        for name, binn in bins.items():
            shm_group = shm._eval("recovery_vision_forward_{}".format(name))
            output = shm_group.get()

            output.center_x = binn.x
            output.center_y = binn.y
            output.probability = binn.probability

            shm_group.set(output)

            cv2.circle(final, (int(binn.x), int(binn.y)), int(math.sqrt(binn.area)), BLUE, 5)
            cv2.putText(final, name, (int(binn.x), int(binn.y) - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLUE, 2)

        self.post("Final", final)


if __name__ == '__main__':
    CashInForward(None, module_options)()
