#!/usr/bin/env python3

from math import degrees, atan, pi, cos, sin
from vision.modules.base import ModuleBase
from vision.options import IntOption
from vision.framework.draw import draw_line
from conf.vehicle import cameras
from auv_math.camera import calc_forward_angles

options = [
    IntOption('x', 396, 0, 640),
    IntOption('top_y', 124, 0, 512),
    IntOption('bottom_y', 269, 0, 512)
]

class Analysis(ModuleBase):

    def compute_3d_coordinates(focal_length_mm, sensor_width_mm, sensor_height_mm, image_width_px, image_height_px, bar_top_px, bar_bottom_px, bar_height_m, camera_position):
        pixel_size_mm = sensor_width_mm / image_width_px
        focal_length_px = focal_length_mm / pixel_size_mm
        principal_point = (image_width_px / 2, image_height_px / 2)
        bar_top_normalized = ((bar_top_px[0] - principal_point[0]) / focal_length_px, (bar_top_px[1] - principal_point[1]) / focal_length_px)
        bar_bottom_normalized = ((bar_bottom_px[0] - principal_point[0]) / focal_length_px, (bar_bottom_px[1] - principal_point[1]) / focal_length_px)
        height_normalized = bar_bottom_normalized[1] - bar_top_normalized[1]
        distance = bar_height_m / height_normalized
        bar_top_3d = (bar_top_normalized[0] * distance, bar_top_normalized[1] * distance, distance)
        bar_bottom_3d = (bar_bottom_normalized[0] * distance, bar_bottom_normalized[1] * distance, distance)
        return bar_top_3d, bar_bottom_3d

    def process(self, img):

        draw_line(img, (self.options['x'], self.options['top_y']),
                (self.options['x'], self.options['bottom_y']),
                color=(0, 255, 0), thickness=5)
        self.post('forward', img)

        forward = cameras['forward']
        bar_top_3d, bar_bottom_3d = compute_3d_coordinates(forward['focal_length_mm'], forward['sensor_size_wh_mm'][0],
                forward['sensor_size_wh_mm'][1], forward['width'], forward['height'], self.options['x'], self.options['x'],
                self.options['bottom_y'] - self.options['top_y'], camera_position=forward['position'])

        
        
        # top_h, top_p = calc_forward_angles(cameras['forward'],
        #         (self.options['x'], self.options['top_y']))
        # bottom_h, bottom_p = calc_forward_angles(cameras['forward'],
        #         (self.options['x'], self.options['bottom_y']))

        # # print(degrees(top_p), degrees(bottom_p))

        # X = 1.22 * atan(pi / 2 - top_p) * atan(pi / 2 - bottom_p) / (atan(pi / 2 - top_p) + atan(pi / 2 - bottom_p))
        # F = X * cos(top_h)
        # S = X * sin(top_h)

        # print(F, S)
        
        


if __name__ == '__main__':
    Analysis('forward', options)()