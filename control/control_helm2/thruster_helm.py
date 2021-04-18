#!/usr/bin/env python3

from helm_basis import *

import shm

BOX_WIDTH = 24
BOX_HEIGHT = 8


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
        ], title=get_index(thruster), width=BOX_WIDTH)

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
                    + ' -- mode: ' +
                    StyledString.highlight_if(
                        'broken', not is_reversed)
                    + ' {b} / ' +
                    StyledString.highlight_if(
                        'reversed', is_reversed)
                    + ' {r}'
                ),
            ], title=None, width=BOX_WIDTH * 4, height=3),
        ),
        Hbox(*map(make_thruster_panel,
             thrusters[:len(thrusters)//2]),
             height=BOX_HEIGHT),
        Hbox(*map(make_thruster_panel,
             thrusters[len(thrusters)//2:]),
             height=BOX_HEIGHT),
        Hbox(LineLambdaPanel([
            lambda: StyledString(
                'Press {{n}} key to toggle [{}] status for thruster {{n}}'
                .format('reversed' if is_reversed else 'broken'))],
            title=None, width=BOX_WIDTH * 4, height=3))
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

    # janky way to keep track of state
    # TODO: provide way to access current mode from helm_basis.py
    is_reversed = True

    def change_mode(rev):
        nonlocal is_reversed
        is_reversed = rev
        return 'default' if rev else 'broken'

    # reversed
    modal_callbacks['default'] = {
        'B': lambda: change_mode(False),
        'b': lambda: change_mode(False),
    }

    # broken
    modal_callbacks['broken'] = {
        'R': lambda: change_mode(True),
        'r': lambda: change_mode(True),
    }

    def add_thruster_callbacks(thruster, index):
        modal_callbacks['default'][str(index)] = \
            lambda: toggle_reversed(thruster)
        modal_callbacks['broken'][str(index)] = \
            lambda: toggle_broken(thruster)

    for thruster, index in thruster_index_map.items():
        add_thruster_callbacks(thruster, index)

    return panels, callbacks, modal_callbacks


if __name__ == '__main__':
    start_helm(*build_thruster_helm())
