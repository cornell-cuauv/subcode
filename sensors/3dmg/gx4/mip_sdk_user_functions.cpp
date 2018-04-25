
#include "mip_sdk_user_functions.h"

#include <exception>

#include "../../serial/serial.h"

using namespace sensorserial;

char serial_port_prefix[32] = {0};

/*
 * 3DMG-GX4 User-Defined Serial Interface
 * Allows the API to communicate via serial using the same AUV
 * serial library that all other daemons use
 */

/////////////////////////////////////////////////////////////////////////////
//
//! @fn
//! u16 mip_sdk_port_open(void *port_handle, int port_num, int baudrate)
//
//! @section DESCRIPTION
//! Target-Specific communications port open.
//
//! @section DETAILS
//!
//! @param [out] void *port_handle - target-specific port handle pointer (user
//!                                          needs to allocate memory for this)
//! @param [in] int port_num       - port number (as recognized by the
//!                                                          operating system.)
//! @param [in] int baudrate       - baudrate of the com port.
//
//! @retval MIP_USER_FUNCTION_ERROR  When there is a problem opening the
//!                                                                     port.\n
//! @retval MIP_USER_FUNCTION_OK     The open was successful.\n
//
//! @section NOTES
//!
//! None
//!
//
/////////////////////////////////////////////////////////////////////////////

u16 mip_sdk_port_open(void **port_handle, int port_num, int baudrate)
{
    SerialPort *serial_port;
    char port_name[100] = {0};
    sprintf(port_name, "%s%d", serial_port_prefix, port_num);

    try {
        serial_port = new SerialPort(port_name, baudrate);
    } catch (std::exception &e) {
        fprintf(stderr, "Port %s not found\n", port_name);
        return MIP_USER_FUNCTION_ERROR;
    }
    *port_handle = serial_port;
    return MIP_USER_FUNCTION_OK;
}


/////////////////////////////////////////////////////////////////////////////
//
//! @fn
//! u16 mip_sdk_port_close(void *port_handle)
//
//! @section DESCRIPTION
//! Target-Specific port close function
//
//! @section DETAILS
//!
//! @param [in] void *port_handle - target-specific port handle pointer (user
//!                                          needs to allocate memory for this)
//
//! @retval MIP_USER_FUNCTION_ERROR  When there is a problem closing the
//!                                                                     port.\n
//! @retval MIP_USER_FUNCTION_OK     The close was successful.\n
//
//! @section NOTES
//!
//! None
//!
//
/////////////////////////////////////////////////////////////////////////////

u16 mip_sdk_port_close(void *port_handle)
{
    SerialPort* port = (SerialPort*) port_handle;
    if (port == NULL) return MIP_USER_FUNCTION_ERROR;
    delete port;
    return MIP_USER_FUNCTION_OK;
}


/////////////////////////////////////////////////////////////////////////////
//
//! @fn
//! u16 mip_sdk_port_write(void *port_handle, u8 *buffer, u32 num_bytes,
//!                                         u32 *bytes_written, u32 timeout_ms)
//
//! @section DESCRIPTION
//! Target-Specific Port Write Function.
//
//! @section DETAILS
//!
//! @param [in]  void *port_handle  - target-specific port handle pointer
//!                                    (user needs to allocate memory for this)
//! @param [in]  u8 *buffer         - buffer containing num_bytes of data
//! @param [in]  u32 num_bytes      - the number of bytes to write to the port
//! @param [out] u32 *bytes_written - the number of bytes actually written to
//!                                                                    the port
//! @param [in]  u32 timeout_ms     - the write timeout
//
//! @retval MIP_USER_FUNCTION_ERROR  When there is a problem communicating with
//!                                                                 the port.\n
//! @retval MIP_USER_FUNCTION_OK     The write was successful.\n
//
//! @section NOTES
//!
//! None
//!
//
/////////////////////////////////////////////////////////////////////////////

u16 mip_sdk_port_write(void *port_handle, u8 *buffer, u32 num_bytes,
                                            u32 *bytes_written, u32 timeout_ms)
{
    SerialPort* port = (SerialPort*) port_handle;
    if (port == NULL) return MIP_USER_FUNCTION_ERROR;
    *bytes_written = port->writeSer(buffer, num_bytes); // TODO: Need timeout?
    return MIP_USER_FUNCTION_OK;
}


/////////////////////////////////////////////////////////////////////////////
//
//! @fn
//! u16 mip_sdk_port_read(void *port_handle, u8 *buffer, u32 num_bytes,
//!                                            u32 *bytes_read, u32 timeout_ms)
//
//! @section DESCRIPTION
//! Target-Specific Port Write Function.
//
//! @section DETAILS
//!
//! @param [in]  void *port_handle  - target-specific port handle pointer
//!                                    (user needs to allocate memory for this)
//! @param [in]  u8 *buffer         - buffer containing num_bytes of data
//! @param [in]  u32 num_bytes      - the number of bytes to write to the port
//! @param [out] u32 *bytes_read    - the number of bytes actually read from
//!                                                                  the device
//! @param [in]  u32 timeout_ms     - the read timeout
//
//! @retval MIP_USER_FUNCTION_ERROR  When there is a problem communicating with
//!                                                                 the port.\n
//! @retval MIP_USER_FUNCTION_OK     The read was successful.\n
//
//! @section NOTES
//!
//! None
//!
//
/////////////////////////////////////////////////////////////////////////////

u16 mip_sdk_port_read(void *port_handle, u8 *buffer, u32 num_bytes,
                                               u32 *bytes_read, u32 timeout_ms)
{
    SerialPort* port = (SerialPort*) port_handle;
    if (port == NULL) return MIP_USER_FUNCTION_ERROR;
    int nread = port->readnWithTimeout(buffer, num_bytes, timeout_ms * 1000);
    if (nread < 0) return MIP_USER_FUNCTION_ERROR; // Timeout or port error
    *bytes_read = nread;
    return MIP_USER_FUNCTION_OK;
}


/////////////////////////////////////////////////////////////////////////////
//
//! @fn
//! u32 mip_sdk_port_read_count(void *port_handle)
//
//! @section DESCRIPTION
//! Target-Specific Function to Get the Number of Bytes Waiting on the Port.
//
//! @section DETAILS
//!
//! @param [in]  void *port_handle  - target-specific port handle pointer
//                                     (user needs to allocate memory for this)
//
//! @returns  Number of bytes waiting on the port,\n
//!           0, if there is an error.
//
//! @section NOTES
//!
//! None
//!
//
/////////////////////////////////////////////////////////////////////////////

u32 mip_sdk_port_read_count(void *port_handle)
{
    SerialPort* port = (SerialPort*) port_handle;
    if (port == NULL) return 0;
    return port->getBytesWaiting();
}


/////////////////////////////////////////////////////////////////////////////
//
//! @fn
//! u32 mip_sdk_get_time_ms()
//
//! @section DESCRIPTION
//! Target-Specific Call to get the current time in milliseconds.
//
//! @section DETAILS
//!
//! @param [in]  void *port_handle  - target-specific port handle pointer
//                                     (user needs to allocate memory for this)
//
//! @returns  Current time in milliseconds.
//
//! @section NOTES
//!
//!   1) This value should not roll-over in short periods of time
//!                                                            (e.g. minutes)\n
//!   2) Most systems have a millisecond counter that rolls-over every 32
//!                                                                      bits\n
//!      (e.g. 49.71 days roll-over period, with 1 millisecond LSB)\n
//!   3) An absolute reference is not required since this function is\n
//!      used for relative time-outs.
//!
//
/////////////////////////////////////////////////////////////////////////////

u32 mip_sdk_get_time_ms()
{
    struct timespec ts;
    if(clock_gettime(CLOCK_MONOTONIC,&ts) != 0) {
        return -1;
    }
    return (u32)(ts.tv_sec* 1000ll + ((ts.tv_nsec / 1000000)));

}

