#!/usr/bin/env python3

import traceback
import sys

import cv2
import numpy as np
import shm

from vision.modules.base import ModuleBase
from vision import options

options = [
            options.IntOption('red_lab_a_min', 200, 0, 255),
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
            # print(len(keypoints))
            self.post("bounding boxes", boxes)
            # im_with_keypoints = cv2.drawKeypoints(img, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
            # cv2.imshow("out", im_with_keypoints)

            # return grayImage


            # lab = cv2.cvtColor(mat, cv2.COLOR_BGR2LAB)
            # lab_split = cv2.split(lab)
            # self.post('lab_a_split', lab_split[1])

            # # detect red section
            # threshed = cv2.inRange(lab_split[1],
            #         self.options['red_lab_a_min'],
            #         self.options['red_lab_a_max'])
            # threshed = cv2.erode(threshed,
            #         (2 * self.options['erode_kernel'] + 1,
            #         2 * self.options['erode_kernel'] + 1))
            # self.post('red_threshed', threshed)

            # # draw centroids for red sections
            # _, contours, _ = cv2.findContours(threshed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            # for contour in contours:
            #     moments = cv2.moments(contour)
            #     cX = int(moments['m10'] / moments['m00'])
            #     cY = int(moments['m01'] / moments['m00'])
            #     cv2.drawContours(mat, [contour], -1, (0, 255, 0), 2)
            #     cv2.circle(mat, (cX, cY), 7, (255, 255, 255), -1)
            # self.post('centroids', mat)

            # # detect black section
            # threshed = cv2.inRange(lab_split[0],
            #         self.options['black_lab_l_min'],
            #         self.options['black_lab_l_max'])
            # threshed = cv2.erode(threshed,
            #         (2 * self.options['erode_kernel'] + 1,
            #         2 * self.options['erode_kernel'] + 1),
            #         iterations=self.options['black_erode_iters'])
            # self.post('black_threshed', threshed)

            # # draw centroids for black sections
            # _, contours, _ = cv2.findContours(threshed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            # for contour in contours:
            #     moments = cv2.moments(contour)
            #     cX = int(moments['m10'] / moments['m00'])
            #     cY = int(moments['m01'] / moments['m00'])
            #     cv2.drawContours(mat, [contour], -1, (0, 255, 0), 2)
            #     cv2.circle(mat, (cX, cY), 7, (255, 255, 255), -1)
            # self.post('centroids', mat)

            # # detect green section
            # threshed = cv2.inRange(lab_split[1],
            #         self.options['green_lab_a_min'],
            #         self.options['green_lab_a_max'])
            # threshed = cv2.erode(threshed,
            #         (2 * self.options['erode_kernel'] + 1,
            #         2 * self.options['erode_kernel'] + 1))
            # self.post('green_threshed', threshed)

            # # TODO: Use red section to determine center, rather than green
            # # detect diameters of green section to calculate location of center
            # # of roulette board
            # blurred = cv2.GaussianBlur(threshed,
            #         (2 * self.options['blur_kernel'] + 1,
            #         2 * self.options['blur_kernel'] + 1), 0)
            # self.post('blurred', blurred)

            # edges = cv2.Canny(blurred,
            #         self.options['canny_low_thresh'],
            #         self.options['canny_high_thresh'])
            # self.post('edges', edges)
            # lines = cv2.HoughLines(edges,
            #         self.options['hough_lines_rho'],
            #         self.options['hough_lines_theta'] * np.pi / 180,
            #         self.options['hough_lines_thresh'])

            # lines = [(idx, line[0]) for (idx, line) in enumerate(lines[:2])]
            # line_equations = []
            # lines_mat = mat.copy()
            # for (i, (rho,theta)) in lines:
            #     a = np.cos(theta)
            #     b = np.sin(theta)
            #     x0 = a*rho
            #     y0 = b*rho
            #     x1 = int(x0 + 1000*(-b))
            #     y1 = int(y0 + 1000*(a))
            #     x2 = int(x0 - 1000*(-b))
            #     y2 = int(y0 - 1000*(a))
            #     cv2.line(lines_mat,(x1,y1),(x2,y2),(0,0,255),2)
            #     line_equations.append((float(x1), float(x2), float(y1), float(y2)))

            # self.post('lines', lines_mat)

            # # calculate intersection of diameters of green section
            # [x01, x02, y01, y02] = line_equations[0]
            # [x11, x12, y11, y12] = line_equations[1]
            # b1 = (y02 - y01) / max(1e-10, x02 - x01)
            # b2 = (y12 - y11) / max(1e-10, x12 - x11)
            # intersection_x = int((b1 * x01 - b2 * x11 + y11 - y01) / (b1 - b2))
            # intersection_y = int(b1 * (intersection_x - x01) + y01)
            # center_mat = mat.copy()
            # cv2.circle(center_mat, (intersection_x, intersection_y), 7, (255, 255, 255), -1)
            # self.post('center', center_mat)

            # # draw centroids of green sections and predict location ~3 seconds later
            # _, contours, _ = cv2.findContours(threshed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            # for contour in contours:
            #     moments = cv2.moments(contour)
            #     cX = int(moments['m10'] / max(1e-10, moments['m00']))
            #     cY = int(moments['m01'] / max(1e-10, moments['m00']))
            #     cv2.drawContours(mat, [contour], -1, (0, 255, 0), 2)
            #     cv2.circle(mat, (cX, cY), 7, (255, 255, 255), -1)
            #     self.post('centroids', mat)
            #     translated_x = cX - intersection_x
            #     translated_y = cY - intersection_y
            #     predicted_x = translated_x * np.cos(np.radians(20)) - translated_y * np.sin(np.radians(20))
            #     predicted_y = translated_x * np.sin(np.radians(20)) + translated_y * np.cos(np.radians(20))
            #     predicted_x = int(predicted_x + intersection_x)
            #     predicted_y = int(predicted_y + intersection_y)
            #     cv2.circle(mat, (predicted_x, predicted_y), 7, (255, 0, 0), -1)
            # self.post('predicted_green', mat)
        except Exception as e:
            traceback.print_exc(file=sys.stdout)

if __name__ == '__main__':
    Dice('forward', options)()