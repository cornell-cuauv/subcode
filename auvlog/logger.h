#pragma once

/* A simple logging system for C/C++ built for AUV. The framework supports:
 *  1. levels: debug, info, warning, error
 *  2. filtering: log levels below [auvlog_level] are not printed to stdout/stderr
 *      however, all log levels are sent to the central logging server.
 *
 * View examples/example.c or examples/example.cpp for examples.
 *  1. It is safe to #include "auvlog/logger.h" in every library C/C++ file
 *      you want to be able to log in.
 *  2. To initialize logging, call auvlog_init() in the main function that
 *      imports the library files.
 *
 * I apologize in advance for this messy code. This was necessary to have the
 * header file work for both C/C++ compilers.
 *
 * Contact Jeffrey Qian if this breaks. [Precondition] Jeffrey exists.
 */

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Logging levels. They are ordered from least important to most important.
 */
enum log_level {
    AUV_DEBUG = 0,
    AUV_INFO = 1,
    AUV_WARNING = 2,
    AUV_ERROR = 3,
};

/** Initializes the logging system. Put this at the start of every main function
 * in every binary you wish to have logging support in.
 *
 * @param ll is the minimum logging level. All logs auvlog_level with level ll
 * such that ll < auvlog_level are discarded.
 */
void auvlog_init(enum log_level ll);

/** Generate and logs the message for C programs. Follows a printf type signature.  * @param level log level
 * @param file file name
 * @param func function name
 * @param line_num line number in code where logging is happening
 * @param fmt format string
 *
 * msg format: [level: day:hour:sec][file.func@line_num]\t<msg>\n
 *
 * fmt is treated as a format-string and subsequent arguments are fed into
 * fmt creating msg (See 'man printf')
 */
void auvlog_c_raw(enum log_level level, const char* file, const char* func,
                  const int line_num, const char* fmt, ...);

//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
// THE FOLLOWING FUNCTIONS ARE ONLY DEFINED IF YOU COMPILE FOR C
//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

#ifndef __cplusplus
/* Please use the functions below to log.
 *
 * auvlog_[ll](message) - logs [message] at level [ll]
 * auvlog_[ll]f(message, ...) - formats [message] with subsequent aguments and
 *      logs the result at level [ll]
 */
#define auvlog_debug(message) \
    auvlog_c_raw(AUV_DEBUG, __FILE__, __func__, __LINE__, message, 0);
#define auvlog_debugf(message, ...) \
    auvlog_c_raw(AUV_DEBUG, __FILE__, __func__, __LINE__, message, __VA_ARGS__);
#define auvlog_info(message) \
    auvlog_c_raw(AUV_INFO, __FILE__, __func__, __LINE__, message, 0);
#define auvlog_infof(message, ...) \
    auvlog_c_raw(AUV_INFO, __FILE__, __func__, __LINE__, message, __VA_ARGS__);
#define auvlog_warning(message) \
    auvlog_c_raw(AUV_WARNING, __FILE__, __func__, __LINE__, message, 0);
#define auvlog_warningf(message, ...) \
    auvlog_c_raw(AUV_WARNING, __FILE__, __func__, __LINE__, message, __VA_ARGS__);
#define auvlog_error(message) \
    auvlog_c_raw(AUV_ERROR, __FILE__, __func__, __LINE__, message, 0);
#define auvlog_errorf(message, ...) \
    auvlog_c_raw(AUV_ERROR, __FILE__, __func__, __LINE__, message, __VA_ARGS__);
#endif

#ifdef __cplusplus
}
//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
// THE FOLLOWING FUNCTIONS ARE ONLY DEFINED IF YOU COMPILE FOR CPP
//!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#include <string>
using std::string;
/** Generate and logs the message for Cpp
 * @param level log level
 * @param file file name
 * @param func function name
 * @param line_num line number in code where logging is happening
 * @param msg string
 *
 * msg format: [level: day:hour:sec][file.func@line_num]\t<msg>\n
 *
 * You should use #include<lib/fmt.h> and use format strings to
 * build your msg that you want to log.
 */
void auvlog_raw(enum log_level level, const char* file, const char* func,
                const int line_num, const string msg);

// auvlog_[ll](message) - logs [message] at level [ll]
#define auvlog_debug(message) \
    auvlog_raw(AUV_DEBUG, __FILE__, __func__, __LINE__, message);
#define auvlog_info(message) \
    auvlog_raw(AUV_INFO, __FILE__, __func__, __LINE__, message);
#define auvlog_warning(message) \
    auvlog_raw(AUV_WARNING, __FILE__, __func__, __LINE__, message);
#define auvlog_error(message) \
    auvlog_raw(AUV_ERROR, __FILE__, __func__, __LINE__, message);
#endif
