#!/usr/bin/env python3

import sys
from math import tan, pi, radians, degrees, atan
import shm
from auv_math.camera import calc_forward_angles
from conf.vehicle import cameras
from mission.framework.base import AsyncBase
from mission.framework.position import move_x
from mission.framework.movement import relative_to_initial_heading

# GATE_VERTICAL_LENGTH = 0.6096
GATE_VERTICAL_LENGTH = 0.9

def denormalize(cam, point):
    x = point[0] * cam['width'] + cam['width'] / 2
    y = point[1] * cam['width'] + cam['height'] / 2
    return (x, y)

def heading_to_point(cam, point):
    x, y = denormalize(cam, point)
    h_dist_from_focal_plane_center = (x - cam['width'] / 2) / cam['width'] * cam['sensor_size_wh_mm'][0]
    angle_from_focal_plane_to_sensor = degrees(atan(cam['focal_length_mm'] / h_dist_from_focal_plane_center))
    if angle_from_focal_plane_to_sensor < 0:
        return -angle_from_focal_plane_to_sensor - 90
    else:
        return 90 - angle_from_focal_plane_to_sensor




class AnalyticGate(AsyncBase):
    def __init__(self):
        self.first_task = self.main()

    async def main(self):
        gate = shm.gate_vision.get()

        h, _ = calc_forward_angles(cameras['forward'], denormalize(cameras['forward'], (gate.leftmost_x, gate.leftmost_y)))
        #h = heading_to_point(cameras['forward'], (gate.leftmost_x, gate.leftmost_y))
        print(degrees(h))

        """
        if not (-gate.leftmost_len / 2 < -gate.leftmost_y < gate.leftmost_len / 2):
            print('Error: the vertical must pass through the horizontal')
            sys.exit(1)
        left_top_pos_on_screen = (gate.leftmost_x, gate.leftmost_y - gate.leftmost_len / 2)
        print('left_top_pos_on_screen:', left_top_pos_on_screen)
        heading_to_left_top, pitch_to_left_top = calc_forward_angles(cameras['forward'], left_top_pos_on_screen)
        print('heading_to_left_top:', heading_to_left_top)
        print('pitch_to_left_top:', pitch_to_left_top)
        left_distance_above_horizontal = (-left_top_pos_on_screen[1] / gate.leftmost_len) * GATE_VERTICAL_LENGTH
        print('left_distance_above_horizontal:', left_distance_above_horizontal)
        forward_distance = tan(pi / 2 - pitch_to_left_top) * left_distance_above_horizontal
        print('forward_distance:', forward_distance)
        await relative_to_initial_heading(degrees(heading_to_left_top))
        """

if __name__ == '__main__':
    AnalyticGate().run()
