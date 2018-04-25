#ifndef GX4COMMONINIT_
#define GX4COMMONINIT_

#include <cctype>
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>

#include "SDK/Include/mip_sdk.h"
#include "SDK/Include/byteswap_utilities.h"
#include "SDK/Include/mip_gx4_imu.h"
#include "SDK/Include/mip_sdk_ahrs.h"
#include "SDK/Include/mip_gx4_25.h"
#include "mip_sdk_user_functions.h"

#define DEFAULT_PACKET_TIMEOUT_MS  1000 //milliseconds

#define BAUD_RATE   115200

/*
 * Initializes the GX4 on the provided serial port
 * Puts gx4 into idle mode and attempts pinging; also runs startup tests
 * Information about the IMU is also printed
 */
int gx4_common_init(char *serial_port, mip_interface &device_interface) {

    // Copy the "base" path of the serial port (i.e. "/dev/ttyUSB_gemini_" to the
    // SDK interface using an extern string. This horrible hack is necessary since
    // the SDK only takes an integer to represent a serial port (windows-based code,
    // anyone?)
    char* src = serial_port;;
    char* dst = serial_port_prefix;
    while (*src) {
        if (isdigit(*src)) break;
        *dst++ = *src++;
    }
    uint32_t com_port;
    com_port = atoi(src);

    //Initialize the interface to the device
    if (mip_interface_init(com_port, BAUD_RATE, &device_interface, DEFAULT_PACKET_TIMEOUT_MS) != MIP_INTERFACE_OK) {
        fprintf(stderr, "Unable to initialize 3dmg-gx4\n");
        return 1;
    }

    // Set device to idle
    while (mip_base_cmd_idle(&device_interface) != MIP_INTERFACE_OK);

    // Ping device
    while (mip_base_cmd_ping(&device_interface) != MIP_INTERFACE_OK);

    // Retrieve & print device information
    base_device_info_field device_info;
    char str[20] = {0};
    while (mip_base_cmd_get_device_info(&device_interface, &device_info) != MIP_INTERFACE_OK);
    #define PRINT_INFO(TXT, FIELD)\
    memcpy(str, device_info.FIELD, BASE_DEVICE_INFO_PARAM_LENGTH*2);\
    printf("%s\t=>%s\n", TXT, str);
    PRINT_INFO("Model Name", model_name);
    PRINT_INFO("Model Number", model_number);
    PRINT_INFO("Serial Number", serial_number);

    // Run a quick systems test to make sure everything is working properly!
    uint32_t bit_result;
    while (mip_base_cmd_built_in_test(&device_interface, &bit_result) != MIP_INTERFACE_OK);
    if (bit_result != 0) {
        fprintf(stderr, "Built-in system test failed! Got error code 0x%08X\n.", bit_result);
        fprintf(stderr, "This could indicate hardware failure. Consult the manual.\n");
        return 1;
    }

    mip_complementary_filter_settings settings;
    settings.up_compensation_enable = 1;
    settings.north_compensation_enable = 0;
    settings.up_compensation_time_constant = 1.0;
    settings.north_compensation_time_constant = 500.0;

    mip_3dm_cmd_complementary_filter_settings(&device_interface, 0x01,
                                               &settings);

    return 0;
}

#endif // GX4COMMONINIT

