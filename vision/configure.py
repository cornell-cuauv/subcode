#!/usr/bin/env python3
from build import ninja_common
build = ninja_common.Build('vision')

build.build_shared('camera_message_framework',
                   sources=[
                       'lib/camera_message_framework_c.cpp',
                       'lib/camera_message_framework.cpp',
                       'lib/filelock.cpp',
                   ],
                   auv_deps=['auvlog', 'fmt'],
                   cflags=['-Ivision/', '-Ilib'],
                   )

# Python capture sources
build.install('auv-webcam-camera', f='vision/capture_sources/generic_camera.py')
build.install('auv-video-camera', f='vision/capture_sources/video.py')
build.install('auv-camera-stream-server', f='vision/capture_sources/stream_server.py')
build.install('auv-camera-stream-client', f='vision/capture_sources/stream_client.py')
build.install('auv-flir-camera', f='vision/capture_sources/flir.py')
build.install('auv-zed-camera', f='vision/capture_sources/zed.py')


build.install('auv-yolo-shm', f='vision/misc/yolo_shm.py')
