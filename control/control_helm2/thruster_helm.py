#!/usr/bin/env python3

from helm_basis import *

import shm

# auv-thruster-helm: Easy controls for changing reversed/broken thruster status in SHM.
#
# TODO: perhaps integrate some other things:
#  - start thruster test directly from thruster helm?
#  - display which thruster board and ECE-side variable each thruster is connected to?
#      (see thruster mapper for how to do this)

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
        return str(index) + ": " + name

    def make_thruster_panel(thruster):
        return LineLambdaPanel(
            [
                lambda: highlight_shm_if("reversed", shm.reversed_thrusters, thruster),
                lambda: highlight_shm_if("broken", shm.broken_thrusters, thruster),
                lambda: highlight_shm_if("spinning", shm.motor_desires, thruster),
                lambda: ("PWM: " + str(getattr(shm.motor_desires, thruster).get())),
            ],
            title=get_index(thruster),
            width=BOX_WIDTH,
        )

    panels = Vbox(
        Hbox(
            LineLambdaPanel(
                [
                    lambda: (
                        StyledString.highlight_if("SK", shm.switches.soft_kill.get())
                        + " "
                        + StyledString.highlight_if("HK", shm.switches.hard_kill.get())
                        + " "
                        + StyledString.highlight_if(
                            "EN", shm.settings_control.enabled.get()
                        )
                        + " -- mode: "
                        + StyledString.highlight_if("reversed", mode == "reversed")
                        + " {r} / "
                        + StyledString.highlight_if("broken", mode == "broken")
                        + " {b} / "
                        + StyledString.highlight_if("spinning", mode == "spinning")
                        + " {s}"
                    ),
                ],
                title=None,
                width=BOX_WIDTH * 4,
                height=3,
            ),
        ),
        Hbox(
            *map(make_thruster_panel, thrusters[: len(thrusters) // 2]),
            height=BOX_HEIGHT
        ),
        Hbox(
            *map(make_thruster_panel, thrusters[len(thrusters) // 2 :]),
            height=BOX_HEIGHT
        ),
        Hbox(
            LineLambdaPanel(
                [
                    lambda: StyledString(
                        "Press {{n}} key to toggle [{}] status for thruster {{n}}".format(
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
                        lambda : f"Press {{w}} to write current reversal settings to the appropriate <vehicle>.toml file."], title="Controls", width = BOX_WIDTH * 4, height = 6))
    )

    def soft_kill(killed):
        shm.switches.soft_kill.set(killed)

    def toggle_controller():
        shm.settings_control.enabled.set(not shm.settings_control.enabled.get())

    def toggle_reversed(thruster):
        var = getattr(shm.reversed_thrusters, thruster)
        var.set(not var.get())

    def toggle_broken(thruster):
        var = getattr(shm.broken_thrusters, thruster)
        var.set(not var.get())

    def toggle_spinning(thruster):
        var = getattr(shm.motor_desires, thruster)
        var.set(0 if var.get() else 30)


    #(Nathaniel Navarro): Writes to appropriate <vehicle>.toml file based on environment variables after
    # asking for confirmation. Based on toml reading logic from ../../conf/vehicle.py
    # as of 2023-02-13
    def write_to_conf_file():
        import tomlkit #modules are only ever loaded once
        import sys
        import os

        DIR = os.environ.get("CUAUV_SOFTWARE")
        if DIR is None:
            sys.stderr.write("vehicle.py: CUAUV_SOFTWARE must be set "
                             "to the root of the software repository.\n")
            sys.exit(1)
        
        VEHICLE = os.getenv("CUAUV_VEHICLE")
        VEHICLE_TYPE = os.getenv("CUAUV_VEHICLE_TYPE")
        
        if VEHICLE is None or not VEHICLE in ["odysseus", "ajax"]:
            sys.stderr.write("vehicle.py: CUAUV_VEHICLE must be set "
                             "to one of { odysseus, ajax }.\n")
            sys.exit(1)
        if VEHICLE_TYPE is None or not VEHICLE_TYPE in ["mainsub", "minisub"]:
            sys.stderr.write("vehicle.py: CUAUV_VEHICLE_TYPE must be set "
                             "to one of { mainsub, minisub }.\n")
            sys.exit(1)
        
        is_mainsub = VEHICLE_TYPE == "mainsub"
        is_minisub = VEHICLE_TYPE == "minisub"
        is_in_simulator = os.getenv('CUAUV_LOCALE') == 'simulator'
        
        conf_toml = None
        file_path = os.path.join(DIR, "conf", f"{VEHICLE}.toml")
        with open(file_path) as f:
            conf_toml = tomlkit.parse(f.read())
        

        #(Nathaniel Navarro): Yuck yuck nested loops
        for thruster_name in thrusters:
            for i in range(len(conf_toml["thrusters"])): #list of thrusters
                if conf_toml["thrusters"][i]["name"] == thruster_name:
                    #print(getattr(shm.reversed_thrusters,thruster_name).get())
                    shm_direction = bool(getattr(shm.reversed_thrusters, thruster_name).get())
                    conf_toml["thrusters"][i]["reversed"] = shm_direction

        with open(file_path,"w") as f:
            f.write(tomlkit.dumps(conf_toml))



    callbacks = {
        " ": (lambda: soft_kill(True)),
        curses.KEY_F5: (lambda: soft_kill(False)),
        "\\": (lambda: soft_kill(False)),
        "|": toggle_controller,
        curses.KEY_F12: toggle_controller,
        "w": write_to_conf_file
    }

    modal_callbacks = {}

    # janky way to keep track of state
    # TODO: provide way to access current mode from helm_basis.py
    mode = "reversed"

    def change_mode(new_mode):
        nonlocal mode
        mode = new_mode
        return mode

    # reversed
    modal_callbacks["reversed"] = {
        "b": lambda: change_mode("broken"),
        "s": lambda: change_mode("spinning"),
    }
    # another hacky thing
    modal_callbacks["default"] = modal_callbacks["reversed"]

    # broken
    modal_callbacks["broken"] = {
        "r": lambda: change_mode("reversed"),
        "s": lambda: change_mode("spinning"),
    }

    # spinning
    modal_callbacks["spinning"] = {
        "b": lambda: change_mode("broken"),
        "r": lambda: change_mode("reversed"),
    }

    def add_thruster_callbacks(thruster, index):
        modal_callbacks["default"][str(index)] = lambda: toggle_reversed(thruster)
        modal_callbacks["broken"][str(index)] = lambda: toggle_broken(thruster)
        modal_callbacks["spinning"][str(index)] = lambda: toggle_spinning(thruster)

    for thruster, index in thruster_index_map.items():
        add_thruster_callbacks(thruster, index)

    return panels, callbacks, modal_callbacks


if __name__ == "__main__":
    start_helm(*build_thruster_helm())
