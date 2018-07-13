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
    options.BoolOption('in_simulator', False),
    options.BoolOption('preprocess_debug', False),
    options.BoolOption('thresh_debug', True),
    options.BoolOption('contour_debug', False),
    options.BoolOption('bins_debug', False),

    options.IntOption('green_luv_l_min', 0, 0, 255),
    options.IntOption('green_luv_l_max', 0, 0, 255),

    options.IntOption('erode_size', 15, 1, 40),
    options.IntOption('gaussian_kernel', 15, 1, 40),
    options.IntOption('gaussian_stdev', 30, 0, 40),
    options.IntOption('thresh_size', 150, 1, 100),
    options.IntOption('min_area', 2000, 1, 2000),
    options.DoubleOption('min_circularity', .10, 0, 1),
    options.DoubleOption('max_rectangularity', .75, 0, 1),
    options.DoubleOption('max_joining_dist', 200, 0, 500),
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


class CashInDownward(ModuleBase):
    def preprocess(self, img, debug=False):
        k_size = self.options["gaussian_kernel"]
        k_std = self.options["gaussian_stdev"]
        blurred = cv2.GaussianBlur(self.img, (k_size * 2 + 1, k_size * 2 + 1), k_std, k_std)

        if debug:
            self.post("preprocessed", blurred)

        return blurred


    def threshold(self, img, debug=False):
        threshes = {}
        debugs = {}

        luv = cv2.cvtColor(img, cv2.COLOR_BGR2LUV)
        (luv_l, luv_u, luv_v) = cv2.split(luv)

        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        (lab_l, lab_a, lab_b) = cv2.split(lab)

        debugs["luv_u"] = luv_u
        debugs["luv_l"] = luv_l
        debugs["lab_a"] = lab_a


        threshes["bin_green"] = cv2.adaptiveThreshold(
            lab_a,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            self.options["thresh_size"] * 2 + 1,
            5,
        )

        threshes["bin_red"] = cv2.adaptiveThreshold(
            luv_u,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            self.options["thresh_size"] * 2 + 1,
            -3,
        )


        e_size = self.options["erode_size"]
        e_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (e_size * 2 + 1, e_size * 2 + 1), (e_size, e_size))

        cleaned = {
            name: cv2.dilate(cv2.erode(image, e_kernel), e_kernel)
            for name, image in threshes.items()
        }

        if debug:
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


    def find_contours(self, images, debug=False):
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

        if debug:
            for name, fcs in contours.items():
                image = self.img.copy()
                cs = [fc.contour for fc in fcs]
                cv2.drawContours(image, cs, -1, BLUE, 2)
                self.post("contours_{}".format(name), image)

        return contours


    Bin = namedtuple("Bin", ["x", "y", "area", "probability"])

    def find_bins(self, featured_contours, debug=False):
        bins = {}

        for name, fcs in featured_contours.items():
            if len(fcs) == 0:
                bins[name] = self.Bin(0, 0, 0, 0)
                continue

            # total_area = sum(fc.area for fc in fcs)
            # x = sum(fc.x * fc.area for fc in fcs) / total_area
            # y = sum(fc.y * fc.area for fc in fcs) / total_area
            # area = total_area

            fc = max(fcs, key=lambda fc: fc.area)
            area = fc.area
            x = fc.x
            y = fc.y

            bins[name] = self.Bin(x, y, area, 1)

        if debug:
            for name, binn in bins.items():
                image = self.img.copy()
                cv2.circle(image, (int(binn.x), int(binn.y)), int(math.sqrt(binn.area)), BLUE, 5)
                self.post("bin_{}".format(name), image)

        return bins


    def process(self, img):
        print("asdf")
        self.img = img

        h, w, _ = img.shape

        shm.camera.downward_height.set(h)
        shm.camera.downward_width.set(w)

        self.post("Original", img)

        preprocessed_image = self.preprocess(self.img, debug=self.options["preprocess_debug"])
        threshed = self.threshold(preprocessed_image, debug=self.options["thresh_debug"])
        contours = self.find_contours(threshed, debug=self.options["contour_debug"])
        bins = self.find_bins(contours, debug=self.options["bins_debug"])

        final = img.copy()

        for name, binn in bins.items():
            shm_group = shm._eval("recovery_vision_downward_{}".format(name))
            output = shm_group.get()

            output.area = binn.area
            output.center_x = binn.x
            output.center_y = binn.y
            output.probability = binn.probability

            shm_group.set(output)

            cv2.circle(final, (int(binn.x), int(binn.y)), int(math.sqrt(binn.area)), BLUE, 5)
            cv2.putText(final, name, (int(binn.x), int(binn.y) - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, BLUE, 2)

        self.post("Final", final)


if __name__ == '__main__':
    CashInDownward("downward", module_options)()
