#!/usr/bin/env python3
from build import ninja_common
import os

build = ninja_common.Build('vision')

build.install('auv-poster', f='vision/modules/poster.py')

build.build_shared('auv-camera-message-framework',
                   ['lib/camera_message_framework.cpp'], deps=['pthread'], auv_deps=['utils'], cflags=['-Ivision/'])
build.build_shared('auv-color-balance', ['utils/color_correction/color_balance.cpp'],
                   pkg_confs=['opencv4'], auv_deps=['utils'], cflags=['-Ivision/'])
build.build_shared('auv-camera-filters',
                   ['lib/camera_filters.cpp'], pkg_confs=['opencv4'], auv_deps=['utils'], cflags=['-Ivision/'])

build.build_cmd('auv-firewire-daemon', ['lib/firewire_camera.cpp'], deps=[
                'dc1394'], auv_deps=['auv-camera-message-framework'], pkg_confs=['opencv4'], cflags=['-Ivision/'])

build.install('auv-start-cameras', f='vision/core/camera_manager.py')

build.install('auv-webcam-camera',
              f='vision/capture_sources/generic_video_capture.py')
build.install('auv-video-camera', f='vision/capture_sources/Video.py')

build.install('auv-camera-stream-server',
              f='vision/capture_sources/stream_server.py')
build.install('auv-camera-stream-client',
              f='vision/capture_sources/stream_client.py')

# Python capture sources
build.install('auv-zed-camera', f='vision/capture_sources/zed.py')

build.install('auv-yolo-shm', f='vision/misc/yolo_shm.py')

camera_apis = {
                "ueye.h": ("ueye", "UeyeCamera.cpp", "ueye_api"),
               }
for incl, (name, src, lib) in camera_apis.items():
    include_full_path = os.path.join("/usr/include", incl)
    if 'NIXOS' in os.environ or os.path.isfile(include_full_path):
        build.build_cmd("auv-%s-camera" % name,
                        ["capture_sources/camera_mainmaker.cpp", "capture_sources/%s" % src],
                        deps=[lib], pkg_confs=['opencv4'],
                        auv_deps=['utils', 'auv-camera-message-framework',
                                  'auv-camera-filters', 'auvshm'],
                                  cflags=['-Ivision/'])
    else:
        print("Could not build capture source for \"%s\" camera because you are missing \"%s\"." % (
            name, include_full_path))
