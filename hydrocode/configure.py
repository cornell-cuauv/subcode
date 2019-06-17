#!/usr/bin/env python3

from build import ninja_common
build = ninja_common.Build('hydrocode')
#build.install('libliquid.so', f='hydrocode/libliquid.so')
build.build_cmd('auv-hydromathd', ['hydromathd.cpp', 'udp_receiver.cpp', 'udp_sender.cpp', 'pinger_tracking.cpp'],
                auv_deps=['shm'], deps=['liquid'])

build.install('auv-hydro-heading', 'hydrocode/scripts/heading_plot.py')
build.install('auv-hydro-raw-plot', 'hydrocode/scripts/raw_plot.py')
build.install('auv-hydro-trigger-plot', 'hydrocode/scripts/trigger_plot.py')
build.install('auv-hydro-dft-plot', 'hydrocode/scripts/dft_plot.py')
