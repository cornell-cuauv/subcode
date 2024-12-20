#!/usr/bin/env python3

from build import ninja_common
build = ninja_common.Build('sensors')

build.build_shared('auvserial',
                ['serial/serial.cpp'])

# build.build_cmd('auv-podd',
#                ['power/podd/main.cpp'],
#                auv_deps=['auvserial', 'auvshm'])

# build.build_cmd('auv-hydrod-ui',
#                ['hydrod2/hydro_ui.cpp'],
#                auv_deps=['auvshm'],
#                deps=['ncurses'])

build.install('auv-linearizerd', 'sensors/linearizer/auv-linearizerd.py')
build.install('auv-kalmand', 'sensors/kalman/auv-kalmand.py')
build.install('auv-kalman3d', 'sensors/kalman3d/auv-kalman3d.py')
build.install('auv-zero-heading', 'sensors/kalman/set_zero_heading.py')
