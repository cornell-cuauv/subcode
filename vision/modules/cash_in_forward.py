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


class CashInForward(ModuleBase):
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

        if self.options["in_simulator"]:
            # dist_from_green = np.linalg.norm(luv.astype(int) - [150, 90, 103], axis=2)

            # threshes["green"] = cv2.inRange(
            #     dist_from_green,
            #     0,
            #     40,
            # )

            threshes["green"] = cv2.adaptiveThreshold(
                lab_a,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                self.options["thresh_size"] * 2 + 1,
                5,
            )

            threshes["red"] = cv2.adaptiveThreshold(
                luv_u,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                self.options["thresh_size"] * 2 + 1,
                -3,
            )

        else:
            threshes["green"] = cv2.adaptiveThreshold(
                luv_l,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY_INV,
                self.options["thresh_size"] * 2 + 1,
                9
            )

            # threshes["green"] = cv2.inRange(
            #     luv_l,
            #     self.options["green_luv_l_min"],
            #     self.options["green_luv_l_max"],
            # )

            threshes["red"] = cv2.adaptiveThreshold(
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
            # name: cv2.erode(image, e_kernel)
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

    @staticmethod
    def calc_contour_features(contour):
        moments = cv2.moments(contour)
        x = int(moments['m10']/moments['m00'])
        y = int(moments['m01']/moments['m00'])

        area = cv2.contourArea(contour)

        return CashInForward.FeaturedContour(x, y, area, contour)


    @staticmethod
    def fc_togetherness_rating(fc1, fc2):
        dist = math.hypot(fc1.x - fc2.x, fc1.y - fc2.y)

        if dist < 1:
            return float('Inf')

        return dist


    @staticmethod
    def avg_fc(*fcs):
        total_area = sum(fc.area for fc in fcs)
        x = sum(fc.x * fc.area for fc in fcs) / total_area
        y = sum(fc.y * fc.area for fc in fcs) / total_area
        area = total_area

        return CashInForward.FeaturedContour(x, y, area, None)


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

                circle = cv2.minEnclosingCircle(contour)
                rect = cv2.boundingRect(contour)

                if area / (math.pi * circle[1] ** 2) < self.options["min_circularity"]:
                    continue

                if area / (rect[2] * rect[3]) > self.options["max_rectangularity"]:
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

            contours_to_draw = []

            # total_area = sum(fc.area for fc in fcs)
            # x = sum(fc.x * fc.area for fc in fcs) / total_area
            # y = sum(fc.y * fc.area for fc in fcs) / total_area
            # area = total_area

            largest_fc = max(fcs, key=lambda fc: fc.area)
            area = largest_fc.area
            x = largest_fc.x
            y = largest_fc.y

            contours_to_draw.append((largest_fc.contour, RED))

            result_fc = largest_fc

            if len(fcs) >= 2:
                fc2 = min(fcs, key=lambda fc: self.fc_togetherness_rating(largest_fc, fc))

                if self.fc_togetherness_rating(largest_fc, fc2) < self.options["max_joining_dist"]:
                    result_fc = self.avg_fc(largest_fc, fc2)

                    contours_to_draw.append((fc2.contour, MAGENTA))

            binn = bins[name] = self.Bin(result_fc.x, result_fc.y, result_fc.area, 1)

            if debug:
                image = self.img.copy()
                cv2.circle(image, (int(binn.x), int(binn.y)), int(math.sqrt(binn.area)), BLUE, 5)

                for contour, color  in contours_to_draw:
                    cv2.drawContours(image, [contour], -1, color, 2)

                self.post("bin_{}".format(name), image)

        return bins


    def process(self, img):
        print("asdf")
        self.img = img

        h, w, _ = img.shape

        shm.camera.forward_height.set(h)
        shm.camera.forward_width.set(w)

        self.post("Original", img)

        preprocessed_image = self.preprocess(self.img, debug=self.options["preprocess_debug"])
        threshed = self.threshold(preprocessed_image, debug=self.options["thresh_debug"])
        contours = self.find_contours(threshed, debug=self.options["contour_debug"])
        bins = self.find_bins(contours, debug=self.options["bins_debug"])

        final = img.copy()

        for name, binn in bins.items():
            shm_group = shm._eval("recovery_vision_forward_{}".format(name))
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
    CashInForward("forward", module_options)()
