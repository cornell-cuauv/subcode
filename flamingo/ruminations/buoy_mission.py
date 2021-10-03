initial_state = {'buoy_visible': EQ(True), 'buoy_centered': EQ(True), 'buoy_rammed': EQ(True)}

goal = {'buoy_rammed': EQ(True)}

actions = [
    Action(
        name='search',
        preconds={},
        invariants={},
        postconds={'buoy_visible': EQ(True)},
        func=...
    ),
    Action(
        name='center',
        preconds={'buoy_visible': EQ(True)},
        invariants={'buoy_visible': EQ(True)},
        postconds={'buoy_visible': EQ(True), 'buoy_centered': EQ(True)}
        func=...
    ),
    Acion(
        name='ram',
        preconds={'buoy_visible': EQ(True), 'buoy_centered': EQ(True)},
        invariants={'buoy_visible': EQ(True), 'buoy_centered': EQ(True)},
        postconds={'buoy_visivle': EQ(True), 'buoy_centered': EQ(True), 'buoy_rammed': EQ(True)}
        func=...
    )
]
