import math

import shm

def move_flat_relative(meters, degrees):
    shm.navigation_settings.position_controls.set(1)
    north_desire = shm.navigation_desires.north
    north_reality = shm.kalman.north
    east_desire = shm.navigation_desires.east
    east_reality = shm.kalman.east
    movement_angle = math.radians(shm.kalman.heading.get() + degrees)
    north_desire.set(north_reality.get() + meters * math.sin(movement_angle))
    east_desire.set(east_reality.get() + meters * math.cos(movement_angle))
    while abs(north_reality.get() - north_desire.get()) > 0.1 or abs(east_reality.get() - east_desire.get()) > 0.1:
        pass
    shm.navigation_settings.position_controls.set(0)

def move_forward(meters):
    move_flat_relative(meters, 0)

def move_backward(meters):
    move_flat_relative(meters, 180)

def move_left(meters):
    move_flat_relative(meters, 90)

def move_right(meters):
    move_flat_relative(meters, 270)

def move_up(meters):
    shm.navigation_settings.position_controls.set(1)
    depth_desire = shm.navigation_desires.depth
    depth_reality = shm.kalman.depth
    depth_desire.set(depth_reality.get() - meters)
    while abs(depth_reality.get() - depth_desire.get()) > 0.1:
        pass
    shm.navigation_settings.position_controls.set(0)

def move_down(meters):
    move_up(-meters)

def rotate_left(degrees):
    heading_desire = shm.navigation_desires.heading
    true_heading = shm.kalman.heading
    heading_desire.set(true_heading.get() - degrees)
    while abs(true_heading.get() - heading_desire.get()) > 0.1:
        pass

def rotate_right(degrees):
    rotate_left(-degrees)
