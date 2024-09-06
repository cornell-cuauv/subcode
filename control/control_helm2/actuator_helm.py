#!/usr/bin/env python3

from helm_basis import *
from mission.framework.actuation import *
import asyncio

import shm

BOX_WIDTH = 24
BOX_HEIGHT = 6

def build_actuator_helm():
    actuators = actuator_list

    # 4x4 grid
    def make_actuator_panel(actuator):
        return LineLambdaPanel([
            lambda: StyledString(
                ("[ENABLED] " if actuator.get_on() else "DISABLED") + 
                ("  (") +
                (" [ENABLED]" if actuator.get_on_readback() else "DISABLED") +
                (")")
            ),
            lambda: f"pwm: {actuator.get_pwm():4.0f} ({actuator.get_pwm_readback():4.0f})",
            lambda: f"ang: {actuator.get_angle():4.0f} ({actuator.get_angle_readback():4.0f})"
        ], title=str(actuator), width=BOX_WIDTH, height = 6)

    panels = Vbox(
        Hbox(LineLambdaPanel([
            lambda: (
                StyledString.highlight_if(
                    'Soft Killed', shm.switches.soft_kill.get())
                + ' | ' +
                StyledString.highlight_if(
                    'Hard Killed', shm.switches.hard_kill.get())
                + ' | ' +
                StyledString(
                    'CONNECTED' if shm.connected_devices.actuators.get()
                    else '$<white,red>NOT CONNECTED$')
            ),
        ], title=None, width=BOX_WIDTH * 4, height=3),
        ),
        *[
            Hbox(*map(make_actuator_panel,
                      actuators[i*4:(i+1)*4]),
                 height=BOX_HEIGHT)
            for i in range(0, len(actuators)//4)
        ],
        Hbox(LineLambdaPanel([
            lambda: "        # --> Increase PWM & Enable Actuator",
            lambda: "SHIFT + # --> Decrease PWM & Enable Actuator",
            lambda: "        Z --> Disable ALL Actuators",
            lambda: "",
            lambda: "        T --> Fire Torpedo",
            lambda: "        D --> Fire Dropper",
            lambda: "        R --> Reset Torpedo Dropper",
            lambda: "",
            lambda: "       F5 --> Soft Kill Submarine",
            lambda: "        \\ --> Un-Soft Kill Submarine",
        ], title=None, width=BOX_WIDTH * 4, height=12)),

    )

    def soft_kill(killed):
        shm.switches.soft_kill.set(killed)

    def disable_all():
        for actuator in actuators:
            actuator.disable()
            
    def raise_pwm(actuator):
        if not actuator.get_on():
            actuator.enable()
        else:
            actuator.add_angle(10)
    
    def lower_pwm(actuator):
        if not actuator.get_on():
            actuator.enable()
        else:
            actuator.add_angle(-10)

    callbacks = {
        ' ': (lambda: soft_kill(True)),
        curses.KEY_F5: (lambda: soft_kill(False)),
        '\\': (lambda: soft_kill(False)),
        'z': disable_all,
        'Z': disable_all,
        't': lambda: asyncio.run(fire_torpedo()),
        'T': lambda: asyncio.run(fire_torpedo()),
        'd': lambda: asyncio.run(fire_dropper()),
        'D': lambda: asyncio.run(fire_dropper()),
        'r': lambda: asyncio.run(reset_torpedo_dropper()),
        'R': lambda: asyncio.run(reset_torpedo_dropper()),
    }
    
    # because python only does scoping at the level of functions
    capital_mapping = {
        '0': ')', '1': '!', '2': '@', '3': '#', 
        '4': '$', '5': '%', '6': '^', '7': '&', 
        '8': '*', '9': '(', 'a': 'A', 'b': 'B', 
        'c': 'C', 'd': 'D', 'e': 'E', 'f': 'F',
    }

    def add_callbacks(actuator):
        key = hex(actuator.id)[2:].lower()
        callbacks[key] = lambda: raise_pwm(actuator)
        
        if key in capital_mapping:
            cap = capital_mapping[key]
            callbacks[cap] = lambda: lower_pwm(actuator)

    # Smart Loops Mess This Up
    for actuator in actuators:
        add_callbacks(actuator)
        
    modal_callbacks = {
        'default': {},
    }

    return panels, callbacks, modal_callbacks


if __name__ == '__main__':
    start_helm(*build_actuator_helm())
