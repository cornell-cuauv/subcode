import shm

from action import Action

# State
buoy_visible = lambda: shm.red_buoy_results.heuristic_score.get() > 0.8
buoy_centered = lambda: abs(shm.red_buoy_results.center_x.get()) < 0.2 and abs(shm.red_buoy_results.center_y.get()) < 0.2
buoy_rammed = lambda: shm.mission_status.red_buoy_rammed.get()

state = [buoy_visible, buoy_centered, buoy_rammed]

# Goal
goal = buoy_rammed

# Actions
actions = [
    Action(
        name="search",
        preconditions=[],
        invariants=[],
        postconditions=[buoy_visible],
        function=framework.search.spin_search(goal=buoy_visible)
    ),
    Action(
        name="center",
        preconditions=[buoy_visible],
        invariants=[buoy_visible],
        postconditions=[buoy_centered],
        function=framework.targeting.forward_target(x=lambda: shm.red_buoy_results.center_x.get(), y=lambda: shm.red_buoy_results.center_y.get())
    ),
    Action(
        name="ram",
        preconditions=[buoy_centered],
        invariants=[buoy_centered],
        postconditions=[buoy_rammed],
        function=framework.combinators.sequential(framework.combinators.while(condition=lambda: shm.red_buoy_results.area.get() < 0.5, framework.movement.forward(0.1)), lambda: shm.mission_status.red_buoy_rammed.set(True))
    )
]
