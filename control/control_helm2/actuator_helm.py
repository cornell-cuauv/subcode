#!/usr/bin/env python3

from helm_basis import *

import shm

BOX_WIDTH = 20
BOX_HEIGHT = 5


def build_actuator_helm():
    actuators = list(filter(lambda n: n.startswith('trigger_'),
                            [name for name, typ in shm.actuator_desires._fields]))
    actuators_tup = list(zip(actuators, range(len(actuators))))

    def highlight_shm_if(text, shm_group, shm_var):
        return StyledString.highlight_if(text, getattr(shm_group, shm_var).get())

    def index_to_key(i):
        return hex(i)[2:]

    def key_to_index(k):
        return int('0x' + k, 16)

    # 4x4 grid
    def make_actuator_panel(tup):
        (actuator, i) = tup
        return LineLambdaPanel([
            lambda: highlight_shm_if('active', shm.actuator_desires, actuator),
        ], title='{}: {}'.format(index_to_key(i), actuator), width=BOX_WIDTH)

    panels = Vbox(
        Hbox(LineLambdaPanel([
            lambda: (
                StyledString.highlight_if(
                    'SK', shm.switches.soft_kill.get())
                + ' ' +
                StyledString.highlight_if(
                    'HK', shm.switches.hard_kill.get())
                + ' ' +
                StyledString(
                    '[ACT]' if shm.connected_devices.actuators.get()
                    else '$<white,red>ACT$ (actuators not connected)')
            ),
        ], title=None, width=BOX_WIDTH * 4, height=3),
        ),
        *[
            Hbox(*map(make_actuator_panel,
                      actuators_tup[i*4:(i+1)*4]),
                 height=BOX_HEIGHT)
            for i in range(0, len(actuators)//4)
        ],
        Hbox(LineLambdaPanel([
            lambda: "Press {n} key to toggle actuator {n}. Press 'z' to disable all."
        ], title=None, width=BOX_WIDTH * 4, height=3))
    )

    def soft_kill(killed):
        shm.switches.soft_kill.set(killed)

    def toggle_active(name):
        var = getattr(shm.actuator_desires, name)
        var.set(not var.get())

    def disable_all():
        for actuator in actuators:
            var = getattr(shm.actuator_desires, actuator)
            var.set(False)

    callbacks = {
        ' ': (lambda: soft_kill(True)),
        curses.KEY_F5: (lambda: soft_kill(False)),
        '\\': (lambda: soft_kill(False)),
        'z': disable_all,
        'Z': disable_all,
    }

    # because python only does scoping at the level of functions
    def add_callback(i, name):
        callbacks[index_to_key(i)] = lambda: toggle_active(name)

    for (i, name) in enumerate(actuators):
        add_callback(i, name)

    modal_callbacks = {
        'default': {},
    }

    return panels, callbacks, modal_callbacks


if __name__ == '__main__':
    start_helm(*build_actuator_helm())
