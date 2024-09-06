#!/usr/bin/env python3

from build import ninja_common

build = ninja_common.Build('led')

build.install('auv-ledd', f = 'led/ledd.py')
