from flamingo.framework import GE, LE, TH, Action

from mission.framework.combinators import Sequential, While
from mission.framework.search import SearchFor, SwaySearch
from mission.framework.primitive import Zero, NoOp
from mission.framework.targeting import ForwardTarget
from mission.framework.movement import VelocityX
from mission.framework.timing import Timer

import shm
buoy = shm.red_buoy_results

visible = GE(buoy.heuristic_score, 0.7, consistency=(20, 30))
centered_x = TH(buoy.center_x, 0, 0.1)
centered_y = TH(buoy.center_y, 0, 0.1)
near = GE(buoy.area, 10000)
far = LE(buoy.area, 5000)
rammed = 'rammed'

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
back_off = Sequential(
    VelocityX(-0.2),
    While(
        lambda: NoOp(),
        lambda: shm.red_buoy_results.area.get() > 5000
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
        preconds=[visible, far],
        invariants=[visible],
        postconds=[visible, centered_x, centered_y],
        task=center
    ),
    Action(
        name='approach',
        preconds=[visible, centered_x, centered_y],
        invariants=[visible, centered_x, centered_y],
        postconds=[visible, centered_x, centered_y, near],
        task=approach
    ),
    Action(
        name='back_off',
        preconds=[visible],
        invariants=[visible],
        postconds=[visible, far],
        task=back_off
    ),
    Action(
        name='ram',
        preconds=[visible, centered_x, centered_y, near],
        invariants=[],
        postconds=[rammed],
        task=ram
    ) 
]
