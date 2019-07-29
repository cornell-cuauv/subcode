from mission.framework.combinators import Sequential, Conditional
from mission.framework.primitive import Succeed, Fail
from mission.framework.timing import Timeout, Timed

from mission.missions.vampire import GrabVampire, Search, CenterAny, which_visible, ReleaseVampire
from mission.missions.attilus_garbage import PositionMarkers, MoveNE
from mission.missions.crucifix import GrabCrucifix, SearchCrucifix

markers = PositionMarkers

STATES = ['first', 'second']
crucifix_state = 0

EDGE_RATIO = 0.1

def change_state(state):
    global crucifix_state
    crucifix_state = state
    return Succeed()

def non_crucifix_task():
    """Do non crucifix task first. If crucifix not found, do marker 2"""
    if crucifix_state == 2:
        return STATES[0]
    return STATES[1]

def crucifix_task():
    """Do non crucifix task second. If crucifix not found, do marker 1"""
    if crucifix_state == 2:
        return STATES[1]
    return STATES[0]

Recovery = lambda: Sequential(
    Timed(CenterAny(), 40),
    markers.set('first'),
    Conditional(Timeout(SearchCrucifix, 80), on_success=Sequential(markers.set('crucifix'), change_state(1)), on_fail=Succeed()),
    reflect(),
    markers.go_to('second'),
    Timed(CenterAny(), 40),
    markers.set('second'),
    Conditional(Timeout(SearchCrucifix, 80), on_success=Sequential(markers.set('crucifix'), change_state(2)), on_fail=Succeed()) if not crucifix_state else Succeed(),
    markers.go_to(non_crucifix_task()),
    GrabVampire(),
    ReleaseVampire(edge(non_crucifix_task())),
    markers.go_to(crucifix_task()),
    GrabVampire(),
    ReleaseVampire(edge(crucifix_task())),
)

def reflect():
    global markers
    point1 = markers.get('center')
    point2 = markers.get('first')
    if point1 is not None and point2 is not None:
        x = point1[0] - (point2[0] - point1[0])
        y = point1[1] - (point2[1] - point1[1])
        marker.set('second', (x, y))
        return Succeed()
    return Fail()

def edge(ed):
    global markers
    center = markers.get('center')
    vampire = markers.get(ed)
    return ((vampire[0] - center[0]) * EDGE_RATIO + vampire[0], (vampire[1] - center[1]) * EDGE_RATIO + vampire[1])
