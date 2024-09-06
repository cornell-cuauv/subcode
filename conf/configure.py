#!/usr/bin/env python3

from build import ninja_common

build = ninja_common.Build("conf")

# note: no dependency for toml because it is a header-only library
build.build_shared("conf",
        ["vehicle.cpp"],
        pkg_confs=["eigen3"],
        lflags=[],
        cflags=[])
# build.rust_build('rust_conf')
