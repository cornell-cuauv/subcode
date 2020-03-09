#!/usr/bin/env python3

from build import ninja_common
build = ninja_common.Build('hydrocode')
build.build_cmd('auv-pingerd', ['pingerd/main.cpp', 'pingerd/pinger.cpp', 'pingerd/constants.cpp',
                                'common/udp_receiver.cpp', 'common/udp_sender.cpp'], auv_deps=['shm'],
                deps=['liquid'])

build.install('auv-pinger-raw-plot', 'hydrocode/pingerd/scripts/pinger_raw_plot.py')
build.install('auv-pinger-sense-plot', 'hydrocode/pingerd/scripts/pinger_sense_plot.py')
build.install('auv-pinger-trigger-plot', 'hydrocode/pingerd/scripts/pinger_trigger_plot.py')
build.install('auv-pinger-heading', 'hydrocode/pingerd/scripts/pinger_heading_plot.py')
