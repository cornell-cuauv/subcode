# Utilities for using SLAM

import numpy as np
import shm

from slam.slam_client import SlamClient

from mission.framework.targeting import ForwardTarget, DownwardTarget

# Vision coords: camera_x, camera_y, dist
# Sub coords: X, Y, Z
# Slam coords: north, east, depth

CAMERA_DIMS = [
    (shm.camera.forward_width.get(), shm.camera.forward_height.get()),
    (shm.camera.downward_width.get(), shm.camera.downward_height.get()),
]

CAMERA_CENTERS = [(CAMERA_DIM[0] / 2, CAMERA_DIM[1] / 2) for CAMERA_DIM in CAMERA_DIMS]

CAMERA_VIEWING_ANGLES = [
    #[73.7, 73.7],
    [76.75, 74.6], # measured
    #[103.6, 76.6], # X, Y forward
    [100, 100], # X. Y downward TODO this isn't an actual value
]

def vision_to_sub(x, y, dist, camera):
    theta = (x - CAMERA_CENTERS[camera][0]) / CAMERA_DIMS[camera][0] * CAMERA_VIEWING_ANGLES[camera][0]
    phi = (y - CAMERA_CENTERS[camera][1]) / CAMERA_DIMS[camera][1] * CAMERA_VIEWING_ANGLES[camera][1]

    dy = dist * np.sin(np.radians(theta))
    dz = dist * np.sin(np.radians(phi))

    return np.array([np.sqrt(dist**2 - dy**2 - dz**2), dy, dz])

# Returns just X and Y
def sub_to_vision(sub_coords, camera):
    theta = np.degrees(np.arctan2(sub_coords[1], np.sqrt(sub_coords[0]**2 + sub_coords[2]**2)))
    phi = np.degrees(np.arctan2(sub_coords[2], np.sqrt(sub_coords[0]**2 + sub_coords[1]**2)))

    return (theta * CAMERA_DIMS[camera][0] / (CAMERA_VIEWING_ANGLES[camera][0] * 2) + CAMERA_CENTERS[camera][0],
            phi * CAMERA_DIMS[camera][1] / (CAMERA_VIEWING_ANGLES[camera][1] * 2) + CAMERA_CENTERS[camera][1])

make_rotate = lambda theta: np.array([
    [np.cos(theta), -np.sin(theta), 0],
    [np.sin(theta), np.cos(theta), 0],
    [0, 0, 1],
])

# this is just identity
# for some reason flipping depth breaks crap
make_flip_depth = lambda: np.array([
    [1, 0, 0],
    [0, 1, 0],
    [0, 0, 1],
])

make_add_depth = lambda depth: np.array([0, 0, depth])

# Convert sub to slam coords. Deals in np arrays.
def sub_to_slam(sub_coords):
    kalman = shm.kalman.get()

    rotate = make_rotate(-np.radians(kalman.heading))
    flip_depth = make_flip_depth()
    add_depth = make_add_depth(kalman.depth)

    return np.dot(np.dot(sub_coords.T, rotate).T, flip_depth) + add_depth

# Convert slam to sub coords. Deals in np arrays.
def slam_to_sub(slam_coords):
    kalman = shm.kalman.get()

    rotate = make_rotate(np.radians(kalman.heading))
    flip_depth = make_flip_depth()
    add_depth = make_add_depth(kalman.depth)

    return np.dot(np.dot(slam_coords - add_depth, flip_depth).T, rotate).T

slam = SlamClient()

def check_camera(camera):
    return 1 if camera in ['downward', 'down', 'd'] else 0

def observe(name, x, y, dist, camera=0):
    return slam.observe_landmark(name, *sub_to_slam(vision_to_sub(x, y, dist, check_camera(camera))), uncertainty=1)

def request(name, camera):
    return sub_to_vision(slam_to_sub(np.array(slam.request_landmark(name)[0])), check_camera(camera))

def ForwardTargetObject(name, deadband):
    return ForwardTarget(request(name, 0), CAMERA_CENTERS[0], deadband)

def DownwardTargetObject(name, deadband):
    return DownwardTarget(request(name, 1), CAMERA_CENTERS[1], deadband)
