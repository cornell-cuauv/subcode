#include "logger.h"

#include <lib/fmt.h>
#include <nanomsg/pubsub.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include <chrono>
#include <iostream>
#include <thread>

#include "json.hpp"
#include "nn.hpp"

using std::cerr;
using std::cout;
using std::endl;
using std::string;
using json = nlohmann::json;

enum log_level auvlog_level = AUV_WARNING;
nn::socket auvlog_sock(AF_SP, NN_PUB);

string level_to_string(enum log_level level) {
    string debug = "\033[0;37mDEBUG\033[0m";
    string info = "\033[0;36mINFO\033[0m";
    string warning = "\033[0;33mWARNING\033[0m";
    string error = "\033[0;31mERROR\033[0m";
    string arr[] = {debug, info, warning, error};
    return arr[level];
}

void auvlog_c_raw(enum log_level level, const char* file, const char* func,
                  const int line_num, const char* fmt, ...) {
    // fmt string
    char* ret;
    va_list args;
    va_start(args, fmt);

    // this is for logging, so failed allocation is not fatal
    if (0 > vasprintf(&ret, fmt, args)) ret = NULL;
    va_end(args);

    string msg;

    if (ret) {
        msg = string(ret);
    } else {
        fprintf(stderr, "Error while logging message: Memory allocation failed\n");
        msg = "";
    }
    free(ret);
    auvlog_raw(level, file, func, line_num, msg);
}

void auvlog_raw(enum log_level level, const char* file, const char* func,
                const int line_num, const string msg) {
    // grab time
    time_t rawtime;
    struct tm* timeinfo;
    time(&rawtime);
    timeinfo = localtime(&rawtime);

    // send everything to the server
    json e = {
        {"level", level},
        {"file", file},
        {"func", func},
        {"line_num", line_num},
        {"hour", timeinfo->tm_hour},
        {"min", timeinfo->tm_min},
        {"sec", timeinfo->tm_sec},
        {"msg", msg}};

    string serialized = e.dump();
    auvlog_sock.send(serialized.c_str(), serialized.size(), 0);

    // only print to stdout/stderr if the the log level is high enough
    if (level < auvlog_level) return;
    string final_msg = fmt::format("[{}: {}:{}:{}][{}.{}@{}]\t{}",
                                   level_to_string(level),
                                   timeinfo->tm_hour,
                                   timeinfo->tm_min,
                                   timeinfo->tm_sec,
                                   file,
                                   func,
                                   line_num,
                                   msg);

    if (level == AUV_ERROR) {
        cerr << final_msg << endl;
    } else {
        cout << final_msg << endl;
    }
}

void auvlog_init(enum log_level ll) {
    auvlog_level = ll;
    auvlog_sock.connect("tcp://127.0.0.1:7654");
    std::this_thread::sleep_for(std::chrono::milliseconds(400));
}
