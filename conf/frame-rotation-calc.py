#!/usr/bin/env python3

"""A simple tool used to calculate values to fill certain values in the configuration
toml"""

import numpy as np
import conf.vehicle as vehicle_conf

if __name__ == '__main__':
    if vehicle_conf.is_mainsub:
        xy_plane_center = np.zeros(shape=(3,))
        xy_plane_thrusters = ['fore_port', 'aft_port', 'fore_starboard', 'aft_starboard']
        thrusters = vehicle_conf.thrusters
        dvl_pos = np.array(vehicle_conf.dvl_absolute_position)

        for name in xy_plane_thrusters:
            for thruster in thrusters:
                if name == thruster['name']:
                    xy_plane_center += np.array(thruster['pos'])

        xy_plane_center /= len(xy_plane_thrusters)

        print("center of rotation along xy plane:", xy_plane_center)
        print("dvl position relative to cog:", dvl_pos)
        vec_offset = xy_plane_center - dvl_pos
        scalar_offset = (vec_offset[0] ** 2 + vec_offset[1] ** 2) ** 0.5
        print("calculated dvl offset:", scalar_offset)

