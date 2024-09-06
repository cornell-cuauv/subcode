#!/usr/bin/env python3
import shm
import time
import math
import numpy
import cupy as cp
import conf.vehicle as vehicle_conf
import sensors.kalman3d.util as util

from auv_math.quat import Quaternion
from functools import reduce
from sensors.kalman3d.kalman_filters import LinearKalmanFilter

# IMPORTANT
# The code below uses two reference frame
#   1. AUV reference frame (based off of GX4 hpr + kalman_offset) (+X forward, +Y right, +Z down)
#   2. Global reference frame (North is heading = 0 deg and East = 90 deg)


def rec_get_attr(s: str):
    """returns shm.(s)"""
    return reduce(lambda acc, e: getattr(acc, e),
                  s.split('.'), shm)


# configure ease of access for vehicle information
gx_hpr = vehicle_conf.gx_hpr
gx_hpr[0] += shm.kalman_settings.heading_offset.get()

GX_ORIENTATION_OFFSET = Quaternion(hpr=gx_hpr)
GX_POSITION_OFFSET = cp.array([0, 0, 0])  # TODO
DVL_POSITION_OFFSET = cp.array([0, 0, 0])  # TODO

heading_var = rec_get_attr(vehicle_conf.sensors['heading'])
pitch_var = rec_get_attr(vehicle_conf.sensors['pitch'])
roll_var = rec_get_attr(vehicle_conf.sensors['roll'])

heading_rate_var = rec_get_attr(vehicle_conf.sensors['heading_rate'])
pitch_rate_var = rec_get_attr(vehicle_conf.sensors['pitch_rate'])
roll_rate_var = rec_get_attr(vehicle_conf.sensors['roll_rate'])

depth_var = rec_get_attr(vehicle_conf.sensors['depth'])
depth_offset_var = rec_get_attr(vehicle_conf.sensors['depth_offset'])

velx_var = rec_get_attr(vehicle_conf.sensors['velx'])
vely_var = rec_get_attr(vehicle_conf.sensors['vely'])
velz_var = rec_get_attr(vehicle_conf.sensors['velz'])

accelx_var = rec_get_attr(vehicle_conf.sensors['accelx'])
accely_var = rec_get_attr(vehicle_conf.sensors['accely'])
accelz_var = rec_get_attr(vehicle_conf.sensors['accelz'])

dvl_beam_vars = [shm.dvl.low_amp_1,
                 shm.dvl.low_amp_2,
                 shm.dvl.low_amp_3,
                 shm.dvl.low_amp_4,
                 shm.dvl.low_correlation_1,
                 shm.dvl.low_correlation_2,
                 shm.dvl.low_correlation_3,
                 shm.dvl.low_correlation_4]

quat_group = rec_get_attr(vehicle_conf.sensors["quaternion"])


def get_heading_quat() -> Quaternion:
    """Returns a quaternion denoting durring heading transformed to AUV
    reference frame"""
    q = quat_group.get()
    quat = Quaternion([q.q0, q.q1, q.q2, q.q3])
    quat *= GX_ORIENTATION_OFFSET
    return quat


def get_hpr_rate_vec() -> numpy.ndarray:
    """Returns np.array([heading, pitch, roll]) angular velocity in deg/s
    transformed to the AUV reference frame"""
    hpr_rate_vec = numpy.array(
        [roll_rate_var.get(), pitch_rate_var.get(), heading_rate_var.get()])
    hpr_rate_vec = numpy.eye(3).dot(
        GX_ORIENTATION_OFFSET.matrix()).dot(hpr_rate_vec)
    hpr_rate_vec[0], hpr_rate_vec[2] = hpr_rate_vec[2], hpr_rate_vec[0]
    return hpr_rate_vec


def get_accel_rate_vec(auv_orientation: Quaternion, hpr_accel_vec: numpy.ndarray) -> numpy.ndarray:
    """Returns angular acceleration in the format np.array([heading, pitch, roll]) 
    in deg/s^2 transformed to the AUV reference frame with a gravitational offset.

    `auv_orientation` is the AUV's current orientation is the untransformed 
    hpr acceleration.

    """
    accel_vec = numpy.array(
        [accelx_var.get(), accely_var.get(), accelz_var.get()])
    accel_vec = numpy.eye(3).dot(
        GX_ORIENTATION_OFFSET.matrix()).dot(accel_vec)

    # offset gravity, rotate the gravity vector by the auv_orientation
    rotation = auv_orientation.conjugate()
    gravity_vec = numpy.array([0, 0, 9.81])
    gravity_vec = rotation.matrix().dot(gravity_vec)
    # TODO: offset acceleration due to angular acceleration

    return accel_vec + gravity_vec


def get_velocity_vec(hpr_deg_rate_vec, sub_quat) -> numpy.ndarray:
    """Returns the auv velocity in the format numpy.array([vel_x, vel_y])"""
    beams_good = sum([not var.get() for var in dvl_beam_vars]) >= 2
    if not vehicle_conf.dvl_present or not beams_good:
        return None, None, None

    vel_vec = numpy.array([-velx_var.get(), -vely_var.get(), -velz_var.get()])

    # rotate DVL velocities - swap x and y zxis
    vel_vec[0], vel_vec[1] = vel_vec[1], -vel_vec[0]
    # invert z axis so we measure depth rate instead of altitude rate
    vel_vec[2] *= -1

    if vehicle_conf.dvl_reversed:
        vel_vec[0] *= -1
        vel_vec[1] *= -1

    # offset velocity to account for misaligned DVL position around center of
    # rotation
    skew_factor = vehicle_conf.dvl_offset * 2 * math.pi / 360
    vel_vec[1] -= skew_factor * hpr_deg_rate_vec[0]

    vel_body_frame = Quaternion(hpr=(0, 0, 180)) * vel_vec
    hpr = sub_quat.hpr()
    vel_spitz_frame = (Quaternion(hpr=(hpr[0] % 360, 0, 0)).conjugate() * sub_quat) \
        * vel_body_frame
    return vel_spitz_frame


def create_position_filters(dt):
    x0 = cp.zeros(7)
    P0 = cp.eye(7)

    # vel += vel * drag + accel
    # accel = accel
    F = cp.array(
        [
            [0.99, dt, 0, 0, 0, 0, 0],  # vel = vel + dt * accel
            [0, 1, 0, 0, 0, 0, 0],  # accel = accel
            [0, 0, 0.99, dt, 0, 0, 0],  # vely
            [0, 0, 0, 1, 0, 0, 0],  # accely
            # pos_z = pos + dt * pos + 0.5 dt ^ 2 * accel
            [0, 0, 0, 0, 1, dt, 0.5 * dt ** 2],
            [0, 0, 0, 0, 0, 0.99, dt],  # velz
            [0, 0, 0, 0, 0, 0, 1],  # accelz
        ]
    )

    # we're able to measure [force_x, force_y, force_z] in newtons, the force
    # causes an acceleration. F=ma, a = F/m
    weight_kg = vehicle_conf.gravity_force / 9.81
    G = cp.array(
        [[0, 0, 0],
         [dt/weight_kg, 0, 0],
         [0, 0, 0],
         [0, dt/weight_kg, 0],
         [0, 0, 0],
         [0, 0, 0],
         [0, 0, dt/weight_kg]]
    )

    # we obtain every measurement but position for x and y
    dvl_zn_size = 7
    dvl_H_matrix = cp.array(
        [[1, 0, 0, 0, 0, 0, 0],  # vel_x
         [0, 1, 0, 0, 0, 0, 0],  # accel_x
         [0, 0, 1, 0, 0, 0, 0],  # vel_y
         [0, 0, 0, 1, 0, 0, 0],  # accel_y
         [0, 0, 0, 0, 1, 0, 0],  # pos_z
         [0, 0, 0, 0, 0, 1, 0],  # vel_z
         [0, 0, 0, 0, 0, 0, 1]]  # accel_z
    )
    dvl_R_matrix = cp.array(
        [[0.005, 0, 0, 0, 0, 0, 0],  # vel_x
         [0, 0.2, 0, 0, 0, 0, 0],  # accel_x
         [0, 0, 0.005, 0, 0, 0, 0],  # vel_y
         [0, 0, 0, 0.2, 0, 0, 0],  # accel_x
         [0, 0, 0, 0, 0.01, 0, 0],  # pos_z
         [0, 0, 0, 0, 0, 1, 0],  # vel_z
         [0, 0, 0, 0, 0, 0, 1]]  # accel_z
    )

    nodvl_zn_size = 4
    nodvl_H_matrix = cp.array(
        [[0, 1, 0, 0, 0, 0, 0],  # accel_x
         [0, 0, 0, 1, 0, 0, 0],  # accel_y
         [0, 0, 0, 0, 1, 0, 0],  # pos_z
         [0, 0, 0, 0, 0, 0, 1]]  # accel_z
    )
    nodvl_R_matrix = cp.array(
        [[0.1, 0, 0, 0],  # accel_x
         [0, 0.1, 0, 0],  # accel_x
         [0, 0, 0.01, 0],  # pos_z
         [0, 0, 0, 1]]  # accel_z
    )

    # simulation covariance
    # idea is that we can't determine drag/accel, so we don't
    # trust the simulation step
    Q = cp.array(
        [[1, 0, 0, 0, 0, 0, 0],
         [0, 1, 0, 0, 0, 0, 0],
         [0, 0, 1, 0, 0, 0, 0],
         [0, 0, 0, 1, 0, 0, 0],
         [0, 0, 0, 0, 1, 0, 0],
         [0, 0, 0, 0, 0, 1, 0],
         [0, 0, 0, 0, 0, 0, 1]]
    ) * 0.3

    position_filter_dvl = LinearKalmanFilter(
        x0,
        P0,
        dvl_H_matrix,
        dvl_zn_size,
        dvl_R_matrix,
        F,
        G,
        3,
        Q
    )

    position_filter_nodvl = LinearKalmanFilter(
        x0,
        P0,
        nodvl_H_matrix,
        nodvl_zn_size,
        nodvl_R_matrix,
        F,
        G,
        3,
        Q
    )
    return position_filter_dvl, position_filter_nodvl


def create_orientation_filter(dt):
    h = get_heading_quat()

    x0 = cp.array([h[0], h[1], h[2], h[3], 0, 0, 0])
    P0 = cp.identity(7)
    H = cp.identity(7)
    zn_size = 7
    R = cp.array([[90, 0, 0, 0, 0, 0, 0],
                  [0, 90, 0, 0, 0, 0, 0],
                  [0, 0, 90, 0, 0, 0, 0],
                  [0, 0, 0, 90, 0, 0, 0],
                  [0, 0, 0, 0, 1.5, 0, 0],
                  [0, 0, 0, 0, 0, 1.7, 0],
                  [0, 0, 0, 0, 0, 0, 1.5]])

    # we currently don't apply angular velocities to quaternions, so our
    # transition function is just the identity
    orientation_filter = LinearKalmanFilter(
        x0,
        P0,
        H,
        zn_size,
        R
    )

    return orientation_filter


def angle_clamp(x, clamp):
    if x < -clamp:
        return x + clamp
    if x > clamp:
        return x - clamp
    return x


if __name__ == '__main__':
    dt = 1/20

    # orientation in the AUV reference frame
    orientation_filter = create_orientation_filter(dt)
    orientation_filter.predict()

    # position in the AUV reference frame
    dvl_filter, nodvl_filter = create_position_filters(dt)
    updated_filter = nodvl_filter  # the filter updated with measurement
    starved_filter = dvl_filter   # the filter not updated with measurement
    updated_filter.predict()

    old_hpr_rate = get_hpr_rate_vec()
    while True:
        start_time = time.time()

        # Step 1: predict
        orientation_filter.predict()

        cpf = shm.control_passive_forces.get()
        cio = shm.control_internal_outs.get()

        updated_filter.predict(
            cp.array([cpf.f_x + cio.f_x, cpf.f_y + cio.f_y, cpf.f_z + cio.f_z]))

        # Step 2: update
        # update orientation filter

        heading_quat = get_heading_quat()
        q0, q1, q2, q3 = heading_quat.q
        hpr_rate = get_hpr_rate_vec()
        hpr_accel_rate = (hpr_rate - old_hpr_rate) / dt
        old_hpr_rate = hpr_rate

        orientation_measurement = cp.array([q0, q1, q2, q3,
                                            hpr_rate[0], hpr_rate[1], hpr_rate[2]])
        orientation_filter.update(orientation_measurement)

        # update position filter
        ax, ay, az = (0,0,0) # get_accel_rate_vec(heading_quat, hpr_accel_rate)
        vx, vy, vz = get_velocity_vec(hpr_rate, heading_quat)
        depth = depth_var.get() - depth_offset_var.get()

        if vx is None:
            # we use the filter without velocity measurements
            measurements = cp.array([ax, ay, depth, az])
            updated_filter = nodvl_filter
            starved_filter = dvl_filter
            dvl_flag = False
        else:
            # we use the filter with velocity measurements
            measurements = cp.array([vx, ax, vy, ay, depth, vz, az])
            updated_filter = dvl_filter
            starved_filter = nodvl_filter
            dvl_flag = True

        updated_filter.update(measurements)
        # sync the filters
        starved_filter.xn = updated_filter.xn
        starved_filter.Pn = updated_filter.Pn

        # measure and update shm
        x_orientation, p_orientation = orientation_filter.measure()
        h_out, p_out, r_out = Quaternion(cp.asnumpy(x_orientation[:4])).hpr()
        x_position, p_position = updated_filter.measure()

        kalman_group = shm.kalman.get()
        old_depth = kalman_group.depth
        kalman_group.heading = h_out % 360
        kalman_group.pitch = angle_clamp(p_out, 180)
        kalman_group.roll = angle_clamp(r_out, 180)
        kalman_group.q0 = x_orientation[0]
        kalman_group.q1 = x_orientation[1]
        kalman_group.q2 = x_orientation[2]
        kalman_group.q3 = x_orientation[3]
        kalman_group.heading_rate = cp.radians(x_orientation[4])
        kalman_group.pitch_rate = cp.radians(x_orientation[5])
        kalman_group.roll_rate = cp.radians(x_orientation[6])

        kalman_group.velx = x_position[0]
        kalman_group.accelx = x_position[1]
        kalman_group.vely = x_position[2]
        kalman_group.accely = x_position[3]
        kalman_group.depth = x_position[4]
        kalman_group.velz = x_position[5] if dvl_flag else (
            kalman_group.depth - old_depth) / dt
        kalman_group.accelz = x_position[6]
        kalman_group.depth_rate = kalman_group.velz

        c = cp.cos(math.radians(kalman_group.heading))
        s = cp.sin(math.radians(kalman_group.heading))

        north_vel = kalman_group.velx * c - kalman_group.vely * s
        east_vel = kalman_group.velx * s + kalman_group.vely * c

        kalman_group.north += north_vel * dt
        kalman_group.east += east_vel * dt

        # print(f"North={kalman_group.north:7.4f} East={kalman_group.east:7.4f} VelX={kalman_group.velx:7.4f} VelY = {kalman_group.vely:7.4f}, AccelX={kalman_group.accelx:7.4f}, AccelY={kalman_group.accelx:7.4f}, AccelZ={kalman_group.accelz:7.4f}, Heading={kalman_group.heading:7.4f}, HeadingRate={kalman_group.heading_rate:7.4f}, Pitch={kalman_group.pitch:7.4f}, Roll={kalman_group.roll:7.4f}",end='\r')
        shm.kalman.set(kalman_group)

        elapsed_time = time.time() - start_time
        if elapsed_time < dt:
            time.sleep(dt - elapsed_time)
        else:
            print(
                f'error, kalman tick performed slower than {int(1/dt)} hz. Current tick ran at {1/elapsed_time} hz')
