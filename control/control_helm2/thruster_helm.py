#!/usr/bin/env python3

from helm_basis import *

import shm


def build_thruster_helm():
    thrusters = [name for name, typ in shm.motor_desires._fields]

    def highlight_shm_if(text, shm_group, shm_var):
        return StyledString.highlight_if(text, getattr(shm_group, shm_var).get())

    index = 0
    thruster_index_map = {}

    def get_index(name):
        nonlocal index
        index += 1
        thruster_index_map[name] = index
        return str(index) + ': ' + name

    def make_thruster_panel(thruster):
        return LineLambdaPanel([
            lambda: (
                highlight_shm_if('broken', shm.broken_thrusters, thruster)
                + ' / ' +
                highlight_shm_if('reversed', shm.reversed_thrusters, thruster)
            ),
            lambda: (
                'PWM: ' +
                str(getattr(shm.motor_desires, thruster).get())
            ),
        ], title=get_index(thruster))

    panels = Vbox(
        Hbox(
            LineLambdaPanel([
                lambda: (
                    StyledString.highlight_if(
                        'SK', shm.switches.soft_kill.get())
                    + ' ' +
                    StyledString.highlight_if(
                        'HK', shm.switches.hard_kill.get())
                    + ' ' +
                    StyledString.highlight_if(
                        'EN', shm.settings_control.enabled.get())
                ),
            ], title=None, height=3),
        ),
        Hbox(*map(make_thruster_panel, thrusters[:len(thrusters)//2])),
        Hbox(*map(make_thruster_panel, thrusters[len(thrusters)//2:])),
    )

    def soft_kill(killed):
        shm.switches.soft_kill.set(killed)

    def toggle_controller():
        shm.settings_control.enabled.set(
            not shm.settings_control.enabled.get())

    def toggle_reversed(thruster):
        var = getattr(shm.reversed_thrusters, thruster)
        var.set(not var.get())

    def toggle_broken(thruster):
        var = getattr(shm.broken_thrusters, thruster)
        var.set(not var.get())

    callbacks = {
        ' ': (lambda: soft_kill(True)),
        curses.KEY_F5: (lambda: soft_kill(False)),
        '|': toggle_controller,
    }

    modal_callbacks = {}

    # reversed
    modal_callbacks['default'] = {
        'B': lambda: 'broken',
        'b': lambda: 'broken',
    }

    # broken
    modal_callbacks['broken'] = {
        'R': lambda: 'default',
        'r': lambda: 'default',
    }

    def add_thruster_callbacks(thruster, index):
        modal_callbacks['default'][str(index)] = \
            lambda: toggle_reversed(thruster)
        modal_callbacks['broken'][str(index)] = \
            lambda: toggle_broken(thruster)

    for thruster, index in thruster_index_map.items():
        add_thruster_callbacks(thruster, index)

    print(modal_callbacks)

    return panels, callbacks, modal_callbacks


if __name__ == '__main__':
    start_helm(*build_thruster_helm())
