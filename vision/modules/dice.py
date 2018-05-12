#!/usr/bin/env python3

import traceback
import sys

import cv2
import numpy as np
import shm

from vision.modules.base import ModuleBase
from vision import options

options = [
          ]

class Dice(ModuleBase):

    def approximate(self, c):
        return cv2.approxPolyDP(c,0.01*cv2.arcLength(c,True),True)

    def process(self, mat):
        try:
            hsv = cv2.cvtColor(mat, cv2.COLOR_BGR2HSV)
            self.post('hsv', hsv)

            sensitivity = 50
            # define range of white color in HSV
            lower_white = np.array([0,0,255-sensitivity], dtype=np.uint8)
            upper_white = np.array([255,sensitivity,255], dtype=np.uint8)

            # Threshold the HSV image to get only white colors
            mask = cv2.inRange(hsv, lower_white, upper_white)

            self.post("white", mask)

            # Bitwise-AND mask and original image
            color = cv2.bitwise_and(mat,mat.copy(), mask=mask)

            # CV_BGR2GRAY
            grayImage = cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
            # blur to remove noise
            grayImage = cv2.GaussianBlur(grayImage, (5, 5), 0, 0)
            # Hard thresholding to get values within our range
            ret, grayImage = cv2.threshold(grayImage, 28, 255, cv2.THRESH_BINARY)
            # Edge detection
            edges = cv2.Canny(grayImage, 2, 4)

            self.post("Canny edges", edges)

            # Contour detection. We find only the external contours.
            image, contours, hierarchy = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

            # print("Number of contours: ", len(contours))

            approximate_contours = list(map(self.approximate, contours))
            avg_contour_area = np.mean(list(map(lambda x: cv2.contourArea(x), approximate_contours)))
            # print("Average area: ", avg_contour_area)
            bounding_contours = list(filter(lambda c: cv2.contourArea(c) > avg_contour_area-200, approximate_contours))

            # Draw bounding boxes around each interesting contour
            bounding_boxes = list(map(cv2.minAreaRect, bounding_contours))
            boxes = mat.copy()
            for b in bounding_boxes:
                box = cv2.boxPoints(b)
                box = np.int0(box)
                cv2.drawContours(boxes, [box], 0, (0, 0, 255), 2)

            self.post("bounding boxes", boxes)

            box_contours = list(map(lambda x: [np.int0(cv2.boxPoints(x))], bounding_boxes))

            # Set up the detector with default parameters.
            params = cv2.SimpleBlobDetector_Params()

            # Change thresholds
            params.minThreshold = 240;
            params.maxThreshold = 255;

            params.filterByArea = True
            params.minArea = 5

            params.minDistBetweenBlobs = 1

            params.filterByInertia = True
            params.minInertiaRatio = 0.1

            params.filterByCircularity = False

            detector = cv2.SimpleBlobDetector_create(params)

            for i in range(len(bounding_boxes)):
                mask = np.zeros_like(grayImage)
                cv2.drawContours(mask, box_contours[i], 0, 255, -1)
                out = np.zeros_like(grayImage)
                out[mask == 255] = grayImage[mask == 255]
                keypoints = detector.detect(out)
                cv2.putText(boxes, str(len(keypoints)), (int(bounding_boxes[i][0][0]) - 50, int(bounding_boxes[i][0][1])), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 0), 2)
            self.post("bounding boxes", boxes)
            im_with_keypoints = cv2.drawKeypoints(img, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
            self.post("out", im_with_keypoints)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)

if __name__ == '__main__':
    Dice('forward', options)()