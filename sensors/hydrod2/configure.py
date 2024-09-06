#!/usr/bin/env python3

from build import ninja_common
build = ninja_common.Build('sensors/hydrod2')

build.build_cmd('auv-hydrod-ui',
                ['hydro_ui.cpp'],
                auv_deps=['auvshm'],
                deps=['ncurses'])
