#!/usr/bin/env python3

from build import ninja_common
build = ninja_common.Build('hydrocode')
build.build_cmd('auv-hydromathd', ['hydromathd.cpp', 'udp_receiver.cpp', 'udp_sender.cpp', 'pinger_tracking.cpp', 'comms.cpp', 'common_dsp.cpp'],
                auv_deps=['shm'], deps=['liquid'])

build.install('auv-hydro-heading', 'hydrocode/scripts/heading_plot.py')
build.install('auv-hydro-raw-plot', 'hydrocode/scripts/raw_plot.py')
build.install('auv-hydro-trigger-plot', 'hydrocode/scripts/trigger_plot.py')
build.install('auv-hydro-dft-plot', 'hydrocode/scripts/dft_plot.py')
build.install('auv-hydro-raw-comms-plot', 'hydrocode/scripts/raw_comms_plot.py')
