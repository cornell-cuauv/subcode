#include <stdint.h>

#ifndef PACKDEF_H
#define PACKDEF_H


struct __attribute__ ((__packed__)) gyro_stab_euler_packet
{
	uint8_t Header;

	int16_t Roll;
	int16_t Pitch;
	int16_t Yaw;
    
	int16_t TimeTicks;

	int16_t Checksum;
};

struct __attribute__ ((__packed__)) gyro_stab_vector_packet
{
    uint8_t Header;

    int16_t StabMagField_X;
    int16_t StabMagField_Y;
    int16_t StabMagField_Z;

	int16_t StabAccel_X;
	int16_t StabAccel_Y;
	int16_t StabAccel_Z;

	int16_t CompAngRate_X;
	int16_t CompAngRate_Y;
	int16_t CompAngRate_Z;

    int16_t TimeTicks;

    int16_t Checksum;
};

struct __attribute__ ((__packed__)) quat_packet
{
    uint8_t Header;

    int16_t Q0;
    int16_t Q1;
    int16_t Q2;
    int16_t Q3;

    int16_t TimeTicks;
    int16_t Checksum;
};

struct __attribute__ ((__packed__)) eeprom_read_packet
{
    uint8_t Header;

    int16_t Data;
    
    int16_t TimeTicks;

    int16_t Checksum;
};

struct __attribute__ ((__packed__)) tare_read_packet
{
    uint8_t Header;
    int16_t TimeTicks;
    int16_t Checksum;
};
#endif
