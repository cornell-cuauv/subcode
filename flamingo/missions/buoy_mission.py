from flamingo.framework import *
from mission.framework.combinators import *
from mission.framework.search import *
from mission.framework.targeting import *

visible = Condition(shm.red_buoy_results.heuristic_score, GE(0.7), consistency=(20, 30))
centered_x = Condition(shm.red_buoy_results.center_x, TH(0, 0.1))
centered_y = Condition(shm.red_buoy_results.center_y, TH(0, 0.1))
near = Condition(shm.red_buoy_results.area, GE(10000))
rammed = Condition('buoy_rammed', EQ(True))

initial_state = {'buoy_rammed': False}
goal = [rammed]

search = Sequential(
    SearchFor(
        SwaySearch(1, 1),
        lambda: shm.red_buoy_results.heuristic_score.get() > 0.7
    ),
    Zero()
)
center = ForwardTarget(
    point=lambda: (
        shm.red_buoy_results.center_x.get(),
        shm.red_buoy_results.center_y.get()
    ),
    target=(0, 0)
)
approach = Sequential(
    VelocityX(0.2),
    While(
        lambda: NoOp(),
        lambda: shm.red_buoy_results.area.get() < 10000
    ),
    Zero()
)
ram = Sequential(
    VelocityX(0.4),
    Timer(2),
    VelocityX(-0.4),
    Timer(2),
    Zero()
)

actions = [
    Action(
        name='search',
        preconds=[],
        invariants=[],
        postconds=[visible],
        task=search
    ),
    Action(
        name='center',
        preconds=[visible],
        invariants=[visible],
        postconds=[centered_x, centered_y],
        task=center
    ),
    Action(
        name='approach',
        preconds=[centered_x, centered_y],
        invariants=[centered_x, centered_y],
        postconds=[centered_x, centered_y, near],
        task=approach
    ),
    Action(
        name='ram',
        preconds=[centered_x, centered_y, near],
        invariants=[],
        postconds=[rammed],
        task=ram
    ) 
]
