#!/usr/bin/env python3
import shm.depth_torpedos_board
from vision.modules.base import ModuleBase
from vision import options
from vision.framework.draw import draw_rect, draw_rot_rect
from vision.framework.color import bgr_to_gray
from vision.framework.color import below_threshold
from vision.framework.color import binary_threshold
from vision.framework.color import binary_threshold_inv

from vision.framework.color import range_threshold
from vision.framework.draw import draw_contours
from vision.framework.draw import draw_circle
from vision.framework.feature import outer_contours
from vision.framework.transform import erode
from vision.framework.transform import dilate
from vision.framework.transform import rect_kernel
# from vision.framework.transform import elliptic_kernel
from vision.framework.feature import contour_centroid
from vision.framework.feature import contour_area
from vision.framework.feature import min_enclosing_circle
from vision.framework.feature import min_enclosing_rect
from vision.framework.color import white_balance_bgr, white_balance_bgr_blur
import shm
import cv2
import math
import numpy as np


module_options = [
  options.BoolOption("Hue Inverse", False),
  options.IntOption('min_board_thresh', 45, 0, 255),
  options.IntOption('max_goals_thresh', 45, 0, 255),
]

# assumming no obb in yolo
class DepthTorpedo(ModuleBase):
    def process(self, img):
        depth_board = shm.depth_torpedos_board.get()
        tr_x = depth_board.top_right_x
        tr_y = depth_board.top_right_y

        br_x = depth_board.bottom_right_x
        br_y = depth_board.bottom_right_y

        tl_x = depth_board.top_left_x
        tl_y = depth_board.top_left_y

        bl_x = depth_board.bottom_left_x
        bl_y = depth_board.bottom_left_y

        corner_1 = (tl_x,tl_y)
        corner_2 = (br_x,br_y)
        roi = img[int(tl_y):int(br_y), int(tl_x):int(br_x)]
        mean_val = cv2.mean(roi)
        draw_rect(img,corner_1,corner_2)
        self.post('normal of goal', img)

        print(mean_val)

if __name__ == '__main__':
  DepthTorpedo("depth", module_options)()
