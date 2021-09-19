import shm

from action import Action
from flamingo import framework

# State
buoy_visible = lambda: shm.red_buoy_results.heuristic_score.get() > 0.8
buoy_centered = lambda: abs(shm.red_buoy_results.center_x.get()) < 0.2 and abs(shm.red_buoy_results.center_y.get()) < 0.2
buoy_rammed = lambda: shm.red_buoy_results.probability.get()

state = [buoy_visible, buoy_centered, buoy_rammed]

# Goal
goal = buoy_rammed

# Actions
def spin_search(goal):
    rotation = 0
    while not goal():
        framework.move_forward(rotation / 5)
        framework.rotate_right(5)
        rotation += 5

def forward_target(x, y):
    while abs(x) > 0.1 or abs(y) > 0.1:
        if x < -0.1:
            framework.move_right(0.5)
        elif x > 0.1:
            framework.move_left(0.5)
        elif y < -0.1:
            framework.move_up(0.5)
        elif y > 0.1:
            framework.move_down(0.5)

def ram():
    while shm.red_buoy_results.area.get() < 0.5:
        framework.move_forward(0.1)
    shm.red_buoy_results.probability.set(True)

actions = [
    Action(
        name="search",
        preconditions=[],
        invariants=[],
        postconditions=[buoy_visible],
        function=lambda: spin_search(buoy_visible)
    ),
    Action(
        name="center",
        preconditions=[buoy_visible],
        invariants=[buoy_visible],
        postconditions=[buoy_visible, buoy_centered],
        function=lambda: forward_target(shm.red_buoy_results.center_x.get(), shm.red_buoy_results.center_y.get())
    ),
    Action(
        name="ram",
        preconditions=[buoy_centered],
        invariants=[buoy_visible, buoy_centered],
        postconditions=[buoy_rammed],
        function=ram
    )
]
