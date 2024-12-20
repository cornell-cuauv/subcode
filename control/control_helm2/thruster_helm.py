#!/usr/bin/env python3

import asyncio
from helm_basis import *

import shm
import shm.debug_name_thrusters
from control.thrusters import all_thrusters


# auv-thruster-helm: Easy controls for changing reversed/broken thruster status in SHM.
#
# TODO: perhaps integrate some other things:
#  - start thruster test directly from thruster helm?
#  - display which thruster board and ECE-side variable each thruster is connected to?
#      (see thruster mapper for how to do this)

BOX_WIDTH = 28
BOX_HEIGHT = 6

TEST_MODE = "run test"
REVERSED_MODE = "toggle reversed"
BROKEN_MODE = "toggle broken"

def disable_controller():
    """Disable the controller and every PID loop."""
    control = shm.settings_control
    control.enabled.set(0)
    control.heading_active.set(0)
    control.pitch_active.set(0)
    control.roll_active.set(0)
    control.velx_active.set(0)
    control.vely_active.set(0)
    control.depth_active.set(0)

def build_thruster_helm():
    thrusters = [thruster.name for thruster in all_thrusters]

    def highlight_shm_if(text, shm_group, shm_var):
        return StyledString.highlight_if(text, getattr(shm_group, shm_var).get())

    index = 0
    thruster_index_map = {}

    def get_index(name):
        nonlocal index
        index += 1
        thruster_index_map[name] = index
        debug_name = vars(shm.debug_name_thrusters)[name].get()
        return str(index) + ": " + debug_name

    def make_thruster_panel(thruster):
        return LineLambdaPanel(
            [
                lambda: highlight_shm_if("reversed", shm.reversed_thrusters, thruster),
                lambda: highlight_shm_if("broken", shm.broken_thrusters, thruster),
                lambda: ("PWM: " + str(getattr(shm.motor_desires, thruster).get())),
            ],
            title=get_index(thruster),
            width=BOX_WIDTH,
            height=6,
        )

    panels = Vbox(
        Hbox(
            LineLambdaPanel(
                [
                    lambda: (
                        StyledString.highlight_if("SK", shm.switches.soft_kill.get()) + " " + 
                        StyledString.highlight_if("HK", shm.switches.hard_kill.get()) + " " + 
                        StyledString.highlight_if(
                            "EN", shm.settings_control.enabled.get()
                        ) + 
                        " -- mode: " + 
                        StyledString.highlight_if(TEST_MODE, mode == TEST_MODE) + " {t} / " + 
                        StyledString.highlight_if(REVERSED_MODE, mode == REVERSED_MODE) + " {r} / " + 
                        StyledString.highlight_if(BROKEN_MODE, mode == BROKEN_MODE) + " {b}"
                    ),
                ],
                title=None,
                width=BOX_WIDTH * 4,
                height=3,
            ),
        ),
        Hbox(
            *map(make_thruster_panel, thrusters[: len(thrusters) // 2]),
            height=BOX_HEIGHT,
        ),
        Hbox(
            *map(make_thruster_panel, thrusters[len(thrusters) // 2 :]),
            height=BOX_HEIGHT,
        ),
        Hbox(
            LineLambdaPanel(
                [
                    lambda: StyledString(
                        "Press {{n}} key to [{}] status for thruster {{n}}".format(
                            mode
                        )
                    )
                ],
                title="Status",
                width=BOX_WIDTH * 4,
                height=4,
            )
        ),
        Hbox(
            LineLambdaPanel(
                [
                    lambda: f"Press <space> to soft kill.",
                    lambda: f"Press \\ to enable.",
                    lambda: f"Press {{w}} to write current reversal settings to the appropriate <vehicle>.toml file.",
                    lambda: f"trogdor restart controld3 to reset thruster reversals according to <vehicle>.toml file"
                ],
                title="Controls",
                width=BOX_WIDTH * 4,
                height=7,
            )
        ),
    )
    #############################
    #Functions used in callbacks#
    #############################

    def soft_kill(killed):
        shm.switches.soft_kill.set(killed)

    def toggle_controller():
        shm.settings_control.enabled.set(not shm.settings_control.enabled.get())

    async def toggle_reversed(thruster):
        var = getattr(shm.reversed_thrusters, thruster)
        var.set(not var.get())

    async def toggle_broken(thruster):
        var = getattr(shm.broken_thrusters, thruster)
        var.set(not var.get())

    async def run_test(thruster):
        disable_controller()

        thruster_rev = getattr(shm.reversed_thrusters, thruster)
        thruster_pwm = getattr(shm.motor_desires, thruster)

        test_pwm = 30

        pwms = list(range(0, test_pwm + 1))
        pwms += reversed(pwms)
        sleep = 0.5 / len(pwms)

        for pwm in pwms:
            wait = asyncio.sleep(sleep)
            if thruster_rev.get():
                thruster_pwm.set(-pwm)
            else:
                thruster_pwm.set(+pwm)
            await wait

        thruster_pwm.set(0)

    # (Nathaniel Navarro): Writes to appropriate <vehicle>.toml file based on environment variables after
    # asking for confirmation. Based on toml reading logic from ../../conf/vehicle.py
    # as of 2023-02-13
    def write_to_conf_file():
        import tomlkit  # modules are only ever loaded once
        import sys
        import os

        DIR = os.environ.get("CUAUV_SOFTWARE")
        if DIR is None:
            sys.stderr.write("vehicle.py: CUAUV_SOFTWARE must be set to the root of the software repository. Nothing was written\n")
            return

        VEHICLE = os.getenv("CUAUV_VEHICLE")
        VEHICLE_TYPE = os.getenv("CUAUV_VEHICLE_TYPE")

        if VEHICLE is None :
            sys.stderr.write("vehicle.py: CUAUV_VEHICLE must be set. Nothing was written\n")
            return
        if VEHICLE_TYPE is None or not VEHICLE_TYPE in ["mainsub", "minisub"]:
            sys.stderr.write("vehicle.py: CUAUV_VEHICLE_TYPE must be set to one of { mainsub, minisub }. Nothing was written. \n")
            return

        is_mainsub = VEHICLE_TYPE == "mainsub"
        is_minisub = VEHICLE_TYPE == "minisub"
        is_in_simulator = os.getenv("CUAUV_LOCALE") == "simulator"

        conf_toml = None
        file_path = os.path.join(DIR, "conf", f"{VEHICLE}.toml")
        try:
            with open(file_path) as f:
                conf_toml = tomlkit.parse(f.read())
        except FileNotFoundError:
            sys.stderr.write(f"Config file {VEHICLE}.toml was not found as {file_path}. Nothing was written.\n")
            return

        for thruster_name in thrusters:
            for i in range(len(conf_toml["thrusters"])):  # list of thrusters
                if conf_toml["thrusters"][i]["name"] == thruster_name:
                    shm_direction = bool(getattr(shm.reversed_thrusters, thruster_name).get())
                    conf_toml["thrusters"][i]["reversed"] = shm_direction
                    shm_broken = bool(getattr(shm.broken_thrusters, thruster_name).get())
                    conf_toml["thrusters"][i]["broken"] = shm_broken


        with open(file_path, "w") as f:
            f.write(tomlkit.dumps(conf_toml))

    #################################
    #End functions used in callbacks#
    #################################

    #(Nathaniel Navarro): general callbacks not needing a number to be pressed to change things
    callbacks = {
        " ": (lambda: soft_kill(True)),
        curses.KEY_F5: (lambda: soft_kill(False)),
        "\\": (lambda: soft_kill(False)),
        "|": toggle_controller,
        curses.KEY_F12: toggle_controller,
        "w": write_to_conf_file,
    }

    modal_callbacks = {}

    # janky way to keep track of state
    # TODO: provide way to access current mode from helm_basis.py
    mode = TEST_MODE

    def change_mode(new_mode):
        nonlocal mode
        mode = new_mode
        return mode

    # testing
    modal_callbacks[TEST_MODE] = {
        "r": lambda: change_mode(REVERSED_MODE),
        "b": lambda: change_mode(BROKEN_MODE),
    }

    # another hacky thing
    modal_callbacks["default"] = modal_callbacks[TEST_MODE]

    # reversed
    modal_callbacks[REVERSED_MODE] = {
        "t": lambda: change_mode(TEST_MODE),
        "b": lambda: change_mode(BROKEN_MODE),
    }

    # broken
    modal_callbacks[BROKEN_MODE] = {
        "t": lambda: change_mode(TEST_MODE),
        "r": lambda: change_mode(REVERSED_MODE),
    }

    def add_thruster_callbacks(thruster, index):
        modal_callbacks["default"][str(index)] = lambda: asyncio.run(run_test(thruster))
        modal_callbacks[TEST_MODE][str(index)] = lambda: asyncio.run(run_test(thruster))
        modal_callbacks[REVERSED_MODE][str(index)] = lambda: asyncio.run(toggle_reversed(thruster))
        modal_callbacks[BROKEN_MODE][str(index)] = lambda: asyncio.run(toggle_broken(thruster))

    for thruster, index in thruster_index_map.items():
        add_thruster_callbacks(thruster, index)

    return panels, callbacks, modal_callbacks

if __name__ == "__main__":
    start_helm(*build_thruster_helm())
