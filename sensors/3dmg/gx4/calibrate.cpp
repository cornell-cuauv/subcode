#include <math.h>
#include <stdio.h>
#include <stdint.h>
#include <iostream>
#include "commoninit.h"

mip_interface device_interface;

/*
 * LORD Microstrain 3DM-GX4 Calibration Utility
 * Provides basic calibration functions including:
 *  - Gyro Bias Calibration
 *  - Taring Functionality
 *
 * For more device setup / hard & soft iron calibration:
 *  - Download Microstrain's MIP software
 *    http://www.microstrain.com/inertial/3dm-gx4-25
 *  - Use these instructions to access the serial port from a Windows laptop
 *    https://cuauv.org/wiki/Software/usbip
*/

using namespace std;

#define RAD_TO_DEG(X) (X * 180. / M_PI)
#define DEG_TO_RAD(X) (X * M_PI / 180.)

/*
 * MAIN
 */
int main(int argc, char **argv) {
    char resp;

    printf("== LORD Microstrain 3DM-GX4 Calibration Utility ==\n");

    if (argc != 2) {
        printf("Usage: auv-3dmgx4-calibrate [serial port]\n");
        return 1;
    }

    if (gx4_common_init(argv[1], device_interface)) {
        fprintf(stderr, "Unable to initialize gx4\n");
        return 1;
    }

    // *** Gyro bias ***
   
    cout << "Do you wish to adjust the gyro bias? [y/N] "; 
    cin >> resp;
    if (!cin.fail() && resp == 'y') {

        cout << "Select an option:" << endl << 
            "\t1) Reset gyro bias to factory defaults" << endl << 
            "\t2) Capture gyro bias vector" << endl << " > "; 
        cin >> resp;

        if (!cin.fail()) {
            switch(resp) {
                case '1':
                    // Reset gyro bias
                    while (mip_3dm_cmd_gyro_bias(&device_interface, MIP_FUNCTION_SELECTOR_LOAD_DEFAULT, NULL) != MIP_INTERFACE_OK);
                    cout << "Gyro bias has been reset to default settings." << endl;
                    break;

                case '2':
                    {
                        // Calibrate gyro bias
                        uint16_t duration = 20000; //milliseconds
                        cout << "About to perform gyro capture. " << endl <<
                            "Make sure the GX4 has been running for at least 3 minutes so it has warmed up." << endl <<
                            "Calibration will take " << duration/1000 << " seconds." << endl <<
                            "MAKE SURE THE SUB REMAINS ABSOLUTELY STATIONARY." << endl << endl;
                        // cout << "[Press enter to continue]";
                        // cin >> resp;
                        float bias_vector[3] = {0, 0, 0};
                        cout << "ENTER" << endl;
                        // int res = mip_3dm_cmd_capture_gyro_bias(&device_interface, duration, bias_vector);
                        // printf("Gyro bias capture response: %d", res);
                        while (mip_3dm_cmd_capture_gyro_bias(&device_interface, duration, bias_vector) != MIP_INTERFACE_OK);
                        printf("Gyro Bias Captured:\nbias_vector[0] = %f\nbias_vector[1] = %f\nbias_vector[2] = %f\n\n", 
                                bias_vector[0], bias_vector[1], bias_vector[2]);
                        cout << endl;
                        cout << "Do you wish to save the gyro bias to EEPROM? [Y/n] ";
                        cin >> resp;
                        if (cin.fail() || resp != 'n') {
                            while (mip_3dm_cmd_gyro_bias(&device_interface, MIP_FUNCTION_SELECTOR_STORE_EEPROM, 
                                        bias_vector) != MIP_INTERFACE_OK);
                            cout << "Saved." << endl;
                        }
                    }
                    break;

                default:
                    cout << "Option " << resp << " not recognized." << endl;
                    break;
            }
        }
    }

    // *** Taring ***
    cout << "Do you wish to perform a tare operation? (Recalibrating the sensor reference frame) [y/N] ";
    cin >> resp;
    if (!cin.fail() && resp == 'y') {

        float readback_angles[3] = {0};
        while (mip_filter_sensor2vehicle_tranformation(&device_interface, MIP_FUNCTION_SELECTOR_READ,
                   readback_angles) != MIP_INTERFACE_OK);

        cout << "Current sensor-to-vehicle transformation:" << endl;
        printf("\tRoll:\t%.2f deg\n", RAD_TO_DEG(readback_angles[0]));
        printf("\tPitch:\t%.2f deg\n", RAD_TO_DEG(readback_angles[1]));
        printf("\tHeading:\t%.2f deg\n", RAD_TO_DEG(readback_angles[2]));

        cout << "Select a tare operation: " << endl << 
            "\t1) Reset tare to factory settings" << endl <<
            "\t2) Manually set sensor-to-vehicle transformation" << endl <<
            "\t3) Perform an automatic tare" << endl <<
            " > ";

        cin >> resp;
        if (!cin.fail()) {
            switch(resp) {
                case '1':
                    while (mip_filter_tare_orientation(&device_interface, MIP_FUNCTION_SELECTOR_LOAD_DEFAULT, 0) != MIP_INTERFACE_OK);
                    cout << "Tare set to factory defaults." << endl;
                    break;
                case '2':
                    {
                        float angles[3] = {0};
                        cout << "Input new ROLL (degrees):" << endl << " > ";
                        cin >> angles[0]; if (cin.fail()) { cout << "Invalid entry. Must input a float." << endl; break;}
                        cout << "Input new PITCH (degrees):" << endl << " > ";
                        cin >> angles[1]; if (cin.fail()) { cout << "Invalid entry. Must input a float." << endl; break;}
                        cout << "Input new HEADING (degrees):" << endl << " > ";
                        cin >> angles[2]; if (cin.fail()) { cout << "Invalid entry. Must input a float." << endl; break;}

                        angles[0] = DEG_TO_RAD(angles[0]);
                        angles[1] = DEG_TO_RAD(angles[1]);
                        angles[2] = DEG_TO_RAD(angles[2]);

                        while (mip_filter_sensor2vehicle_tranformation(&device_interface, MIP_FUNCTION_SELECTOR_WRITE,
                                angles) != MIP_INTERFACE_OK);

                        while (mip_filter_sensor2vehicle_tranformation(&device_interface, MIP_FUNCTION_SELECTOR_STORE_EEPROM,
                                angles) != MIP_INTERFACE_OK);

                        float readback_angles[3] = {0};
                        while (mip_filter_sensor2vehicle_tranformation(&device_interface, MIP_FUNCTION_SELECTOR_READ,
                                   readback_angles) != MIP_INTERFACE_OK);

                        cout << "Values saved to device." << endl << 
                            "New sensor-to-vehicle transformation:" << endl;
                        printf("\tRoll:\t%.2f deg\n", RAD_TO_DEG(readback_angles[0]));
                        printf("\tPitch:\t%.2f deg\n", RAD_TO_DEG(readback_angles[1]));
                        printf("\tHeading:\t%.2f deg\n", RAD_TO_DEG(readback_angles[2]));

                    }
                    break;

                case '3':
                    {
                        cout << "You can choose to tare any combination of the PITCH, ROLL, and YAW axes." << endl;
                        uint8_t tare_flags = 0;
                        cout << "Do you wish to tare the ROLL axis? [y/N] ";
                        cin >> resp; if (!cin.fail() && resp == 'y') tare_flags |= FILTER_TARE_ROLL_AXIS;
                        cout << "Do you wish to tare the PITCH axis? [y/N] ";
                        cin >> resp; if (!cin.fail() && resp == 'y') tare_flags |= FILTER_TARE_PITCH_AXIS;
                        cout << "Do you wish to tare the YAW (heading) axis? [y/N] ";
                        cin >> resp; if (!cin.fail() && resp == 'y') tare_flags |= FILTER_TARE_YAW_AXIS;
                       
                        long tarewaitsec = 5; 
                        cout << "Ready to perform tare. Put the vehicle in its \"0-state\" orientation." << endl <<
                            "Once taring begins, please keep the vehicle perfectly still for " << tarewaitsec << " seconds." << endl;
                        // cin >> resp;

                        cout << "Performing tare. Please wait..." << endl;

                        // Reinitialize the filter (required for tare operation)
                        float angles[3] = {0, 0, 0};
                        cout << "mip_filter_set_init_attitude" << endl;
                        int res1 = 1;
                        while (res1 != 0) {
                            res1 = mip_filter_set_init_attitude(&device_interface, angles);
                            cout << res1 << endl;
                        }
                        usleep(tarewaitsec * 1e6); // wait for filter to re-establish running state


                        cout << "mip_filter_tare_orientation" << endl;

                        int res2 = 1;
                        while (res2 != 0) {
                            res2 = mip_filter_tare_orientation(&device_interface, MIP_FUNCTION_SELECTOR_WRITE, tare_flags);
                            cout << res2 << endl;
                        }

                        cout << "Tare complete." << endl;

                        float readback_angles[3] = {0};
                        while (mip_filter_sensor2vehicle_tranformation(&device_interface, MIP_FUNCTION_SELECTOR_READ,
                                   readback_angles) != MIP_INTERFACE_OK);

                        cout << "Current sensor-to-vehicle transformation (tare results):" << endl;
                        printf("\tRoll:\t%.2f deg\n", RAD_TO_DEG(readback_angles[0]));
                        printf("\tPitch:\t%.2f deg\n", RAD_TO_DEG(readback_angles[1]));
                        printf("\tHeading:\t%.2f deg\n", RAD_TO_DEG(readback_angles[2]));

                        cout << "Do you wish to save this tare to EEPROM? [Y/n] ";
                        cin >> resp;
                        if (cin.fail() || resp != 'n') {
                            while (mip_filter_sensor2vehicle_tranformation(&device_interface, MIP_FUNCTION_SELECTOR_STORE_EEPROM,
                                    readback_angles) != MIP_INTERFACE_OK);
                            cout << "Saved." << endl;
                        }
                    }
                    break;

                default:
                    cout << "Option " << resp << " not recognized." << endl;
                    break;
            }
        }
    }

    return 0;
}

