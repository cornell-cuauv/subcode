#pragma once

#include <auvlog/logger.h>
#include <lib/fmt.h>

#include <iostream>
#include <string>

enum class Log { info,
                 warn,
                 error };

#define LOG(logLevel, message)       \
    switch (logLevel) {              \
        case Log::info:              \
            auvlog_info(message);    \
            break;                   \
        case Log::warn:              \
            auvlog_warning(message); \
            break;                   \
        case Log::error:             \
            auvlog_error(message);   \
            break;                   \
    }

#define LOG_DEV(logLevel, device, port, message)                                    \
    switch (logLevel) {                                                             \
        case Log::info:                                                             \
            auvlog_info(fmt::format("device.{}@{} {}", device, port, message));     \
            break;                                                                  \
        case Log::warn:                                                             \
            auvlog_warning(fmt::format("device.{}@{} {}", device, port, message));  \
            break;                                                                  \
        case Log::error:                                                            \
            auvlog_error(fmt::format("device.{}@{} {}", device, port, message));    \
            break;                                                                  \
    }
