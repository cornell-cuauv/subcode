#!/usr/bin/env python3

import sys
import cv2
import pickle
from vision.modules.base import ModuleBase
from vision.framework.draw import draw_rect

class Undistort(ModuleBase):
    def process(self, img):
        with open(f'{sys.path[0]}/../configs/polaris_downcam_undistort.pickle', 'rb') as f:
            ret, mtx, dist, rvecs, tvecs = pickle.load(f)
        h, w = img.shape[:2]
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w,h), 1, (w,h))
        dst = cv2.undistort(img, mtx, dist, None, newcameramtx)
        x, y, w, h = roi
        dst = dst[y:y+h, x:x+w]
        # dst = cv2.resize(dst, (640, 512))
        # print(w, h)
        # draw_rect(dst, (x, y), (x + w, y + h))
        self.post('img', dst)

if __name__ == '__main__':
    Undistort('downward', [])()