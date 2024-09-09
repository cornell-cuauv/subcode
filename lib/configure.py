#!/usr/bin/env python3

from build import ninja_common

build = ninja_common.Build("lib")

build.build_shared("json",
        [
            "jsoncpp.cpp",
        ],
        lflags=[])

build.build_shared("fmt",
        [
            "fmt/format.cc",
            "fmt/ostream.cc",
            "fmt/posix.cc",
        ],
        lflags=[])
