#!/usr/bin/env python3

from build import ninja_common
build = ninja_common.Build('hydrocode')

build.install('auv-pingerd', f='hydrocode/pingerd.py')

