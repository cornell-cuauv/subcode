/////////////////////////////////////////////////////////////////////////////
//
//! @file    mip_sdk_user_functions.h
//! @author  Nathan Miller
//! @version 1.0
//
//! @description Target-Specific, User-Defined Functions Definitions
//
// External dependencies:
//
//
//
//! @copyright 2011 Microstrain.
//
//!@section CHANGES
//!
//
//!@section LICENSE
//!
//! THE PRESENT SOFTWARE WHICH IS FOR GUIDANCE ONLY AIMS AT PROVIDING
//! CUSTOMERS WITH CODING INFORMATION REGARDING THEIR PRODUCTS IN ORDER
//! FOR THEM TO SAVE TIME. AS A RESULT, MICROSTRAIN SHALL NOT BE HELD LIABLE
//! FOR ANY DIRECT, INDIRECT OR CONSEQUENTIAL DAMAGES WITH RESPECT TO ANY
//! CLAIMS ARISING FROM THE CONTENT OF SUCH SOFTWARE AND/OR THE USE MADE BY
//! CUSTOMERS OF THE CODING INFORMATION CONTAINED HEREIN IN CONNECTION WITH
//! THEIR PRODUCTS.
//
/////////////////////////////////////////////////////////////////////////////

#ifndef _MIP_SDK_USER_FUNCTIONS_H
#define _MIP_SDK_USER_FUNCTIONS_H

////////////////////////////////////////////////////////////////////////////////
//
//Include Files
//
////////////////////////////////////////////////////////////////////////////////

#include "SDK/Include/mip.h"
#include <time.h>
#include <unistd.h>

////////////////////////////////////////////////////////////////////////////////
//
// Defines
//
////////////////////////////////////////////////////////////////////////////////
//! @def

#define MIP_USER_FUNCTION_OK    0
#define MIP_USER_FUNCTION_ERROR 1


////////////////////////////////////////////////////////////////////////////////
//
// Function Prototypes
//
////////////////////////////////////////////////////////////////////////////////

extern char serial_port_prefix[32];

u16 mip_sdk_port_open(void **port_handle, int port_num, int baudrate);
u16 mip_sdk_port_close(void *port_handle);

u16 mip_sdk_port_write(void *port_handle, u8 *buffer, u32 num_bytes, u32 *bytes_written, u32 timeout_ms);
u16 mip_sdk_port_read(void *port_handle, u8 *buffer, u32 num_bytes, u32 *bytes_read, u32 timeout_ms);

u32 mip_sdk_port_read_count(void *port_handle);

u32 mip_sdk_get_time_ms();



#endif
