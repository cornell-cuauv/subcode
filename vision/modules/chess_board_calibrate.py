#!/usr/bin/env python3

import sys
import cv2
import numpy as np
import pickle
from vision.modules.base import ModuleBase


class ChessBoardCalibrate(ModuleBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        self.objp = np.zeros((6*7,3), np.float32)
        self.objp[:,:2] = np.mgrid[0:7,0:6].T.reshape(-1,2)
        self.objpoints = []
        self.imgpoints = [] 

    def process(self, img):

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        ret, corners = cv2.findChessboardCorners(gray, (7,6), None)
        if ret == True:
            self.objpoints.append(self.objp)
            corners2 = cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), self.criteria)
            self.imgpoints.append(corners2)
            cv2.drawChessboardCorners(img, (7,6), corners2, ret)
            self.post('img', img)
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(self.objpoints, self.imgpoints, gray.shape[::-1], None, None)
            with open(f'{sys.path[0]}/../configs/polaris_downcam_undistort.pickle', 'wb') as f:
                pickle.dump([ret, mtx, dist, rvecs, tvecs], f)
        else:
            self.post('img', img)
        


if __name__ == '__main__':
    ChessBoardCalibrate('downward', [])()