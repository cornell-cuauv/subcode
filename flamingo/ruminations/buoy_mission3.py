buoys = ['red', 'yellow', 'green']

buoy_results = lambda buoy: getattr(shm, buoy + '_buoy_results')

heuristic_score = lambda buoy: buoy_results(buoy).heuristic_score.get()
center = lambda buoy: (buoy_results(buoy).center_x.get(), buoy_results(buoy).center.y)
area = lambda buoy: buoy_results(buoy).area.get()

evaluators = {
    'visible(buoy)': lambda buoy: heuristics_score(buoy) > 0.7,
    'centered(buoy)': lambda buoy: abs(center(buoy)[0]) < 0.05 and abs(center(buoy)[1]) < 0.05,
    'close(buoy)': lambda buoy: area(buoy) >= 10000
}

actions = [
    Action(
        name = 'search',
        param_sources = (buoys),
        postconds={'visible(buoy)': True},
        func = lambda buoy: Sequential(SearchFor(SwaySearch(), lambda: heuristic_score(buoy) > 0.7), Zero())
    ),
    Action(
        name = 'center',
        param_sources = (buoys),
        preconds = {'visible(buoy)': True},
        invariants = {'visible(buoy)': True},
        postconds = {'centered(buoy)': True},
        func = lambda buoy: ForwardTarget(point=center, target=(0, 0))
    ),
    Action(
        name = 'approach',
        param_sources = (buoys),
        preconds = {'centered(buoy)': True},
        invariants = {'centered(buoy)': True},
        postconds = {'centered(buoy)': True, 'close(buoy)': True},
        func = lambda buoy: Sequential(VelocityX(0.2), While(lambda: None, lambda: area(buoy) < 10000), Zero())
    )
    Action(
        name = 'ram',
        param_sources = (buoys),
        preconds = {'centered(buoy)': True, 'close(buoy)': True},
        invariants = {'centered(buoy)': True, 'close(buoy)': True},
        postconds = {'rammed(buoy)': True}
        func = lambda _: Sequential(VelocityX(0.4), Timer(2), VelocityX(-0.4), Timer(2), Zero())
    )
]
