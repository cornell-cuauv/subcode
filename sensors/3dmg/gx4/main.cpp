#include <math.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>

#include "libshm/c/shm.h"
#include "commoninit.h"

/*
 * GX4 CUAUV Interface
 * Uses LORD Microstrain 3DM-GX4 SDK
 *
 * Jeff Heidel 2014
 *
 * ---
 *
 * At present we are just using AHRS (IMU) data. The "Estimation Filter" data
 * has too slow of a heading rise time for my comfort. Perhaps we can configure
 * something to get around this problem. Someone could ask Microstrain?
 *
 * See the auv-3dmgx4-calibrate program for calibration utilities.
 */

mip_interface device_interface;
struct gx4 shmgx4;

#define RAD_TO_DEG(X) (X * 180. / M_PI)
#define G_GRAV  9.80665
#define GAUSS_TO_MICROTESLA 100

/*
 * Called by the SDK when a new AHRS packet is received from the gx4
 * Packets specified during initialization will be provided at regular intervals
 */
void ahrs_packet_callback(void *usr_ptr, uint8_t *packet, uint16_t packet_size, uint8_t callback_type) {
    mip_field_header *field_header;
    uint8_t *field_data;
    uint16_t field_offset = 0;

    mip_ahrs_euler_angles *euler;
    mip_ahrs_scaled_accel *accel;
    mip_ahrs_scaled_gyro *gyro;
    mip_ahrs_scaled_mag *mag;
    mip_ahrs_quaternion *quat;

    //mip_filter_attitude_euler_angles *euler_ef;
    //mip_filter_attitude_quaternion *quat_ef;

    switch (callback_type) {
        case MIP_INTERFACE_CALLBACK_VALID_PACKET:
            while (mip_get_next_field(packet, &field_header, &field_data, &field_offset) == MIP_OK) {
                switch (field_header->descriptor) {

                    /*case MIP_FILTER_DATA_ATT_EULER_ANGLES:
                        euler_ef = (mip_filter_attitude_euler_angles*)field_data;
                        mip_filter_attitude_euler_angles_byteswap(euler_ef);
                        shmgx4.heading = RAD_TO_DEG(euler_ef->yaw);
                        shmgx4.pitch = RAD_TO_DEG(euler_ef->pitch);
                        shmgx4.roll = RAD_TO_DEG(euler_ef->roll);
                        if (shmgx4.heading < 0) shmgx4.heading += 360.;
                        break;*/

                    case MIP_AHRS_DATA_EULER_ANGLES:
                        euler = (mip_ahrs_euler_angles*) field_data;
                        mip_ahrs_euler_angles_byteswap(euler);
                        shmgx4.heading = RAD_TO_DEG(euler->yaw);
                        shmgx4.pitch = RAD_TO_DEG(euler->pitch);
                        shmgx4.roll = RAD_TO_DEG(euler->roll);
                        if (shmgx4.heading < 0) shmgx4.heading += 360.;
                        break;

                    case MIP_AHRS_DATA_GYRO_SCALED:
                        gyro = (mip_ahrs_scaled_gyro*) field_data;
                        mip_ahrs_scaled_gyro_byteswap(gyro);
                        shmgx4.ratex = RAD_TO_DEG(gyro->scaled_gyro[0]);
                        shmgx4.ratey = RAD_TO_DEG(gyro->scaled_gyro[1]);
                        shmgx4.ratez = RAD_TO_DEG(gyro->scaled_gyro[2]);
                        break;

                    case MIP_AHRS_DATA_ACCEL_SCALED:
                        accel = (mip_ahrs_scaled_accel*) field_data;
                        mip_ahrs_scaled_accel_byteswap(accel);
                        shmgx4.accelx = accel->scaled_accel[0] * G_GRAV;
                        shmgx4.accely = accel->scaled_accel[1] * G_GRAV;
                        shmgx4.accelz = accel->scaled_accel[2] * G_GRAV;
                        break;

                    case MIP_AHRS_DATA_MAG_SCALED:
                        mag = (mip_ahrs_scaled_mag *) field_data;
                        mip_ahrs_scaled_mag_byteswap(mag);
                        shmgx4.mag_x = mag->scaled_mag[0] * GAUSS_TO_MICROTESLA;
                        shmgx4.mag_y = mag->scaled_mag[1] * GAUSS_TO_MICROTESLA;
                        shmgx4.mag_z = mag->scaled_mag[2] * GAUSS_TO_MICROTESLA;
                        break;

                    case MIP_AHRS_DATA_QUATERNION:
                        quat = (mip_ahrs_quaternion*) field_data;
                        mip_ahrs_quaternion_byteswap(quat);
                        shmgx4.q0 = quat->q[0];
                        shmgx4.q1 = quat->q[1];
                        shmgx4.q2 = quat->q[2];
                        shmgx4.q3 = quat->q[3];
                        break;

                    default:
                        printf("Received unexpected descriptor 0x%02X\n", field_header->descriptor);
                        break;
                }
            }
            shmgx4.packets_received++;
            break;

        case MIP_INTERFACE_CALLBACK_CHECKSUM_ERROR:
            fprintf(stderr, "Packet checksum failure!\n");
            shmgx4.packets_corrupted++;
            break;

        case MIP_INTERFACE_CALLBACK_TIMEOUT:
            fprintf(stderr, "Packet timeout!\n");
            shmgx4.packets_timeout++;
            break;

        default:
            break;
    }

    shm_setg(gx4, shmgx4);
}

/*
 * MAIN
 */
int main(int argc, char **argv) {
    printf("== LORD Microstrain 3DM-GX4 daemon ==\n");

    if (argc != 2) {
        printf("Usage: auv-3dmgx4d [serial port]\n");
        return 1;
    }

    if (gx4_common_init(argv[1], device_interface)) {
        fprintf(stderr, "Unable to initialize gx4\n");
        return 1;
    }

    // Initialize AUV shared memory interface
    shm_init();
    shmgx4.packets_received = 0;
    shmgx4.packets_corrupted = 0;
    shmgx4.packets_timeout = 0;

    uint8_t descriptor = MIP_AHRS_DATA_SET;

    // Setup data callback
    if (mip_interface_add_descriptor_set_callback(
          &device_interface, descriptor, NULL, &ahrs_packet_callback
         ) != MIP_INTERFACE_OK) {
        fprintf(stderr, "Callback initialization failed\n");
        return 1;
    }

    // Setup desired AHRS packet data
    uint8_t data_stream_format_descriptors[10];
    uint16_t data_stream_format_decimation[10];
    uint8_t data_stream_format_num_entries;

    float rate = 1000 / 100; // 100 HZ
    uint8_t vals[] = { MIP_AHRS_DATA_EULER_ANGLES,
                       MIP_AHRS_DATA_GYRO_SCALED,
                       MIP_AHRS_DATA_ACCEL_SCALED,
                       MIP_AHRS_DATA_MAG_SCALED,
                       MIP_AHRS_DATA_QUATERNION };
    data_stream_format_num_entries = 5;

    for (int i = 0; i < data_stream_format_num_entries; i++) {
        data_stream_format_descriptors[i] = vals[i];
        data_stream_format_decimation[i] = rate;
    }

    while (mip_3dm_cmd_ahrs_message_format(&device_interface, MIP_FUNCTION_SELECTOR_WRITE,
                &data_stream_format_num_entries, data_stream_format_descriptors,
                data_stream_format_decimation) != MIP_INTERFACE_OK);

    // Enable AHRS data stream
    uint8_t enable = 0x01;
    while (mip_3dm_cmd_continuous_data_stream(&device_interface, MIP_FUNCTION_SELECTOR_WRITE,
               MIP_3DM_AHRS_DATASTREAM, &enable) != MIP_INTERFACE_OK);

    printf("Data streaming now active...\n");
    while (true) {
        // Have SDK read port & handle new data
        mip_interface_update(&device_interface);
        usleep(0); // yield
    }

    printf("Exit!\n");
    return 0;
}
