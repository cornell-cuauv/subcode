#include <stdint.h>
#include <stdio.h>
#include "packetdef.h"
#include "../../serial/serial.h"
#include <netinet/in.h>
#include <exception>
#include <signal.h>
#include "libshm/c/shm.h"

#define CMD_GYRO_STAB_EULER 0x0E
#define CMD_INSTANTANEOUS_EULER 0x0D
#define CMD_RAW_SENSOR_BITS 0x01
#define CMD_GYRO_STAB_VECTOR 0x02
#define CMD_INSTANTANEOUS_VECTOR 0x03
#define CMD_INSTANTANEOUS_QUAT 0x04
#define CMD_GYRO_STAB_QUAT 0x05
#define CMD_CAPTURE_GYRO_BIAS 0x06
#define BAUD_RATE 38400
#define TIMEOUT 100000
#define ACCELGAINSCALE 8500
#define GYROGAINSCALE 10000

// EXPERIMENTAL:
//Use this if you want non-gyro stabilised output
// #define INSTANTANEOUS

// Gyro defaults to filtered (estimating gyro biases is useful)
// #define INSTANTANEOUS_GYRO

using namespace sensorserial;
int16_t accel_gain_scale = 8500;
int16_t gyro_gain_scale = 10000;

const double degrees_transform = 360./65536;
double accel_transform;
double angrate_transform;
double quat_transform = 8192.;

bool calibrate = false;
bool remove_calibrate = false;
bool tare = false;
bool remove_tare = false;
bool capgyro = false;

bool stop_calibrate = false;

void handle_sig(int sig) {
    if(calibrate && stop_calibrate == false) {
        stop_calibrate = true;
    }
    else {
        exit(0);
    }
}

//Checksum is calculated by adding up the signed 16-bit numbers
//before the last 16-bit quantity, which is the checksum.
bool calcChecksum(uint8_t *buf, size_t size) {
    size_t checksum_index = (size/2) - 1;
    int16_t sum = buf[0];
    int16_t *casted_buf = (int16_t*)(buf+1);
    for(unsigned int i=0; i<checksum_index; i++) {
        //Serial comes in big endian. We must convert to our
        //host endianness.
        casted_buf[i] = ntohs(casted_buf[i]);
        sum += casted_buf[i];
    }
    return sum == (int16_t)ntohs(casted_buf[checksum_index]);
}

// 'ser' must be an opened serial port, 'cmd' is a 1-byte cmd to send to the 
// 3dmg, 'buf' is a buffer to put the returned data (of expected length 'size') // into and must be at least 'size' in length
bool grabPacket(SerialPort *ser, uint8_t *cmd, size_t cmd_size, uint8_t *buf, size_t size, bool timeout=true) 
{
    ser->writeSer(cmd, cmd_size);

    ssize_t nRead;
    if (timeout)
        nRead = ser->readnWithTimeout(buf, size, TIMEOUT);
    else
        nRead = ser->readSer(buf, size);

    if(nRead == -1){
        fprintf(stderr, "Error reading serial");
    }
    else if( (size_t)nRead != size || nRead % 2 == 0) {
        fprintf(stderr, "Packet size %zu does not match expected size %zu!\n", nRead, size);
    }
    else if(buf[0] != cmd[0]) {
        fprintf(stderr, "Packet header wrong!\n");
    }
    else if(!calcChecksum(buf, size)) {
        fprintf(stderr, "Checksum failed!\n");
    }
    else {
        return true;
    }

    ser->flushBuffers();
    return false;
}

int main(int argc, char **argv) {
    if (argc > 3 || argc < 2 || (argc == 3 && strncmp(argv[1], "-c", 2) != 0
                                           && strncmp(argv[1], "-t", 2) != 0
                                           && strncmp(argv[1], "-g", 2) != 0
                                           && strncmp(argv[1], "-rc", 2) != 0
                                           && strncmp(argv[1], "-rt", 2) != 0)){
        printf("Usage:\tauv-3dmgd [-c(alibration)] [-t(are)] SERIAL_PORT\n");
        printf("\tauv-3dmg -rt to remove tare\n");
        printf("\tauv-3dmg -rc to remove calibration\n");
        printf("\tauv-3dmg -g to capture gyro bias\n");
        return -1;
    }

    shm_init();

    calibrate = strncmp(argv[1], "-c", 2) == 0;
    capgyro = strncmp(argv[1], "-g", 2) == 0;
    remove_calibrate = strncmp(argv[1], "-rc", 3) == 0;
    tare = strncmp(argv[1], "-t", 2) == 0;
    remove_tare = strncmp(argv[1], "-rt", 3) == 0;

    signal(SIGINT, handle_sig);

    SerialPort *serial_port;

    try {
        serial_port = new SerialPort(argv[argc-1], BAUD_RATE);
    } catch (std::exception& e) {
        fprintf(stderr, "Port %s not found\n", argv[argc-1]);
        return -1;
    }

    uint8_t buf[256];
    gyro_stab_euler_packet *epkt = (gyro_stab_euler_packet *)&buf;
    gyro_stab_vector_packet *vpkt = (gyro_stab_vector_packet *)&buf;
    eeprom_read_packet *rpkt = (eeprom_read_packet *)&buf;
    quat_packet *qpkt = (quat_packet *)&buf;

    struct threedmg sharedVars;

    uint8_t cmd[256];

    if (calibrate) {
        printf("2D Calibration...\nPlease rotate the vehicle many times (at least 720 degrees) and press Ctrl-C when done\n");
        printf("Be sure to rotate the vehicle in both directions!");
        cmd[0] = 0x40;
        serial_port->writeSer(cmd, 1);
        cmd[0] = 0x41;
        while(!stop_calibrate) {
            usleep(5000);
            serial_port->writeSer(cmd, 1);
        }
        printf("Calculating parameters and writing to EEPROM\n");
        cmd[0] = 0x42; cmd[1] = 0x71; cmd[2] = 0x3E; cmd[3] = 0x01; cmd[4] = 0x01; cmd[5] = 0xF4;
        serial_port->writeSer(cmd, 6);
        exit(0);
    }
    else if (capgyro) {
        printf("Capturing gyro bias...\n");
        printf("Please keep the vehicle ABSOLUTELY still\n");
        cmd[0] = CMD_CAPTURE_GYRO_BIAS;
        serial_port->writeSer(cmd, 1);
        printf("Gyro bias captured\n");
        exit(0);
    }
    else if (tare) {
        printf("Taring the coordinate system...\n");
        printf("This may take a few seconds, please keep the vehicle still\n");
        cmd[0] = 0x0F; cmd[1] = 0xC1; cmd[2] = 0xC3; cmd[3] = 0xC5;
        if (grabPacket(serial_port, cmd, 4, buf,
            sizeof(tare_read_packet), false)) {
                printf("Coordinate system tared succesfully.\n");
        }
        exit(0);
    }

    else if (remove_tare) {
        printf("Removing coordinate system tare...\n");
        cmd[0] = 0x11; cmd[1] = 0xC1; cmd[2] = 0xC3; cmd[3] = 0xC5;
        if (grabPacket(serial_port, cmd, 4, buf,
            sizeof(tare_read_packet), false)) {
                printf("Coordinate system tare removed succesfully.\n");
        }
        exit(0);
    }

    else if (remove_calibrate) {
        printf("Sending command to remove calibration...\n");
        cmd[0] = 0x40; cmd[1] = 0x71; cmd[2] = 0x3E;
        serial_port->writeSer(cmd, 3);
        printf("Done.\n");
        exit(0);
    }

    //Read accel gain scale
    cmd[0] = 0x28; cmd[1] = 0x00; cmd[2] = 0xE6;
    while(!grabPacket(serial_port, cmd, 3, buf, sizeof(eeprom_read_packet))) {
        fprintf(stderr, "Failing to read accel gain scale, retrying\n");
    }
    accel_gain_scale = rpkt->Data;
    printf("Accel Gain Scale: %d\n", accel_gain_scale);
    accel_transform = 32768000./accel_gain_scale / 9.8;
    
    //Read gyro gain scale
    cmd[0] = 0x28; cmd[1] = 0x00; cmd[2] = 0x82;
    while(!grabPacket(serial_port, cmd, 3, buf, sizeof(eeprom_read_packet))) {
        fprintf(stderr, "Failing to read gyro gain scale, retrying\n");
    }
    gyro_gain_scale = rpkt->Data;
    printf("Gyro Gain Scale: %d\n", gyro_gain_scale);
    angrate_transform = 32768000./gyro_gain_scale / (180./3.14159);

    while (1) {
        // Get gyro-stabilized Euler angles
#ifdef INSTANTANEOUS
        cmd[0] = CMD_INSTANTANEOUS_EULER;
#else
        cmd[0] = CMD_GYRO_STAB_EULER;
#endif
        if (grabPacket(serial_port, cmd, 1, buf, sizeof(gyro_stab_euler_packet))) {
            sharedVars.heading = epkt->Yaw * degrees_transform;
            sharedVars.pitch = epkt->Pitch * degrees_transform;
            sharedVars.roll = epkt->Roll * degrees_transform;

            sharedVars.clk_ticks = (uint16_t)(epkt->TimeTicks);
        }

#ifdef INSTANTANEOUS_GYRO
        cmd[0] = CMD_INSTANTANEOUS_VECTOR;
#else
        cmd[0] = CMD_GYRO_STAB_VECTOR;
#endif

        // Get gyro-stabilized acceleration and rotation data
        if (grabPacket(serial_port, cmd, 1, buf, sizeof(gyro_stab_vector_packet))) {
            sharedVars.accelx = vpkt->StabAccel_X / accel_transform;
            sharedVars.accely = vpkt->StabAccel_Y / accel_transform;
            sharedVars.accelz = vpkt->StabAccel_Z / accel_transform;

            sharedVars.heading_rate = vpkt->CompAngRate_Z / angrate_transform;
            sharedVars.pitch_rate = vpkt->CompAngRate_Y / angrate_transform;
            sharedVars.roll_rate = vpkt->CompAngRate_X / angrate_transform;
            
            sharedVars.clk_ticks = (uint16_t)(vpkt->TimeTicks);
        }

#ifdef INSTANTANEOUS
        cmd[0] = CMD_INSTANTANEOUS_QUAT;
#else
        cmd[0] = CMD_GYRO_STAB_QUAT;
#endif
        if (grabPacket(serial_port, cmd, 1, buf, sizeof(quat_packet))) {
            // TODO BIG ENDIAN VS LITTLE ENDIAN?!
            // MSB comes first from the 3dmg
            sharedVars.q0 = qpkt->Q0 / quat_transform;
            sharedVars.q1 = qpkt->Q1 / quat_transform;
            sharedVars.q2 = qpkt->Q2 / quat_transform;
            sharedVars.q3 = qpkt->Q3 / quat_transform;
            sharedVars.clk_ticks = (uint16_t)(qpkt->TimeTicks);
        }

        /*// Get raw sensor bits for debugging
        cmd[0] = CMD_RAW_SENSOR_BITS;
        int16_t gyro_x, gyro_y, gyro_z;
        if (grabPacket(serial_port, cmd, 1, buf, sizeof(gyro_stab_vector_packet))) {
            gyro_x = vpkt->CompAngRate_X;
            gyro_y = vpkt->CompAngRate_Y;
            gyro_z = vpkt->CompAngRate_Z;
            printf("%d %d %d\n", gyro_x, gyro_y, gyro_z);
        }*/

        shm_setg(threedmg, sharedVars);

    }
    delete serial_port;
}
