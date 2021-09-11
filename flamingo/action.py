class Action:
    def __init__(self, *, name, preconditions, invariants, postconditions, function):
        self.name = name
        self.preconditions = preconditions
        self.invariants = invariants
        self.postconditions = postconditions
        self.function = function
