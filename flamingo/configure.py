#!/usr/bin/env python3

from build import ninja_common
build = ninja_common.Build('flamingo')

build.install('auv-flam', f='flamingo/runner.py')
