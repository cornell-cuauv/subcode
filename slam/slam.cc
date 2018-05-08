#include "slam_server.h"
#include "slam_filter.h"
#include <iostream>

int main(int argc, char** argv) {
    SlamFilter s{2};
    SlamServer server {&s};
    server.Listen();
    return 0;
}
