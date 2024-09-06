#!/usr/bin/env python3

from build import ninja_common
build = ninja_common.Build('sensors/3dmg/gx4')

build.build_shared('gx4sdk',
                ['SDK/Source/mip_sdk_system.c',
                 'SDK/Source/mip_sdk_base.c',
                 'SDK/Source/mip_sdk_ahrs.c',
                 'SDK/Source/mip.c',
                 'SDK/Source/mip_sdk_3dm.c',
                 'SDK/Source/ring_buffer.c',
                 'SDK/Source/mip_sdk_inteface.c',
                 'SDK/Source/mip_sdk_filter.c',
                 'SDK/Source/byteswap_utilities.c',
                 'mip_sdk_user_functions.cpp'],
                cflags=['-Isensors/3dmg/gx4/SDK/Include',
                        '-Isensors/3dmg/gx4/'],
                auv_deps=['auvserial']
                )

build.build_cmd('auv-3dmgx4d',
                ['main.cpp'],
                auv_deps=['auvshm', 'gx4sdk'],
                )

build.build_cmd('auv-3dmgx4-calibrate',
                ['calibrate.cpp'],
                auv_deps=['gx4sdk'])
