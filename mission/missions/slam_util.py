# Utilities for using SLAM

import numpy as np
import shm
from conf.vehicle import cameras

# Vision coords: camera_x, camera_y, dist
# Sub coords: X, Y, Z
# Slam coords: north, east, depth

CAMERA_DIMS = [
    (shm.camera.forward_width.get(), shm.camera.forward_height.get()),
    (shm.camera.downward_width.get(), shm.camera.downward_height.get()),
]

def vision_to_sub(x, y, dist):
    theta = x # TODO calibrate
    phi = y # TODO calibrate

    return np.array(
        dist * np.cos(theta) * np.cos(phi),
        dist * np.sin(theta) * np.cos(phi),
        dist * np.cos(theta) * np.sin(phi),
    )

make_rotate = lambda theta: np.array([
    [np.cos(theta), -np.sin(theta), 0],
    [np.sin(theta), np.cos(theta), 0],
    [0, 0, 1],
])

make_flip_depth = lambda: np.array([
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, -1],
])

make_add_depth = lambda depth: np.array([0, 0, depth])

# Convert sub to slam coords. Deals in np arrays.
def sub_to_slam(sub_coords):
    kalman = shm.kalman.get()

    rotate = make_rotate(np.radians(kalman.heading))
    flip_depth = make_flip_depth()
    add_depth = make_add_depth(kalman.depth)

    return np.dot(np.dot(sub_coords.T, rotate).T, flip_depth) + add_depth

# Convert slam to sub coords. Deals in np arrays.
def slam_to_sub(slam_coords):
    kalman = shm.kalman.get()

    rotate = make_rotate(-np.radians(kalman.heading))
    flip_depth = make_flip_depth()
    add_depth = make_add_depth(kalman.depth)

    return np.dot(np.dot(slam_coords - add_depth, flip_depth).T, rotate).T
