#!/usr/bin/env python3

from build import ninja_common

build = ninja_common.Build('auvlog')

build.install('auv-lr',   f='auvlog/reader.py')
build.install('auv-ld',   f='auvlog/daemon.py')
build.install('auv-log',  f='auvlog/logger.py')

build.build_shared('auvlog',
  [   
      'logger.cpp'
  ], auv_deps = ['fmt'], deps=['nanomsg']
)

build.build_c_cmd('auvlog-c-example', ['examples/example.c'], auv_deps = ['auvlog'])
build.build_cmd('auvlog-cpp-example', ['examples/example.cpp'], auv_deps = ['auvlog', 'fmt'])
# build.build_cmd('auvlog-example', ['example.cpp'], deps = ['nanomsg'], auv_deps = ['auvlog'])
