#!/usr/bin/env python3

from build import ninja_common

build = ninja_common.Build('serial/seriald')
build.build_cmd(
        'auv-seriald',
        [
            'main.cpp',
            'config.cpp',
            'device.cpp',
            'device_list.cpp',
            'sub_status.cpp',
        ],
        deps=['nanomsg'],
        auv_deps=['auvshm', 'auvlog', 'auv-serial', 'fmt'],)

build.install('auv-find-gxdvl', f='serial/seriald/util/find_dvl_gx.sh')
#build.test_gtest(
#        'seriald-new',
#        [
#            'config.cpp',
#            'device.cpp',
#            'device_list.cpp',
#            'sub_status.cpp',
#            # 'test/config/config.cpp',
#            # 'test/device/device.cpp',
#        ],
#        deps=['nanomsg', 'cppformat'],
#        auv_deps=['auvshm', 'auvlog', 'auv-serial'],)
